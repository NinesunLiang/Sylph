#!/usr/bin/env python3
from __future__ import annotations

import re

from carroros_hooklib import append_audit, hook_block, hook_continue, read_stdin_json, sanitize_text

FORBIDDEN_COMPLETION = [
    r"\bDONE\b",
    r"\bVERIFIED\b",
    r"\bACCEPTED\b",
    r"\bTRUSTED\b",
    r"\bPROBABLY_OK\b",
    r"\bLOOKS_FINE\b",
    r"\bSKIP_VERIFY\b",
    r"应该差不多了",
    r"基本上完成了",
    r"理论上没问题",
    r"大概可以了",
    r"看起来都好了",
    r"应该没问题",
    r"一切正常",
    r"should be done",
    r"basically finished",
    r"looks good to me",
    r"i think it's done",
    r"probably fine",
]

ALLOW_CONTEXT = [
    r"verify_gate\.py",
    r"verify_decision",
    r"VerifyGate",
    r"sovereign-verdict",
    r"archive_engine\.py",
]

def extract_response(payload: dict) -> str:
    for key in ("response", "content", "message", "text", "assistant_response"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    return str(payload)[:5000]

def main() -> int:
    payload = read_stdin_json()
    response = extract_response(payload)
    if not response:
        return hook_continue("CompletionGate: no_response")

    has_forbidden = [pat for pat in FORBIDDEN_COMPLETION if re.search(pat, response, re.IGNORECASE)]
    if not has_forbidden:
        return hook_continue("CompletionGate: OK")

    allowed = any(re.search(pat, response, re.IGNORECASE) for pat in ALLOW_CONTEXT)
    if allowed:
        return hook_continue("CompletionGate: allowed_context")

    append_audit({
        "event_type": "completion_gate_warning",
        "actor": "hook:posttool-completion-gate",
        "decision": "BLOCK",
        "reason": "soft_or_forbidden_completion_language",
        "matches": has_forbidden[:5],
        "preview": sanitize_text(response, 200),
    })

    return hook_block(
        "CompletionGate: BLOCK soft/fake completion language. Use VerifyGate evidence before claiming completion."
    )

if __name__ == "__main__":
    raise SystemExit(main())