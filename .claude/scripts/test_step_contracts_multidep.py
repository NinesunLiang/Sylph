"""薄封装：step_contracts 依赖激活不变量已内建到 self_check()。

验证逻辑在 step_contracts.self_check()，本文件保留 pytest 入口 + 独立断言
防 self_check 退化。
"""
from step_contracts import _deps_all_completed, find_first_activatable_step
import step_contracts


def test_self_check_no_violations():
    assert step_contracts.self_check() == []


def test_multi_dep_all_completed_is_activatable():
    steps = [
        {"id": "S1", "status": "completed", "depends_on": "none"},
        {"id": "S2", "status": "completed", "depends_on": "S1"},
        {"id": "S3", "status": "completed", "depends_on": "S2"},
        {"id": "S4", "status": "completed", "depends_on": "S3"},
        {"id": "S5", "status": "completed", "depends_on": "S4"},
        {"id": "S6", "status": "pending", "depends_on": "S2,S3,S4"},
        {"id": "S7", "status": "pending", "depends_on": "S6"},
    ]
    assert find_first_activatable_step(steps) == "S6"


def test_deps_all_completed_helper():
    completed = {"S1", "S2", "S3", "S4", "S5"}
    assert _deps_all_completed("none", completed) is True
    assert _deps_all_completed("S2,S3,S4", completed) is True
    assert _deps_all_completed("S2,S3,S9", completed) is False
