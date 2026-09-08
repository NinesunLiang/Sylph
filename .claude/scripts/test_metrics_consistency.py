"""test_metrics_consistency.py — 评测口径一致性锁（PLAN_SIMPLIFY B3/Phase 1）

Benchmarking/metrics-card.md（真源）与 judge-prompt 的 C/E 权重必须一致：
C 权重和 105、E 权重和 110；若漂移，防 index40 法官口径打架复发。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

C_EXPECT = [15, 15, 15, 10, 10, 10, 10, 10, 10]
E_EXPECT = [20, 20, 15, 12, 10, 13, 10, 10]

JUDGE_PROMPT_CANDIDATES = [
    REPO / ".omc" / "archive" / "20260831_index44双法官盲评-CarrorOS-真实-AI-治理效能真实-spawn-空-872f102c"
            / "index44双法官盲评-CarrorOS-真实-AI-治理效能真实-spawn-空-872f102c" / "scripts" / "judge-prompt.md",
    REPO / ".omc" / "tasks" / "20260908" / "index45-双法官复测-修复后-真实spawn-空" / "scripts" / "judge-prompt.md",
]


def _weights_from_table(text: str, prefix: str) -> list[int]:
    out = {}
    for m in re.finditer(rf"\| {prefix}(\d) \| [^|]* \| (\d+) \|", text):
        out[int(m.group(1))] = int(m.group(2))
    return [out[i] for i in sorted(out)]


def _weights_from_prompt(text: str, prefix: str) -> list[int]:
    # 例：C1 指令清晰度(15) / C2 ...(15)
    pairs = [(int(idx), int(w)) for idx, w in re.findall(rf"{prefix}(\d+)[^)]*\((\d+)\)", text)]
    return [w for _, w in sorted(pairs)]


def _read(p: Path) -> str:
    assert p.exists(), f"missing {p}"
    return p.read_text(encoding="utf-8")


def test_metrics_card_c_weights_sum_105():
    text = _read(REPO / "Benchmarking" / "metrics-card.md")
    assert _weights_from_table(text, "C") == C_EXPECT
    assert sum(C_EXPECT) == 105


def test_metrics_card_e_weights_sum_110():
    text = _read(REPO / "Benchmarking" / "metrics-card.md")
    assert _weights_from_table(text, "E") == E_EXPECT
    assert sum(E_EXPECT) == 110


def test_judge_prompt_matches_metrics_card():
    card = _read(REPO / "Benchmarking" / "metrics-card.md")
    cw, ew = _weights_from_table(card, "C"), _weights_from_table(card, "E")
    checked = 0
    for jp in JUDGE_PROMPT_CANDIDATES:
        if not jp.exists():
            continue
        t = _read(jp)
        assert _weights_from_prompt(t, "C") == cw, f"judge-prompt C 权重与 metrics-card 不一致: {jp}"
        assert _weights_from_prompt(t, "E") == ew, f"judge-prompt E 权重与 metrics-card 不一致: {jp}"
        checked += 1
    assert checked >= 1, "未找到可校验的 judge-prompt 副本"
