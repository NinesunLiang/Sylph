#!/usr/bin/env python3
"""auto-snapshot.py — Stop / PostToolUse:Edit|Write — 会话结束时自动保存状态快照（分支/轮次/未提交文件）
Role: 会话结束时自动保存状态快照（分支/轮次/未提交文件）

等效移植自 auto-snapshot.sh (532行):
- 保存 session-snapshot.json (含 timestamp/turns/branch/modified_files/staged_files)
- SHA256 防篡改摘要
- 文档同步检查 (源文件修改时提醒更新 executor.md)
- 生成 session-handoff.md 交接备忘录
- 生成 session-dump.json 结构化转储
- 配置变更自动回归检测
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, hc_emit_hook_json, flywheel_event, output_continue

# ─── 路径常量 ───

PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
SCRIPT_DIR = _HOOKS_DIR

# ─── 跨平台获取文件 mtime ───

def _get_mtime(filepath):
    """获取文件的 mtime（秒级时间戳），跨平台兼容。"""
    try:
        return int(os.path.getmtime(str(filepath)))
    except (OSError, ValueError):
        return 0


# ─── 读取轮次计数 ───

def _read_turns():
    """从 session-turns.json 读取轮次计数。"""
    turns_file = STATE_DIR / "session-turns.json"
    if not turns_file.exists():
        return 0
    try:
        with open(turns_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("count", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    # fallback: grep-style parsing
    try:
        content = turns_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'"count"\s*:\s*(\d+)', content)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return 0


# ─── 获取当前分支 ───

def _get_branch():
    """获取当前 git 分支名。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return "unknown"


# ─── git diff 文件列表 → JSON ───

def _git_diff_names(cached=False):
    """获取 git diff 文件列表，返回 list[str]。"""
    cmd = ["git", "diff", "--name-only"]
    if cached:
        cmd.append("--cached")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            timeout=10
        )
        if result.returncode == 0:
            return [l.rstrip() for l in result.stdout.splitlines() if l.rstrip()]
    except (subprocess.SubprocessError, OSError):
        pass
    return []


# ─── 去除代理对（surrogate） ───

def _strip_surr(obj):
    """递归去除所有字符串中的 lone surrogate codepoints。"""
    if isinstance(obj, str):
        return "".join(c for c in obj if not (0xD800 <= ord(c) <= 0xDFFF))
    if isinstance(obj, list):
        return [_strip_surr(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _strip_surr(v) for k, v in obj.items()}
    return obj


# ─── 写 JSON 文件（原子写入） ───

def _write_json_atomic(filepath, data):
    """原子写入 JSON 文件。"""
    tmp = str(filepath) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.rename(tmp, str(filepath))


# ─── SHA256 防篡改摘要 ───

def _write_sha256(filepath):
    """写入 SHA256 摘要文件。"""
    sha256_file = Path(str(filepath) + ".sha256")
    try:
        import hashlib
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            h.update(f.read())
        sha256_file.write_text(h.hexdigest() + "\n", encoding="utf-8")
    except OSError:
        pass


# ─── 文档同步检查 ───

def _doc_sync_check(modified_files, staged_files):
    """检查本次修改的源文件是否有对应的 executor.md 更新。"""
    source_ext = hc_get("project.source_extensions", "*.go")
    ext_suffix = source_ext.lstrip("*")

    def _filter_ext(files):
        return [f for f in files if f.endswith(ext_suffix)]

    mod_go = _filter_ext(modified_files)
    staged_go = _filter_ext(staged_files)
    all_go_files = sorted(set(mod_go + staged_go))

    if not all_go_files:
        return

    exec_doc = hc_get("workflow.executor_doc", "executor.md")
    doc_root = hc_get("workflow.doc_root", "rpe")
    plan_doc = hc_get("workflow.plan_doc", "plan.md")

    # 检查 executor.md 是否在本次修改范围内
    all_modified = set(modified_files + staged_files)
    has_executor_update = exec_doc in all_modified

    if not has_executor_update:
        print(f"\n⚠️ 文档同步提醒: 本次修改了 {len(all_go_files)} 个 {ext_suffix} 文件但未更新 {exec_doc}。", file=sys.stderr, flush=True)
        print(f"若涉及状态/接口/行为变更，请同步更新 {doc_root}/{{feature}}/{exec_doc} 和 {plan_doc}。", file=sys.stderr, flush=True)
        print(f"涉及文件: {', '.join(all_go_files)}", file=sys.stderr, flush=True)


# ─── 生成 session-handoff.md ───

def _generate_handoff(branch, turns):
    """生成会话交接备忘录。"""
    handoff_file = STATE_DIR / "session-handoff.md"
    doc_root = hc_get("workflow.doc_root", "rpe")
    exec_doc = hc_get("workflow.executor_doc", "executor.md")
    handoff_enabled = hc_get("session_handoff.enabled", "true")
    max_adr = int(hc_get("session_handoff.max_adr_lines", "10"))
    max_todo = int(hc_get("session_handoff.max_todo_lines", "10"))
    max_lessons = int(hc_get("session_handoff.max_lessons", "3"))

    if handoff_enabled.lower() != "true":
        return

    sections = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections.append(f"# 会话交接备忘录\n> 生成时间: {now} | 分支: {branch} | 轮次: {turns}\n")

    # 查找活跃的 executor.md
    executor_files = []
    rpe_dir = PROJECT_ROOT / doc_root
    if rpe_dir.is_dir():
        try:
            for feature in sorted(os.listdir(str(rpe_dir))):
                epath = rpe_dir / feature / exec_doc
                if epath.is_file():
                    executor_files.append((feature, epath))
        except OSError:
            pass

    for feature, epath in executor_files:
        try:
            content = epath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # 正在做什么：检测 🔄 / ✅ / ⛔ 行
        active_steps = re.findall(r".*🔄.*", content)
        completed_steps = re.findall(r".*✅.*", content)
        blocked_steps = re.findall(r".*⛔.*", content)

        if active_steps or completed_steps or blocked_steps:
            sections.append(f"## Feature: {feature}\n")

        if active_steps:
            sections.append("### 🔄 进行中")
            for s in active_steps[:5]:
                sections.append(f"- {s.strip()}")
        if completed_steps or blocked_steps:
            sections.append(f"\n### 进度: ✅ {len(completed_steps)} 完成, 🔄 {len(active_steps)} 进行中, ⛔ {len(blocked_steps)} 阻塞")

        # 关键决策: ADR
        adr_lines = [l.strip() for l in content.split("\n") if "ADR-" in l]
        if adr_lines:
            sections.append("\n### 关键决策")
            for l in adr_lines[:max_adr]:
                sections.append(f"- {l}")

        # 未完成项: TODO
        todo_lines = [l.strip() for l in content.split("\n") if re.match(r"\s*-\s*\[", l)]
        if todo_lines:
            sections.append("\n### 未完成项")
            for l in todo_lines[:max_todo]:
                sections.append(f"- {l}")

        # 关键决策: 从 executor.md 和 plan.md 扫描决策关键词
        decision_pattern = re.compile(r"决定|选择|确认|方案[A-Ca-c]|采用|用户.*同意|放弃.*改用", re.IGNORECASE)
        decision_lines = [l.strip() for l in content.split("\n") if decision_pattern.search(l) and l.strip()]

        # 同时扫描 plan.md
        plan_path = os.path.join(os.path.dirname(str(epath)), "plan.md")
        if os.path.isfile(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8") as pf:
                    plan_content = pf.read()
                decision_lines += [l.strip() for l in plan_content.split("\n") if decision_pattern.search(l) and l.strip()]
            except OSError:
                pass

        # 去重并截断
        seen = set()
        unique_decisions = []
        for l in decision_lines:
            if l not in seen:
                seen.add(l)
                unique_decisions.append(l)

        if unique_decisions:
            sections.append("\n### 关键决策 (本轮)")
            for l in unique_decisions[:5]:
                sections.append(f"- {l}")

        # 踩坑记录
        pitfall_pattern = re.compile(r"踩坑|注意|坑:|问题:|bug|⚠️|BLOCKED|失败.*因为|原因.*是", re.IGNORECASE)
        pitfall_lines = [l.strip() for l in content.split("\n") if pitfall_pattern.search(l) and l.strip()]
        if pitfall_lines:
            sections.append("\n### 踩坑记录")
            seen_p = set()
            for l in pitfall_lines:
                if l not in seen_p:
                    seen_p.add(l)
                    sections.append(f"- {l}")
                if len(seen_p) >= 5:
                    break

    # 未解决的错误: 从 error-dna.json 读取
    error_dna_path = STATE_DIR / "error-dna.json"
    if error_dna_path.exists():
        try:
            with open(error_dna_path, "r", encoding="utf-8") as ef:
                raw = json.load(ef)
            # 实际文件结构: {"error_signatures": {...}}, 也可能是列表
            if isinstance(raw, dict):
                sigs = raw.get("error_signatures", {})
                error_data = [{"signature": k, **v} for k, v in sigs.items()]
            elif isinstance(raw, list):
                error_data = raw
            else:
                error_data = []
            unfixed = [e for e in error_data if e.get("status") != "fixed"]
            if unfixed:
                sections.append("\n## 未解决的错误")
                for e in unfixed[:3]:
                    sig = e.get("signature", "(unknown)")
                    count = e.get("count", 1)
                    last_seen = e.get("last_seen", "")
                    sections.append(f"- {sig} (出现{count}次, 最后: {last_seen})")
        except (json.JSONDecodeError, OSError):
            pass

    # 当前 Todo 队列
    todo_path = STATE_DIR / "todo-queue.md"
    if todo_path.exists():
        try:
            todo_content = todo_path.read_text(encoding="utf-8", errors="replace").strip()
            if todo_content:
                active = [l for l in todo_content.split("\n") if "[·]" in l]
                pending = [l for l in todo_content.split("\n") if re.match(r"\s*-\s*\[", l)]
                if active or pending:
                    sections.append("\n## 当前 Todo")
                    for l in active[:5]:
                        sections.append(f" {l.strip()}")
                    for l in pending[:5]:
                        sections.append(f" {l.strip()}")
        except OSError:
            pass

    # 本次涉及文件
    edit_log_path = STATE_DIR / "session-edit-log.txt"
    if edit_log_path.exists():
        try:
            raw_files = [l.strip() for l in edit_log_path.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            unique_files = sorted(set(raw_files))
            if unique_files:
                sections.append(f"\n## 本次涉及文件 ({len(unique_files)}个)")
                for f in unique_files[:10]:
                    sections.append(f"- {f}")
        except OSError:
            pass

    # 修改的文件（从 git）
    try:
        modified = subprocess.run(
            ["git", "diff", "--name-only"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10
        ).stdout.strip()
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10
        ).stdout.strip()
        all_files = set(filter(None, (modified + "\n" + staged).split("\n")))
        if all_files:
            sections.append("\n## 修改的文件")
            for f in sorted(all_files)[:15]:
                sections.append(f"- {f}")
    except (subprocess.SubprocessError, OSError):
        pass

    # non-rpe fallback: 无 executor.md 时注入 git log 摘要
    if not executor_files:
        try:
            log_result = subprocess.run(
                ["git", "log", "--oneline", "--no-merges", "-10"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=10
            )
            if log_result.returncode == 0 and log_result.stdout.strip():
                sections.append("\n## 最近提交（rpe 工作流未启用时的替代摘要）")
                for line in log_result.stdout.strip().split("\n")[:10]:
                    sections.append(f"- `{line.strip()}`")
                sections.append("\n> 💡 启用 rpe 工作流后（`mkdir rpe && mkdir rpe/{feature}`），交接内容将更丰富")
        except (subprocess.SubprocessError, OSError):
            pass

    # 踩过的坑: claude-next.md 最近条目
    claude_next = _HOOKS_DIR.parent / "claude-next.md"
    if claude_next.exists():
        try:
            cn_content = claude_next.read_text(encoding="utf-8", errors="replace")
            lesson_titles = re.findall(r"^## \[.+?\] (.+)", cn_content, re.MULTILINE)
            if lesson_titles:
                sections.append("\n## 近期教训")
                for t in lesson_titles[-max_lessons:]:
                    sections.append(f"- {t}")
        except OSError:
            pass

    # 写入
    handoff_file.parent.mkdir(parents=True, exist_ok=True)
    handoff_file.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"Session handoff saved: {len(sections)} sections", file=sys.stderr, flush=True)


# ─── 生成 session-dump.json ───

def _generate_dump(branch, turns):
    """生成结构化 session dump。"""
    dump_file = STATE_DIR / "session-dump.json"

    dump = {}

    # 1. git_state
    try:
        modified = subprocess.run(
            ["git", "diff", "--name-only"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10
        ).stdout.strip().split("\n")
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10
        ).stdout.strip().split("\n")
        diff_stat = subprocess.run(
            ["git", "diff", "--stat"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10
        ).stdout.strip()
        modified = [f for f in modified if f]
        staged = [f for f in staged if f]
        dump["git_state"] = {
            "branch": branch,
            "turns": int(turns) if isinstance(turns, int) else 0,
            "modified_files": modified,
            "staged_files": staged,
            "diff_stat": diff_stat[:500],
        }
    except Exception as e:
        dump["git_state"] = {"branch": branch, "error": str(e)}

    # 2. error_summary
    error_path = STATE_DIR / "error-dna.json"
    if error_path.exists():
        try:
            with open(error_path, "r", encoding="utf-8") as f:
                error_data = json.load(f)
            signatures = error_data.get("error_signatures", {})
            unfixed = []
            for sig, info in signatures.items():
                if info.get("status") != "fixed":
                    unfixed.append({
                        "signature": sig[:20],
                        "count": info.get("count", 0),
                        "last_seen": info.get("last_seen", ""),
                        "message": info.get("message", "")[:120],
                    })
            dump["error_summary"] = {"unfixed_count": len(unfixed), "errors": unfixed[:5]}
        except Exception:
            dump["error_summary"] = {"error": "parse_failed"}
    else:
        dump["error_summary"] = {"error": "no_file"}

    # 3. todo_queue
    todo_path = STATE_DIR / "todo-queue.md"
    if todo_path.exists():
        try:
            content = todo_path.read_text(encoding="utf-8", errors="replace")
            items = [l.strip() for l in content.split("\n") if "[·]" in l or re.match(r"\s*-\s*\[", l)]
            dump["todo_queue"] = items[:10]
        except Exception:
            dump["todo_queue"] = []
    else:
        dump["todo_queue"] = []

    # 4. active_features
    active = []
    rpe_dir = PROJECT_ROOT / "rpe"
    if rpe_dir.is_dir():
        try:
            for feat in sorted(os.listdir(str(rpe_dir))):
                ppath = rpe_dir / feat / "state" / "progress.md"
                if ppath.is_file():
                    try:
                        first = ppath.read_text(encoding="utf-8", errors="replace")[:300]
                        active.append({"feature": feat, "status_snippet": first[:200]})
                    except Exception:
                        active.append({"feature": feat, "status_snippet": "(read_error)"})
        except OSError:
            pass
    dump["active_features"] = active[:5]

    # 5. token_usage
    token_path = STATE_DIR / "token-tracking-index.json"
    if token_path.exists():
        try:
            dump["token_usage"] = json.loads(token_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            dump["token_usage"] = {}
    else:
        dump["token_usage"] = {}

    # 6. claude_next_hits
    cn_path = _HOOKS_DIR.parent / "claude-next.md"
    if cn_path.exists():
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            content = cn_path.read_text(encoding="utf-8", errors="replace")
            today_lines = [l.strip() for l in content.split("\n") if today in l]
            dump["claude_next_hits"] = today_lines[:5]
        except Exception:
            dump["claude_next_hits"] = []
    else:
        dump["claude_next_hits"] = []

    # 7. edit_log
    edit_log_path = STATE_DIR / "session-edit-log.txt"
    if edit_log_path.exists():
        try:
            files = sorted(set(l.strip() for l in edit_log_path.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()))
            dump["edit_log"] = files[:20]
        except Exception:
            dump["edit_log"] = []
    else:
        dump["edit_log"] = []

    # 写原子
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    dump = _strip_surr(dump)
    _write_json_atomic(dump_file, dump)
    print(f"Session dump written: {len(dump)} sections", file=sys.stderr, flush=True)


# ─── 配置变更自动回归检测 ───

def _regression_check():
    """检测 harness.yaml 或 settings.json 修改时间是否变化，触发回归校验。"""
    reg_baseline = STATE_DIR / ".regression-baseline.txt"
    reg_changed = False

    config_files = [
        PROJECT_ROOT / ".claude" / "harness.yaml",
        PROJECT_ROOT / ".claude" / "settings.json",
    ]

    for cfg in config_files:
        if not cfg.exists():
            continue
        cfg_mtime = _get_mtime(cfg)
        cfg_name = cfg.name
        baseline_mtime = ""
        if reg_baseline.exists():
            try:
                for line in reg_baseline.read_text(encoding="utf-8", errors="replace").splitlines():
                    if "=" in line:
                        k, _, v = line.partition("=")
                        if k == cfg_name:
                            baseline_mtime = v
                            break
            except OSError:
                pass
        if baseline_mtime and cfg_mtime != int(baseline_mtime) if baseline_mtime.isdigit() else False:
            reg_changed = True
            break
        # Also set reg_changed if baseline_mtime was "" but cfg has mtime (first run)
        if not baseline_mtime and cfg_mtime > 0:
            # First time seeing this config, no baseline yet — not a change
            pass

    if reg_changed:
        flywheel_event("auto_snapshot", "triggered", "P2")
        print("  ⚙️ 配置变更检测: 触发自动化回归校验", file=sys.stderr, flush=True)
        reg_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        reg_out = STATE_DIR / f"auto-regression-{reg_ts}.json"

        # 后台运行回归
        pid = os.fork()
        if pid == 0:
            # Child process
            try:
                smoke_result = subprocess.run(
                    ["bash", str(PROJECT_ROOT / ".claude" / "scripts" / "harness-smoke-test.sh")],
                    capture_output=True, text=True, timeout=120
                )
                smoke_output = smoke_result.stdout + smoke_result.stderr
                smoke_sum = ""
                for line in smoke_output.splitlines():
                    if "summary:" in line:
                        smoke_sum = line.strip()

                audit_result = subprocess.run(
                    ["bash", str(PROJECT_ROOT / ".claude" / "scripts" / "audit-hooks.sh")],
                    capture_output=True, text=True, timeout=120
                )
                audit_output = audit_result.stdout + audit_result.stderr
                audit_red = "-"
                m = re.search(r"🔴 严重: (\d+)", audit_output)
                if m:
                    audit_red = m.group(1)
                audit_yellow = "-"
                m = re.search(r"🟡 次要: (\d+)", audit_output)
                if m:
                    audit_yellow = m.group(1)

                result = {
                    "timestamp": reg_ts,
                    "trigger": "config_change",
                    "smoke": smoke_sum,
                    "audit_red": audit_red,
                    "audit_yellow": audit_yellow,
                }
                _write_json_atomic(reg_out, result)
                print(f"  ✔ 回归结果: {smoke_sum}  audit: {audit_red}🔴 {audit_yellow}🟡", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"  ❌ 回归异常: {e}", file=sys.stderr, flush=True)
            os._exit(0)
        else:
            # Parent: fork succeeded, log the regression run
            log_path = STATE_DIR / f".regression-run-{reg_ts}.log"
            log_path.write_text(f"Regression PID: {pid}\n", encoding="utf-8")

    # 更新基线
    baseline_lines = []
    for cfg in config_files:
        if cfg.exists():
            cfg_mtime = _get_mtime(cfg)
            baseline_lines.append(f"{cfg.name}={cfg_mtime}")
    if baseline_lines:
        reg_baseline.parent.mkdir(parents=True, exist_ok=True)
        reg_baseline.write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")


# ─── Main ───

def main():
    if not hc_enabled("auto_snapshot"):
        output_continue()
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # 读取轮次计数
    turns = _read_turns()

    # 获取当前分支
    branch = _get_branch()

    # 获取未提交修改文件列表
    modified_files = _git_diff_names(cached=False)
    staged_files = _git_diff_names(cached=True)

    # 生成时间戳
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 写入快照文件
    snapshot = {
        "timestamp": timestamp,
        "turns": turns,
        "branch": branch,
        "modified_files": modified_files,
        "staged_files": staged_files,
    }
    snapshot = _strip_surr(snapshot)
    snapshot_file = STATE_DIR / "session-snapshot.json"
    _write_json_atomic(snapshot_file, snapshot)

    # SHA256 防篡改摘要
    _write_sha256(snapshot_file)

    print(f"Session snapshot saved: turns={turns} branch={branch}", file=sys.stderr, flush=True)

    # 文档同步检查
    _doc_sync_check(modified_files, staged_files)

    # 生成交接备忘录
    _generate_handoff(branch, turns)

    # 生成结构化 session dump
    _generate_dump(branch, turns)

    # 配置变更自动回归检测
    _regression_check()

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
