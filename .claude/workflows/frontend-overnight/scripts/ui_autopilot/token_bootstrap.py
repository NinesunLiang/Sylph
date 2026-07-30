"""token_bootstrap.py — T0 rapid token extraction from prototype.

Extracts the top 50 highest-frequency computed style values from a prototype
page using Playwright. Clusters by category (color/spacing/radius/typography)
and outputs:
  - Bootstrap CSS variables file
  - JSON token index for T1 refinement
  - Summary for human signoff

This is a Phase 0 / daytime operation. Tokens are frozen before night-run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Configuration ──────────────────────────────────────────────────────────────


BOOTSTRAP_PROPERTIES: set[str] = {
    "color", "background-color", "border-color",
    "font-size", "font-weight", "line-height",
    "border-radius", "gap", "padding", "padding-top",
    "padding-right", "padding-bottom", "padding-left",
    "width", "height", "box-shadow",
}

CATEGORY_MAP: dict[str, str] = {
    "color": "color", "background-color": "color", "border-color": "color",
    "font-size": "font-size", "font-weight": "font-weight",
    "line-height": "line-height",
    "border-radius": "radius",
    "gap": "spacing", "padding": "spacing", "padding-top": "spacing",
    "padding-right": "spacing", "padding-bottom": "spacing",
    "padding-left": "spacing",
    "box-shadow": "shadow",
}

TOP_N: dict[str, int] = {
    "color": 20, "font-size": 8, "font-weight": 6,
    "line-height": 6, "radius": 6, "spacing": 12, "shadow": 4,
}

SPACING_QUANTUM: int = 2  # px quantization step
COLOR_DELTA_E_MERGE: float = 2.0


# ── Data Structures ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class RawToken:
    """A single observed computed style value."""
    property: str
    value: str
    count: int = 0
    weight: float = 0.0  # area-weighted frequency

    @property
    def category(self) -> str:
        return CATEGORY_MAP.get(self.property, "other")


@dataclass(slots=True)
class BootstrapResult:
    """Output of token bootstrap."""
    native_variables: dict[str, str] = field(default_factory=dict)
    extracted: list[RawToken] = field(default_factory=list)
    css_variables: str = ""
    token_index: dict[str, str] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


# ── Playwright Extraction Script ────────────────────────────────────────────────

EXTRACTION_SCRIPT = r"""
async ({ properties }) => {
    const results = [];
    const body = document.querySelector('body');
    if (!body) return results;

    const elements = body.querySelectorAll('*');
    for (const el of elements) {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);

        // Skip invisible / tiny elements
        if (rect.width < 2 || rect.height < 2 ||
            style.display === 'none' || style.visibility === 'hidden') {
            continue;
        }

        const area = rect.width * rect.height;
        for (const prop of properties) {
            const value = style.getPropertyValue(prop).trim();
            if (!value || value === 'none' || value === 'normal' ||
                value === 'auto' || value === 'transparent' ||
                value === 'rgba(0, 0, 0, 0)') {
                continue;
            }
            results.push({ property: prop, value, area });
        }
    }
    return results;
}
"""

CUSTOM_PROPERTIES_SCRIPT = r"""
() => {
    const result = {};
    const root = getComputedStyle(document.documentElement);
    for (const sheet of document.styleSheets) {
        try {
            for (const rule of sheet.cssRules) {
                if (!(rule instanceof CSSStyleRule)) continue;
                for (const name of rule.style) {
                    if (name.startsWith('--')) {
                        const resolved = root.getPropertyValue(name).trim();
                        if (resolved) result[name] = resolved;
                    }
                }
            }
        } catch (e) {
            // Cross-origin stylesheet: skip
        }
    }
    return result;
}
"""


# ── Bootstrap Engine ───────────────────────────────────────────────────────────


def bootstrap_from_observations(
    observations: list[dict[str, Any]],
    custom_properties: dict[str, str],
    output_dir: Path,
) -> BootstrapResult:
    """Process raw observations into a BootstrapResult.

    This is the core algorithm — Playwright extraction is done externally
    (by the orchestrator or a dedicated playwright script) and the raw
    observations are passed here for processing.

    Args:
        observations: List of {property, value, area} dicts
        custom_properties: Prototype CSS variables
        output_dir: Where to write output files

    Returns:
        BootstrapResult with all output artifacts
    """
    result = BootstrapResult(
        native_variables=custom_properties,
    )

    # ── Aggregate by property + value, weighted by element area ──
    freq: dict[str, RawToken] = {}

    for obs in observations:
        prop = obs.get("property", "")
        value = obs.get("value", "")
        area = float(obs.get("area", 0))

        key = f"{prop}::{value}"
        existing = freq.get(key)

        if existing:
            existing.count += 1
            existing.weight += area
        else:
            freq[key] = RawToken(
                property=prop,
                value=value,
                count=1,
                weight=area,
            )

    # ── Quantize spacing values ──
    for token in freq.values():
        if token.category == "spacing":
            token.value = _quantize_spacing(token.value, SPACING_QUANTUM)

    # ── Sort by category, take top-N ──
    by_category: dict[str, list[RawToken]] = {}
    for token in freq.values():
        cat = token.category
        by_category.setdefault(cat, []).append(token)

    selected: list[RawToken] = []
    for cat, tokens in by_category.items():
        tokens.sort(key=lambda t: t.weight, reverse=True)
        limit = TOP_N.get(cat, 4)
        selected.extend(tokens[:limit])

    result.extracted = selected

    # ── Merge similar colors ──
    selected = _merge_similar_colors(selected)

    # ── Generate CSS Variables ──
    css_lines = [
        "/* AUTO-GENERATED: UI Autopilot Token Bootstrap */",
        "/* Source: prototype computed style extraction */",
        "/* Run T1 refinement to improve accuracy */",
        ":root {",
    ]

    # Native prototype variables first
    if custom_properties:
        css_lines.append("")
        css_lines.append("  /* === Prototype Native Variables === */")
        for name, value in sorted(custom_properties.items()):
            css_lines.append(f"  {name}: {value};")

    # Extracted by category
    cat_counters: dict[str, int] = {}
    css_lines.append("")
    css_lines.append("  /* === Bootstrap Extracted Values === */")

    for token in sorted(selected, key=lambda t: (t.category, -t.weight)):
        cat = token.category
        cat_counters[cat] = cat_counters.get(cat, 0) + 1
        var_name = f"--ui-bootstrap-{cat}-{cat_counters[cat]}"
        css_lines.append(
            f"  {var_name}: {token.value}; "
            f"/* freq:{token.count} area:{token.weight:.0f} */"
        )
        result.token_index[var_name] = token.value

    css_lines.append("}")
    css_lines.append("")

    result.css_variables = "\n".join(css_lines)

    # ── Build JSON output ──
    result.summary = {
        "generatedAt": "",  # filled by caller
        "prototypeUrl": "",  # filled by caller
        "nativeVariables": custom_properties,
        "extracted": [
            {
                "category": t.category,
                "property": t.property,
                "value": t.value,
                "frequency": t.count,
                "areaWeight": t.weight,
            }
            for t in selected
        ],
        "tokenIndex": result.token_index,
    }

    # ── Write output files ──
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "bootstrap-tokens.css").write_text(
        result.css_variables, encoding="utf-8"
    )

    (output_dir / "bootstrap-tokens.json").write_text(
        json.dumps(result.summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return result


# ── Helper Functions ───────────────────────────────────────────────────────────


def _quantize_spacing(value: str, quantum: int = 2) -> str:
    """Quantize a spacing value to the nearest step.

    Examples:
        "13px" → "14px" (nearest 2px step)
        "1.5rem" → "1.5rem" (rem units not quantized)
    """
    if not value.endswith("px"):
        return value

    try:
        px = float(value[:-2])
        quantized = round(px / quantum) * quantum
        return f"{max(quantum, quantized)}px"
    except (ValueError, TypeError):
        return value


def _merge_similar_colors(tokens: list[RawToken]) -> list[RawToken]:
    """Merge tokens with similar colors (within ΔE threshold).

    Groups color tokens by similarity, keeping the highest-frequency
    representative for each cluster.
    """
    color_tokens = [t for t in tokens if t.category == "color"]
    non_color = [t for t in tokens if t.category != "color"]

    if len(color_tokens) <= 1:
        return tokens

    # Simple grouping by first 2 hex chars (approximation of hue proximity)
    clusters: dict[str, list[RawToken]] = {}
    for token in color_tokens:
        val = token.value.strip()
        if val.startswith("#"):
            prefix = val[1:3] if len(val) >= 3 else val
        elif val.startswith("rgb"):
            prefix = val[:10]  # Group by rgb prefix
        else:
            prefix = val[:6]
        clusters.setdefault(prefix, []).append(token)

    merged = []
    for group in clusters.values():
        # Keep the highest-weight token as representative
        group.sort(key=lambda t: t.weight, reverse=True)
        representative = group[0]
        representative.count = sum(t.count for t in group)
        representative.weight = sum(t.weight for t in group)
        merged.append(representative)

    return merged + non_color


def get_bootstrap_script() -> str:
    """Return the Playwright extraction JavaScript.

    This is used by the orchestrator to inject into a Playwright page.
    """
    return EXTRACTION_SCRIPT


def get_custom_properties_script() -> str:
    """Return the Playwright custom-properties extraction JavaScript."""
    return CUSTOM_PROPERTIES_SCRIPT
