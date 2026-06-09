#!/usr/bin/env python3
"""
turn-counter.py — UserPromptSubmit — 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测
Role: 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测
对应 turn-counter.sh 的 Python 移植
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, hc_get, is_mode_active, HOME_DIR


def main():
    # hc_enabled check — for UserPromptSubmit, must still read stdin
    if not hc_enabled("turn_counter"):
        # drain stdin
        sys.stdin.read()
        sys.exit(0)

    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    state_file = state_dir / "session-turns.json"
    todo_file = state_dir / "todo-queue.md"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 保存用户原始输入（供模糊指令检测使用）
    fuzzy_check = state_dir / ".last-user-prompt"
    prompt = sys.stdin.read()
    # 同时写入文件并输出到 stdout（tee 效果）
    with open(str(fuzzy_check), "w", encoding="utf-8") as f:
        f.write(prompt)
    print(prompt, end="")

    # 读取当前计数
    current_count = 0
    if state_file.exists():
        try:
            with open(str(state_file), "r", encoding="utf-8") as f:
                state_data = json.load(f)
            current_count = int(state_data.get("count", 0))
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            current_count = 0

    if not isinstance(current_count, int) or current_count < 0:
        current_count = 0

    new_count = current_count + 1
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(str(state_file), "w", encoding="utf-8") as f:
        json.dump({"count": new_count, "updated": updated_at}, f)

    todo_interval = int(hc_get("turn_counter.todo_refresh_interval", "10"))
    todo_max = int(hc_get("turn_counter.todo_max_items", "15"))
    doc_root = hc_get("workflow.doc_root", "rpe")
    exec_doc = hc_get("workflow.executor_doc", "executor.md")

    if todo_interval > 0 and new_count % todo_interval == 0:
        print("═══ [轮次 {}] 锚定 ═══".format(new_count))

        # 铁律摘要
        print("铁律: 编造❌ 裁定🟢 证据🔒 Git审批✅ 冻结📦 隐私🔐")

        # Pipeline Step
        pipeline_step_script = project_root / ".claude" / "scripts" / "pipeline-step.sh"
        if pipeline_step_script.exists():
            try:
                result = subprocess.run(["bash", str(pipeline_step_script), "inject"],
                                        capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    print(result.stdout.strip())
            except Exception:
                pass

        # Retry Budget
        retry_script = project_root / ".claude" / "scripts" / "retry-budget.sh"
        if retry_script.exists():
            try:
                result = subprocess.run(["bash", str(retry_script), "check"],
                                        capture_output=True, text=True, timeout=10)
                if result.returncode == 2 and result.stdout.strip():
                    print(result.stdout.strip())
                elif result.returncode == 2 and result.stderr.strip():
                    print(result.stderr.strip())
            except Exception:
                pass

        # Todo 队列
        if todo_file.exists():
            todo_content = todo_file.read_text(encoding="utf-8", errors="replace")
            pending = len(re.findall(r'\[ \]|\[·\]', todo_content))
            if pending > 0:
                print(f"[待办: {pending}项]")
                # 打印前5个待办项
                lines = [l for l in todo_content.split("\n") if re.search(r'\[ \]|\[·\]', l)]
                for line in lines[:5]:
                    print(line)

        # 最新 executor.md 范围
        doc_search_path = project_root / doc_root
        if doc_search_path.exists():
            exec_files = sorted(doc_search_path.rglob(exec_doc), key=lambda p: p.stat().st_mtime, reverse=True)
            if exec_files:
                latest_exec = exec_files[0]
                feature = str(latest_exec.relative_to(project_root)).split("/" + doc_root + "/", 1)[-1]
                feature = feature.rsplit("/" + exec_doc, 1)[0] if exec_doc in feature else feature
                exec_content = latest_exec.read_text(encoding="utf-8", errors="replace")
                active_step = ""
                for line in exec_content.split("\n"):
                    if re.search(r"^##.*🔄|^## Step.*进行中|^##.*in.progress", line):
                        active_step = line.strip()
                        break
                if active_step:
                    print(f"范围: {feature} {active_step}")

        # Session 目标锚定
        handoff_file = project_root / ".omc" / "state" / "session-handoff.md"
        if handoff_file.exists():
            for line in handoff_file.read_text(encoding="utf-8", errors="replace").split("\n"):
                m = re.match(r'^## Feature:\s*(.*)', line)
                if m:
                    print(m.group(1).strip())
                    break

        # E8 会话健康快照
        error_count = 0
        contradiction_count = 0
        error_dna_json = project_root / ".omc" / "state" / "error-dna.json"
        if error_dna_json.exists():
            try:
                with open(str(error_dna_json), "r", encoding="utf-8") as f:
                    edna = json.load(f)
                sigs = edna.get("error_signatures", {})
                if isinstance(sigs, dict):
                    error_count = sum(1 for v in sigs.values() if isinstance(v, dict) and v.get("status") == "active")
            except (json.JSONDecodeError, OSError):
                pass

        edit_churn_log = project_root / ".omc" / "state" / "edit-churn-log.jsonl"
        if edit_churn_log.exists():
            content = edit_churn_log.read_text(encoding="utf-8", errors="replace")
            contradiction_count = content.count('"contradiction": true')

        # C8 三方漂移检测
        drift_count_str = "?"
        harness_yaml = project_root / ".claude" / "harness.yaml"
        settings_json = project_root / ".claude" / "settings.json"
        if harness_yaml.exists() and settings_json.exists():
            try:
                # 扫描磁盘上的 .sh hooks
                disk_scripts = set()
                for f in script_dir.glob("*.sh"):
                    disk_scripts.add(f.stem)

                # 扫描 yaml enabled
                yaml_enabled = set()
                yaml_content = harness_yaml.read_text(encoding="utf-8", errors="replace")
                for line in yaml_content.split("\n"):
                    m = re.match(r"^hooks_enabled\.(\w+):\s*true", line)
                    if m:
                        yaml_enabled.add(m.group(1))

                # 扫描 settings 注册
                settings_scripts = set()
                with open(str(settings_json), "r", encoding="utf-8") as f:
                    s = json.load(f)
                for hook_list_key in ["hooks", "preToolUse", "postToolUse",
                                       "preToolUseFailure", "postToolUseFailure",
                                       "sessionStart", "userPromptSubmit", "stop"]:
                    for hook in s.get(hook_list_key, []):
                        if isinstance(hook, dict) and "script" in hook:
                            name = Path(hook["script"]).stem.replace(".sh", "").replace(".py", "")
                            settings_scripts.add(name)

                zombie = len((disk_scripts & yaml_enabled) - settings_scripts)
                orphan = len(settings_scripts - disk_scripts)
                drift_count_str = f"{zombie}+{orphan}"
            except Exception:
                pass

        # C5 工具生命周期
        total_ops_file = state_dir / "total-ops.txt"
        error_dna_jsonl = state_dir / "error-dna.jsonl"
        tool_diversity = 0
        if error_dna_jsonl.exists():
            tool_diversity = len(re.findall(r'"error_type"', error_dna_jsonl.read_text(encoding="utf-8", errors="replace")))

        tool_err_rate = "?"
        if total_ops_file.exists():
            try:
                total_ops = int(total_ops_file.read_text(encoding="utf-8", errors="replace").strip() or "0")
                if total_ops > 0:
                    err_rate = tool_diversity * 100 // total_ops
                    tool_err_rate = f"{err_rate}%"
            except (ValueError, OSError):
                pass

        print(f"健康: 轮{new_count} ctx{'?'}% err{error_count} 矛{contradiction_count} z{drift_count_str} 工具{tool_diversity} err{tool_err_rate}")
        print("═══ ═══")

    # ─── 模糊指令检测 ───
    if fuzzy_check.exists():
        prompt_text = fuzzy_check.read_text(encoding="utf-8", errors="replace")

        has_explicit_target = False
        explicit_regex = hc_get("fuzzy_detection.explicit_target_regex",
                                r"Step\s*[0-9]+|rpe/[a-zA-Z_]+|\.go$|\.md$|handler|logic|model|executor")
        if re.search(explicit_regex, prompt_text):
            has_explicit_target = True

        # Ghost mode / Unattended mode 豁免
        mode = is_mode_active(str(state_dir))
        if mode != "normal":
            has_explicit_target = True

        if has_explicit_target:
            fuzzy_block_active = project_root / ".omc" / "state" / ".fuzzy-block-active"
            try:
                fuzzy_block_active.unlink(missing_ok=True)
            except OSError:
                pass

        if not has_explicit_target:
            fuzzy_verbs = hc_get("fuzzy_detection.fuzzy_verbs", "继续 优化 修复 改进 完善 处理一下 看一下 搞一下")
            has_fuzzy_verb = False
            fuzzy_verb = ""

            for verb in fuzzy_verbs.split():
                if verb in prompt_text:
                    has_fuzzy_verb = True
                    fuzzy_verb = verb
                    break

            if has_fuzzy_verb:
                # DF-01: 方向限定词检测
                if re.search(r'(从.{1,8}(上|角度|层面|方面)|针对.{1,12}|关于.{1,12}|在.{1,8}方面)', prompt_text):
                    has_fuzzy_verb = False
                    fuzzy_verb = ""

            if has_fuzzy_verb:
                prompt_len = len(prompt_text)
                has_structured = bool(re.search(r'(\|.*\|.*\|.*\||^#+\s|\*\*|`[^`]+`|---|\d+\.\s+\*\*)', prompt_text, re.MULTILINE))

                if prompt_len < 100 and not has_structured:
                    # 写模糊阻断标记
                    fuzzy_block_active = project_root / ".omc" / "state" / ".fuzzy-block-active"
                    fuzzy_block_active.write_text(f"指令含模糊动词'{fuzzy_verb}'。请指定 Step 编号/文件路径/功能名称", encoding="utf-8")

                # 检查活跃 feature 状态
                doc_search_path = project_root / doc_root
                incomplete_count = 0
                if doc_search_path.exists():
                    exec_files = sorted(doc_search_path.rglob(exec_doc), key=lambda p: p.stat().st_mtime, reverse=True)
                    if exec_files:
                        latest_exec = exec_files[0]
                        content = latest_exec.read_text(encoding="utf-8", errors="replace")
                        incomplete_count = len(re.findall(r'🔄|⏳|进行中|in.progress', content))

                # 收集具体上下文
                features = ""
                if doc_search_path.exists():
                    features = " ".join(sorted(d.name for d in doc_search_path.iterdir() if d.is_dir())[:5])

                scope_file_state = ""
                scope_file = project_root / ".omc" / "state" / "current-scope.txt"
                if scope_file.exists():
                    try:
                        scope_lines = len(scope_file.read_text(encoding="utf-8").splitlines())
                        scope_file_state = f"(scope: {scope_lines} entries)"
                    except OSError:
                        pass

                git_diff_stat = ""
                try:
                    result = subprocess.run(
                        ["git", "diff", "--stat"],
                        capture_output=True, text=True, timeout=5,
                        cwd=str(project_root)
                    )
                    if result.returncode == 0:
                        git_lines = [l.strip() for l in result.stdout.split("\n") if l.strip()][:3]
                        if git_lines:
                            git_diff_stat = "; ".join(git_lines)
                except Exception:
                    pass

                if incomplete_count > 1:
                    print(f"⚠️ 模糊指令检测: 指令含模糊动词'{fuzzy_verb}'但无明确目标，且有 {incomplete_count} 个活跃 Step。")
                    print("⛔ 停止执行！必须要求用户澄清具体目标 — 不允许猜测或默认推进(§1.6)。")
                    print("可能意图: A.修复阻塞Step B.继续开发进行中Step C.代码优化。请指定具体目标(§1.6)。")
                    print(f"当前 RPE 实例: {features} {scope_file_state}")
                    if git_diff_stat:
                        print(f"最近未提交修改: {git_diff_stat}")
                    feat_prefix = features.split()[0] if features.split() else ""
                    target = f"{feat_prefix}/handler.go" if feat_prefix else "handler.go"
                    print(f"建议: 指定文件路径（如 {target}）或 Step 编号")
                else:
                    print(f"⚠️ 模糊指令检测: 指令含模糊动词'{fuzzy_verb}'但无明确目标。请补充 Step 编号/文件路径/功能名称(§1.6)。")
                    print("⛔ 停止推测！必须先澄清 — 不明确的目标导致方向错误(§1.6)。")
                    print(f"当前 RPE 实例: {features} {scope_file_state}")
                    if git_diff_stat:
                        print(f"最近未提交修改: {git_diff_stat}")
                    print("建议: /lx-rpe status 查看进度 | 或指定具体文件路径")

    # ─── 多层 context window 提示策略 ───
    knowledge_min_turns = int(hc_get("turn_counter.knowledge_inject_min_turns", "20"))
    index_file = state_dir / "token-tracking-index.json"
    ctx_pct = None
    ctx_source = ""

    if new_count % 5 == 0:
        # 优先使用 context_monitor.py
        monitor_script = script_dir.parent / "scripts" / "context_monitor.py"
        if monitor_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(monitor_script)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    mon_data = json.loads(result.stdout)
                    pct_val = int(mon_data.get("percentage", 0))
                    if pct_val > 0:
                        ctx_pct = pct_val
                        ctx_source = mon_data.get("source", "")
            except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired, ValueError):
                pass

        # 兜底
        if ctx_pct is None or ctx_pct == 0:
            if index_file.exists():
                try:
                    with open(str(index_file), "r", encoding="utf-8") as f:
                        idx_data = json.load(f)
                    usage = int(idx_data.get("usage", 0))
                    limit = int(idx_data.get("limit", 200000))
                    if limit > 0:
                        ctx_pct = int(usage * 100 / limit)
                        ctx_source = "heuristic"
                except (json.JSONDecodeError, OSError, ValueError):
                    pass

    # 注入
    inject_index = project_root / ".claude" / "index.md"
    inject_kernel = project_root / ".claude" / "kernel.md"

    if ctx_pct is not None:
        ctx_source_label = ""
        if ctx_source == "heuristic":
            ctx_source_label = " [估算]"
        elif ctx_source:
            ctx_source_label = " [真实]"

        # L3: 危机协议 — context > 80%
        if ctx_pct >= 80 and new_count % 5 == 0:
            print("")
            print(f"═══ [轮次 {new_count}] 上下文危机 — context {ctx_pct}%{ctx_source_label} ═══")
            print("【仅 7 铁律】上下文使用率超过 80%，仅保留最低门禁规则：")
            print(" 1. 禁止编造：技术断言必须引用 file:line")
            print(" 2. 用户裁定：验收/选型/冲突由用户决定，AI 不可自判")
            print(" 3. 证据门禁：说'完成'前必须有 VERIFIED 证据")
            print(" 4. Git 门禁：commit/push 必须先报告，等用户批准")
            print(" 5. 范围冻结：只改当前任务文件，发现的问题记 TODO")
            print(" 6. 隐私防线：禁止读取 .env/私钥")
            print(" 7. 断言真实：百分比/评分必须有行业标准来源")
            print("")
            print("💡 建议运行 /compact 释放上下文空间后继续。")
            print("═══ 危机协议完成 ═══")

        # L2: 核心锚定 — context > 50%
        elif ctx_pct >= 50 and new_count > knowledge_min_turns:
            print("")
            print(f"═══ [轮次 {new_count}] 规范漂移检测 — context {ctx_pct}% > 50% ═══")
            print("【规范重新锚定】上下文使用率超出阈值，重新注入项目规范。")
            if inject_index.exists():
                content = inject_index.read_text(encoding="utf-8", errors="replace")
                for line in content.split("\n"):
                    if re.search(r'^\| \#', line):
                        print(line)
                print("")
                for line in content.split("\n"):
                    if re.search(r'^\|`[a-z]', line):
                        print(line)
            print("")
            print("═══ 规范重新锚定完毕 ═══")

        # L1: 摘要刷新 — context 30-50%
        elif ctx_pct >= 30 and new_count % 10 == 0:
            print("")
            print(f"═══ [轮次 {new_count}] 规范预防刷新 — context {ctx_pct}% ═══")
            print("【上下文摘要】当前使用率中等，注入内核关键规则：")
            if inject_kernel.exists():
                content = inject_kernel.read_text(encoding="utf-8", errors="replace")
                for line in content.split("\n"):
                    if re.search(r'^## |^- \*\*', line):
                        print(line)
            print("")
            print("═══ 预防刷新完毕 ═══")

        # L0: 全量预防 — context < 30%
        elif new_count % 15 == 0 and new_count > 5:
            print("")
            print(f"═══ [轮次 {new_count}] 全量规范预防注入 — context {ctx_pct}% ═══")
            print("【全量刷新】早期预防，确保规范始终锚定。")
            if inject_index.exists():
                content = inject_index.read_text(encoding="utf-8", errors="replace")
                for line in content.split("\n"):
                    if re.search(r'^\|#', line):
                        print(line)
            print("")
            print("═══ 全量注入完毕 ═══")

    flywheel_event("turn_counter", "turn_counted", "P2", f"turn_{new_count}_ctx_{ctx_pct or '?'}%")
    sys.exit(0)


if __name__ == "__main__":
    main()
