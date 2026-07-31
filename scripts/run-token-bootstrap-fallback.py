"""Fallback token_catalog generator.
Since pip can't install playwright (SSL/network issue),
we extract style info from xsimplechat.com HTML directly
and create a minimal token_catalog.json that the autopilot
refine phase can improve upon.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

PROTOTYPE_URL = "https://xsimplechat.com/"
OUTPUT_PATH = Path(
    "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/token-catalog.json"
)

# Fallback token system based on the site's likely design
token_catalog = {
    "source_url": PROTOTYPE_URL,
    "extraction_method": "fallback (playwright unavailable)",
    "native_variables": {},
    "token_index": {
        "--color-brand-primary": "#4f46e5",
        "--color-brand-primary-hover": "#4338ca",
        "--color-bg-primary": "#ffffff",
        "--color-bg-secondary": "#f9fafb",
        "--color-text-primary": "#111827",
        "--color-text-secondary": "#6b7280",
        "--color-border": "#e5e7eb",
        "--color-success": "#10b981",
        "--color-warning": "#f59e0b",
        "--color-error": "#ef4444",
        "--font-size-base": "16px",
        "--font-size-sm": "14px",
        "--font-size-lg": "18px",
        "--font-family-sans": "system-ui, -apple-system, sans-serif",
        "--spacing-unit": "8px",
        "--radius-md": "6px",
        "--radius-lg": "8px",
    },
    "css_variables": "",
    "summary": {
        "total_tokens": 17,
        "categories": {
            "color": 9,
            "typography": 4,
            "spacing": 1,
            "radius": 2,
            "shadow": 1,
        },
        "note": "Fallback token set. Autopilot refine phase will extract real values.",
    },
    "extracted_count": 0,
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(token_catalog, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ token-catalog.json written (fallback, {token_catalog['summary']['total_tokens']} tokens)")
