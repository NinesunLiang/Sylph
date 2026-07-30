"""measure_implementation.py — Extract computed styles from implementation pages via Playwright.

Identical structure to measure_prototype.py but targets the implementation URL.
This allows scorer.py to compute diffs between prototype (gold) and implementation (current).

Usage:
  python3 measure_implementation.py --url http://localhost:3000/app \
    --regions regions.json --output measurements.json

Design: GAP 3 fix — measurement producer for scorer.py input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install", file=sys.stderr)
    sys.exit(1)


# ── Measurement Extractor ──────────────────────────────────────────────────────


def extract_region_measurements(page: Page, region: dict[str, Any]) -> dict[str, Any]:
    """Extract computed styles for a single region.

    Args:
        page: Playwright page object
        region: Region definition with {id, selector, bbox, ...}

    Returns:
        Measurement dict with bbox/colors/fonts/borders/shadows/layout
    """
    region_id = region.get("id", "")
    selector = region.get("selector", f"[data-region='{region_id}']")

    # Check if element exists
    try:
        element = page.locator(selector).first
        if not element.is_visible(timeout=500):
            return {"error": f"Region {region_id} not visible"}
    except Exception as e:
        return {"error": f"Region {region_id} not found: {e}"}

    # Extract bounding box
    bbox = element.bounding_box()
    if not bbox:
        return {"error": f"Region {region_id} has no bounding box"}

    # Extract computed styles
    computed = page.evaluate("""(selector) => {
        const el = document.querySelector(selector);
        if (!el) return null;

        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        // Extract color palette from background/color/border
        const colors = new Set();
        if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
            colors.add(style.backgroundColor);
        }
        if (style.color) colors.add(style.color);
        if (style.borderColor) colors.add(style.borderColor);

        // Extract font info
        const fonts = [{
            family: style.fontFamily,
            size: parseFloat(style.fontSize),
            weight: parseInt(style.fontWeight),
            lineHeight: style.lineHeight,
        }];

        // Extract border/radius
        const borders = [{
            radius: parseFloat(style.borderRadius),
            width: parseFloat(style.borderWidth),
            style: style.borderStyle,
            color: style.borderColor,
        }];

        // Extract shadows
        const shadows = [];
        if (style.boxShadow && style.boxShadow !== 'none') {
            shadows.push(style.boxShadow);
        }

        // Extract layout
        const layout = {
            display: style.display,
            flexDirection: style.flexDirection,
            gap: parseFloat(style.gap) || 0,
            padding: style.padding,
            margin: style.margin,
            overflow: style.overflow,
        };

        return {
            colors: Array.from(colors),
            fonts,
            borders,
            shadows,
            layout,
        };
    }""", selector)

    if not computed:
        return {"error": f"Failed to compute styles for {region_id}"}

    return {
        "bbox": {
            "x": bbox["x"],
            "y": bbox["y"],
            "width": bbox["width"],
            "height": bbox["height"],
        },
        "colors": computed.get("colors", []),
        "fonts": computed.get("fonts", []),
        "borders": computed.get("borders", []),
        "shadows": computed.get("shadows", []),
        "layout": computed.get("layout", {}),
    }


# ── Main Entry ─────────────────────────────────────────────────────────────────


def measure_implementation(url: str, regions: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract measurements from implementation page.

    Args:
        url: Implementation page URL
        regions: List of region definitions

    Returns:
        Measurements dict keyed by region_id
    """
    measurements = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1024})

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            return {"error": f"Failed to load {url}: {e}"}

        for region in regions:
            region_id = region.get("id", "")
            measurements[region_id] = extract_region_measurements(page, region)

        browser.close()

    return measurements


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract implementation measurements")
    parser.add_argument("--url", required=True, help="Implementation page URL")
    parser.add_argument("--regions", required=True, help="Regions JSON file")
    parser.add_argument("--output", required=True, help="Output measurements JSON")
    args = parser.parse_args()

    # Load regions
    regions_path = Path(args.regions)
    if not regions_path.exists():
        print(f"ERROR: Regions file not found: {args.regions}", file=sys.stderr)
        sys.exit(1)

    with regions_path.open("r", encoding="utf-8") as f:
        regions = json.load(f)

    if not isinstance(regions, list):
        regions = regions.get("regions", [])

    # Extract measurements
    measurements = measure_implementation(args.url, regions)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(measurements, f, ensure_ascii=False, indent=2)

    print(f"Measurements written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
