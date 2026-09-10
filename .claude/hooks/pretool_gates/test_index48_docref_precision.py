"""index48：doc-reference 门禁匹配精度修复（人类裁决：按 CarrorOS 哲学「修，不删」）。

问题（本轮实测触发）：
  门禁用 `grep -rl "<basename>"` 搜文档，是**子串匹配**。删除 `flywheel.py` 时，
  文档里提到的 `stop-flywheel.py`（**保留中的另一个文件**）被误判为「仍在引用 flywheel.py」，
  导致删除被 REDIRECT，重复两次后升级为 ASK_USER → 浪费一次人类裁决。

裁决依据：
  - 哲学#3 零信任：门禁自身的判定也必须经得起验证，子串匹配不算
  - 哲学#1 少即是多：用一次精确匹配替代粗匹配
  - 门禁意图正确（本轮它确实拦对过 scorecard.md 引用 error-dna 的真实案例）→ 故「修」而非「删」

修法：匹配改为「路径边界」——目标文件名前必须是行首或非 [A-Za-z0-9_.-] 字符。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))


def test_substring_collision_is_not_a_reference(tmp_path):
    """stop-flywheel.py 不得被当作 flywheel.py 的引用。"""
    from pretool_gates.checks import _doc_reference_hits

    doc = tmp_path / "adr.md"
    doc.write_text("见 stop-flywheel.py 与 lib/flywheel.py 二者\n", encoding="utf-8")

    hits = _doc_reference_hits(str(tmp_path), "flywheel.py")
    assert len(hits) == 1, f"应只命中真正的 flywheel.py 一处: {hits}"


def test_plain_mention_still_detected(tmp_path):
    """真正的引用必须仍然被检出（不得为降误报而漏报）。"""
    from pretool_gates.checks import _doc_reference_hits

    (tmp_path / "a.md").write_text("调用 flywheel.py 完成升华\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("路径 .claude/scripts/lib/flywheel.py 见下\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("`flywheel.py` 是模块\n", encoding="utf-8")

    hits = _doc_reference_hits(str(tmp_path), "flywheel.py")
    assert len(hits) == 3, f"三处真引用都应命中: {hits}"


def test_no_reference_returns_empty(tmp_path):
    from pretool_gates.checks import _doc_reference_hits

    (tmp_path / "a.md").write_text("只提到 stop-flywheel.py\n", encoding="utf-8")
    assert _doc_reference_hits(str(tmp_path), "flywheel.py") == []
