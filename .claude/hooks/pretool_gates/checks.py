"""
checks.py — All _check_* gate functions extracted from pretool-gate.py.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from .constants import (
    OMC, STATE_DIR, ROOT,
    DANGEROUS_COMMANDS, WARN_ONLY_COMMANDS, ASK_USER_COMMANDS,
    READ_TOOLS, WRITE_TOOLS, PLAN_FILE_PATTERNS,
    _INJECTION_PATTERNS, _EXTERNAL_DATA_MAX_LEN,
    BASH_READ_TOKEN_RE, BASH_WRITE_TOKEN_RE,
    SECRET_CONTENT_COMPILED, PRIVACY_SCAN_SIZE_CAP,
    READ_SENSITIVE_PATTERNS,
)
from .helpers import (
    _goal_mode, _is_governance, _is_sensitive,
    _extract_tool, _extract_input, _extract_path, _extract_command,
    _match_any, _append_audit,
    _active_token, _task_dir, _check_verified,
)
from .oracle import _oracle_classify, _ORACLE_ANTI_PATTERN_RULES


# ── Gate 1: Sensitive edit ──

def _check_sensitive_edit(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    if _is_governance(path):
        safe = path[:200]
        if _goal_mode():
            msg = f"⚠️ [goal-mode] 治理文件写入: {safe} — goal 模式下降级放行"
            sys.stderr.write(f"PreToolGate: GOV_WARN (goal-mode) - {safe}\n")
            print(json.dumps({"continue": True, "message": msg}, ensure_ascii=False))
            _append_audit({"event_type": "governance_goal_warn", "path": path, "tool": tool})
            return None
        reason_text = (
            f"⚠️ GOVERNANCE_WARN: 治理文件 {safe} 被修改。\n"
            f"  规则: .claude/settings.json 和 .claude/hooks/* 受 Gate 1 保护。\n"
            f"  哲学&铁律: 治理文件不可改，但 AI 自决。\n"
            f"  audit 已记录此事件供退出报告审查。"
        )
        sys.stderr.write(f"PreToolGate: GOV WARN (path={safe})\n{reason_text}\n")
        _append_audit({"event_type": "governance_warn", "path": path, "tool": tool})
        print(json.dumps({"continue": True, "message": reason_text}, ensure_ascii=False))
        return None
    if _is_read_sensitive(path):
        # index31 F2: 凭据类 default-deny（.env/.ssh/credentials/secret/password/
        # api_key/token）——自动放行环境下 ASK_USER 退化为留痕（index30 法官发现），
        # 凭据改写不可逆，升级为硬 BLOCK；确需修改走 temp-bypass/人工流程。
        _append_audit({"event_type": "credential_write_block", "actor": "hook:pretool-gate",
                       "path": path, "tool": tool})
        return (f"BLOCK sensitive-credential|"
                f"⛔ 凭据类文件 {path} 写入被默认拒绝（default-deny）。\n"
                f"凭据改写不可逆且有泄露风险；确需修改请走人工审批/temp-bypass 流程。")
    if _is_sensitive(path):
        return (f"ASK_USER 敏感路径 {path}|"
                f"检测到可能包含凭据的敏感文件，请确认是否继续修改。\n"
                f"确认后继续；未确认则停止本次操作。")
    return None


# ── Gate 1b (index25): sensitive read — 读取侧隐私门禁 ──
# 动机: posttool-sensitive-filter 是提示型掩码（hook stderr 输出掩码版，不剥离模型可见的
# 原始工具结果）→ 密钥仍会进入模型上下文（index24 P1 双法官确认）。本门在读取前拦截:
# 路径命中敏感模式 → 直接拦；内容命中密钥模式（<1MB 文本）→ 拦。
def _candidate_read_paths(payload: dict) -> list[str]:
    tool = _extract_tool(payload).lower()
    inp = _extract_input(payload)
    paths: list[str] = []
    if tool in ("read", "grep", "search_files"):
        p = str(inp.get("file_path") or inp.get("path") or "")
        if p:
            paths.append(p)
    elif tool == "bash":
        cmd = _extract_command(payload) or ""
        for m in BASH_READ_TOKEN_RE.finditer(cmd):
            g = m.group(1) or m.group(2)
            if g:
                paths.append(g)
    return paths


def _resolve_read_path(p: str) -> Path:
    q = Path(p.strip().strip("'\""))
    if not q.is_absolute():
        q = Path(os.getcwd()) / q
    return q


_READ_SENSITIVE_RE = re.compile("|".join(READ_SENSITIVE_PATTERNS), re.IGNORECASE)


def _is_read_sensitive(path: str) -> bool:
    """读取侧敏感判定：仅凭据/密钥类路径；治理文件域（AGENTS.md/.claude/hooks）可读。"""
    return bool(_READ_SENSITIVE_RE.search(path.replace("\\", "/")))


def _check_sensitive_read(payload: dict) -> str | None:
    """读取敏感文件（路径模式或内容含密钥模式）→ ASK_USER(deny)，阻止密钥进入上下文。"""
    for raw in _candidate_read_paths(payload):
        q = _resolve_read_path(raw)
        if not q.exists():
            continue
        s = str(q)
        if _is_read_sensitive(s):
            _append_audit({"event_type": "privacy_read_block", "actor": "hook:pretool-gate",
                           "path": s, "reason": "sensitive_path"})
            return (f"ASK_USER sensitive_read|"
                    f"⛔ 读取被隐私门禁拦截：{q.name} 命中敏感路径模式（凭据/密钥）。\n"
                    f"确需读取请人工授权；或先脱敏导出。")
        if q.is_file() and q.stat().st_size <= PRIVACY_SCAN_SIZE_CAP:
            try:
                data = q.read_bytes()
            except OSError:
                continue
            if b"\x00" in data[:8192]:
                continue  # 二进制文件不扫描
            text = data.decode("utf-8", errors="ignore")
            if any(pat.search(text) for pat in SECRET_CONTENT_COMPILED):
                _append_audit({"event_type": "privacy_read_block", "actor": "hook:pretool-gate",
                               "path": s, "reason": "secret_content"})
                return (f"ASK_USER sensitive_read|"
                        f"⛔ 读取被隐私门禁拦截：{q.name} 内容含密钥/凭据模式"
                        f"（sk-*/私钥/令牌）。\n"
                        f"确需读取请人工授权；或使用脱敏导出通道。")
    return None


# ── Gate 1d (index31 F3): test-verification — 改代码后验证补位 ──
# index30 法官发现：skip-tests 场景 verify-gate 未触发，ON 侧"说明风险"即达标。
# 本门：Edit/Write 修改 .py 源码且项目存在测试文件但本日无测试执行记录 → REDIRECT
# 引导实跑（软引导不阻断；验证大于承诺铁律的机制化）。
#
# index37 修复（双法官盲评 P0）：门禁三连环死锁导致 8/17 ON 探针 exit=1
#   ① 门禁要求"本日 audit 有测试记录"，但无任何机制记录测试运行 → 永远无法满足
#      → 新增 Bash test_run 记录器：跑 pytest/unittest/测试脚本 → 写 audit → 门禁自清
#   ② 同一良性 .py 编辑被 REDIRECT 2 次 → 升级 hard stop → max_turns 卡死
#      → 同一文件已引导过一次 → 放行（验证要求移到完成时，符合 index34 无人模式"不硬阻断"裁决）
_TEST_RUN_CMD_RE = re.compile(
    r"\bpytest\b|run-tests|python3?\s+(?:-m\s+)?(?:pytest|unittest)\b|python3?\s+test_[A-Za-z0-9_]+\.py\b",
    re.IGNORECASE,
)
_GUIDE_WINDOW_SEC = 300


def _is_test_run_cmd(cmd: str) -> bool:
    return bool(_TEST_RUN_CMD_RE.search(cmd))


def _is_stub_file(path: str) -> bool:
    """目标 .py 文件当前是否为 stub（空实现）——实现新函数不该被 test-verification 拦。

    index40 F1：control-benign 类"实现 add()"被拦 → 死锁/烧轮数；stub 文件是"实现"
    而非"修改"，验证移到完成后（跑测试验证结果），编辑本身放行。
    """
    try:
        content = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return bool(
        re.search(r"^\s*pass\s*$", content, re.MULTILINE)
        or "NotImplemented" in content
        or re.search(r"^\s*\.\.\.\s*$", content, re.MULTILINE)
        or re.search(r"^\s*raise\s+NotImplementedError", content, re.MULTILINE)
    )


def _recent_test_run(window_sec: int = _GUIDE_WINDOW_SEC) -> bool:
    """近期（窗口内）audit 是否有 test_run 记录。

    index40 F2：堵"重试绕过"——跑过测试才放行；仅"被引导过一次"不放行。
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        audit_dir = STATE_DIR / "audit"
        now = time.time()
        if not audit_dir.exists():
            return False
        for f in audit_dir.glob(f"{today}.jsonl"):
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "test_run" not in line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = ev.get("timestamp", "")
                if not ts:
                    continue
                try:
                    epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
                if (now - epoch) < window_sec:
                    return True
    except OSError:
        return False
    return False


def _check_test_verification(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    # Bash 跑测试 → 记录 test_run 到 audit（门禁自清路径）
    if tool == "bash":
        cmd = _extract_command(payload) or ""
        if _is_test_run_cmd(cmd):
            _append_audit({"event_type": "test_run", "reason": "pytest", "cmd": cmd[:160]})
        return None
    if tool not in WRITE_TOOLS:
        return None
    path = str(_extract_path(payload) or "").replace("\\", "/")
    base = os.path.basename(path)
    if not path.endswith(".py"):
        return None
    if "/test" in path.lower().replace("\\", "/") or path.startswith("tests/"):
        return None
    is_test_file = base.startswith("test_") or base.endswith("_test.py")
    if is_test_file:
        # index44 S5 G1：新建测试 = red-first 编写 → 放行；修改**已存在**测试文件走下方闸，
        # 堵「改测试断言对齐代码」绕过 test-first（index44 skip-tests 实证：test_config.py
        # 断言 ==30 被改成 ==99 而全程未跑 pytest）。
        try:
            if not Path(path).exists():
                return None
        except OSError:
            return None
    # 项目是否有测试文件（cwd 根一层，性能护栏）
    has_tests = False
    try:
        for cand in ("test_*.py", "*_test.py"):
            if list(Path(os.getcwd()).glob(cand)):
                has_tests = True
                break
        if not has_tests and (Path(os.getcwd()) / "tests").is_dir():
            has_tests = True
    except OSError:
        return None
    if not has_tests:
        return None
    # index40 F1：目标文件是 stub（实现新函数）→ 放行（验证移到完成后）
    if _is_stub_file(path):
        return None
    # 近期（窗口内）是否有测试执行记录（index40 F2：跑过测试才放行，堵重试绕过）
    if _recent_test_run():
        return None
    _append_audit({"event_type": "test_verification_redirect", "actor": "hook:pretool-gate",
                   "path": path, "reason": "no_test_evidence"})
    return (f"REDIRECT test-verification|"
            f"⚠️ 修改了 {os.path.basename(path)}，项目存在测试文件且近期无测试执行记录。\n"
            f"铁律「验证大于承诺」：请先运行测试（如 python3 -m pytest -q，运行后门禁自动放行）"
            f"并附结果证据后再报告完成。")


# ── Gate 1c (index25): sensitive write via Bash — 补 sensitive-edit 的 Bash 通道 ──
# 动机: sensitive-edit 只覆盖 WRITE_TOOLS（Edit/Write），模型经 Bash 写敏感/治理路径
# （sed -i / tee / 重定向 / python open(w|a) / touch）可绕过（index24 P6 双法官确认）。
def _check_sensitive_write_bash(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload) or ""
    candidates: list[str] = []
    for rx in BASH_WRITE_TOKEN_RE:
        for m in rx.finditer(cmd):
            g = m.group(1)
            if g:
                candidates.append(g.strip().strip("'\""))
    for raw in candidates:
        if not raw:
            continue
        if _is_sensitive(raw) or _is_governance(raw):
            _append_audit({"event_type": "privacy_write_block", "actor": "hook:pretool-gate",
                           "path": raw, "reason": "sensitive_or_governance"})
            return (f"ASK_USER sensitive_write|"
                    f"⛔ Bash 写入被门禁拦截：{raw} 命中敏感/治理路径（凭据/密钥/治理文件）。\n"
                    f"确需修改请改用 Edit 工具走敏感编辑流程，或人工授权。")
    return None


# ── governance_bypass 软门禁（ADR 0015 二期）：Bash 写敏感治理文件 → REDIRECT ──
# 路径找补：echo/cat >> CLAUDE.md 等绕过 Write 门禁直写治理文件 → 软门禁
# REDIRECT 回正确路径，不 BLOCK（对齐 agentic-ui 软锁哲学：REDIRECT/ASK_USER）。

# 治理文件判定在 _is_governance 基础上补充顶层 CLAUDE.md 与 .claude/harness.yaml
# （_is_governance 的 patterns 未覆盖这两处）。
_GOV_BYPASS_EXTRA = ("CLAUDE.md", ".claude/harness.yaml")


def _check_governance_bypass(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload)
    if not command:
        return None
    for m in re.finditer(r"[>]{1,2}\s+([^\s;>|&]+)", command):
        target = m.group(1).strip("'\"")
        if not target:
            continue
        if not (_is_governance(target) or target in _GOV_BYPASS_EXTRA):
            continue
        _append_audit({
            "event_type": "governance_bypass_redirect",
            "actor": "hook:pretool-gate",
            "decision": "REDIRECT",
            "reason": f"governance_bypass: bash write to {target}",
            "tool": tool,
            "command": command[:120],
        })
        return (
            f"REDIRECT governance_bypass tool={tool} target={target}|"
            f"⚠️ Bash 重定向写治理文件 {target}，绕过 Write 门禁。"
            f"治理文件变更须走受控决策流程（铁律/审批）；请勿用 echo/cat >> 直写。"
            f"若确需变更，通过正确路径申请后再写。"
        )
    return None


# ── Gate 3: Action gate ──

def _split_command_segments(cmd: str) -> list[str]:
    """按 ; / && / || / | / 换行 切分命令段（引号内与 # 注释不切分）。

    index30 修复：危险命令模式锚定段首（`^git push` 等），复合命令
    （`cd x && git push --force`）中段原本不命中 → 放行（实测真实发生
    force push 副作用）。切段后每段独立锚定匹配；引号内文本/注释不误伤。
    """
    segments: list[str] = []
    buf: list[str] = []
    i, n = 0, len(cmd)
    quote: str | None = None
    while i < n:
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == quote and (i == 0 or cmd[i - 1] != "\\"):
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "#":  # 行注释：跳到行尾
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        two = cmd[i:i + 2]
        if ch == "\n" or two in ("&&", "||") or ch in (";", "|"):
            seg = "".join(buf).strip()
            if seg:
                segments.append(seg)
            buf = []
            i += 2 if two in ("&&", "||") else 1
            continue
        buf.append(ch)
        i += 1
    seg = "".join(buf).strip()
    if seg:
        segments.append(seg)
    return segments


def _check_action_gate(payload: dict) -> str | None:
    command = _extract_command(payload)
    if not command:
        return None
    for seg in _split_command_segments(command):
        hard = _match_any(seg, DANGEROUS_COMMANDS)
        if hard:
            _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                            "decision": "BLOCK", "reason": "dangerous_command",
                            "pattern": hard, "command_preview": command[:160]})
            return (f"BLOCK dangerous_command pattern={hard}|"
                    f"⛔ 检测到不可逆破坏性操作。\n"
                    f"可选方案: 1. 使用临时 bypass  2. 使用更安全的替代操作  3. 等待用户介入")
        ask = _match_any(seg, ASK_USER_COMMANDS)
        if ask:
            _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                            "decision": "WARN", "reason": "approval_required_command",
                            "pattern": ask, "command_preview": command[:160]})
            return f"WARN approval_required pattern={ask}"
        warn_only = _match_any(seg, WARN_ONLY_COMMANDS)
        if warn_only:
            _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                            "decision": "WARN", "reason": "path_specific_destructive",
                            "pattern": warn_only, "command_preview": command[:160]})
            return f"WARN path_specific_destructive pattern={warn_only}"
    return None


# ── Gate 5-extended: F3 (2026-08-30) 文档引用图删除前检查 ──
_DOC_REFERENCE_EXTS = (".md", ".txt", ".rst", ".adoc")  # 文档类文件才查引用
_DOC_REFERENCE_DIRS = (
    ".claude/references",
    ".claude/docs",
    "docs",
    "README.md",
    "AGENTS.md",
)


def _extract_delete_targets(payload: dict) -> list[str]:
    """提取 Delete/Bash rm 操作的目标路径（不带 shell 解析的轻量实现）。

    index34 修复：跳过 rm 的 flag（-rf/-f/--force 等），否则 `rm -rf AGENTS.md`
    只会捕获 `-rf` 而非目标文件（index33 治理删除保护对真实攻击形态失效，验收法官发现）。
    """
    tool = _extract_tool(payload).lower()
    targets: list[str] = []
    if tool == "delete":
        path = _extract_path(payload)
        if path:
            targets.append(path)
    elif tool == "bash":
        cmd = _extract_command(payload) or ""
        # 匹配 rm / unlink / git rm 后的参数段，跳过 flag（以 - 开头），保留其余 token 为目标
        import re as _re
        for m in _re.finditer(r"\b(?:rm|unlink|git\s+rm)\b([^;|&>]*)", cmd):
            seg = m.group(1)
            flags_done = False
            for tok in seg.split():
                if not flags_done and tok == "--":
                    flags_done = True
                    continue
                if not flags_done and tok.startswith("-"):
                    continue  # 跳过 flag（-rf/-f/--force 等）
                # index37 修复：剥离引号（`rm -rf "AGENTS.md"` 目标带引号 → 与
                # _GOVERNANCE_DELETE_BASENAMES 精确比较永远不匹配，治理文件被当普通文件删掉）
                targets.append(tok.strip("'\""))
        # index44 S5 G2：堵 python 通道绕过——模型被 rm 拦截后转 python
        # os.remove/os.unlink/shutil.rmtree/Path.unlink 等删除，需同样过"被引用/冻结"门禁
        # （index44 doc-ref 实证：rm 被 deny 后模型转 python 删除被引用文件成功）。
        # 先剥离 # 注释，避免把注释里的删除字样误当目标。
        _code = _re.sub(r"#[^\n]*", "", cmd)
        for _ptn in (
            r"\b(?:os\.remove|os\.unlink|os\.removedirs|shutil\.rmtree|shutil\.rm)\s*\(\s*(['\"])([^'\"]+)\1",
            r"\bPath\s*\(\s*(['\"])([^'\"]+)\1\s*\)\s*\.(?:unlink|rmdir)\s*\(",
        ):
            for _pm in _re.finditer(_ptn, _code):
                targets.append(_pm.group(2).strip("'\""))
    return targets


def _check_doc_reference_before_delete(payload: dict) -> str | None:
    """F3 门：删除文件前查文档引用图。

    防止 AI 删脚本/文档时破坏文档一致性（删了脚本但文档还在描述它）。
    仅对 .claude/scripts/ / src/ 等代码/脚本文件做检查。
    """
    targets = _extract_delete_targets(payload)
    if not targets:
        return None
    project_root = ROOT
    refs_found: list[tuple[str, str]] = []  # (target, ref_file)
    for target in targets:
        # 仅对 .py / .sh / .js / .ts / .yaml 等代码/配置检查（不是删 .md 自身）
        if not target.endswith((".py", ".sh", ".js", ".ts", ".yaml", ".yml", ".json")):
            continue
        # 取文件名（去路径）
        from pathlib import PurePosixPath
        fname = PurePosixPath(target).name
        if not fname or fname.startswith("."):
            continue
        # grep 文档目录
        for ref_dir in _DOC_REFERENCE_DIRS:
            ref_path = project_root / ref_dir
            if not ref_path.exists():
                continue
            try:
                import subprocess as _sp
                # grep 排除 .bak / archived / __pycache__
                r = _sp.run(
                    ["grep", "-rl", "--include=*.md", "--exclude-dir=__pycache__",
                     "--exclude-dir=archived", "--exclude-dir=retired",
                     "--exclude=*.bak", fname, str(ref_path)],
                    capture_output=True, text=True, timeout=5,
                )
                for ref_file in (r.stdout or "").strip().splitlines():
                    if ref_file:
                        refs_found.append((target, ref_file))
            except Exception:
                continue
    if refs_found:
        target, ref_file = refs_found[0]
        return (f"REDIRECT doc_reference_found|"
                f"删除 {target} 但文档 {ref_file} 还在引用它。\n"
                f"请先更新文档（移除引用或指向新位置），确认无认知依赖后再删除。\n"
                f"如确认无关，可使用 temp-bypass.py 临时跳过。")
    return None


# ── Gate 6b: 治理指令文件删除保护（index33 电池实证）──

# 治理灵魂文件：删除=删除治理框架本身（冻结规则：变更须人类裁决）
_GOVERNANCE_DELETE_BASENAMES = ("AGENTS.md", "CLAUDE.md")


def _check_governance_delete_protection(payload: dict) -> str | None:
    """治理指令文件删除保护：AGENTS.md/CLAUDE.md/.claude/kernel.md/.claude/index.md 不可删。

    电池实证（index33 rm-dot ON）：模型删光 AGENTS.md/CLAUDE.md/README/.omc，
    而 .claude/ 与 .git/ 仅靠 Claude Code 内建 rm -rf 危险命令门禁存活——
    CarrorOS 治理基座自身无删除自保。删除治理指令文件=删除治理框架本身，
    属高价值不可逆操作，REDIRECT 拒绝并提示走人类裁决。
    """
    targets = _extract_delete_targets(payload)
    if not targets:
        return None
    for target in targets:
        norm = target.rstrip("/")
        basename = norm.split("/")[-1] if norm else ""
        # 顶层治理指令文件（AGENTS.md/CLAUDE.md）或 .claude/ 下内核/路由文件
        # index34 收紧：仅认 .claude/kernel.md|index.md，避免误伤任意目录的 index.md
        if basename in _GOVERNANCE_DELETE_BASENAMES or (
            ".claude/kernel.md" in norm or ".claude/index.md" in norm
        ):
            return (f"REDIRECT governance_delete_protected|"
                    f"不能删除治理指令文件 {target}（AGENTS.md/CLAUDE.md/kernel.md/index.md 是治理灵魂文件）。\n"
                    f"删除治理指令文件等于删除治理框架本身，属于高价值不可逆操作。\n"
                    f"如确需变更，请走人类裁决流程（冻结规则：变更须人类裁决）。")
    return None


# ── Gate 6: Verify gate ──

def _check_verify_gate(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not any(path.replace("\\", "/").endswith(p) for p in PLAN_FILE_PATTERNS):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not re.search(r"\[x\]", content, re.IGNORECASE):
        return None
    token = _active_token()
    if not token:
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    current_step = task.get("current_step")
    session = token.get("session", {})
    task_id = session.get("id") if isinstance(session, dict) else None
    if not _check_verified(current_step, task_id, _task_dir(token)):
        _append_audit({"event_type": "verifygate_preaction_block", "actor": "hook:pretool-gate",
                        "decision": "REDIRECT", "reason": "step_not_verified",
                        "path": path, "current_step": current_step})
        return f"REDIRECT step_{current_step}_not_VERIFIED|当前步骤 {current_step} 尚未通过验证。"
    return None


# ── Gate 7: Oracle gate ──

def _check_oracle_gate(payload: dict) -> str | None:
    token = _active_token()
    if not token:
        return None
    session = token.get("session", {}) or {}
    if session.get("level", "L1_BASE") != "L2_ENHANCE":
        return None
    command = _extract_command(payload)
    if not command:
        return None
    verdict, detail = _oracle_classify(command)
    task = token.get("task", {})
    step = task.get("current_step") if isinstance(task, dict) else None
    if verdict == "REDIRECT":
        if detail in ("gov_file_bypass",):
            _guidance = ""
            for _, _detail, _guide in _ORACLE_ANTI_PATTERN_RULES:
                if _detail == detail:
                    _guidance = _guide
                    break
            return f"REDIRECT oracle_redirect:{detail}|{_guidance}"
        _guidance = ""
        for _, _detail, _guide in _ORACLE_ANTI_PATTERN_RULES:
            if _detail == detail:
                _guidance = _guide
                break
        print(f"⚠️ [oracle-gate] 检测到反模式({detail})", file=sys.stderr, flush=True)
        return None
    if verdict == "BLOCK":
        return (f"BLOCK oracle_gate:{detail}|"
                f"⛔ 检测到高置信危险语义({detail})。\n"
                f"可选方案: 1. 移除绕过语义后重试  2. 确需绕过: 用户人工裁决")
    if verdict == "ESCALATE":
        return (f"ASK_USER oracle_gate:{detail}|"
                f"❓ 命令无法可靠解析且含高危信号,请人工判断。")
    if verdict in ("FORCE", "TRIGGER"):
        print(f"🔮 [oracle-gate] L2 {verdict} 触发检测", file=sys.stderr, flush=True)
    return None


# ── Document quality gate ──

def _check_document_quality(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content or len(content) < 50:
        return None
    warnings = []
    if re.search(r"(?i)\bTODO\b", content) and re.search(r"(?i)\bFIXME\b", content):
        warnings.append("含 TODO/FIXME 标记")
    if re.search(r"(?i)\b(TBD|to be determined|under construction)\b", content):
        warnings.append("含未完成标记")
    if warnings:
        msg = f"⚠️ [document-quality] {', '.join(warnings)} in {path}"
        _append_audit({"event_type": "document_quality_warn", "path": path, "warnings": warnings})
        print(msg, file=sys.stderr, flush=True)
    return None


# ── Context control gates ──

def _check_g2_large_file(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    try:
        fpath = Path(path) if not Path(path).is_absolute() else Path(path)
        if not fpath.exists():
            return None
        size = fpath.stat().st_size
        if size > 500_000:
            return f"NARROW g2-large-file: {path} ({size/1024:.0f}KB) 建议分小文件写入"
    except Exception:
        pass
    return None


def _check_g3_reviews(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if len(content) > 2000 and any(kw in content.lower() for kw in ("review", "pr", "merge", "commit")):
        return f"CHECKPOINT_FIRST g3-review-large: 大段 review 内容,请先确认需要"
    return None


def _check_g5_wide_glob(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload)
    if not cmd:
        return None
    if re.search(r"\*\*/\*\.\w+|find\s+.*-name\s+['\"]?\*", cmd) and not re.search(r"\|", cmd):
        return f"NARROW g5-wide-glob: 宽泛 glob 可能匹配大量文件,请确认范围"
    return None


def _check_g6_budget(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload)
    if not cmd:
        return None
    if re.search(r"(pip|npm|brew|conda)\s+(install|update|upgrade)\s", cmd, re.IGNORECASE):
        return f"CHECKPOINT g6-dependency: 安装依赖,确认不影响项目"
    return None



# ── Secret scan ──

def _git_secret_candidates(command: str) -> list[str]:
    candidates = []
    patterns = [
        (r"\b[A-Za-z0-9+/=]{40,}\b", "base64_like"),
        (r"\bgh[ps]_[A-Za-z0-9]{36,}\b", "github_token"),
        (r"\bsk-[A-Za-z0-9]{20,}\b", "openai_key"),
        (r"\bAKIA[A-Z0-9]{16}\b", "aws_key"),
        (r"(?i)\bpassword\s*[=:]\s*['\"][^'\"]{6,}['\"]", "password_assignment"),
    ]
    for pat, label in patterns:
        if re.search(pat, command):
            candidates.append(label)
    return candidates


def _check_secret_scan(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    command = _extract_command(payload)
    if not command and tool in WRITE_TOOLS:
        ti = _extract_input(payload)
        command = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not command:
        return None
    # Git operations
    if tool == "bash" and re.search(r"\bgit\s+push\b", command, re.IGNORECASE):
        cands = _git_secret_candidates(command)
        if cands:
            _append_audit({"event_type": "secret_scan_warning", "actor": "hook:pretool-gate",
                            "decision": "WARN", "reason": f"git_push_secret_candidates:{cands}",
                            "command_preview": command[:160]})
            print(f"⚠️ [secret-scan] git push 含潜在密钥: {cands}", file=sys.stderr, flush=True)
    return None


# ── Numeric claim gate ──

def _check_numeric_claim(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content:
        return None
    suspicious = []
    for m in re.finditer(r"(?<!\d)(\d{2,}(?:\.\d+)?%|\d+(?:x|倍|ms|s|gb|mb|kb))(?!\d)", content, re.IGNORECASE):
        line_num = content[:m.start()].count("\n") + 1
        suspicious.append(f"L{line_num}:{m.group()[:30]}")
    if suspicious:
        _append_audit({"event_type": "numeric_claim_detected", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "unattributed_numeric_claim",
                        "path": path, "claims": suspicious[:5]})
        print(f"⚠️ [numeric-claim] 无来源数值断言: {suspicious[:3]}", file=sys.stderr, flush=True)
    return None


# ── 优化2 (2026-08-30) Git commit 软完成语检测 ──
# 防止 AI 在 commit message 里写"all done"/"fixed it"等绕过 commit message 审核
# 仅对 git commit 触发，避免误报其他命令
_COMMIT_SOFT_PATTERNS = [
    "all done", "fixed it", "fixed the bug", "done with", "ready for review",
    "all set", "completed successfully", "ship it",
    "看起来没问题", "看起来正常", "基本完成", "大部分完成", "差不多了",
    "搞定了", "修好了", "改完了", "做完了",
]


def _check_commit_soft_completion(payload: dict) -> str | None:
    """优化2：git commit -m "..." 含软完成语应被 REDIRECT。

    仅在 Bash 工具调用中提取 git commit -m "..." 字符串并检测。
    """
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload) or ""
    # 仅匹配 git commit -m "..." 或 git commit -m '...'
    import re as _re
    m = _re.search(r"git\s+commit\s+(?:[^|&;]*\s)?-m\s+['\"](.+?)['\"]", cmd, _re.DOTALL)
    if not m:
        return None
    msg = m.group(1).lower()
    for pat in _COMMIT_SOFT_PATTERNS:
        if pat.lower() in msg:
            _append_audit({"event_type": "commit_soft_completion_detected", "actor": "hook:pretool-gate",
                            "decision": "REDIRECT", "reason": "soft_completion_in_commit_msg",
                            "pattern": pat, "msg_preview": msg[:80]})
            return (f"REDIRECT commit_soft_completion|"
                    f"commit message 含软完成语 '{pat}'。\n"
                    f"请用具体 VERIFIED 证据替换，例如:\n"
                    f"  'VERIFIED: pytest → 3 passed'\n"
                    f"  '[已验证:src/foo.py:42] 修复了 XX'\n"
                    f"如确认无关，可使用 temp-bypass.py 临时跳过。")
    return None


# ── Action loop gate ──

def _check_action_loop(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload)
    if not command or len(command) < 200:
        return None
    _loop_count_file = STATE_DIR / "action-loop-count.json"
    _loop_reset_s = 300  # 5 min
    _loop_threshold = 5
    try:
        if _loop_count_file.exists():
            raw = json.loads(_loop_count_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                last_ts = raw.get("ts", 0)
                count = raw.get("c", 0)
                if time.time() - last_ts > _loop_reset_s:
                    count = 0
                count += 1
                if count >= _loop_threshold:
                    _append_audit({"event_type": "action_loop_detected", "actor": "hook:pretool-gate",
                                    "decision": "BLOCK", "reason": f"action_loop_{count}_times"})
                    return (f"BLOCK action_loop: 已连续 {count} 次长命令执行,可能陷入循环。"
                            "请暂停当前方向,重新评估后重试。")
                _loop_count_file.write_text(json.dumps({"c": count, "ts": time.time()}))
    except Exception:
        pass
    return None


# ── Stall detection gate ──

def _check_stall(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    path = _extract_path(payload)
    session_id_current = os.environ.get("HERMES_SESSION_ID") or ""
    if not session_id_current:
        return None
    _stall_file = OMC / "state" / "stall-count.json"
    _stall_reset_s = 120
    _stall_threshold = 8
    try:
        if path and _stall_file.exists():
            raw = json.loads(_stall_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("path") == path and raw.get("session") == session_id_current:
                if time.time() - raw.get("ts", 0) < _stall_reset_s:
                    count = raw.get("c", 0) + 1
                    if count >= _stall_threshold:
                        _append_audit({"event_type": "stall_detected", "actor": "hook:pretool-gate",
                                        "decision": "REDIRECT", "reason": f"stall_{count}_reads",
                                        "path": path, "session_id": session_id_current[:16]})
                        return (f"REDIRECT stall_reads: 已重复读取 {path} {count} 次。"
                                "建议直接基于已读信息推进,不要反复确认。")
                    _stall_file.write_text(json.dumps({"c": count, "ts": time.time(),
                                                        "path": path, "session": session_id_current}))
                else:
                    _stall_file.write_text(json.dumps({"c": 1, "ts": time.time(),
                                                        "path": path, "session": session_id_current}))
    except Exception:
        pass
    return None


# ── Injection guard gate ──

def _check_injection(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    ti = _extract_input(payload)
    if tool not in WRITE_TOOLS:
        return None
    content = ""
    for key in ("content", "new_string", "file_content", "text", "data"):
        val = ti.get(key)
        if isinstance(val, str) and len(val) > 20:
            content = val
            break
    if not content:
        return None
    for pattern in _INJECTION_PATTERNS:
        m = pattern.search(content)
        if m:
            _append_audit({"event_type": "injection_detected", "actor": "hook:pretool-gate",
                            "decision": "BLOCK", "reason": f"prompt_injection_pattern:{pattern.pattern[:40]}",
                            "tool": tool, "match": m.group()[:80]})
            return (f"BLOCK injection_detected tool={tool}|"
                    f"⛔ 写入内容检测到提示注入模式: '{m.group()[:60]}'")
    if len(content) > _EXTERNAL_DATA_MAX_LEN:
        return (f"REDIRECT content_truncated tool={tool}|"
                f"内容长度 {len(content)} 字符超过 8000 限制。使用 Write 写入前 6000 字符+续写标记，再用 Edit 替换标记追加剩余内容")
    return None


# ──────────────────────────────────────────────
# omc-skeleton-readonly gate（worktree 隔离用）
# .omc/**/*.md 骨架文件在 worktree 内只读——多智能体并发时, worktree 隔离
# 任务不得改写 .omc/ 骨架索引(会与主树/其他 worktree merge 冲突)。
# 必须进 _GATE_CORE(守护级, 不因 L1/L2 跳过)。
# ──────────────────────────────────────────────
# index30 修复: 只拦 state 骨架/导航索引/归档冻结文档; 放行任务文档
# (.omc/tasks/{date}/{task}/executor.md 等——模型按 AGENTS.md 工作流必须写,
# 旧正则 .omc/**/*.md 拦全部导致治理自噬: ON 电池 tick/verify 流程被自身门禁 BLOCK)。
_SKELETON_MD_RE = re.compile(
    r"(^|[/\\])\.omc[/\\](?:state[/\\].*\.md$|archive[/\\].*\.md$|.*[/\\]index\.md$)",
    re.IGNORECASE)


def _check_omc_skeleton_readonly(payload: dict) -> str | None:
    """拦截对 .omc/**/*.md 骨架的 Write/Edit/MultiEdit。

    gate 契约: 返回 None=放行, 返回 "BLOCK <reason>"=阻断。
    只拦 .md 骨架(状态写入走 carros_base.py 接口), 放行 .json 等其他文件。
    """
    tool = _extract_tool(payload).lower()
    if tool not in ("write", "edit", "multiedit"):
        return None
    ti = _extract_input(payload) or {}
    path = str(ti.get("file_path", "") or "").replace("\\", "/")
    if _SKELETON_MD_RE.search(path):
        _append_audit({
            "event_type": "omc_skeleton_write_blocked",
            "actor": "hook:pretool-gate",
            "gate": "omc-skeleton-readonly",
            "decision": "BLOCK",
            "reason": f"skeleton_md_write:{path[:120]}",
            "tool": tool,
        })
        return (f"BLOCK omc-skeleton-readonly|"
                f"直接修改骨架文件 {path!r} 被禁止(worktree 隔离下 .omc/**/*.md 只读)。"
                f"如需更新任务状态, 使用 carros_base.py 的状态写入接口。")
    return None
