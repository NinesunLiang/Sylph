#!/usr/bin/env python3
"""carroros-night-deny.py — 夜跑信任边界 hook v3（FINAL.md v3.1 §4.5 第 1 层）

仅在夜会话激活（.omc/state/night-session.active 存在）时生效；
设计时（白天落盘/Phase 0）不阻断人类与整合者工作。

v3 核心改动（GPT §17a P0-SOL-1：动态路径旁路）：
  v2 的「命令不含控制面 token 即放行」被字符串拼接打穿——
  python3 -c 'Path(".omc/st"+"ate/night-session.active").unlink()' 字面不含连续
  .omc/state → 放行 → 删 marker → hook 熄灯 → 全控制面失守（修复前实证 7/8 穿防）。
  v3 夜间 Bash 改为【无条件默认拒绝】：凡命令必须 fullmatch 结构化白名单，
  与是否提及 token 无关；解释器（python/node/bash/sh）不得作为普通命令裸奔，
  测试/构建必须经 run-gate.sh 包装；禁换行/链式/重定向/命令替换/glob 执行写操作。
  附带修复：P1-SOL-2 marker 改 __file__ 锚定绝对路径（cwd 漂移不再 fail-open；
  NIGHT_DENY_ROOT 仅供测试——锚定根夜间时 override 忽略 + launcher 生产路径
  显式 unset，双层防拐根）；P1-SOL-3 坏 payload / hook 内部异常
  夜间一律 exit 2 fail-closed。

文件工具 deny（命中即 exit 2，含 realpath 解析）：
  scripts/carroros-gates/**、**/gate-results/**、night-manifest*.yaml、
  **/token.json、.claude/settings*.json、.claude/hooks/**、
  verification-summaries/、ac-aggregates/、tokens/、metrics/、
  page-baselines/、smoke-results*.yaml、control-plane-scorecard.yaml、
  morning-report.md、.omc/state/**

Bash 夜间白名单（fullmatch；此外一律 exit 2）：
  1. 门禁脚本：scope-check/c7-check/evidence-check/finalize-page/abstraction-check
  2. run-gate.sh：参数段合法 + wrapped 命令过工具白名单（C2/C4/C5/C6 唯一入口）
  3. carros_base.py 三 API：manifest-json / token-write / gate-results-init
  4. 页基线：git -C R rev-parse HEAD > .../page-baselines/X.sha（唯一合法 > ）
  5. 事件追加：echo ... >> .../execution-events.jsonl（唯一合法 >> ）
  6. 只读命令：cat/ls/grep/rg/head/tail/find(禁-exec)/shasum/stat/file/wc/date/
     sort/uniq/diff/realpath/readlink/basename/dirname/pwd/which
  7. git 只读：status/diff/log/show/rev-parse/ls-files
  8. git 写（页内原子提交，步 3-5）：add / commit（消息禁元字符）
  9. gh pr create|status|view（C8b 建 Draft PR）
 10. lx-goal 运行时：python3 .claude/skills/lx-goal/scripts/lx-goal.py ...
 11. 版本探针：node|pnpm|npm|python3 --version（步 0 指纹比对）
 12. mkdir -p / scoped rm -rf（仅 .omc/task/** artifacts 清理，步 10）
 preflight/morning-report/gen-control-plane-lock/install-night-hook/smoke
 均不在白名单——夜间禁跑（晨收前人类先 rm .omc/state/night-session.active）。

协议与 pretool-gate.py 一致：stdin JSON payload；exit 0 放行，exit 2 阻断。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# P1-SOL-2：marker 锚定 hook 文件位置（cwd 漂移不 fail-open）；
# NIGHT_DENY_ROOT 仅供 smoke 测试覆写仓库根。
# Sol 复审锁紧：锚定根处于夜间时 env override 一律忽略——即便有人能把
# NIGHT_DENY_ROOT 塞进 hook 进程环境，也无法把 marker 根拐到空目录关灯；
# 生产路径另经 hook-launcher.sh 显式 unset 该变量（双层）。
HOOK_FILE = Path(__file__).resolve()
_ANCHOR_ROOT = HOOK_FILE.parents[2]
_ENV_ROOT = os.environ.get("NIGHT_DENY_ROOT")
if _ENV_ROOT and not (_ANCHOR_ROOT / ".omc" / "state" / "night-session.active").exists():
    REPO_ROOT = Path(_ENV_ROOT)
else:
    REPO_ROOT = _ANCHOR_ROOT
MARKER = REPO_ROOT / ".omc" / "state" / "night-session.active"

# ---------- 文件工具：受保护路径 ----------
DENY_PATH_PATTERNS = [
    (re.compile(r"scripts/carroros-gates/"), "门禁脚本目录（控制面，夜跑禁写）"),
    (re.compile(r"/gate-results/"), "gate-results 权威链目录（仅门禁脚本可写）"),
    (re.compile(r"\.omc/night/.*/night-manifest.*\.yaml"), "night-manifest 签署后 immutable"),
    (re.compile(r"token\.json$"), "token.json 仅允许 carros_base.py token-write API"),
    (re.compile(r"/tokens/"), "tokens 目录仅允许 token-write API"),
    (re.compile(r"\.claude/settings[^/]*\.json$"), "settings（防禁用 hook 本身）"),
    (re.compile(r"\.claude/hooks/"), "hook 目录（防改写信任边界自身）"),
    (re.compile(r"verification-summaries/"), "结论文件仅 finalize-page.sh 可写"),
    (re.compile(r"ac-aggregates/"), "AC 聚合仅 evidence-check.sh 可写"),
    (re.compile(r"/metrics/"), "门禁指标仅门禁脚本可写"),
    (re.compile(r"page-baselines/"), "页基线仅允许夜循环步 0 的 git rev-parse 重定向"),
    (re.compile(r"smoke-results.*\.yaml"), "smoke 结果仅 preflight 可写"),
    (re.compile(r"control-plane-scorecard\.yaml|morning-report\.md"), "晨报仅人类晨收可生成"),
    (re.compile(r"\.omc/state/"), "夜会话标记仅 preflight/人类可动"),
]

# run-gate wrapped 命令与 mkdir 禁触碰的控制面 token
PROTECTED_TOKENS = (
    "scripts/carroros-gates", "carroros-gates", "gate-results",
    ".omc/night", ".omc/state", "night-manifest",
    "verification-summar", "ac-aggregates", "page-baselines",
    "token.json", "tokens/", ".claude/settings", ".claude/hooks",
    "carroros-night-deny", "smoke-results", "control-plane-scorecard",
    "morning-report", "carros_base",
)

# 链式/重定向/命令替换（页基线与 events 两条特例在元字符扫描前先行 fullmatch 放行；
# 扫描作用于 _mask_quotes 后的文本——引号内是字面量，壳元字符只在引号外危险）
FORBIDDEN_METACHARS = re.compile(r"&&|\|\||[;|<>`()]|\$\(")

_ARG = r"[^&|;`<>$()]+"  # 参数值：禁元字符，允许空格/引号/中文/$VAR
# 富文本参数（commit/gh 消息体）：壳元字符与括号只允许出现在成对引号内
_QSPAN = r"(?:'[^']*'|\"[^\"]*\")"
_QARG = r"(?:" + _QSPAN + r"|[^&|;`<>$()'\"])+"


def _mask_quotes(cmd: str) -> str | None:
    """引号段替换为等长空白（保持位置/长度），供元字符/ln/find 扫描；
    引号未闭合返回 None —— 夜间无法可靠解析即拒。
    单引号段全掩（bash 中完全字面）；双引号段保留 $( 与反引号可见
    —— bash 在双引号内仍执行命令替换，掩掉会漏判 "$(cat x)" 型攻击。"""
    out: list[str] = []
    i, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if c == "'":
            j = cmd.find("'", i + 1)
            if j == -1:
                return None
            out.append(" " * (j - i + 1))
            i = j + 1
        elif c == '"':
            buf = ['"']
            j = i + 1
            closed = False
            while j < n:
                d = cmd[j]
                if d == '"':
                    buf.append('"')
                    closed = True
                    j += 1
                    break
                if d == "\\" and j + 1 < n:
                    buf.extend((" ", " "))
                    j += 2
                    continue
                if d == "$" and j + 1 < n and cmd[j + 1] == "(":
                    buf.extend(("$", "("))
                    j += 2
                    continue
                if d == "`":
                    buf.append("`")
                    j += 1
                    continue
                buf.append(" ")
                j += 1
            if not closed:
                return None
            out.append("".join(buf))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)

# 两条自带重定向的合法特例（先于元字符扫描判定）
BASELINE_RE = re.compile(r"git\s+-C\s+\S+\s+rev-parse\s+HEAD\s*>\s*\S*page-baselines/\S+\.sha")
EVENTS_RE = re.compile(r"echo\s+[^&|;`<>$()]*>>\s*\S*execution-events\.jsonl")

# ---------- Bash 夜间白名单（全部 fullmatch） ----------
ALLOW_CMD_PATTERNS = [
    # 1. 夜循环门禁脚本
    (re.compile(r"bash\s+\S*scripts/carroros-gates/(scope-check|c7-check|evidence-check|finalize-page|abstraction-check)\.sh(\s+--[a-z-]+\s+" + _ARG + r")+"),
     "门禁脚本"),
    # 3. carros_base 三个 API
    (re.compile(r"python3?\s+\S*carros_base\.py\s+(manifest-json|gate-results-init|token-write)(\s+--[a-z-]+\s+" + _ARG + r")+"),
     "carros_base API"),
    # 6. 只读命令（find 的 -exec/-delete/-ok 在 _bash_verdict 先行拦截）
    (re.compile(r"(cat|ls|head|tail|grep|rg|find|shasum|sha256sum|stat|file|wc|date|sort|uniq|diff|comm|realpath|readlink|basename|dirname|pwd|which)(\s+" + _ARG + r")?"),
     "只读命令"),
    # 7. git 只读
    (re.compile(r"git\s+(-C\s+\S+\s+)?(status|diff|log|show|rev-parse|ls-files)(\s+" + _ARG + r")?"),
     "git 只读"),
    # 8. git 写：页内原子提交（步 3-5；元字符/括号只允许在引号内）
    (re.compile(r"git\s+(-C\s+\S+\s+)?add\s+" + _QARG),
     "git add"),
    (re.compile(r"git\s+(-C\s+\S+\s+)?commit\s+" + _QARG),
     "git commit"),
    # 9. gh（C8b 建 Draft PR + 读状态）
    (re.compile(r"gh\s+pr\s+(create|status|view)(\s+" + _QARG + r")?"),
     "gh pr"),
    # 10. lx-goal 运行时（夜循环宿主）
    (re.compile(r"python3?\s+\.claude/skills/lx-goal/scripts/lx-goal\.py(\s+" + _ARG + r")?"),
     "lx-goal 运行时"),
    # 11. 版本探针（步 0 指纹比对）
    (re.compile(r"(node|pnpm|npm|python3?)\s+(--version|-v|version)"),
     "版本探针"),
]

# run-gate：bash .../run-gate.sh <参数段> -- <wrapped 命令>
RUN_GATE_RE = re.compile(r"bash\s+\S*scripts/carroros-gates/lib/run-gate\.sh\s+(.*?)\s+--\s+(.+)")
RUN_GATE_OUR_ARGS_RE = re.compile(r"(--[a-z-]+\s+" + _ARG + r"\s*)+")
WRAPPED_TOOLS = {"pnpm", "npm", "npx", "node", "tsc", "eslint", "playwright"}
WRAPPED_SCRIPT_RE = re.compile(r"(bash|python3?)\s+\S*(tests?|visual|e2e|scripts)/")


def _allow(msg: str = "OK") -> int:
    print(json.dumps({"continue": True, "message": f"night-deny: {msg}"}, ensure_ascii=False))
    return 0


def _block(reason: str) -> int:
    full = (f"⛔ 夜跑信任边界阻断: {reason}\n"
            f"💡 夜间 Bash 为无条件默认拒绝（GPT §17a P0-SOL-1）；合法形态见 night-loop.md。\n"
            f"💡 被拦后禁止用拼接/变量/glob/cwd 等价改写绕过——记 BLOCKED_CONTROL_PLANE 并停手。\n"
            f"💡 晨收前人类先执行 rm .omc/state/night-session.active 摘除标记。")
    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": full},
    }, ensure_ascii=False))
    sys.stderr.write(f"night-deny: BLOCKED - {reason}\n")
    return 2


def _bash_verdict(cmd: str) -> str | None:
    """返回 None=放行，否则返回阻断原因。夜间无条件默认拒绝（v3）。"""
    cmd = cmd.strip()
    if not cmd:
        return "空命令"
    masked = _mask_quotes(cmd)
    if masked is None:
        return "引号未闭合，夜间无法可靠解析即拒"
    # 换行 = heredoc/多命令拼接（引号内换行是字面量，不拦）
    if "\n" in masked or "\r" in masked:
        return "多行/heredoc 命令夜间全禁"
    # ln 夜间全禁：symlink 可绕过一切路径字符串检查（P0-1 衍生）
    if re.search(r"\bln\b", masked):
        return "ln 夜间全禁（symlink 可绕过路径检查）"
    # find 伪装只读执行写操作（P0-SOL-1 衍生）
    if re.search(r"\bfind\b", masked) and re.search(r"\s-(exec|delete|ok)\b", masked):
        return "find 仅允许只读列举（-exec/-delete/-ok 夜间禁）"

    # run-gate 特例：参数段 + wrapped 命令分别校验（fullmatch 整条命令）
    m = RUN_GATE_RE.fullmatch(cmd)
    if m:
        our, wrapped = m.group(1).strip(), m.group(2).strip()
        if not RUN_GATE_OUR_ARGS_RE.fullmatch(our):
            return "run-gate 参数段非法（仅允许 --key value 对，禁元字符）"
        wrapped_masked = _mask_quotes(wrapped)
        if wrapped_masked is None or "\n" in wrapped_masked or FORBIDDEN_METACHARS.search(wrapped_masked):
            return "run-gate wrapped 命令含链式/重定向/命令替换"
        if any(tok in wrapped for tok in PROTECTED_TOKENS):
            return "run-gate wrapped 命令触碰控制面"
        tool = wrapped.split()[0] if wrapped.split() else ""
        if tool in WRAPPED_TOOLS or WRAPPED_SCRIPT_RE.match(wrapped):
            return None
        return (f"run-gate wrapped 工具不在白名单: {tool!r}"
                f"（C2=tsc/eslint/build，C4/C5=playwright，C6=视觉脚本；包空命令=篡改）")

    # scoped rm -rf：仅 .omc/task/** artifacts 清理（步 10），先于一元字符判定
    if re.fullmatch(r"rm\s+-[rf]+\s+\S*\.omc/task/[^&|;`<>$()]*", cmd):
        return None
    # mkdir：单路径、不碰控制面
    if re.fullmatch(r"mkdir\s+(-p\s+)?[^&|;`<>$()\s]+", cmd):
        if any(tok in cmd for tok in PROTECTED_TOKENS):
            return "mkdir 目标触碰控制面"
        return None

    # 两条自带重定向的合法特例（在全局元字符扫描之前）
    if BASELINE_RE.fullmatch(cmd):
        return None
    if EVENTS_RE.fullmatch(cmd):
        return None
    # 元字符全局禁（扫描引号外文本；此后白名单均不含壳元字符）
    if FORBIDDEN_METACHARS.search(masked):
        return "命令含链式/重定向/命令替换元字符（夜间唯一合法重定向：页基线 > 与 events >>）"
    # git/gh 过宽分支收紧（Sol 复审：白名单形态内的语义误用）
    if re.match(r"git\s+(-C\s+\S+\s+)?(add|commit)\s", cmd):
        if re.search(r"--(amend|no-verify|force)\b", masked) or re.search(r"(^|\s)-f(\s|$)", masked):
            return "git add/commit 夜间禁 --amend/--no-verify/--force/-f（历史改写与钩子绕过）"
    if re.match(r"gh\s+pr\s+create\s", cmd):
        if "--draft" not in cmd:
            return "gh pr create 夜间必须 --draft（draft_pr_on: DONE_only）"
        if re.search(r"--repo\b", masked):
            return "gh pr create 夜间禁 --repo（防推送目标漂移/外泄）"
    # 其余白名单 fullmatch
    for pat, _ in ALLOW_CMD_PATTERNS:
        if pat.fullmatch(cmd):
            return None
    return ("夜间 Bash 默认拒绝：命令不在精确白名单"
            "（工具链走 run-gate.sh；业务文件读写走 Edit/Write；合法形态见 night-loop.md）")


def _night_verdict(payload: dict) -> str | None:
    """夜会话激活时的完整判定；返回 None=放行。"""
    tool = payload.get("tool_name") or payload.get("tool") or ""
    if not isinstance(tool, str) or not tool:
        return "payload 缺 tool_name，fail-closed"

    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit", "Delete"):
        data = payload.get("tool_input") or payload.get("input") or {}
        raw = str(data.get("file_path") or data.get("filePath") or data.get("path")
                  or data.get("notebook_path") or "") if isinstance(data, dict) else ""
        if not raw:
            return f"{tool} payload 缺 file_path，fail-closed"
        candidates = {raw, os.path.realpath(raw)}
        for c in candidates:
            for pat, why in DENY_PATH_PATTERNS:
                if pat.search(c):
                    return f"{tool} -> {raw}：{why}"
        return None

    if tool == "Bash":
        data = payload.get("tool_input") or payload.get("input") or {}
        cmd = data.get("command") if isinstance(data, dict) else None
        if not isinstance(cmd, str) or not cmd.strip():
            return "Bash payload 缺 command 或类型错误，fail-closed"
        return _bash_verdict(cmd)

    # 其余工具（Read/Grep/Glob/Task/Skill/WebFetch/TodoWrite/mcp__* 等）不碰控制面，放行
    return None


def main() -> int:
    night = MARKER.exists()
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        if night:
            return _block("hook payload 非合法 JSON，fail-closed（P1-SOL-3）")
        return _allow("夜会话未激活，放行")
    if not isinstance(payload, dict):
        if night:
            return _block("hook payload 结构非法，fail-closed")
        return _allow("夜会话未激活，放行")

    if not night:
        return _allow("夜会话未激活，放行")
    try:
        verdict = _night_verdict(payload)
    except Exception as e:  # P1-SOL-3：hook 自身异常夜间 fail-closed
        return _block(f"hook 内部异常 fail-closed: {type(e).__name__}")
    if verdict:
        return _block(verdict)
    return _allow()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 最后一道：入口异常也按夜间 fail-closed
        try:
            night = MARKER.exists()
        except Exception:
            night = True  # 连 marker 都读不了 → 视为夜间，从严
        if night:
            sys.stderr.write(f"night-deny: BLOCKED - 入口异常 fail-closed: {type(e).__name__}\n")
            sys.exit(2)
        sys.exit(0)
