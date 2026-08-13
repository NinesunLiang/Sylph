"""phase_rules.py — Shared phase-level file access rules.

Centralizes PHASE_ALLOWED_FILE_PATTERNS and PHASE_PROHIBITED_ALWAYS to avoid
duplication between phase_gate.py and task_generator.py.

Design: Grok Round3 fix G-P0-2 — POLISH phase must NOT touch token source files.
"""

from __future__ import annotations

from .domain import Phase

# ── File Access Rules by Phase ─────────────────────────────────────────────────

PHASE_ALLOWED_FILE_PATTERNS: dict[Phase, list[str]] = {
    Phase.DISCOVERY: [
        "src/**/*.tsx", "src/**/*.ts", "src/**/*.scss", "src/**/*.css",
    ],
    Phase.TOKENS: [
        ".omc/ui-autopilot/*/token-proposals/**/*.json",
        ".omc/ui-autopilot/*/token-proposals/**/*.yaml",
        "artifacts/token-proposals/**/*.json",
        "artifacts/token-proposals/**/*.yaml",
    ],
    Phase.SHELL: [
        "src/shell/**/*.tsx", "src/shell/**/*.scss",
        "src/layouts/**/*.tsx", "src/layouts/**/*.scss",
    ],
    Phase.REGIONS: [
        "src/pages/**/*.tsx", "src/pages/**/*.scss",
        "src/components/**/*.tsx", "src/components/**/*.scss",
    ],
    Phase.ELEMENTS: [
        "src/pages/**/*.tsx", "src/pages/**/*.scss",
        "src/components/**/*.tsx", "src/components/**/*.scss",
    ],
    Phase.INTERACTIONS: [
        "src/pages/**/*.tsx", "src/pages/**/*.scss",
        "src/components/**/*.tsx", "src/components/**/*.scss",
        "src/overlays/**/*.tsx", "src/overlays/**/*.scss",
    ],
    Phase.POLISH: [
        # 🔴 Grok Round3 G-P0-2: token source is immutable during night run.
        # POLISH can refine component SCSS but NOT regenerate tokens.
        "src/pages/**/*.scss",
        "src/components/**/*.scss",
        "src/overlays/**/*.scss",
        "src/shell/**/*.scss",
    ],
    Phase.FINAL_AUDIT: [
        # Read-only audit phase — no file modifications allowed
    ],
}

# Paths that are NEVER writable by any phase during the night run
PHASE_PROHIBITED_ALWAYS: list[str] = [
    "src/styles/tokens/source/**",      # Token source is daytime-only
    "src/styles/tokens/generated/**",   # Generated tokens (codegen output)
    ".claude/workflows/frontend-overnight/scripts/carroros-gates/**",        # Gate scripts
    ".claude/**",                        # CarrorOS config
    ".omc/**",                           # Runtime state
    "node_modules/**",
    "dist/**",
    "build/**",
]
