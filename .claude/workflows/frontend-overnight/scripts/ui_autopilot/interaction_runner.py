"""interaction_runner.py — Assertion catalog executor for D7 scoring.

Reads the assertion catalog (assertion-catalog.yaml in CarrorOS gates)
and executes each declaration via Playwright. Produces evidence files
that feed back into scorer.D7 and evidence_check.

Design: Opus M3 + risk C — makes D7 "legal" (run assertions, count pass/fail).
        Grok G-P0-3 — producers that feed ScorePage, not just calculator.

Usage (conceptual — Playwright run by CC session):
    runner = InteractionRunner(assertion_catalog_path, page)
    results = await runner.execute_all()
    covered, total = results.covered, results.total
    # → feeds scorer.set_interaction_coverage(score, covered, total)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AssertionType(StrEnum):
    """Types of assertions from the catalog."""
    SCROLL = "scroll"      # ix.scroll.end
    HOVER = "hover"        # ix.hover.menu.*
    CLICK = "click"        # ix.click.popover / ix.overlay.dismiss
    KEY = "key"            # ix.overlay.dismiss (Escape)
    DOM = "dom"            # DOM visibility / content check
    STYLE = "style"        # Computed style check (z-index, width, etc.)
    VIEWPORT = "viewport"  # Viewport containment check


class AssertionStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"       # Trigger not found / element missing
    ERROR = "error"           # Execution error (timeout, script error)


@dataclass(slots=True)
class AssertionPredicate:
    """A single assertion condition to verify."""
    type: str = "dom"            # dom | style | viewport
    selector: str = ""
    visible: bool | None = None  # for dom type
    contains: str | None = None  # for dom type
    property: str | None = None  # for style type (zIndex, width, ...)
    expected: str | None = None  # for style type (">= var(--ds-z-dropdown)")


@dataclass(slots=True)
class AssertionDef:
    """A single assertion definition from the catalog."""
    id: str
    page: str = "*"
    trigger: dict[str, Any] = field(default_factory=dict)
    predicates: list[AssertionPredicate] = field(default_factory=list)
    depends_on: str | None = None


@dataclass(slots=True)
class AssertionResult:
    """Result of executing one assertion."""
    assertion_id: str
    status: AssertionStatus = AssertionStatus.SKIPPED
    evidence_files: list[str] = field(default_factory=list)
    error_message: str = ""


@dataclass(slots=True)
class InteractionReport:
    """Aggregated interaction execution results."""
    page_id: str
    assertions: list[AssertionResult] = field(default_factory=list)
    covered: int = 0
    total: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        passed = sum(
            1 for r in self.assertions
            if r.status == AssertionStatus.PASSED
        )
        return passed / self.total

    @property
    def all_passed(self) -> bool:
        return self.pass_rate >= 1.0 if self.total > 0 else False


# ── Minimal required interaction assertions ────────────────────────────────────
# These map to UI_README.md §四 mandatory items + Grok interaction matrix

MINIMAL_REQUIRED_ASSERTIONS: list[dict[str, Any]] = [
    {
        "id": "ix.scroll.end",
        "description": "全高滚动到底 — footer 可见",
        "trigger": {"type": "scroll", "target": "main", "to": "bottom"},
        "predicates": [
            {"type": "dom", "selector": "footer", "visible": True},
        ],
    },
    {
        "id": "ix.sidebar.expand",
        "description": "侧边栏展开 — 宽度正确",
        "trigger": {"type": "click", "target": "[data-qa=sidebar-toggle]"},
        "predicates": [
            {"type": "dom", "selector": ".sidebar--expanded", "visible": True},
        ],
    },
    {
        "id": "ix.sidebar.collapse",
        "description": "侧边栏收起 — 宽度收缩",
        "trigger": {"type": "click", "target": "[data-qa=sidebar-toggle]"},
        "predicates": [
            {"type": "dom", "selector": ".sidebar--collapsed", "visible": True},
        ],
    },
    {
        "id": "ix.hover.menu",
        "description": "悬浮菜单 — hover 后出现",
        "trigger": {"type": "hover", "target": "[data-qa=user-avatar]", "wait_ms": 200},
        "predicates": [
            {"type": "dom", "selector": ".user-menu-overlay", "visible": True},
        ],
    },
    {
        "id": "ix.overlay.dismiss.esc",
        "description": "浮层 Escape 关闭",
        "trigger": {"type": "key", "key": "Escape"},
        "predicates": [
            {"type": "dom", "selector": ".overlay", "visible": False},
        ],
    },
    {
        "id": "ix.overlay.dismiss.mask",
        "description": "浮层点击遮罩关闭",
        "trigger": {"type": "click", "target": ".overlay-mask"},
        "predicates": [
            {"type": "dom", "selector": ".overlay", "visible": False},
        ],
    },
]


# ── Catalog Parser ─────────────────────────────────────────────────────────────


def parse_assertion_catalog(catalog_path: Path) -> list[AssertionDef]:
    """Parse assertion-catalog.yaml into AssertionDef list.

    Compatible with CarrorOS .claude/workflows/frontend-overnight/scripts/carroros-gates/assertion-catalog.yaml format.
    """
    import yaml

    if not catalog_path.exists():
        return []

    try:
        with open(catalog_path) as f:
            raw = yaml.safe_load(f) or {}
    except Exception:
        return []

    assertions = raw.get("assertions", []) or raw.get("interaction_assertions", [])
    if not assertions:
        return []

    defs: list[AssertionDef] = []
    for entry in assertions:
        if not isinstance(entry, dict):
            continue

        preds = []
        for p in entry.get("predicates", []) or []:
            preds.append(AssertionPredicate(
                type=p.get("type", "dom"),
                selector=p.get("selector", ""),
                visible=p.get("visible"),
                contains=p.get("contains"),
                property=p.get("property"),
                expected=p.get("expected"),
            ))

        defs.append(AssertionDef(
            id=entry.get("id", ""),
            page=entry.get("page", "*"),
            trigger=entry.get("trigger", {}),
            predicates=preds,
            depends_on=entry.get("depends_on"),
        ))

    return defs


def get_minimal_assertions() -> list[AssertionDef]:
    """Return the built-in minimal required interaction assertions.

    These are always required (from UI_README.md mandatory items),
    regardless of the extended catalog.
    """
    defs: list[AssertionDef] = []
    for raw in MINIMAL_REQUIRED_ASSERTIONS:
        preds = []
        for p in raw.get("predicates", []):
            preds.append(AssertionPredicate(
                type=p.get("type", "dom"),
                selector=p.get("selector", ""),
                visible=p.get("visible"),
                contains=p.get("contains"),
            ))
        defs.append(AssertionDef(
            id=raw["id"],
            page="*",
            trigger=raw.get("trigger", {}),
            predicates=preds,
        ))
    return defs


def merge_assertions(
    catalog_defs: list[AssertionDef],
    minimal_defs: list[AssertionDef],
) -> list[AssertionDef]:
    """Merge catalog and minimal assertions, deduplicating by ID."""
    seen: set[str] = set()
    merged: list[AssertionDef] = []

    for d in catalog_defs + minimal_defs:
        if d.id not in seen:
            seen.add(d.id)
            merged.append(d)

    return merged
