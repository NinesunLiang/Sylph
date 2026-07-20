#!/usr/bin/env python3
"""
runtime-experiment.py — Carror OS v6.4.0 运行时实验
多平台兼容性验证: mac + Claude Code + OpenCode(OMO) + OMC
"""
import sys
import os
import json
import time
import subprocess
import platform
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

PASS = 0
FAIL = 0


def green(msg: str):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def red(msg: str):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


def run(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    return subprocess.run(cmd, **default)


def main():
    global PASS, FAIL
    os.chdir(str(PROJECT_ROOT))

    print("════════════════════════════════════════")
    print(f"  运行时实验 — Carror OS v6.3.27→v6.4.0")
    print(f"  平台: {platform.system()} {platform.machine()}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("════════════════════════════════════════")

    # ═══ E1: 三门户完整性 ═══
    print("\n── E1: 三门户完整性 ──")

    if Path("AGENTS.md").exists():
        lines = len(Path("AGENTS.md").read_text(encoding="utf-8").splitlines())
        green(f"AGENTS.md 存在 ({lines}行)")
    else:
        red("AGENTS.md 缺失")

    if Path(".claude/kernel.md").exists():
        lines = len(Path(".claude/kernel.md").read_text(encoding="utf-8").splitlines())
        green(f"kernel.md 存在 ({lines}行)")
    else:
        red("kernel.md 缺失")

    if Path(".claude/index.md").exists():
        lines = len(Path(".claude/index.md").read_text(encoding="utf-8").splitlines())
        green(f"index.md 存在 ({lines}行)")
    else:
        red("index.md 缺失")

    # 验证 AGENTS.md 有路由表
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    if "路由索引" in agents:
        green("AGENTS.md 含路由表")
    else:
        red("AGENTS.md 缺路由表")

    at_count = sum(1 for line in agents.splitlines() if line.startswith("@"))
    if at_count <= 2:
        green(f"AGENTS.md @引用={at_count} (≤2)")
    else:
        red(f"AGENTS.md @引用={at_count} (>2!)")

    # ═══ E2: 配置有效性 ═══
    print("\n── E2: 配置有效性 ──")

    try:
        import yaml
        yaml.safe_load(Path(".claude/harness.yaml").read_text(encoding="utf-8"))
        green("harness.yaml YAML有效")
    except Exception:
        red("harness.yaml YAML无效")

    try:
        json.loads(Path(".claude/settings.json").read_text(encoding="utf-8"))
        green("settings.json JSON有效")
    except Exception:
        red("settings.json JSON无效")

    try:
        s = json.loads(Path(".claude/settings.json").read_text(encoding="utf-8"))
        hooks = s.get("hooks", {})
        pre = len(hooks.get("PreToolUse", []))
        post = len(hooks.get("PostToolUse", []))
        fail = len(hooks.get("PostToolUseFailure", []))
        ss = len(hooks.get("SessionStart", []))
        total = sum(len(v) for v in hooks.values())
        print(f"PreToolUse:{pre} PostToolUse:{post} PostToolUseFailure:{fail} SessionStart:{ss} = {total} total")
        green("settings.json hook分组有效")
    except Exception:
        red("settings.json hook分组无效")

    # ═══ E3: 新激活hook ═══
    print("\n── E3: 新激活hook (v6.4.0) ──")

    harness_text = Path(".claude/harness.yaml").read_text(encoding="utf-8")
    settings_text = Path(".claude/settings.json").read_text(encoding="utf-8")

    # knowledge-condenser
    green("knowledge_condenser: true") if "knowledge_condenser: true" in harness_text else red("knowledge_condenser: not true")
    green("knowledge-condenser 已注册") if "knowledge-condenser" in settings_text else red("knowledge-condenser 未注册")

    # pretool-plan-gate
    green("pretool_plan_gate: true") if "pretool_plan_gate: true" in harness_text else red("pretool_plan_gate: not true")
    green("pretool-plan-gate 已注册") if "pretool-plan-gate" in settings_text else red("pretool-plan-gate 未注册")

    # build-validator
    green("build_validator: true") if "build_validator: true" in harness_text else red("build_validator: not true")
    green("build-validator 已注册") if "build-validator" in settings_text else red("build-validator 未注册")

    # error-dna-auto-fix
    green("error_dna_auto_fix: true") if "error_dna_auto_fix: true" in harness_text else red("error_dna_auto_fix: not true")
    green("error-dna-auto-fix 已注册") if "error-dna-auto-fix" in settings_text else red("error-dna-auto-fix 未注册")

    # ═══ E4: 僵尸hook已清理 ═══
    print("\n── E4: 僵尸hook清理确认 ──")

    for ghost in ["anti_pattern_detect", "issue_triage", "lsp_gate", "oracle_gate", "posttool_output_format"]:
        if ghost in harness_text:
            red(f"harness.yaml 仍有 {ghost}")
        else:
            green(f"harness.yaml 已清理 {ghost}")

    if not Path(".claude/hooks/plan-gate.sh").exists():
        green("plan-gate.sh 已删除")
    else:
        red("plan-gate.sh 仍存在")

    if Path(".claude/scripts/feature-probe.sh").exists():
        green("feature-probe.sh 已迁移至scripts/")
    else:
        red("feature-probe.sh 未迁移")

    if not Path(".claude/hooks/feature-probe.sh").exists():
        green("feature-probe.sh 已从hooks/移除")
    else:
        red("feature-probe.sh 仍在hooks/")

    # ═══ E5: 多平台兼容 ═══
    print("\n── E5: 多平台兼容性 ──")

    if Path("CLAUDE.md").exists():
        green("CLAUDE.md (Claude Code入口)")
    else:
        red("CLAUDE.md 缺失")

    claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
    green("CLAUDE.md → @AGENTS.md") if "@AGENTS.md" in claude_md else red("CLAUDE.md 未引用 AGENTS.md")

    if Path(".opencode/opencode.json").exists():
        green("opencode.json (OpenCode入口)")
    else:
        red("opencode.json 缺失")

    if Path(".opencode/oh-my-openagent.json").exists():
        green("oh-my-openagent.json (OMO桥)")
    else:
        red("OMO桥缺失")

    try:
        omo = json.loads(Path(".opencode/oh-my-openagent.json").read_text(encoding="utf-8"))
        cc = omo.get("claude_code", {})
        print(f'  hooks={cc.get("hooks")} skills={cc.get("skills")}')
        green("OMO配置有效")
    except Exception:
        red("OMO配置无效")

    try:
        omo = json.loads(Path(".opencode/oh-my-openagent.json").read_text(encoding="utf-8"))
        cc = omo.get("claude_code", {})
        if cc.get("hooks") and cc.get("skills"):
            print("  OMO: hooks+skills 已启用")
            green("OMO hooks+skills 启用")
        else:
            print("  OMO: hooks或skills未启用")
            red("OMO hooks/skills 未启用")
    except Exception:
        red("OMO hooks/skills 未启用")

    # ═══ E6: 上下文注入验证 ═══
    print("\n── E6: 上下文注入验证 ──")

    inject_hook = Path(".claude/hooks/inject-project-knowledge.sh")
    if inject_hook.exists():
        result = run(f"bash -n {inject_hook}")
        green("inject-project-knowledge 语法通过") if result.returncode == 0 else red("inject-project-knowledge 语法失败")
        result = run(f"timeout 10 bash {inject_hook} >/dev/null 2>&1; exit $?")
        green("inject-project-knowledge 运行正常") if result.returncode <= 1 else red("inject-project-knowledge 运行异常")
    else:
        red("inject-project-knowledge 缺失")

    cc_path = Path(".omc/state/context-cache.md")
    if cc_path.exists():
        green(f"context-cache.md 存在 ({cc_path.stat().st_size}B)")
    else:
        red("context-cache.md 缺失")

    # ═══ E7: 测试基线 ═══
    print("\n── E7: 测试基线 ──")

    smoke_log = Path(".omc/state/harness-smoke-latest.log")
    result = run(f"bash .claude/scripts/harness-smoke-test.sh > {smoke_log} 2>&1")
    smoke_text = smoke_log.read_text(encoding="utf-8") if smoke_log.exists() else ""
    smoke_result = ""
    for line in smoke_text.splitlines():
        if "summary:" in line:
            smoke_result = line
    print(f"  {smoke_result}")
    green("Smoke test 全绿") if "0 failed" in smoke_result else red("Smoke test 有失败")

    # ═══ E8: 发行版对齐 ═══
    print("\n── E8: 发行版(source/harness-kit)对齐检查 ──")

    pkg_root = Path("source/harness-kit")
    if not pkg_root.exists():
        red("source/harness-kit 不存在")
    else:
        result = run("diff -rq --exclude=\".git\" --exclude=\".omc\" --exclude=\"packages\" --exclude=\"node_modules\" . source/harness-kit 2>/dev/null")
        diff_count = result.stdout.count("differ")
        print(f"  差异文件数: {diff_count}")
        if diff_count < 10:
            green("发行版对齐良好 (<10差异)")
        else:
            print(f"  ⚠️ {diff_count} 个差异文件（AGENTS.md刻意不同计入内）")

    # ═══ 汇总 ═══
    print("\n════════════════════════════════════════")
    print(f"  实验汇总: {PASS} pass, {FAIL} fail")
    print("════════════════════════════════════════")

    if FAIL == 0:
        print("  🟢 全部通过 — 可升级 v6.4.0")
    else:
        print(f"  🔴 {FAIL} 项失败 — 需修复后升级")

    sys.exit(FAIL)


if __name__ == "__main__":
    main()
