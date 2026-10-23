"""scorer.py — UIF-99 multi-dimensional scoring engine (Grok specification).

Seven dimensions + two hard gates, aligned with plan §IV:

  D1 Geometry (0.16)     — region IoU + critical edge delta
  D2 Color (0.12)        — LAB ΔE against token ladder
  D3 Typography (0.10)   — font-size/weight/line-height
  D4 Decoration (0.08)   — radius/border/shadow
  D5 Layout (0.12)       — flex/grid/gap/overflow
  D6 TokenAlign (0.18)   — token-index hit rate, raw-value detection
  D7 Interaction (0.24)  — assertion catalog pass rate

Hard gates:
  H1 Engineering — C1+C2+C3 all pass → patch accepted
  H2 Evidence    — evidence_check passes → finalize allowed

Iron rules:
  - H1 or H2 fail → composite = 0.0, patch rejected
  - D7 < 100% → composite capped at 0.94
  - TokenAlign < phase threshold → patch rejected even if visual improves

Design: Grok UIF-99 + Opus cheat detection, adapted for CarrorOS gate chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .domain import Phase, Score, RegionScore, PHASE_THRESHOLDS


# ── Scoring Engine ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ScoringEngine:
    """UIF-99 scoring engine.

    Usage:
        engine = ScoringEngine()
        score = engine.score_page(proto_measures, impl_measures, regions, token_index)
        can_accept, reason = engine.can_accept_patch(score, old_score, phase)
    """

    # Dimension weights (sum = 1.0)
    weights: dict[str, float] = field(default_factory=lambda: {
        "geometry": 0.16,
        "color": 0.12,
        "typography": 0.10,
        "decoration": 0.08,
        "layout": 0.12,
        "token_align": 0.18,
        "interaction": 0.24,
    })

    # Region-level weights (sum = 1.0)
    region_weights: dict[str, float] = field(default_factory=lambda: {
        "geometry": 0.20,
        "color": 0.15,
        "typography": 0.12,
        "decoration": 0.10,
        "layout": 0.15,
        "token_align": 0.18,
        "interaction": 0.10,
    })

    # Hard cap
    interaction_coverage_cap: float = 0.94

    # Token ladder for D6 computation
    _token_index: set[str] | None = field(default=None, repr=False)

    def set_token_index(self, tokens: set[str]) -> None:
        """Set the known token variable names for D6 scoring."""
        self._token_index = tokens

    # ── Page-level scoring ──────────────────────────────────────────────────

    def score_page(
        self,
        prototype_measures: dict[str, Any],
        implementation_measures: dict[str, Any],
        regions: list[dict[str, Any]],
        gate_results: dict[str, bool] | None = None,
    ) -> Score:
        """Compute a full UIF-99 Score from measurements.

        Args:
            prototype_measures: Gold-standard measurements per region
            implementation_measures: Current implementation measurements
            regions: Region definitions with weights
            gate_results: Gate pass/fail status (C1–C8a)

        Returns:
            Complete Score with all dimensions filled
        """
        score = Score()

        # ── Hard gates ──
        if gate_results:
            score.h1_engineering_pass = all(
                gate_results.get(g, False) for g in ["C1", "C2", "C3"]
            )
            score.h2_evidence_pass = gate_results.get("C7", False)
        else:
            # No gate data → assume fail-closed
            score.h1_engineering_pass = False
            score.h2_evidence_pass = False

        # ── Per-region scores ──
        region_scores: list[RegionScore] = []
        total_weight = 0.0

        for region in regions:
            region_id = region.get("id", "")
            weight = float(region.get("weight", 0.1))
            is_critical = bool(region.get("is_critical", False))
            proto = prototype_measures.get(region_id, {})
            impl = implementation_measures.get(region_id, {})

            rs = RegionScore(region_id=region_id, state="default")
            rs.geometry = self._compute_geometry(proto, impl)
            rs.color = self._compute_color(proto, impl)
            rs.typography = self._compute_typography(proto, impl)
            rs.decoration = self._compute_decoration(proto, impl)
            rs.layout = self._compute_layout(proto, impl)
            rs.token_align = self._compute_token_align(proto, impl)

            rs.compute(self.region_weights)
            region_scores.append(rs)

            total_weight += weight

        # ── Aggregate dimensions ──
        if region_scores and total_weight > 0:
            score.geometry = sum(
                rs.geometry * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.color = sum(
                rs.color * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.typography = sum(
                rs.typography * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.decoration = sum(
                rs.decoration * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.layout = sum(
                rs.layout * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.token_align = sum(
                rs.token_align * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            score.interaction = sum(
                rs.interaction * regions[i].get("weight", 0.1)
                for i, rs in enumerate(region_scores)
            ) / total_weight

            # Minimum region similarity
            composites = [rs.composite for rs in region_scores]
            score.minimum_region_similarity = min(composites) if composites else 0.0

        # ── Global similarity (weighted average) ──
        score.global_similarity = score.uif_composite()

        return score

    # ── Interaction coverage ────────────────────────────────────────────────

    def set_interaction_coverage(
        self, score: Score, covered: int, total: int
    ) -> Score:
        """Set interaction coverage and apply the 0.94 cap rule.

        When interaction coverage < 100%, the composite is capped at 0.94
        regardless of visual similarity. This prevents "static 99%"
        without scroll/hover/overlay interactions.
        """
        if total > 0:
            score.interaction_coverage = covered / total
        else:
            score.interaction_coverage = 0.0
        return score

    # ── Patch acceptance ────────────────────────────────────────────────────

    def can_accept_patch(
        self,
        new_score: Score,
        old_score: Score | None,
        phase: Phase,
    ) -> tuple[bool, str]:
        """Determine if a patch should be accepted.

        Decision logic:
          1. Hard gates H1/H2 must pass → else REJECT
          2. Interaction coverage < 1.0 → accept BUT cap applies
          3. TokenAlign dropped → REJECT (hardcode cheat)
          4. Visual improved but TokenAlign stayed same → ACCEPT (neutral)
          5. Visual improved AND TokenAlign improved → ACCEPT (genuine progress)
          6. Visual degraded → REJECT (regression)

        Args:
            new_score: Score after applying patch
            old_score: Score before applying patch (None = initial)
            phase: Current phase (for threshold context)

        Returns:
            (should_accept, reason_string)
        """
        # Hard gates
        if not new_score.h1_engineering_pass:
            return False, "H1_ENGINEERING_FAIL: C1/C2/C3 gate failure"

        if not new_score.h2_evidence_pass:
            return False, "H2_EVIDENCE_FAIL: evidence_check failure"

        # Token cheat detection
        thresholds = PHASE_THRESHOLDS.get(
            phase, PHASE_THRESHOLDS[Phase.ELEMENTS]
        )

        if new_score.token_align < thresholds.d6_token_min:
            return False, (
                f"TOKEN_CHEAT: TokenAlign {new_score.token_align:.3f} "
                f"< phase threshold {thresholds.d6_token_min:.3f}"
            )

        # If no old score (initial state), accept if gates pass
        if old_score is None:
            return True, "INITIAL_ACCEPT: First patch accepted"

        old_composite = old_score.uif_composite()
        new_composite = new_score.uif_composite()

        # Regression detection
        if new_composite < old_composite - 0.001:
            return False, (
                f"REGRESSION: Composite {old_composite:.4f} → {new_composite:.4f}"
            )

        # Hardcode cheat: visual ↑ but token ↓
        if (new_score.global_similarity > old_score.global_similarity + 0.001
                and new_score.token_align < old_score.token_align - 0.01):
            return False, (
                f"CHEAT_DETECTED: Visual +{new_score.global_similarity - old_score.global_similarity:.4f} "
                f"but TokenAlign {old_score.token_align:.3f} → {new_score.token_align:.3f}"
            )

        # Genuine progress
        if new_composite > old_composite + 0.0001:
            return True, f"PROGRESS: {old_composite:.4f} → {new_composite:.4f}"

        # Neutral (within epsilon)
        if abs(new_composite - old_composite) <= 0.0001:
            return True, "NEUTRAL: No significant change"

        return False, "UNKNOWN: Could not determine"

    # ── Dimension calculators ───────────────────────────────────────────────

    def _compute_geometry(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute geometry similarity using bounding box IoU + edge deltas."""
        proto_bbox = proto.get("bbox", {})
        impl_bbox = impl.get("bbox", {})

        if not proto_bbox or not impl_bbox:
            return 0.0

        # IoU
        iou = self._iou(proto_bbox, impl_bbox)

        # Edge deltas (penalize large offsets)
        edge_deltas = []
        for edge in ("x", "y", "width", "height"):
            pv = float(proto_bbox.get(edge, 0))
            iv = float(impl_bbox.get(edge, 0))
            if pv > 0:
                edge_deltas.append(abs(pv - iv) / pv)

        edge_penalty = sum(edge_deltas) / max(len(edge_deltas), 1)
        edge_score = max(0.0, 1.0 - edge_penalty)

        return iou * 0.6 + edge_score * 0.4

    def _compute_color(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute color similarity using palette comparison."""
        proto_colors = proto.get("colors", [])
        impl_colors = impl.get("colors", [])

        if not proto_colors:
            return 1.0  # No color info → assume OK

        # Simple palette match: what fraction of proto colors appear in impl
        matches = 0
        for pc in proto_colors:
            for ic in impl_colors:
                if self._color_delta_e(pc, ic) < 3.0:
                    matches += 1
                    break

        return matches / max(len(proto_colors), 1)

    def _compute_typography(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute typography similarity using font metrics."""
        proto_fonts = proto.get("typography", {})
        impl_fonts = impl.get("typography", {})

        if not proto_fonts:
            return 1.0

        scores = []
        for key in ("fontSize", "fontWeight", "lineHeight", "fontFamily"):
            pv = proto_fonts.get(key)
            iv = impl_fonts.get(key)
            if pv is not None and iv is not None:
                if isinstance(pv, (int, float)) and isinstance(iv, (int, float)):
                    if pv > 0:
                        scores.append(max(0.0, 1.0 - abs(pv - iv) / pv))
                else:
                    scores.append(1.0 if pv == iv else 0.0)

        return sum(scores) / max(len(scores), 1)

    def _compute_decoration(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute decoration similarity (radius/border/shadow)."""
        proto_deco = proto.get("decoration", {})
        impl_deco = impl.get("decoration", {})

        if not proto_deco:
            return 1.0

        scores = []
        for key in ("borderRadius", "borderWidth", "borderStyle", "boxShadow"):
            pv = proto_deco.get(key)
            iv = impl_deco.get(key)
            if pv is not None and iv is not None:
                if isinstance(pv, (int, float)) and isinstance(iv, (int, float)):
                    if pv > 0:
                        scores.append(max(0.0, 1.0 - abs(pv - iv) / pv))
                else:
                    scores.append(1.0 if str(pv) == str(iv) else 0.0)

        return sum(scores) / max(len(scores), 1)

    def _compute_layout(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute layout similarity (flex/grid/gap/overflow)."""
        proto_layout = proto.get("layout", {})
        impl_layout = impl.get("layout", {})

        if not proto_layout:
            return 1.0

        scores = []
        for key in ("display", "flexDirection", "justifyContent",
                     "alignItems", "gap", "overflow"):
            pv = proto_layout.get(key)
            iv = impl_layout.get(key)
            if pv is not None and iv is not None:
                scores.append(1.0 if str(pv) == str(iv) else 0.0)

        return sum(scores) / max(len(scores), 1)

    def _compute_token_align(
        self, proto: dict[str, Any], impl: dict[str, Any]
    ) -> float:
        """Compute token alignment — fraction of values that match token ladder.

        🔴 Opus Round3: FAIL-CLOSED — empty styles = 0.0 (not 1.0).
        Worker submitting 'styles: {}' is treated as having zero token alignment.
        """
        impl_styles = impl.get("styles", {})
        if not impl_styles:
            return 0.0  # 🔴 FAIL-CLOSED: no style data = zero token alignment

        if self._token_index is None or len(self._token_index) == 0:
            # No token index → can't score, assume worst-case (not neutral)
            return 0.0

        total_properties = 0
        token_hits = 0

        for prop, value in impl_styles.items():
            if not isinstance(value, str):
                continue
            total_properties += 1

            # Check if this value references a known token
            if self._value_matches_token(value):
                token_hits += 1

        if total_properties == 0:
            return 0.0  # 🔴 FAIL-CLOSED: no properties = zero token alignment

        return token_hits / total_properties

    def _value_matches_token(self, value: str) -> bool:
        """Check if a CSS value references a known design token."""
        if not self._token_index:
            return False

        # CSS variable reference: var(--ds-*)
        if value.startswith("var(--"):
            var_name = value[4:].split(")")[0].strip()
            return var_name in self._token_index

        # Tailwind token class: not in CSS value, skip
        # Direct value match in token index
        return value in self._token_index

    # ── Utilities ───────────────────────────────────────────────────────────

    @staticmethod
    def _iou(
        a: dict[str, Any], b: dict[str, Any]
    ) -> float:
        """Compute Intersection over Union for two bounding boxes."""
        ax = float(a.get("x", 0))
        ay = float(a.get("y", 0))
        aw = float(a.get("width", 0))
        ah = float(a.get("height", 0))
        bx = float(b.get("x", 0))
        by = float(b.get("y", 0))
        bw = float(b.get("width", 0))
        bh = float(b.get("height", 0))

        if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
            return 0.0

        # Intersection
        ix = max(ax, bx)
        iy = max(ay, by)
        iw = min(ax + aw, bx + bw) - ix
        ih = min(ay + ah, by + bh) - iy

        if iw <= 0 or ih <= 0:
            return 0.0

        intersection = iw * ih
        union = aw * ah + bw * bh - intersection

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _color_delta_e(color_a: str, color_b: str) -> float:
        """Approximate ΔE for two hex color strings.

        Uses a simplified weighted RGB distance (not full LAB ΔE).
        For production use, replace with python-colormath or similar.
        """
        def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join(c * 2 for c in hex_color)
            if len(hex_color) != 6:
                return 0, 0, 0
            return (
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16),
            )

        r1, g1, b1 = _hex_to_rgb(color_a)
        r2, g2, b2 = _hex_to_rgb(color_b)

        # Weighted RGB distance (approximates human perception)
        r_mean = (r1 + r2) / 2
        dr = r1 - r2
        dg = g1 - g2
        db = b1 - b2

        return (
            (2 + r_mean / 256) * dr * dr
            + 4 * dg * dg
            + (2 + (255 - r_mean) / 256) * db * db
        ) ** 0.5


# ── Score Differ ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ScoreDiff:
    """Difference between two scores, for diagnostic purposes."""
    dimension_deltas: dict[str, float] = field(default_factory=dict)
    composite_delta: float = 0.0
    worst_dimension: str = ""
    worst_delta: float = 0.0
    improved_dimensions: list[str] = field(default_factory=list)
    degraded_dimensions: list[str] = field(default_factory=list)
    root_cause_category: str = "unknown"


def compute_score_diff(new_score: Score, old_score: Score) -> ScoreDiff:
    """Compute the difference between two scores for diagnosis.

    Useful for the orchestrator to determine what kind of fix is needed.
    """
    diff = ScoreDiff()

    dims = {
        "geometry": (new_score.geometry, old_score.geometry),
        "color": (new_score.color, old_score.color),
        "typography": (new_score.typography, old_score.typography),
        "decoration": (new_score.decoration, old_score.decoration),
        "layout": (new_score.layout, old_score.layout),
        "token_align": (new_score.token_align, old_score.token_align),
        "interaction": (new_score.interaction, old_score.interaction),
    }

    for dim, (new_val, old_val) in dims.items():
        delta = new_val - old_val
        diff.dimension_deltas[dim] = delta

        if delta > 0.001:
            diff.improved_dimensions.append(dim)
        elif delta < -0.001:
            diff.degraded_dimensions.append(dim)

        if delta < diff.worst_delta:
            diff.worst_delta = delta
            diff.worst_dimension = dim

    diff.composite_delta = new_score.uif_composite() - old_score.uif_composite()

    # Root cause classification
    if diff.worst_dimension in ("geometry", "layout"):
        diff.root_cause_category = "ancestor_geometry"
    elif diff.worst_dimension in ("color", "typography", "decoration"):
        diff.root_cause_category = "style_mismatch"
    elif diff.worst_dimension == "token_align":
        diff.root_cause_category = "token_gap"
    elif diff.worst_dimension == "interaction":
        diff.root_cause_category = "interaction_missing"
    else:
        diff.root_cause_category = "unknown"

    return diff
