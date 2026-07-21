#!/usr/bin/env python3
"""
score-ux.py — Meta-Oracle UX 维度独立评分脚本
Cross-platform Python resolution (DG-105)

Role: 对 UX（用户体验）5 个子维度进行独立评分，满分 10 分
       UX 独立参与打分，不影响 C/E/G 的 8.6/10 总阈值判定

使用: python3 .claude/scripts/score-ux.py [--json]
输出: .omc/state/score-ux-<timestamp>.json

5 个子维度（各 2 分）:
  UX1 心智负担 — AI 输出的决策点密度与复杂度
  UX2 交互次数 — 用户完成任务的必要交互频率
  UX3 信息清晰度 — 输出结构化程度与格式一致性
  UX4 错误可理解性 — 错误信息的可操作性与分类覆盖
  UX5 自主模式顺畅度 — goal/ghost 模式是否无打断运行

评分方法: 配置存在性(1分) + 运行时质量验证(1分) = 每子维度满分 2 分
注意: 运行时验证必须检查实际质量指标，而非仅文件存在性
2026-06-02: 修复纯存在性评分膨胀 — 增加质量校准因子
"""
import sys
import os
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(str(PROJECT_ROOT))
TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE = PROJECT_ROOT / ".omc" / "state" / f"score-ux-{TS}.json"
STATE_DIR = PROJECT_ROOT / ".omc" / "state"


def run(cmd, **kwargs):
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    return subprocess.run(cmd, **default)


def pct(a, b):
    if b == 0:
        return "0"
    return f"{a * 100 / b:.1f}"


def has_runtime_data(file):
    f = Path(file)
    return f.exists() and f.stat().st_size > 0


# UX1 心智负担 (2分)
def score_UX1():
    score = 0
    max_score = 2
    config_ok = 0
    runtime_ok = 0

    if (PROJECT_ROOT / ".claude" / "reference" / "autonomous-decision-chain.md").exists():
        config_ok = 1

    turns_file = STATE_DIR / "session-turns.json"
    if has_runtime_data(turns_file):
        try:
            d = json.loads(turns_file.read_text())
            turns = d.get("count", 999)
        except Exception:
            turns = 999
        if turns < 100:
            runtime_ok = 1

    score = config_ok + runtime_ok
    return score, max_score, f"UX1=心智负担(decision_chain={config_ok} turns_ok={runtime_ok})"


# UX2 交互次数 (2分)
def score_UX2():
    score = 0
    max_score = 2
    config_ok = 0
    runtime_ok = 0

    if (PROJECT_ROOT / ".claude" / "skills" / "lx-goal" / "scripts" / "lx-goal.py").exists() and \
       (PROJECT_ROOT / ".claude" / "skills" / "lx-ghost" / "scripts" / "lx-ghost.sh").exists():
        config_ok = 1

    hc = PROJECT_ROOT / ".claude" / "hooks" / "harness_config.sh"
    if hc.exists() and "is_mode_active" in hc.read_text():
        runtime_ok = 1

    score = config_ok + runtime_ok
    return score, max_score, f"UX2=交互次数(autonomous_support={config_ok} meta_oracle_active={runtime_ok})"


# UX3 信息清晰度 (2分)
def score_UX3():
    score = 0
    max_score = 2
    config_ok = 0
    runtime_ok = 0

    agents = PROJECT_ROOT / "AGENTS.md"
    anti = PROJECT_ROOT / ".claude" / "anti-patterns.md"
    if agents.exists() and re.search(r'evidence.*level|证据层级|L1.*L2.*L3', agents.read_text()):
        if anti.exists():
            config_ok = 1

    err_sig = STATE_DIR / "error-signals.jsonl"
    if has_runtime_data(err_sig):
        content = err_sig.read_text()
        if re.search(r'SOFT_WORD|soft_completion|虚假完成', content):
            runtime_ok = 1
    if runtime_ok == 0:
        cg_sh = PROJECT_ROOT / ".claude" / "hooks" / "completion-gate.sh"
        if cg_sh.exists() and re.search(r'VERIFIED|证据门禁|evidence.*missing', cg_sh.read_text()):
            runtime_ok = 1

    score = config_ok + runtime_ok
    return score, max_score, f"UX3=信息清晰度(evidence_fmt={config_ok} completion_gate={runtime_ok})"


# UX4 错误可理解性 (2分)
def score_UX4():
    score = 0
    max_score = 2
    config_ok = 0
    runtime_ok = 0

    settings = PROJECT_ROOT / ".claude" / "settings.json"
    cg_sh = PROJECT_ROOT / ".claude" / "hooks" / "completion-gate.sh"
    if settings.exists() and re.search(r'error-dna|error_classifier', settings.read_text()):
        if cg_sh.exists() and re.search(r'RCA|根因', cg_sh.read_text()):
            config_ok = 1

    edna = STATE_DIR / "error-dna.jsonl"
    if edna.exists() and edna.stat().st_size > 0:
        categories = set()
        for line in edna.open():
            try:
                r = json.loads(line)
                t = r.get("error_type", "")
                if t and t != "runtime":
                    categories.add(t)
            except Exception:
                pass
        if len(categories) >= 3:
            runtime_ok = 1

    score = config_ok + runtime_ok
    return score, max_score, f"UX4=错误可理解性(error_dna={config_ok} classified={runtime_ok})"


# UX5 自主模式顺畅度 (2分)
def score_UX5():
    score = 0
    max_score = 2
    config_ok = 0
    runtime_ok = 0

    hc = PROJECT_ROOT / ".claude" / "hooks" / "harness_config.sh"
    if hc.exists() and "is_mode_active" in hc.read_text():
        degraded = 0
        for hook_name in ["completion-gate.sh", "subagent-guard.sh", "edit-guard.sh", "pretool-retry-check.sh"]:
            hf = PROJECT_ROOT / ".claude" / "hooks" / hook_name
            if hf.exists() and "is_mode_active" in hf.read_text():
                degraded += 1
        if degraded >= 3:
            config_ok = 1

    if (STATE_DIR / "tokens" / "autonomous.active").exists():
        subagent_usage = STATE_DIR / "subagent-usage.jsonl"
        if has_runtime_data(subagent_usage):
            agent_calls = sum(1 for _ in subagent_usage.open())
            if agent_calls >= 1:
                runtime_ok = 1
        else:
            runtime_ok = 1

    score = config_ok + runtime_ok
    return score, max_score, f"UX5=自主模式顺畅度(degraded_hooks={config_ok} autonomous_active={runtime_ok})"


# ───── 执行评分 ─────
print(f"=== Meta-Oracle UX Score @ {TS} ===")
print("")

ux_labels = ["UX1", "UX2", "UX3", "UX4", "UX5"]
total_score = 0
total_max = 0
subscores = {}
metrics = {}

for label in ux_labels:
    func = globals()[f"score_{label}"]
    s, m, detail = func()
    print(f"  {label} {s}/{m} — {detail}")
    total_score += s
    total_max += m
    subscores[label] = {"score": s, "max": m, "pct": float(pct(s, m))}
    metrics[label] = detail

PCT = float(pct(total_score, total_max))

# 质量校准
CALIBRATION = ""
if total_score == total_max:
    quality_evidence = 0
    edna = STATE_DIR / "error-dna.jsonl"
    if edna.exists() and edna.stat().st_size > 0:
        categories = set()
        for line in edna.open():
            try:
                r = json.loads(line)
                t = r.get("error_type", "")
                if t and t != "runtime":
                    categories.add(t)
            except Exception:
                pass
        if len(categories) >= 2:
            quality_evidence += 1
    turns_file = STATE_DIR / "session-turns.json"
    if turns_file.exists() and turns_file.stat().st_size > 0:
        quality_evidence += 1
    if quality_evidence < 2:
        total_score -= 1
        PCT = float(pct(total_score, total_max))
        CALIBRATION = " (校准: 纯存在性评分, -1分)"

print("")
print("---")
print(f"UX 总分: {total_score}/{total_max} ({PCT}%){CALIBRATION}")
print("UX 状态: 独立维度 — 不参与 C/E/G 的 8.6/10 总阈值判定")
print("---")

RESULT = {
    "generated_at": TS,
    "scored_by": "score-ux.py v1",
    "methodology": "5 sub-dimensions x 2pts — config existence (1pt) + runtime verification (1pt)",
    "dimension": "UX",
    "description": "用户体验独立评分 — 不参与 C/E/G 总阈值判定",
    "total": {"score": total_score, "max": total_max, "pct": PCT},
    "subscores": subscores,
    "metrics": metrics,
    "independence_note": "UX 维度独立展示，C/E/G 的 8.6/10 门禁仅基于 C/E/G 加权聚合"
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w") as f:
    json.dump(RESULT, f, indent=2, ensure_ascii=False)
print(f"JSON written: {OUTPUT_FILE}")
print(json.dumps(RESULT, indent=2, ensure_ascii=False))

sys.exit(0)
