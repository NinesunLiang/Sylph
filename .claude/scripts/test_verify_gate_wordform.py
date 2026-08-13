"""薄封装：verify_gate 词形归一不变量已内建到 self_check()。

验证逻辑在 verify_gate.self_check()（启动时 fail-closed），本文件仅保留
pytest 入口验证 self_check 无违规，并提供独立回归断言（防 self_check 退化）。
"""
import verify_gate as vg


def test_self_check_wordform_no_violations():
    assert vg.self_check() == []


def test_exist_exists_core_term_match():
    """exist/exists 词形归一仍匹配（防 self_check 覆盖退化）。"""
    ev = {"type": "test", "assertion": "artifacts exists（10/10 exit 0）",
          "evidence_level": "E3", "exit_code": 0}
    ok, reason, _ = vg.match_verify_rule("assertion: artifacts exist", [ev])
    assert ok, reason
