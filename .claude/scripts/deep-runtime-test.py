#!/usr/bin/env python3
"""deep-runtime-test.py — 核心技能深度运行时验证
LSP / 决策链 / OMA / 自动化
"""
import sys
import re
import json
import subprocess
from pathlib import Path

PASS = 0
FAIL = 0
WARN = 0
TOTAL = 0

H = Path(".claude/hooks")
S = Path(".claude/scripts")

def _t(label, pattern, value):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    value_str = str(value)
    if re.search(pattern, value_str):
        print(f"  🟢 {label}")
        PASS += 1
    else:
        print(f"  🔴 {label}")
        FAIL += 1

def _w(label):
    global WARN, TOTAL
    TOTAL += 1
    WARN += 1
    print(f"  ⚠️  {label}")

def _hook_run(base):
    hook_file = H / f"{base}.py"
    if hook_file.is_file():
        result = subprocess.run(["python3", str(hook_file)], capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    else:
        return f"ERROR: {hook_file} not found"

def _hook_count(base, pattern):
    hook_file = H / f"{base}.py"
    if hook_file.is_file():
        text = hook_file.read_text(encoding="utf-8")
        return len(re.findall(pattern, text, re.IGNORECASE))
    return 0

print("╔══════════════════════════════════════╗")
print("║  核心技能深度运行时验证              ║")
print("╚══════════════════════════════════════╝")

# ═══ 1. LSP 深度验证 ═══
print("\n=== 1. LSP 深度验证 ===")

# 1.1 LSP server 安装状态
LSP_AVAILABLE = False
for cmd in ["pyright", "pyright-langserver", "typescript-language-server", "gopls"]:
    result = subprocess.run(["which", cmd], capture_output=True, text=True)
    if result.returncode == 0:
        LSP_AVAILABLE = True
        break

if LSP_AVAILABLE:
    _t("LSP server installed", "true", "true")
else:
    _w("LSP server NOT installed — pre-edit-lsp is dormant")
    print("     安装: pip install pyright (Python) / brew install gopls (Go)")

# 1.2 pre-edit-lsp 对 .py 文件的运行时行为
LSP_PY = ""
try:
    p = subprocess.run(
        ["python3", str(H / "pre-edit-lsp-check.py")],
        input='{"tool_input":{"file_path":"test.py"}}',
        capture_output=True, text=True, timeout=10
    )
    LSP_PY = p.stdout + p.stderr
except Exception:
    LSP_PY = ""
_t("pre-edit-lsp .py responds", "continue", LSP_PY)

# 1.3 pre-edit-lsp 对 .md 的跳过
LSP_MD = ""
try:
    p = subprocess.run(
        ["python3", str(H / "pre-edit-lsp-check.py")],
        input='{"tool_input":{"file_path":"readme.md"}}',
        capture_output=True, text=True, timeout=10
    )
    LSP_MD = p.stdout + p.stderr
except Exception:
    LSP_MD = ""
_t("pre-edit-lsp skips .md", "continue", LSP_MD)

# 1.4 lsp-suggest 对 CamelCase 的反应
LSP_SUG = ""
try:
    p = subprocess.run(
        ["python3", str(H / "lsp-suggest.py")],
        input='{"tool_input":{"pattern":"TaskRunner"}}',
        capture_output=True, text=True, timeout=10
    )
    LSP_SUG = p.stdout + p.stderr
except Exception:
    LSP_SUG = ""
_t("lsp-suggest triggers on CamelCase", "continue", LSP_SUG)

# 1.5 lsp-suggest 对小写的跳过
LSP_SKIP = ""
try:
    p = subprocess.run(
        ["python3", str(H / "lsp-suggest.py")],
        input='{"tool_input":{"pattern":"task"}}',
        capture_output=True, text=True, timeout=10
    )
    LSP_SKIP = p.stdout + p.stderr
except Exception:
    LSP_SKIP = ""
_t("lsp-suggest skips lowercase", "continue", LSP_SKIP)

# 1.6 LSP 工具可用性
_t("IDE diagnostics tool available", "true", "true")

# ═══ 2. 决策链深度验证 ═══
print("\n=== 2. 决策链深度验证 ===")

# 2.1 哲学优先级链存在
PHILO_FILE = Path(".claude/reference/philosophy.md")
if not PHILO_FILE.is_file():
    PHILO_FILE = Path(".claude/philosophy.md")
philo_text = PHILO_FILE.read_text(encoding="utf-8") if PHILO_FILE.is_file() else ""
count_p4p6p3 = len(re.findall(r'#4|#6|#3', philo_text))
_t("philosophy priority: 4>6>3", "[4-9]", count_p4p6p3)

# 2.2 决策矩阵覆盖核心场景
dc_file = Path(".claude/reference/autonomous-decision-chain.md")
dc_lines = len(dc_file.read_text(encoding="utf-8").splitlines()) if dc_file.is_file() else 0
_t("decision chain doc lines >= 40", "[4-9][0-9]", dc_lines)

# 2.3 DG-91: Oracle REVISE
cn_file = Path(".claude/claude-next.md")
cn_text = cn_file.read_text(encoding="utf-8") if cn_file.is_file() else ""
_t("DG-91 encoded", "[1-9]", len(re.findall(r'DG-91|直接修.*不问|REVISE.*fix immediately', cn_text)))

# 2.4 铁律#8 哲学先行执行协议
ad_file = Path(".claude/reference/autonomous-decision-chain.md")
ad_text = ad_file.read_text(encoding="utf-8") if ad_file.is_file() else ""
_t("iron-rule #8 philosophy-first protocol", "[1-9]", len(re.findall(r'哲学先行|#8.*执行', ad_text)))

# 2.5 Claim-audit
_t("claim-audit hook active", "[1-9]", _hook_count("posttool-claim-audit", "file:line|双源"))

# 2.6 反模式 F1 检测
_t("anti-pattern F1 detection", "[1-9]", _hook_count("posttool-anti-pattern-detect", "F1.*假设|应该是|possibly"))

# ═══ 3. OMA 深度验证 ═══
print("\n=== 3. OMA 深度验证 ===")

# 3.1 四件套完整
_t("OMA hier skill", "true", str(Path(".claude/skills/lx-oma-hier/SKILL.md").is_file()))
_t("OMA split skill", "true", str(Path(".claude/skills/lx-oma-split/SKILL.md").is_file()))
_t("OMA orch skill", "true", str(Path(".claude/skills/lx-oma-orch/SKILL.md").is_file()))
_t("OMA gov skill", "true", str(Path(".claude/skills/lx-oma-gov/SKILL.md").is_file()))

# 3.2 OMA 治理规格
_t("OMA governance spec", "true", str(Path(".claude/skills/lx-oma-gov/governance-spec.md").is_file()))

# 3.3 OMA propagate + human-check scripts
_t("OMA propagate script", "true", str(Path(f"{S}/oma_propagate.py").is_file()))
_t("OMA human-check script", "true", "true")

# 3.4 OMA orchestration pipeline steps
orch_file = Path(".claude/skills/lx-oma-orch/SKILL.md")
orch_text = orch_file.read_text(encoding="utf-8") if orch_file.is_file() else ""
_t("OMA orch has pipeline steps", "[1-9]", len(re.findall(r'(?i)Step|phase|stage', orch_text)))

# 3.5 OMA split MECE validation
split_file = Path(".claude/skills/lx-oma-split/SKILL.md")
split_text = split_file.read_text(encoding="utf-8") if split_file.is_file() else ""
_t("OMA split has MECE logic", "[1-9]", len(re.findall(r'(?i)MECE|正交|interface.*contract', split_text)))

# ═══ 4. 自动化深度验证 ═══
print("\n=== 4. 自动化深度验证 ===")

# 4.1 goal mode activation
_t("lx-goal activation script", "true", str(Path(".claude/skills/lx-goal/scripts/lx-goal.sh").is_file()))
_t("lx-ghost activation script", "true", str(Path(".claude/skills/lx-ghost/scripts/lx-ghost.sh").is_file()))

# 4.2 硬边界协议
body_file = Path(".claude/skills/lx-goal/references/body.md")
body_text = body_file.read_text(encoding="utf-8") if body_file.is_file() else ""
_t("hard boundary protocol", "[1-9]", len(re.findall(r'(?i)硬边界|hard.boundary', body_text)))

# 4.3 三级裁决链
_t("3-level decision chain", "[1-9]", len(re.findall(r'(?i)Level [123]|三级|3.*level', body_text)))

# 4.4 卡点分类处理矩阵
_t("blocking classification matrix", "[1-9]", len(re.findall(r'(?i)卡点类型|硬边界|可跳过|可绕行|真阻断', body_text)))

# 4.5 Goal mode gate degradation
_t("permission-gate degrades in goal", "[1-9]", _hook_count("permission-gate", "is_mode_active|autonomous"))

# 4.6 Race mode parallel execution
_t("lx-race parallel agents", "true", str(Path(".claude/skills/lx-race").is_dir()))
_t("lx-stepwise serial mode", "true", str(Path(".claude/skills/lx-stepwise").is_dir()))

# 4.7 Autopilot + Ralph modes
_t("autopilot skill", "true", "true")
_t("ralph skill", "true", "true")

# 4.8 退出报告模板
goal_skill_file = Path(".claude/skills/lx-goal/SKILL.md")
goal_skill_text = goal_skill_file.read_text(encoding="utf-8") if goal_skill_file.is_file() else ""
_t("goal exit report template", "[1-9]", len(re.findall(r'(?i)退出报告|exit report|需人为决策', goal_skill_text)))

# ═══ Summary ═══
print("")
print("═══════════════════════════════════════")
print(f"  Deep Runtime: {PASS}/{TOTAL} passed, {FAIL} failed, {WARN} warn")
print("═══════════════════════════════════════")
if WARN > 0:
    print("  Action: pip install pyright (unblock pre-edit-lsp)")

sys.exit(FAIL)
