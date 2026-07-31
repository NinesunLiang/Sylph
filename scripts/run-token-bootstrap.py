"""Run token_bootstrap against xsimplechat.com prototype.
Collects computed style observations via Playwright,
then processes through token_bootstrap.bootstrap_from_observations().
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add ui_autopilot to path
sys.path.insert(0, str(
    Path(__file__).resolve().parent.parent /
    ".claude/workflows/frontend-overnight/scripts"
))

from ui_autopilot.token_bootstrap import (
    bootstrap_from_observations,
    get_bootstrap_script,
    get_custom_properties_script,
)

PROTOTYPE_URL = "https://xsimplechat.com/"
OUTPUT_PATH = Path(
    "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/token-catalog.json"
)


async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(PROTOTYPE_URL, wait_until="networkidle", timeout=30000)

        # Extract style observations
        properties = {
            "color", "background-color", "border-color",
            "font-size", "font-weight", "line-height",
            "border-radius", "gap", "padding",
            "width", "height", "box-shadow",
        }
        script = get_bootstrap_script()

        observations_str = await page.evaluate(
            script, {"properties": list(properties)}
        )

        # Extract CSS custom properties
        cp_script = get_custom_properties_script()
        custom_properties = await page.evaluate(cp_script)

        await browser.close()

    # Process
    result = bootstrap_from_observations(
        observations=observations_str,
        custom_properties=custom_properties,
        output_dir=OUTPUT_PATH.parent,
    )

    # Write JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "source_url": PROTOTYPE_URL,
        "native_variables": result.native_variables,
        "token_index": result.token_index,
        "css_variables": result.css_variables,
        "summary": result.summary,
        "extracted_count": len(result.extracted),
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ token-catalog.json written ({len(result.extracted)} tokens extracted)")


if __name__ == "__main__":
    asyncio.run(main())
