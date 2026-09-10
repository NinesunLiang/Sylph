"""index48：E6 死分支剪除（人类裁决 2026-09-10，选项 B「删死枝，留活枝」）。

**删除依据（实测，排除 /tmp 测试夹具）**：
- E6-CONTRADICTION：唯一写入方 `posttool-claim-audit` 的 churn 写入**硬编码 `contradiction: False`**，
  读取方判 `is True` → **结构上不可能触发**。263 条真实记录中为 0。
- E6-REVERT-DETECTED：**注意措辞**——其写入侧已于 2026-08-12 修好（非结构性死），
  但此后 263 条真实记录中 `revert_of` **全为空**（12 天零触发），
  且该字段的计算需**每次编辑全量读一遍 churn 日志** → 按「收益大才留」判为有成本无收益。

**保留依据（人类 2026-09-09 裁决：「保留 K2（EDIT_REPEAT 防抖）」）**：
- E6-EDIT_REPEAT + E6-CONTENT_FLIP 具备触发条件（真实数据 edit_count 最大 16），
  且 EDIT_REPEAT 正是 K2 autofix (`_autofix_log_edit_repeat`) 的调用点 → **原封保留**。
- HIGH_CHURN（仅 stderr 提示，非违规）保留。
"""
from __future__ import annotations

from pathlib import Path

HOOK = Path(__file__).resolve().parent / "posttool-claim-audit.py"


def _src() -> str:
    return HOOK.read_text(encoding="utf-8")


def _code() -> str:
    return "\n".join(
        l.split("#", 1)[0] for l in _src().splitlines() if l.split("#", 1)[0].strip()
    )


def test_dead_branches_removed():
    """只认「分支标记」——`E6_SELF_CONTRADICTION` 是维度标签，属正当保留。"""
    code = _code()
    for token in ("[E6] CONTRADICTION", "[E6] REVERT_DETECTED"):
        assert token not in code, f"死分支未剪除: {token}"


def test_dead_field_reads_removed():
    """两个死分支依赖的字段读取也应一并移除。"""
    code = _code()
    assert "contradiction" not in code, "仍读取永不触发 contradiction 字段"
    assert "revert_of" not in code, "仍读取永不为真的 revert_of 字段"


def test_k2_live_branches_kept():
    """人类裁决保留 K2 —— EDIT_REPEAT / CONTENT_FLIP / autofix 调用点必须原封不动。"""
    code = _code()
    assert "EDIT_REPEAT" in code, "K2 的 EDIT_REPEAT 分支被误删"
    assert "CONTENT_FLIP" in code, "CONTENT_FLIP 分支被误删"
    assert "_autofix_log_edit_repeat" in code, "K2 autofix 调用点被误删"
    assert "HIGH_CHURN" in code, "HIGH_CHURN 观测被误删"


def test_churn_log_writer_kept():
    """churn 写入是 E6 活分支的数据源，必须保留。"""
    assert "edit-churn-log" in _code(), "churn-log 写入被误删"


def test_if_chain_still_valid():
    """剪除 elif 分支后，控制流必须仍成立（可编译）。"""
    import py_compile
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as fh:
        fh.write(_src().encode("utf-8"))
        tmp = fh.name
    py_compile.compile(tmp, doraise=True)
