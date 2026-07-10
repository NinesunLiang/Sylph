#!/usr/bin/env python3
"""
DeepSeek-V4 Agent Injection Engine — CarrorOS Base 模型强化模块.
Targets: deepseek-v4-flash (aggressive) / deepseek-v4-pro (balanced).

Usage:
  from deepseek_inject import DeepSeekAgentOptimizer
  opt = DeepSeekAgentOptimizer("flash")
  enhanced = opt.inject(base_prompt, agent_state, round_num)
"""

from __future__ import annotations
import json, re, hashlib
from dataclasses import dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════════
# Module 1: Reasoning Chain Enforcer
# ═══════════════════════════════════════════════════════════════

REASONING_CHAIN = """
[REASONING PROTOCOL]
You MUST expand reasoning through these layers. Do NOT skip any layer.

Layer 0 [Context Anchoring]:
- Restate goal with hash anchor: Goal#<hash>
- List constraints with priority P0/P1/P2
- Mark known vs assumed: ✓ for known, ? for assumption

Layer 1 [Decomposition]:
- Break into sub-goals (MECE principle)
- Each sub-goal: dependency (→), risk (L/M/H), testability [T+/T-]
- Output dependency graph

Layer 2 [Solution Space]:
- At least 2 candidates per sub-goal
- Compare: complexity, assumption strength, maintainability
- State why alternatives were rejected

Layer 3 [Contradiction Check]:
- Sub-goal conflicts? Assumption vs constraint clashes? Circular deps?
- If found, backtrack to Layer 1

Layer 4 [Implementation Path]:
- Execution sequence with time markers
- Each step: input/output/side-effects/rollback
- Final verification point (must be automatable)
"""

# ═══════════════════════════════════════════════════════════════
# Module 2: Knowledge Boundary Marker
# ═══════════════════════════════════════════════════════════════

KNOWLEDGE_MARKER = """
[KNOWLEDGE PROTOCOL]
You MUST label every factual claim:

[R]     Reasoned from given information (R: conclusion ← chain A→B→C)
[M|H]   Memory recall, HIGH confidence (core facts like HTTP codes)
[M|M]   Memory recall, MEDIUM confidence (common practices)
[M|L]   Memory recall, LOW confidence (version/config specifics)
[A!]    Assumption, unverified (A: claim | verify by: method)
[?]     Beyond knowledge boundary (? what I don't know | need to check: source)

RULES:
- Version numbers, config values, API signatures MUST have [M|L] or [A!]
- Cross-domain integration MUST mark [BOUNDARY] at each domain edge
- [M|L] items MUST include verification method
- NO unlabeled assertions allowed
"""

# ═══════════════════════════════════════════════════════════════
# Module 3: Self-Check Limiter
# ═══════════════════════════════════════════════════════════════

SELFCHECK_L1 = """
[SELF-CHECK L1 — Syntax & Format]
Verify these anchors (ALL must pass):
[ ] No compile/syntax errors
[ ] Schema compliance
[ ] Linter clean
"""

SELFCHECK_L2 = """
[SELF-CHECK L2 — Logic Consistency]
Verify these anchors (ALL must pass):
[ ] Dependency graph is acyclic
[ ] Boundary conditions covered
[ ] No contradictory claims across layers
"""

SELFCHECK_L3 = """
[SELF-CHECK L3 — Integration] (Pro only)
Verify these anchors:
[ ] E2E test passes
[ ] Performance within bounds
"""

# ═══════════════════════════════════════════════════════════════
# Module 4: State Compression Engine
# ═══════════════════════════════════════════════════════════════

@dataclass
class StateCompressionEngine:
    """Layered state manager for 1M context optimization."""
    max_tokens: int = 128000  # flash limit
    state: dict = field(default_factory=lambda: {
        "goal": "", "plan": [], "memory": [], "context": [], "round": 0
    })

    def compress(self, round_num: int, context_size: int) -> str | None:
        """Return injection text if compression is needed, else None."""
        if not self._should_inject(round_num, context_size):
            return None
        self.state["round"] = round_num
        pending = [p for p in self.state.get("plan", []) if not p.get("done")]
        decisions = [m for m in self.state.get("memory", [])
                     if m.get("type") == "decision" and m.get("confidence", 0) > 0.7]
        recent = self.state.get("context", [])[-5:]

        lines = [f"[STATE INJECTION — Round {round_num}]",
                 f"Goal: {self._hash(self.state.get('goal', ''))}",
                 f"Pending ({len(pending)}):"]
        for i, p in enumerate(pending[:10]):
            lines.append(f"  {i+1}. [PENDING] {p.get('title', '?')}")
        for d in sorted(decisions, key=lambda x: x.get("confidence", 0), reverse=True)[:3]:
            lines.append(f"  • {d['content']} [conf:{d['confidence']:.2f}]")
        lines.append(f"Recent ({len(recent)}):")
        for i, ctx in enumerate(recent):
            lines.append(f"  T-{len(recent)-i}: {str(ctx)[:120]}")
        lines.append("[STATE INJECTION END]")
        return "\n".join(lines)

    def _should_inject(self, round_num: int, context_size: int) -> bool:
        return context_size > self.max_tokens * 0.7 or round_num % 5 == 0

    @staticmethod
    def _hash(s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()[:6]


# ═══════════════════════════════════════════════════════════════
# Optimizer: unified injection entry point
# ═══════════════════════════════════════════════════════════════

class DeepSeekAgentOptimizer:
    """CarrorOS injection optimizer for deepseek models."""

    def __init__(self, model_type: str = "flash"):
        self.model_type = model_type
        self.state_engine = StateCompressionEngine(
            max_tokens=128000 if model_type == "flash" else 500000
        )

    def inject(self, base_prompt: str, agent_state: dict | None = None,
               round_num: int = 0, context_size: int = 0) -> str:
        """Full injection — call this from hooks."""
        parts = [base_prompt]

        # Always inject reasoning + knowledge protocols
        parts.insert(0, REASONING_CHAIN)
        parts.insert(1, KNOWLEDGE_MARKER)

        # Self-check: L1+L2 for flash, L3 for pro
        check = SELFCHECK_L1 + SELFCHECK_L2
        if self.model_type == "pro":
            check += SELFCHECK_L3
        parts.append(check)

        # State compression: periodic
        if agent_state and self.state_engine._should_inject(round_num, context_size):
            inj = self.state_engine.compress(round_num, context_size)
            if inj:
                parts.append(inj)

        return "\n\n".join(parts)

    @staticmethod
    def detect_model(model_name: str) -> str | None:
        """Return 'flash', 'pro', or None if not a deepseek model."""
        if "flash" in model_name.lower():
            return "flash"
        if "pro" in model_name.lower():
            return "pro"
        if "deepseek" in model_name.lower():
            return "flash"  # default
        return None


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "flash"
    opt = DeepSeekAgentOptimizer(model)
    sample = opt.inject("Analyze the architecture of this project.", round_num=5)
    print(sample[:500])
