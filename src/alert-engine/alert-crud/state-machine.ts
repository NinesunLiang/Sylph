// Alert state machine — validates and executes status transitions
//
// Valid transitions:
//   active  → paused | triggered | expired
//   paused  → active | expired
//   triggered → active | expired
//   expired  → (terminal, no outbound transitions)
//
// Idempotent: transitioning to the same status is a no-op

import { AlertStatus } from './alert-model';

export type TransitionResult =
  | { ok: true; newStatus: AlertStatus }
  | { ok: false; error: string; currentStatus: AlertStatus };

const VALID_TRANSITIONS: Record<AlertStatus, AlertStatus[]> = {
  active:       ['paused', 'triggered', 'expired'],
  paused:       ['active', 'expired'],
  triggered:    ['active', 'expired'],
  expired:      [], // terminal
};

export function canTransition(from: AlertStatus, to: AlertStatus): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}

export function validateTransition(
  currentStatus: AlertStatus,
  targetStatus: AlertStatus,
): TransitionResult {
  if (currentStatus === targetStatus) {
    return { ok: true, newStatus: targetStatus }; // idempotent
  }

  if (!canTransition(currentStatus, targetStatus)) {
    return {
      ok: false,
      error: `Cannot transition from ${currentStatus} to ${targetStatus}`,
      currentStatus,
    };
  }

  return { ok: true, newStatus: targetStatus };
}
