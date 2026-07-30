"""interaction_assertion_runner.py — D7 Interaction coverage measurement producer.

Runs Playwright assertions from the assertion catalog to measure interaction coverage:
  (passed_assertions / total_assertions).

P0-3 fix: Provides D7 dimension (24% weight) previously missing from UIF-99 scoring.

Design:
  - Assertion catalog: reads .omc/ui-autopilot/*/assertion-catalog.yaml
  - Playwright runner: executes each assertion against implementation URL
  - Output schema: {"interaction_coverage": float, "passed": int, "total": int}

Usage:
  python3 interaction_assertion_runner.py --url http://localhost:3000 \
    --catalog .omc/.../assertion-catalog.yaml --output measurements.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ── Assertion Catalog Loader ───────────────────────────────────────────────────


def load_assertion_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    """Load assertions from YAML catalog.

    Expected catalog format:
      assertions:
        - id: click-submit-button
          selector: "button[type=submit]"
          action: click
          expect: navigation
        - id: hover-menu-reveals-dropdown
          selector: ".menu-trigger"
          action: hover
          expect: visible:.dropdown-menu

    Returns:
        List of assertion dicts
    """
    if not catalog_path.exists():
        print(f"WARNING: Assertion catalog not found: {catalog_path}", file=sys.stderr)
        return []

    try:
        data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        return data.get("assertions", [])
    except (yaml.YAMLError, OSError) as e:
        print(f"ERROR: Failed to parse assertion catalog: {e}", file=sys.stderr)
        return []


# ── Assertion Runner ───────────────────────────────────────────────────────────


def run_assertion(page: Page, assertion: dict[str, Any]) -> tuple[bool, str]:
    """Execute a single Playwright assertion.

    Args:
        page: Playwright page object
        assertion: Assertion dict with {id, selector, action, expect}

    Returns:
        (passed: bool, reason: str)
    """
    assertion_id = assertion.get("id", "unknown")
    selector = assertion.get("selector")
    action = assertion.get("action")
    expect = assertion.get("expect")

    if not selector or not action:
        return False, f"{assertion_id}: missing selector or action"

    try:
        element = page.locator(selector).first

        # Execute action
        if action == "click":
            element.click(timeout=2000)
        elif action == "hover":
            element.hover(timeout=2000)
        elif action == "fill":
            fill_value = assertion.get("value", "test")
            element.fill(fill_value, timeout=2000)
        elif action == "check":
            element.check(timeout=2000)
        elif action == "select":
            select_value = assertion.get("value", "")
            element.select_option(select_value, timeout=2000)
        else:
            return False, f"{assertion_id}: unknown action '{action}'"

        # Verify expectation
        if expect == "navigation":
            page.wait_for_load_state("networkidle", timeout=3000)
            return True, f"{assertion_id}: navigation occurred"
        elif expect.startswith("visible:"):
            target_selector = expect.split(":", 1)[1]
            page.locator(target_selector).first.wait_for(state="visible", timeout=2000)
            return True, f"{assertion_id}: {target_selector} became visible"
        elif expect.startswith("hidden:"):
            target_selector = expect.split(":", 1)[1]
            page.locator(target_selector).first.wait_for(state="hidden", timeout=2000)
            return True, f"{assertion_id}: {target_selector} became hidden"
        elif expect == "enabled":
            if element.is_enabled(timeout=1000):
                return True, f"{assertion_id}: element enabled"
            return False, f"{assertion_id}: element not enabled"
        elif expect == "disabled":
            if element.is_disabled(timeout=1000):
                return True, f"{assertion_id}: element disabled"
            return False, f"{assertion_id}: element not disabled"
        else:
            # Default: action succeeded without explicit expectation
            return True, f"{assertion_id}: action succeeded"

    except PWTimeoutError as e:
        return False, f"{assertion_id}: timeout ({e})"
    except Exception as e:
        return False, f"{assertion_id}: error ({e})"


def run_all_assertions(url: str, assertions: list[dict[str, Any]]) -> dict[str, Any]:
    """Run all assertions against the implementation URL.

    Args:
        url: Implementation URL to test
        assertions: List of assertion dicts

    Returns:
        Measurement dict with interaction_coverage, passed, total
    """
    passed = 0
    total = len(assertions)
    results = []

    if total == 0:
        return {
            "interaction_coverage": 0.0,
            "passed": 0,
            "total": 0,
            "results": [],
        }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=10000)
        except Exception as e:
            print(f"ERROR: Failed to load {url}: {e}", file=sys.stderr)
            browser.close()
            return {
                "interaction_coverage": 0.0,
                "passed": 0,
                "total": total,
                "error": f"Failed to load URL: {e}",
            }

        for assertion in assertions:
            # Reset page state before each assertion
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=5000)
            except Exception:
                pass  # Continue with current state if reload fails

            assertion_passed, reason = run_assertion(page, assertion)
            if assertion_passed:
                passed += 1

            results.append({
                "id": assertion.get("id", "unknown"),
                "passed": assertion_passed,
                "reason": reason,
            })

        browser.close()

    coverage = passed / total if total > 0 else 0.0

    return {
        "interaction_coverage": round(coverage, 4),
        "passed": passed,
        "total": total,
        "results": results,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="D7 Interaction coverage measurement producer"
    )
    parser.add_argument(
        "--url", required=True,
        help="Implementation URL to test"
    )
    parser.add_argument(
        "--catalog", required=True, type=Path,
        help="Path to assertion catalog YAML"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output JSON path (default: stdout)"
    )

    args = parser.parse_args()

    # Load assertion catalog
    assertions = load_assertion_catalog(args.catalog)
    if not assertions:
        print("WARNING: No assertions loaded from catalog", file=sys.stderr)
        result = {
            "interaction_coverage": 0.0,
            "passed": 0,
            "total": 0,
            "results": [],
        }
    else:
        # Run assertions
        result = run_all_assertions(args.url, assertions)

    # Write output
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output_json, encoding="utf-8")
        print(f"✅ D7 measurement written to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
