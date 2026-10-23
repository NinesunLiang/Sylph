"""One-shot, human-readable feedback from a JEV checklist."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def project_candidate_feedback(candidate_path: str | Path | None) -> dict:
    """Expose project candidates as feedback only; never enforce them."""
    if candidate_path is None or not Path(candidate_path).is_file():
        return {"count": 0, "candidates": [], "unavailable_reason": None}
    data = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    candidates = data.get("candidates") or []
    return {
        "count": len(candidates),
        "candidates": [
            {"candidate_id": item.get("candidate_id"), "source": item.get("source"),
             "text": item.get("text"), "enforcement": "feedback_only"}
            for item in candidates
        ],
        "unavailable_reason": data.get("unavailable_reason"),
    }


def emit_feedback(checklist_path: str | Path, output_dir: str | Path,
                  task_id: str, step_id: str, candidate_path: str | Path | None = None) -> dict:
    """Write one feedback artifact; never call JEV or mutate the task."""
    checklist = json.loads(Path(checklist_path).read_text(encoding="utf-8"))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    feedback_path = out / f"{task_id}-{step_id}-feedback.json"
    if feedback_path.exists():
        return json.loads(feedback_path.read_text(encoding="utf-8"))

    summary = checklist.get("summary") or {}
    violated = summary.get("violated") or []
    uncertain = (summary.get("insufficient") or []) + (summary.get("undecided") or [])
    tuning = [x.get("rule_id") for x in (summary.get("escalate_for_rule_tuning") or [])]
    unavailable = summary.get("unavailable") or []
    needs_review = bool(violated or uncertain or tuning or unavailable)
    if needs_review:
        action = "请查看 JEV 结果；如有必要，调整当前改动。只建议再调整一次，不自动重跑。"
    else:
        action = "JEV 未发现需要反馈的问题；继续当前流程。"

    project_rules = project_candidate_feedback(candidate_path)
    feedback = {
        "schema_version": "carros.jev_feedback.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "step_id": step_id,
        "feedback_emitted": True,
        "one_shot": True,
        "needs_review": needs_review,
        "violated": violated,
        "evidence_insufficient": uncertain,
        "unavailable": unavailable,
        "rule_tuning_candidates": tuning,
        "project_rule_candidates": project_rules,
        "action": action,
        "source_checklist": str(checklist_path),
        "llm_decision": "pending",
    }
    feedback_path.write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return feedback
