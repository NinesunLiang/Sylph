#!/usr/bin/env python3
"""lsp-gate.py — SessionStart — 检测项目语言对应的 LSP 是否可用
Role: 确保基础设施就绪再开始工作
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled


def main():
    # ── Guard ──
    if not hc_enabled("lsp_gate"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Path setup ──
    hooks_dir = Path(__file__).resolve().parent
    project_root = (hooks_dir / "../..").resolve()

    # ── Detect project language ──
    has_go = (project_root / "go.mod").exists() or bool(list(project_root.glob("*.go")))
    has_py = (project_root / "requirements.txt").exists() or \
             (project_root / "pyproject.toml").exists() or \
             bool(list(project_root.glob("*.py")))
    has_ts = False
    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        try:
            content = pkg_json.read_text(encoding="utf-8", errors="replace")
            if '"typescript"' in content:
                has_ts = True
        except Exception:
            pass
    has_rs = (project_root / "Cargo.toml").exists()

    # ── Detect LSP availability ──
    missing = []

    if has_go and not shutil.which("gopls"):
        missing.append("gopls (Go)")

    if has_py:
        has_pyright = shutil.which("pyright") is not None
        if not has_pyright:
            try:
                result = subprocess.run(
                    ["pip", "show", "pyright"],
                    capture_output=True, text=True, timeout=5
                )
                has_pyright = result.returncode == 0
            except Exception:
                has_pyright = False
        if not has_pyright:
            missing.append("pyright (Python)")

    if has_ts and not shutil.which("typescript-language-server"):
        missing.append("typescript-language-server (TS)")

    if has_rs and not shutil.which("rust-analyzer"):
        missing.append("rust-analyzer (Rust)")

    # ── Output ──
    if missing:
        missing_str = " ".join(missing)
        result = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[lsp-gate] 项目语言缺少LSP: {missing_str}。"
                    "Run: brew install gopls pyright typescript-language-server rust-analyzer"
                )
            }
        }
        print(json.dumps(result, ensure_ascii=True))
    else:
        print('{"continue": true}')

    sys.exit(0)


if __name__ == "__main__":
    main()
