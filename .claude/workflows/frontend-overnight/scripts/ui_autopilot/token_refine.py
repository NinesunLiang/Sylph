"""token_refine.py — T1 incremental token refinement during the repair loop.

After T0 bootstrap generates draft tokens, T1 refinement runs after each
region/element phase completion to:
  1. Compare prototype vs implementation computed styles
  2. Identify token value mismatches
  3. Generate TokenProposal entries (NOT direct modifications!)
  4. Merge proposals that point to the same new value (confidence boost)

Token proposals are queued for human signoff during morning review.
The night-run can only ConsumeTokenRepair or ProposeToken — never
modify token source/generated files directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Token Proposal ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TokenProposal:
    """A proposed token modification. Does NOT directly modify tokens.

    Proposals are queued for human signoff during morning review.
    Only after signoff can tokens be regenerated via codegen.
    """
    token_name: str
    current_value: str
    proposed_value: str
    confidence: float
    evidence_state_ids: list[str]
    affected_targets: list[str]
    source: str  # 'computed_style' | 'prototype_variable' | 'visual_model'

    @property
    def delta_description(self) -> str:
        return f"{self.token_name}: {self.current_value} → {self.proposed_value}"


# ── Token Refiner ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class TokenRefiner:
    """Incremental token refinement engine.

    Key difference from full re-extraction: refinement is incremental,
    processing only the tokens exposed by the current phase's mismatches,
    not re-clustering the entire page each time.

    Args:
        bootstrap_json_path: Path to bootstrap-tokens.json (T0 output)
        generated_css_path: Path to the generated CSS variables file
    """

    bootstrap_json_path: Path = field(default=None)  # type: ignore
    generated_css_path: Path = field(default=None)  # type: ignore

    _bootstrap: dict[str, Any] = field(default_factory=dict, repr=False)
    _token_index: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.bootstrap_json_path and self.bootstrap_json_path.exists():
            try:
                self._bootstrap = json.loads(
                    self.bootstrap_json_path.read_text(encoding="utf-8")
                )
            except Exception:
                self._bootstrap = {}

        if self.generated_css_path and self.generated_css_path.exists():
            self._load_token_index()

    @classmethod
    def from_paths(
        cls,
        bootstrap_json_path: Path,
        generated_css_path: Path,
    ) -> "TokenRefiner":
        """Factory that sets paths to attributes so __post_init__ handles loading."""
        instance = cls.__new__(cls)
        instance.bootstrap_json_path = bootstrap_json_path
        instance.generated_css_path = generated_css_path
        instance._bootstrap = {}
        instance._token_index = {}
        TokenRefiner.__post_init__(instance)
        return instance

    # ── Public API ─────────────────────────────────────────────────────────

    def find_violating_targets(
        self,
        score_report: dict[str, Any],
        threshold: float = 0.97,
    ) -> list[str]:
        """Find targets where the root cause is token-related.

        Args:
            score_report: Score report dict with per-target breakdown
            threshold: Composite score threshold below which to flag

        Returns:
            List of target IDs with token-related deficiencies
        """
        token_categories = {
            "color_token", "typography_token",
            "spacing_token", "component_token",
        }

        return [
            target_id
            for target_id, scores in score_report.get("targets", {}).items()
            if scores.get("composite", 1.0) < threshold
            and scores.get("root_cause_category") in token_categories
        ]

    def propose_refinements(
        self,
        violating_targets: list[str],
        prototype_measurements: dict[str, Any],
        implementation_measurements: dict[str, Any],
    ) -> list[TokenProposal]:
        """Generate token refinement proposals for violating targets.

        For each target, compares prototype vs implementation computed styles.
        When a mismatch is found and implementation uses a known token,
        generates a proposal to update the token value.

        Args:
            violating_targets: Target IDs with token issues
            prototype_measurements: Prototype measurements per target
            implementation_measurements: Implementation measurements per target

        Returns:
            Sorted list of TokenProposal (highest confidence first)
        """
        proposals: list[TokenProposal] = []

        for target_id in violating_targets:
            proto = prototype_measurements.get(target_id, {})
            impl = implementation_measurements.get(target_id, {})

            if not proto or not impl:
                continue

            # Compare property by property
            for prop, proto_value in proto.get("styles", {}).items():
                impl_value = impl.get("styles", {}).get(prop)

                if impl_value is None or proto_value == impl_value:
                    continue  # Match or missing → skip

                # Find which token variable the implementation uses
                token_name = self._find_token_for_property(prop, str(impl_value))

                if token_name is None:
                    # Raw value — register as ProposeToken gap
                    proposals.append(TokenProposal(
                        token_name=f"proto.{prop}",
                        current_value=str(impl_value),
                        proposed_value=str(proto_value),
                        confidence=0.6,
                        evidence_state_ids=[target_id],
                        affected_targets=[target_id],
                        source="computed_style",
                    ))
                    continue

                # Known token — propose value update
                proposals.append(TokenProposal(
                    token_name=token_name,
                    current_value=str(impl_value),
                    proposed_value=str(proto_value),
                    confidence=0.85,
                    evidence_state_ids=[target_id],
                    affected_targets=[target_id],
                    source="computed_style",
                ))

        return self._merge_proposals(proposals)

    def find_nearest_token(
        self, css_property: str, value: str
    ) -> tuple[str | None, float]:
        """Find the nearest matching token for a property value.

        Args:
            css_property: CSS property name
            value: Value to match

        Returns:
            (token_name, distance) or (None, float('inf'))
        """
        if not self._token_index:
            return None, float("inf")

        # For spacing values, try numeric proximity
        if css_property in ("padding", "gap", "margin", "width", "height"):
            return self._nearest_spacing(value)

        # For other properties, exact match in token index
        if value in self._token_index:
            return value, 0.0

        return None, float("inf")

    @property
    def token_index(self) -> dict[str, str]:
        return dict(self._token_index)

    @property
    def token_count(self) -> int:
        return len(self._token_index)

    # ── Internal ───────────────────────────────────────────────────────────

    def _load_token_index(self) -> None:
        """Parse generated CSS to build token_name → value index."""
        if not self.generated_css_path or not self.generated_css_path.exists():
            return

        css_text = self.generated_css_path.read_text(encoding="utf-8")
        for line in css_text.splitlines():
            line = line.strip()
            if ":" not in line or not line.startswith("--"):
                continue
            # Parse: --ui-bootstrap-color-1: #F5F7FA;
            name, _, value = line.partition(":")
            name = name.strip()
            value = value.strip().rstrip(";").strip()

            if name:
                self._token_index[name] = value

    def _find_token_for_property(
        self, css_property: str, value: str
    ) -> str | None:
        """Find a token variable name for a given CSS property+value.

        Checks both:
          1. var() references in implementation code
          2. Direct value match in token index
        """
        if not self._token_index:
            return None

        # Check var() references
        if value.startswith("var(--"):
            var_name = value[4:].split(")")[0].strip()
            if var_name in self._token_index:
                return var_name

        # Check direct value match (reverse lookup)
        for name, token_val in self._token_index.items():
            if token_val == value:
                return name

        return None

    def _nearest_spacing(self, value: str) -> tuple[str | None, float]:
        """Find the nearest spacing token by numeric proximity."""
        if not value.endswith("px"):
            return None, float("inf")

        try:
            px = float(value[:-2])
        except (ValueError, TypeError):
            return None, float("inf")

        spacing_tokens = {
            k: v for k, v in self._token_index.items()
            if "spacing" in k.lower() and v.endswith("px")
        }

        best_name = None
        best_distance = float("inf")

        for name, token_val in spacing_tokens.items():
            try:
                token_px = float(token_val[:-2])
                distance = abs(px - token_px)
                if distance < best_distance:
                    best_distance = distance
                    best_name = name
            except (ValueError, TypeError):
                continue

        return best_name, best_distance

    @staticmethod
    def _merge_proposals(
        proposals: list[TokenProposal],
    ) -> list[TokenProposal]:
        """Merge proposals that point to the same {token → new_value}.

        When multiple targets independently suggest the same token update,
        confidence is boosted (multi-source corroboration).
        """
        merged: dict[str, TokenProposal] = {}

        for proposal in proposals:
            key = f"{proposal.token_name}::{proposal.proposed_value}"
            existing = merged.get(key)

            if existing is None:
                merged[key] = proposal
            else:
                # Merge evidence and boost confidence
                new_states = list(set(
                    existing.evidence_state_ids + proposal.evidence_state_ids
                ))
                new_targets = list(set(
                    existing.affected_targets + proposal.affected_targets
                ))
                new_confidence = min(
                    0.99,
                    existing.confidence + 0.05 * len(new_targets),
                )
                merged[key] = TokenProposal(
                    token_name=existing.token_name,
                    current_value=existing.current_value,
                    proposed_value=existing.proposed_value,
                    confidence=new_confidence,
                    evidence_state_ids=new_states,
                    affected_targets=new_targets,
                    source=existing.source,
                )

        return sorted(
            merged.values(),
            key=lambda p: (p.confidence, len(p.affected_targets)),
            reverse=True,
        )


# ── Utility ────────────────────────────────────────────────────────────────────


import json  # noqa: E402
