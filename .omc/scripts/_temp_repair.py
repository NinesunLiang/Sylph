    try:
        gate_script = _hook_dir / "pre_action_gate.py"
        cmd = [sys.executable, str(gate_script), spec_path] + token_arg
        r = subprocess.run(cmd, capture_output=True, text=True)
        output = r.stdout.strip() if r.stdout else r.stderr.strip()
        if output:
            print(output)
        return r.returncode
    finally:
        Path(spec_path).unlink(missing_ok=True)


def _sub_token(task_dir: str, parent_id: str, step_id: str, plan_text: str = "") -> dict:
    """生成 subagent token.json — 子代理的启动契约

    subagent 读这个文件知道：为谁工作（parent_id）、
    要做什么（subtask.plan）、被允许做什么（session.level）
    """
    now = datetime.now(timezone.utc)
    return {
        "schema_version": _SCHEMA_VERSION,
        "session": {
            "id": f"{parent_id}-{step_id}",
            "level": "L1_SUB",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "parent": {
            "task_dir": task_dir,
            "task_id": parent_id,
            "step_id": step_id,
        },
        "subtask": {
            "plan": plan_text,
        },
        "status": "active",
        "stats": {"done": 0, "total": 1, "tick": 0},
    }


def _result_template() -> dict:
    """result.json 模板 — subagent 完成工作后写"""
    return {
        "status": "running",
        "summary": "",
        "evidence": [],
        "files_changed": [],
        "failure": None,
        "completed_at": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
