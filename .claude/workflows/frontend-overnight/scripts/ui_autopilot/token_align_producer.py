"""token_align_producer.py — D6 Token alignment measurement producer.

Scans implementation source files and compares token usage against the token catalog
to compute alignment rate: (used_tokens / total_tokens).

P0-3 fix: Provides D6 dimension (18% weight) previously missing from UIF-99 scoring.

Design:
  - Static analysis: grep for token references in .tsx/.scss files
  - Token catalog: reads .omc/ui-autopilot/*/token-catalog.json or artifacts/tokens/
  - Output schema: {"alignment_rate": float, "used_tokens": int, "total_tokens": int}

Usage:
  python3 token_align_producer.py --source-dir src/pages --catalog-path .omc/.../token-catalog.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ── Token Catalog Loader ───────────────────────────────────────────────────────


def load_token_catalog(catalog_path: Path) -> set[str]:
    """Load token identifiers from catalog JSON.

    Expected catalog format:
      {
        "tokens": [
          {"id": "color-primary-500", "value": "#3B82F6", ...},
          {"id": "spacing-md", "value": "16px", ...}
        ]
      }

    Returns:
        Set of token IDs
    """
    if not catalog_path.exists():
        print(f"WARNING: Token catalog not found: {catalog_path}", file=sys.stderr)
        return set()

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        tokens = data.get("tokens", [])
        return {t["id"] for t in tokens if isinstance(t, dict) and "id" in t}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Failed to parse token catalog: {e}", file=sys.stderr)
        return set()


# ── Source File Scanner ────────────────────────────────────────────────────────


def scan_token_usage(source_dir: Path, token_ids: set[str]) -> set[str]:
    """Scan source files for token references.

    Token reference patterns:
      - CSS variables: var(--color-primary-500)
      - SCSS variables: $spacing-md
      - TS imports: tokens.colorPrimary500
      - Literal strings: "color-primary-500"

    Args:
        source_dir: Root directory to scan (.tsx, .ts, .scss, .css)
        token_ids: Set of valid token IDs from catalog

    Returns:
        Set of token IDs found in source files
    """
    used_tokens = set()

    patterns = [
        re.compile(r"var\(--([a-zA-Z0-9_-]+)\)"),       # CSS variables
        re.compile(r"\$([a-zA-Z0-9_-]+)"),              # SCSS variables
        re.compile(r"tokens\.([a-zA-Z0-9_]+)"),         # TS token object
        re.compile(r"['\"]([a-zA-Z0-9_-]+)['\"]"),      # String literals
    ]

    extensions = {".tsx", ".ts", ".scss", ".css"}

    if not source_dir.exists():
        print(f"WARNING: Source directory not found: {source_dir}", file=sys.stderr)
        return used_tokens

    for file_path in source_dir.rglob("*"):
        if file_path.suffix not in extensions:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            for pattern in patterns:
                for match in pattern.finditer(content):
                    token_candidate = match.group(1)
                    # Normalize camelCase to kebab-case for comparison
                    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", token_candidate).lower()
                    if normalized in token_ids:
                        used_tokens.add(normalized)
                    elif token_candidate in token_ids:
                        used_tokens.add(token_candidate)
        except (OSError, UnicodeDecodeError) as e:
            print(f"WARNING: Failed to read {file_path}: {e}", file=sys.stderr)
            continue

    return used_tokens


# ── Alignment Rate Computer ────────────────────────────────────────────────────


def compute_alignment_rate(used_tokens: set[str], total_tokens: set[str]) -> dict[str, Any]:
    """Compute token alignment rate.

    Args:
        used_tokens: Set of token IDs found in source
        total_tokens: Set of all token IDs from catalog

    Returns:
        Measurement dict with alignment_rate, used_tokens, total_tokens
    """
    used_count = len(used_tokens)
    total_count = len(total_tokens)

    if total_count == 0:
        alignment_rate = 0.0
    else:
        alignment_rate = used_count / total_count

    return {
        "alignment_rate": round(alignment_rate, 4),
        "used_tokens": used_count,
        "total_tokens": total_count,
        "used_token_ids": sorted(used_tokens),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="D6 Token alignment measurement producer"
    )
    parser.add_argument(
        "--source-dir", required=True, type=Path,
        help="Source directory to scan for token usage"
    )
    parser.add_argument(
        "--catalog-path", required=True, type=Path,
        help="Path to token catalog JSON"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output JSON path (default: stdout)"
    )

    args = parser.parse_args()

    # Load token catalog
    token_ids = load_token_catalog(args.catalog_path)
    if not token_ids:
        print("ERROR: No tokens loaded from catalog", file=sys.stderr)
        return 1

    # Scan source files
    used_tokens = scan_token_usage(args.source_dir, token_ids)

    # Compute alignment rate
    result = compute_alignment_rate(used_tokens, token_ids)

    # Write output
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output_json, encoding="utf-8")
        print(f"✅ D6 measurement written to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
