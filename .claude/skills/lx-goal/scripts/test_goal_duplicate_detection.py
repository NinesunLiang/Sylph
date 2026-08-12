"""精专化测试：lx-goal 同目标并发激活检测（C7 提分）。

验证：
1. _goal_base 正确提取语义 base（去随机后缀）
2. _find_active_goal 检测到同 base 已有活跃任务（.lock 或 state=active）
3. 无活跃任务时不误报
"""
import importlib.util
import json
import sys
from pathlib import Path

LX_GOAL_DIR = Path(__file__).resolve().parent

# 用 importlib 从文件加载 lx_goal，避免 pytest cwd 差异
_spec = importlib.util.spec_from_file_location("lx_goal_under_test", LX_GOAL_DIR / "lx-goal.py")
assert _spec is not None and _spec.loader is not None
lx_goal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lx_goal)


def _make_token(root: Path, slug: str, state: str | None, lock: bool):
    """创建 token 文件模拟活跃任务。"""
    tokens = root / ".omc" / "tokens" / "20260812"
    tokens.mkdir(parents=True, exist_ok=True)
    token_path = tokens / f"{slug}.json"
    data = {
        "session": {"id": slug},
        "goal": {"state": state} if state else {},
        "task": {},
    }
    token_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if lock:
        token_path.with_name(token_path.name + ".lock").write_text("", encoding="utf-8")


def test_goal_base_extraction():
    goal = "独立评估 CarrorOS 真实 AI 治理效能 index13 评分+发掘优化项实现"
    base = lx_goal._goal_base(goal)
    assert base == "独立评估-CarrorOS-真实-AI-治理效能-index13-评分发掘优化项实现"
    # 两个不同后缀的 slug 应共享 base
    slug1 = f"{base}-abcdef01"
    slug2 = f"{base}-12345678"
    assert slug1.startswith(base) and slug2.startswith(base)


def test_find_active_goal_by_lock(tmp_path):
    root = tmp_path
    # 模拟活跃任务（有 .lock）
    _make_token(root, "目标A-abc12345", None, lock=True)
    active = lx_goal._find_active_goal("目标A", tokens_root=root / ".omc" / "tokens")
    assert active == "目标A-abc12345", f"应检测到活跃任务, got {active}"


def test_find_active_goal_by_state(tmp_path):
    root = tmp_path
    _make_token(root, "目标B-def67890", "EXECUTING", lock=False)
    active = lx_goal._find_active_goal("目标B", tokens_root=root / ".omc" / "tokens")
    assert active == "目标B-def67890"


def test_find_active_goal_no_false_positive(tmp_path):
    root = tmp_path
    # 无活跃任务（已归档，无 lock 且 state=ARCHIVED）
    _make_token(root, "目标C-ghi12345", "ARCHIVED", lock=False)
    active = lx_goal._find_active_goal("目标C", tokens_root=root / ".omc" / "tokens")
    assert active is None, f"归档任务不应误报活跃, got {active}"


def test_find_active_goal_different_goal(tmp_path):
    root = tmp_path
    _make_token(root, "目标A-abc12345", "EXECUTING", lock=False)
    # 不同目标的 base 不应命中
    active = lx_goal._find_active_goal("完全不同的目标", tokens_root=root / ".omc" / "tokens")
    assert active is None
