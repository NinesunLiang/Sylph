#!/usr/bin/env python3
"""
Compatibility shim.

oracle_agent.py has been split into:
- static_oracle_agent.py
- runtime_oracle_agent.py
- oracle_spawn.py

Use oracle_spawn.py for normal review.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

def main() -> int:
    script_dir = Path(__file__).resolve().parent
    target = script_dir / "static_oracle_agent.py"

    print(
        "DEPRECATED: oracle_agent.py is now static_oracle_agent.py. "
        "Use oracle_spawn.py for dual-agent review.",
        file=sys.stderr,
    )

    cmd = [sys.executable, str(target), *sys.argv[1:]]
    return subprocess.run(cmd, check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())