#!/usr/bin/env python3
"""
resolve-doc-path.py — 根据路径注册表解析文件路径
Python 移植版，完全等价 resolve-doc-path.sh v1.0

用法: FILE_TYPE=auto-score-report python3 resolve-doc-path.py [date]
返回: 解析后的路径到 stdout; 未注册类型返回 "UNREGISTERED" 到 stderr + exit 1
"""

import os
import sys
from datetime import datetime
from pathlib import Path

FILE_TYPE = os.environ.get("FILE_TYPE", "")
DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
TS = datetime.now().strftime("%Y%m%d-%H%M%S")

if not FILE_TYPE:
    print("UNREGISTERED: FILE_TYPE not set", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
REGISTRY = PROJECT_ROOT / ".claude" / "reference" / "path-registry.yaml"

# Try YAML registry first
if REGISTRY.exists():
    try:
        import yaml
        with open(REGISTRY, "r") as f:
            reg = yaml.safe_load(f)
        entry = reg.get("paths", {}).get(FILE_TYPE, {})
        if entry:
            result = entry.get("path", "")
            if result:
                # Replace template variables
                result = result.replace("{date}", DATE)
                result = result.replace("{ts}", TS)
                print(result)
                sys.exit(0)
    except ImportError:
        pass
    except Exception:
        pass

# Fallback: hardcoded paths (keep system available)
HARDCODED_PATHS = {
    "auto-score-report": f".omc/state/scores/{DATE}/auto-score.json",
    "score-ux-report": f".omc/state/scores/{DATE}/score-ux.json",
    "smoke-test-log": f".omc/state/smoke/{DATE}/harness-smoke.log",
    "smoke-failure": f".omc/state/smoke/{DATE}/smoke-failure-{TS}.json",
    "capability-test-log": f".omc/state/capability/{DATE}/capability-matrix-test.log",
    "completion-evidence": f".omc/state/evidence/.completion-evidence-{TS}",
    "plan-document": f".omc/plans/{DATE}/",
    "task-state": f".omc/state/tasks/{TS}/",
    "dogfood-record": f".omc/state/dogfood/dogfood-{DATE}.yaml",
    "capability-test-report": f"docs/internal/capability-test-report-{DATE}.md",
    "mode-token": f".omc/state/tokens/{FILE_TYPE}.json",
    "file-lock": ".omc/locks/default.lock",
}

if FILE_TYPE in HARDCODED_PATHS:
    print(HARDCODED_PATHS[FILE_TYPE])
else:
    print(f"UNREGISTERED: {FILE_TYPE} 未在路径注册表中", file=sys.stderr)
    sys.exit(1)
