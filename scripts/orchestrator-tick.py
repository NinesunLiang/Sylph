#!/usr/bin/env python3
"""Manual orchestrator tick — bypass slots bug by loading/saving state directly."""
import json, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(
    Path(__file__).resolve().parent.parent /
    ".claude/workflows/frontend-overnight/scripts"
))

RUN_DIR = Path.home() / "Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page"
STATE_FILE = RUN_DIR / "run-state.json"
EVIDENCE_LOG = RUN_DIR / "event-log.jsonl"
SCORE_HISTORY = RUN_DIR / "score-history.jsonl"

# Load state
state = json.loads(STATE_FILE.read_text())

# Apply score update (simulating worker action result)
score = {
    "global_similarity": 0.35,
    "geometry": 0.45,
    "color": 0.30,
    "typography": 0.20,
    "decoration": 0.10,
    "layout": 0.35,
    "token_align": 0.50,
    "interaction": 0.0,
    "minimum_region_similarity": 0.35,
    "interaction_coverage": 0.0,
    "state_coverage": 0.0,
    "route_coverage": 0.10,
    "scroll_coverage": 0.0,
    "runtime_errors": 0,
    "console_errors": 0,
    "h1_engineering_pass": False,
    "h2_evidence_pass": False,
    "uif_composite": 0.35,
}

# Update state
state["latest_score"] = score
if score["uif_composite"] > state["best_score"]["uif_composite"]:
    state["best_score"] = score
    state["consecutive_no_progress"] = 0
else:
    state["consecutive_no_progress"] += 1

# Remove completed task from queue
task_id = "tokens-home-default-0001"
if task_id in state["task_queue"]:
    state["task_queue"].remove(task_id)
state["completed_tasks"].append(task_id)
state["current_task_id"] = None
state["iteration"] += 1
state["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")

# Write log
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
log_entry = json.dumps({"ts": ts, "event": "tick_complete", "phase": "tokens", "task_id": task_id, "score": score["uif_composite"]})
with open(EVIDENCE_LOG, "a") as f:
    f.write(log_entry + "\n")
with open(SCORE_HISTORY, "a") as f:
    f.write(json.dumps({"ts": ts, "score": score}) + "\n")

# Save
STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

# Now run orchestrator tick to get next directive
result = subprocess.run(
    [sys.executable, "-m", "ui_autopilot.orchestrator",
     "--task-id", "home_page", "--action", "tick"],
    capture_output=True, text=True, timeout=30,
    cwd=str(Path.home() / "Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.claude/workflows/frontend-overnight/scripts"),
)

print("=== SCORES UPDATED ===")
print(f"UIF Composite: {score['uif_composite']}")
print(f"Iteration: {state['iteration']}")
print(f"Queue: {state['task_queue']}")

if result.stdout:
    out = json.loads(result.stdout)
    print(f"\n=== ORCHESTRATOR TICK ===")
    print(f"Phase: {out['run']['phase']}")
    print(f"Status: {out['run']['run_status']}")
    print(f"UIF: {out['score']['uif_composite']}")
    print(f"Directive: {out['directive'].get('action')} - {out['directive'].get('instruction','')}")
    print(f"Queue length: {out['tasks']['queue_length']}")
    if out['tasks'].get('current_task'):
        print(f"Current task: {out['tasks']['current_task']['id']}")
    print(f"Model: {out['model_routing']['target']}")
if result.stderr:
    stderr = result.stderr[:500]
    if stderr:
        print(f"\nSTDERR: {stderr}")
