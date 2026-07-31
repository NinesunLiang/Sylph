#!/usr/bin/env python3
"""Process raw Playwright observations through token_bootstrap to generate catalog."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(
    Path(__file__).resolve().parent.parent /
    ".claude/workflows/frontend-overnight/scripts"
))

from ui_autopilot.token_bootstrap import bootstrap_from_observations

RAW_DATA = Path("/tmp/tokens-raw.json")
OUTPUT_PATH = Path(
    "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/token-catalog.json"
)

raw = json.loads(RAW_DATA.read_text())
observations = raw["observations"]
custom_properties = raw["custom_properties"]

result = bootstrap_from_observations(observations, custom_properties, OUTPUT_PATH.parent)

output = {
    "source_url": "https://xsimplechat.com/",
    "extraction_method": "playwright (node)",
    "observations_processed": len(observations),
    "native_variables": result.native_variables,
    "token_index": result.token_index,
    "css_variables": result.css_variables,
    "summary": result.summary,
    "extracted_count": len(result.extracted),
}

OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ token-catalog.json written ({len(result.extracted)} tokens extracted)")
print(f"   Categories: {result.summary.get('categories', {})}")
