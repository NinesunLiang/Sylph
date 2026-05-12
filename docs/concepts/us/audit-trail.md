# Audit Trail (审计追踪)

> **Every AI action is recorded, immutable, and replayable.**

---

## Why Audit?

When AI writes code autonomously, you need **forensic evidence** of what happened:

- Did the AI access production credentials?
- Did the AI delete or modify files outside the task scope?
- Did session handoff preserve the full decision history?

Trust is not a feeling. It is a ledger.

---

## Core Components

### read-tracker

Records every file the AI reads during a session -- path, timestamp, and purpose. Provides a complete access log for security review.

- Location: `.omc/state/read-tracker.txt`
- Format: `TIMESTAMP | FILE_PATH | TRIGGER`

### turn-counter

Tracks every AI turn (request-response cycle) in the current session. Used by `context-guard` to estimate context consumption and trigger handoffs or fuses.

- Threshold 1: 50% turns -> active handoff signal
- Threshold 2: 80% turns -> hard stop

### session-snapshot

At each handoff or termination, a snapshot is written containing:

- Full turn history summary
- Files modified in the session
- Gate events triggered
- Current task progress

Snapshots enable session recovery without restarting from scratch.

- Location: `.omc/state/sessions/<session-id>/`

---

## Audit Dashboard

The `/lx-status` command renders an audit dashboard with three panels:

| Panel | Data |
| :---- | :--- |
| Token Savings | Estimated tokens saved by progressive disclosure vs. monolithic system prompt. |
| Self-Heal Rate | Error DNA matching rate -- how often recurring errors are automatically corrected. |
| Execution Profile | Timeline of Gate events, file modifications, and session handoffs. |

---

## SHA256 Integrity

All audit records are hashed with SHA256 at write time. If a record is tampered with after creation, the hash mismatch is detectable on verification.

This ensures:

- Records cannot be silently modified by future AI sessions.
- A security auditor can verify the integrity of the entire trail.
- Non-repudiation for critical actions (credential access, destructive commands).

---

## Related

- [Gates: privacy-gate](./gates.md) -- records privacy gate events in the trail
- Dashboard: `.claude/scripts/audit_dashboard.py`
