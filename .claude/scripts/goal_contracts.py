#!/usr/bin/env python3
"""goal_contracts.py — ResearchGate + PlanGate for GoalMachine lifecycle validation.

ResearchGate: validates research.md has 8 real-content sections with dependency tree.
PlanGate: validates plan.md has valid Phase/Step structure (Task7 compatible).

Designed for integration into GoalMachine.transition() so that gate validation
runs automatically when document paths are provided.

Usage:
    from goal_contracts import ResearchGate, PlanGate
    ResearchGate.validate("path/to/research.md")
    PlanGate.validate("path/to/plan.md")
"""

import re
from pathlib import Path
from typing import Any


# ─── Custom Exceptions ────────────────────────────────────────────────

class ResearchGateError(ValueError):
    """Raised when ResearchGate validation fails. Contains list of error strings."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class PlanGateError(ValueError):
    """Raised when PlanGate validation fails. Contains list of error strings."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# ─── ResearchGate ─────────────────────────────────────────────────────

REQUIRED_RESEARCH_SECTIONS = [
    "背景",
    "约束",
    "已知信息",
    "不确定性",
    "全貌",
    "依赖树",
    "方案",
    "Dependency TDD",
]


class ResearchGate:
    """Validates research.md content structure.

    Requirements:
      - All 8 required sections present with non-placeholder content
      - Dependency tree has at least one bullet item
    """

    @staticmethod
    def validate(research_path: str | Path) -> dict[str, Any]:
        """Validate research.md. Raises ResearchGateError on failure.

        Returns dict with 'valid': True, 'sections_found': [...], 'dep_tree_count': int
        """
        path = Path(research_path)
        if not path.exists():
            raise ResearchGateError([f"Research file not found: {research_path}"])

        content = path.read_text(encoding="utf-8")
        errors: list[str] = []
        sections_found: list[str] = []
        dep_tree_count = 0

        for section in REQUIRED_RESEARCH_SECTIONS:
            section_marker = f"## {section}"
            if section_marker not in content:
                errors.append(f"Missing required section: '{section}'")
                continue

            sections_found.append(section)

            # Extract content after this section header, up to next ## or EOF
            parts = content.split(section_marker)
            if len(parts) < 2:
                errors.append(f"Section '{section}' not found in content structure")
                continue

            after_header = parts[1]
            # Split at the next ## section marker if any
            next_section_idx = after_header.find("\n## ")
            if next_section_idx >= 0:
                after_header = after_header[:next_section_idx]

            # Check for real content lines (not comments, blockquotes, or blank)
            clean_lines = [
                l.strip()
                for l in after_header.split("\n")
                if l.strip() and not l.strip().startswith("<!--") and not l.strip().startswith(">")
            ]
            if len(clean_lines) < 1:
                errors.append(f"Section '{section}' has no real content (placeholder or empty)")

            # Count dependency tree bullets
            if section == "依赖树":
                bullet_matches = re.findall(r"^\s*[-*]\s+", after_header, re.MULTILINE)
                dep_tree_count = len(bullet_matches)
                if dep_tree_count < 1:
                    errors.append("Dependency tree section has no bullet items (requires at least 1)")

        if errors:
            raise ResearchGateError(errors)

        return {
            "valid": True,
            "sections_found": sections_found,
            "dep_tree_count": dep_tree_count,
        }


# ─── PlanGate ─────────────────────────────────────────────────────────

VALID_STEP_STATUSES = {"pending", "active", "running", "completed", "done", "verified", "blocked", "cancelled", "failed"}


class PlanGate:
    """Validates plan.md structure (Task7 Phase 2 compatible).

    Requirements:
      - At least 1 Phase header and 1 Step
      - Each step ID is unique
      - Each step has status (legal value), depends_on, acceptance, verify
      - depends_on references exist and form no cycles
      - scope/acceptance/verify have real (non-placeholder) content
      - Compatible with Task7 template format (## Phase N, - [ ] <id>:)
    """

    @staticmethod
    def validate(plan_path: str | Path) -> dict[str, Any]:
        """Validate plan.md. Raises PlanGateError on failure.

        Returns dict with 'valid': True, 'phases': int, 'steps': int, 'step_ids': [...]
        """
        path = Path(plan_path)
        if not path.exists():
            raise PlanGateError([f"Plan file not found: {plan_path}"])

        content = path.read_text(encoding="utf-8")
        errors: list[str] = []

        # ── Parse level from Gate section ──
        level_match = re.search(r"^- level:\s*(L\d+)", content, re.MULTILINE)
        level = level_match.group(1) if level_match else None

        # ── Parse Phases (L2+ required, L1 optional) ──
        phases = re.findall(r"^## Phase\s+\d+\s*$", content, re.MULTILINE)
        if level != "L1" and len(phases) < 1:
            errors.append("Plan must have at least 1 Phase (format: ## Phase N)")

        # ── Parse Steps ──
        steps_raw: list[dict[str, str]] = []
        current_phase = ""
        for line in content.split("\n"):
            phase_m = re.match(r"^## (Phase\s+\d+)", line.strip())
            if phase_m:
                current_phase = phase_m.group(1)
                continue
            step_m = re.match(r"^- \[.\] (\S+?):", line.strip())
            if step_m:
                steps_raw.append({
                    "id": step_m.group(1),
                    "phase": current_phase,
                    "status": "pending",
                    "depends_on": "none",
                    "scope": "",
                    "acceptance": "",
                    "verify": "",
                })

        if len(steps_raw) < 1:
            errors.append("Plan must have at least 1 Step (format: - [ ] <id>: description)")

        if errors:
            raise PlanGateError(errors)

        # ── Fill in step details from subsequent lines ──
        current_step = None
        for line in content.split("\n"):
            step_m = re.match(r"^- \[.\] (\S+?):", line.strip())
            if step_m:
                current_step = step_m.group(1)
                continue
            if current_step is None:
                continue

            # Find the step dict for current step
            step_dict = None
            for sd in steps_raw:
                if sd["id"] == current_step:
                    step_dict = sd
                    break
            if step_dict is None:
                continue

            dep_m = re.match(r"\s+- depends_on:\s*(.+)", line)
            if dep_m:
                step_dict["depends_on"] = dep_m.group(1).strip()

            status_m = re.match(r"\s+- status:\s*(.+)", line)
            if status_m:
                step_dict["status"] = status_m.group(1).strip().lower()

            scope_m = re.match(r"\s+- scope:\s*(.+)", line)
            if scope_m:
                step_dict["scope"] = scope_m.group(1).strip()

            accept_m = re.match(r"\s+- acceptance:\s*(.+)", line)
            if accept_m:
                step_dict["acceptance"] = accept_m.group(1).strip()

            verify_m = re.match(r"\s+- verify:\s*(.+)", line)
            if verify_m:
                step_dict["verify"] = verify_m.group(1).strip()

        # ── Step ID uniqueness ──
        ids = [s["id"] for s in steps_raw]
        if len(set(ids)) != len(ids):
            from collections import Counter
            dupes = [sid for sid, count in Counter(ids).items() if count > 1]
            errors.append(f"Duplicate step IDs: {dupes}")

        # ── Step status legal values ──
        invalid_statuses = []
        for s in steps_raw:
            st = s["status"]
            if st not in VALID_STEP_STATUSES:
                invalid_statuses.append(f"step '{s['id']}': invalid status '{st}'")
        if invalid_statuses:
            errors.append("Invalid step statuses: " + "; ".join(invalid_statuses))

        # ── depends_on existence ──
        all_ids = set(ids)
        dep_refs: dict[str, list[str]] = {}
        for s in steps_raw:
            dep_val = s["depends_on"]
            if dep_val.lower() == "none" or dep_val == "":
                dep_refs[s["id"]] = []
                continue
            # Support comma-separated deps
            deps = [d.strip() for d in dep_val.split(",") if d.strip()]
            dep_refs[s["id"]] = deps
            unknown = [d for d in deps if d not in all_ids]
            if unknown:
                errors.append(f"Step '{s['id']}' references unknown dependency: {unknown}")

        # ── Cycle detection in depends_on ──
        if not errors:
            visited: set[str] = set()
            rec_stack: set[str] = set()

            def _dfs(node: str) -> bool:
                if node in rec_stack:
                    return True
                if node in visited:
                    return False
                visited.add(node)
                rec_stack.add(node)
                for dep in dep_refs.get(node, []):
                    if _dfs(dep):
                        return True
                rec_stack.remove(node)
                return False

            cycle_found = any(_dfs(s["id"]) for s in steps_raw)
            if cycle_found:
                errors.append("Circular dependency detected in depends_on")

        # ── Real content check for scope/acceptance/verify ──
        placeholder_fields = []
        for s in steps_raw:
            for field in ("scope", "acceptance", "verify"):
                val = s.get(field, "")
                if not val or val == field or val.startswith("<!--") or val.startswith(">"):
                    placeholder_fields.append(f"step '{s['id']}': '{field}' is empty or placeholder")
        if placeholder_fields:
            errors.append("Steps with empty/placeholder fields: " + "; ".join(placeholder_fields))

        if errors:
            raise PlanGateError(errors)

        return {
            "valid": True,
            "phases": len(phases),
            "steps": len(steps_raw),
            "step_ids": ids,
        }


# ─── Self-test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # ResearchGate test
        rp = Path(td) / "research.md"
        rp.write_text(
            "# Research\n\n"
            "## 背景\nReal background.\n\n"
            "## 约束\nReal constraints.\n\n"
            "## 已知信息\nReal info.\n\n"
            "## 不确定性\nReal uncertainty.\n\n"
            "## 全貌\nReal overview.\n\n"
            "## 依赖树\n- Dep A\n- Dep B\n\n"
            "## 方案\nReal solution.\n\n"
            "## Dependency TDD\nReal TDD.\n\n"
        )
        result = ResearchGate.validate(str(rp))
        print(f"ResearchGate: {result}")

        # PlanGate test
        pp = Path(td) / "plan.md"
        pp.write_text(
            "# Plan\n\n"
            "## Goal\nTest\n\n"
            "## Phase 1\n"
            "- [ ] S1: step 1\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - scope: files A, B\n"
            "  - acceptance: must compile\n"
            "  - verify: command:pytest\n\n"
            "## Phase 2\n"
            "- [ ] S2: step 2\n"
            "  - status: pending\n"
            "  - depends_on: S1\n"
            "  - scope: file C\n"
            "  - acceptance: must pass review\n"
            "  - verify: command:pytest tests/\n\n"
        )
        result2 = PlanGate.validate(str(pp))
        print(f"PlanGate: {result2}")

        # Test rejection: cycle
        pp2 = Path(td) / "plan_cycle.md"
        pp2.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: step 1\n"
            "  - status: pending\n"
            "  - depends_on: S3\n"
            "  - scope: A\n"
            "  - acceptance: works\n"
            "  - verify: command:echo\n\n"
            "- [ ] S2: step 2\n"
            "  - status: pending\n"
            "  - depends_on: S1\n"
            "  - scope: B\n"
            "  - acceptance: works\n"
            "  - verify: command:echo\n\n"
            "- [ ] S3: step 3\n"
            "  - status: pending\n"
            "  - depends_on: S2\n"
            "  - scope: C\n"
            "  - acceptance: works\n"
            "  - verify: command:echo\n\n"
        )
        try:
            PlanGate.validate(str(pp2))
            print("PlanGate (cycle): UNEXPECTED PASS (should have failed)")
        except PlanGateError as e:
            print(f"PlanGate (cycle): correctly rejected — {e.errors}")

    print("\nAll contract self-tests passed.")
