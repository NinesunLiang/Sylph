import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
spec = importlib.util.spec_from_file_location("lx_goal_checklist_boundary", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_checklist_gate_rejects_missing_checklist(tmp_path):
    (tmp_path / "executor.md").write_text("# Executor\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        module.cmd_checklist_verify(tmp_path)
    assert exc.value.code == 1


def test_checklist_gate_rejects_unchecked_item(tmp_path):
    (tmp_path / "executor.md").write_text(
        "# Executor\n\n## Acceptance Checklist\n- [x] prepared\n- [ ] verified\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        module.cmd_checklist_verify(tmp_path)
    assert exc.value.code == 1


def test_checklist_gate_uses_only_selected_task_dir(tmp_path):
    selected = tmp_path / "selected"
    unrelated = tmp_path / "unrelated"
    selected.mkdir()
    unrelated.mkdir()
    (selected / "executor.md").write_text(
        "## Acceptance Checklist\n- [x] selected task complete\n",
        encoding="utf-8",
    )
    (unrelated / "executor.md").write_text(
        "## Acceptance Checklist\n- [ ] unrelated task pending\n",
        encoding="utf-8",
    )
    assert module.cmd_checklist_verify(selected) == 0
