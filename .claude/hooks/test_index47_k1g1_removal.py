"""index47 S3：K1/G1 编造检测删除回归（人类 2026-09-09 授权）。

保留：K2（EDIT_REPEAT 防抖，_autofix_log_edit_repeat）、E6、soft-completion 检测。
删除：K1/G1 数值断言来源强制（G1_PSEUDO_INTEGRITY / G1_MARKETING_CLAIM /
      _autofix_source_annotations）——12 天遥测中 G1_PSEUDO_INTEGRITY 零触发。

测量依据：`.omc/state/hook-evidence.jsonl` 与 `.omc/state/audit/*.jsonl` 中
`G1_PSEUDO_INTEGRITY` 命中数 = 0；`.claude/references/anti-patterns.md` K1 条目
自述最后触发 2026-08-14。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

HOOK = Path(__file__).resolve().parent / "posttool-claim-audit.py"


def _src() -> str:
    return HOOK.read_text(encoding="utf-8")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("claim_audit47", HOOK)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_g1_detection_removed():
    src = _src()
    for token in ("G1_PSEUDO_INTEGRITY", "G1_MARKETING_CLAIM", "_autofix_source_annotations"):
        assert token not in src, f"K1/G1 残留: {token}"


def test_k2_and_soft_completion_kept():
    src = _src()
    assert "_autofix_log_edit_repeat" in src, "K2（EDIT_REPEAT 防抖）被误删"
    assert "soft" in src.lower(), "soft-completion 检测被误删"
    assert "E6_VIOLATIONS" in src, "E6 自我矛盾检测被误删"


def test_module_still_importable_and_has_main():
    assert callable(_load().main)
