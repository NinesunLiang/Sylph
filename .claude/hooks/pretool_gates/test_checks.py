from . import checks


def test_plan_gate_does_not_create_implicit_task_without_active_token(monkeypatch):
    called = False

    def fail_auto_init(_path=None):
        nonlocal called
        called = True

    monkeypatch.setattr(checks, "_active_token", lambda: None)
    monkeypatch.setattr(checks, "_auto_init", fail_auto_init)

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "notes.txt"},
    }

    assert checks._check_plan_gate(payload) is None
    assert called is False
