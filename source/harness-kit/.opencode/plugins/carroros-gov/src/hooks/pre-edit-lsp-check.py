#!/usr/bin/env python3
"""
pre-edit-lsp-check.py — PreToolUse:Edit — 编辑前强制诊断检查 (v2)
编辑代码文件前主动获取诊断结果，注入 AI 上下文
永不阻断 (exit 0) — 诊断注入不阻断编辑
"""

import json
import re
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event


def safe_strip_ansi(text):
    """Strip ANSI escape sequences."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


def run_diagnostic(full_path, ext):
    """Run LSP diagnostic based on file extension. Returns diagnostic text."""
    full_path = Path(full_path)

    if not full_path.exists():
        return ""

    try:
        if ext in ("py", "pyi"):
            # Python: try pyright > py_compile
            try:
                result = subprocess.run(
                    ["pyright", str(full_path), "--outputjson"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode in (0, 1, 2):
                    d = json.loads(result.stdout)
                    errs = d.get("generalDiagnostics", [])
                    if errs:
                        lines = []
                        for e in errs[:5]:
                            sev = e.get("severity", "?")
                            line_num = e.get("range", {}).get("start", {}).get("line", "?")
                            msg = e.get("message", "")[:100]
                            lines.append(f"  L{sev} line {line_num}: {msg}")
                        return "\n".join(lines)
                    else:
                        return "  ✅ pyright: no errors"
            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
                pass

            # Fallback: py_compile
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(full_path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return "  ✅ py_compile: syntax OK"
                else:
                    return f"  ❌ compile failed: {safe_strip_ansi(result.stderr.strip()[:200])}"
            except Exception:
                pass

        elif ext in ("ts", "tsx", "js", "jsx"):
            try:
                result = subprocess.run(
                    ["tsc", "--noEmit", "--pretty", "false", str(full_path)],
                    capture_output=True, text=True, timeout=60
                )
                output = safe_strip_ansi(result.stdout or result.stderr or "")
                lines = [l for l in output.splitlines() if l.strip()][:5]
                return "\n".join(lines) if lines else ""
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                pass

            try:
                result = subprocess.run(
                    ["node", "--check", str(full_path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return "  ✅ node --check: syntax OK"
                else:
                    return f"  ❌ syntax error: {safe_strip_ansi(result.stderr.strip()[:200])}"
            except Exception:
                pass

        elif ext == "go":
            try:
                result = subprocess.run(
                    ["go", "vet", str(full_path)],
                    capture_output=True, text=True, timeout=60
                )
                if result.stderr.strip():
                    lines = [l for l in safe_strip_ansi(result.stderr).splitlines() if l.strip()][:5]
                    return "\n".join(lines) if lines else ""
                else:
                    return "  ✅ go vet: no issues"
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                pass

        elif ext == "rs":
            return "  ⚠️  Rust: no built-in syntax checker — use IDE getDiagnostics"

        elif ext in ("sh", "bash"):
            try:
                result = subprocess.run(
                    ["bash", "-n", str(full_path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return "  ✅ bash -n: syntax OK"
                else:
                    return f"  ❌ bash syntax error: {safe_strip_ansi(result.stderr.strip()[:200])}"
            except Exception:
                pass

    except Exception:
        pass

    return ""


def main():
    if not hc_enabled("lsp_gate"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    file_path = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or {}
            file_path = ti.get("file_path", "") or parsed.get("args", {}).get("filePath", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    project_root = (_HOOKS_DIR / "../..").resolve()
    ext = Path(file_path).suffix.lstrip(".") if "." in file_path else ""

    full_path = project_root / file_path
    if not full_path.exists():
        full_path = Path(file_path)

    if not full_path.exists():
        # File doesn't exist yet (new file being created) — no diagnostics possible
        ctx = f"[lsp-gate] 编辑前诊断: {file_path}\n  ⚠️ 文件尚未创建，跳过诊断"
        print(ctx, file=sys.stderr)
        result = json.dumps({
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": ctx
            }
        })
        print(result)
        sys.exit(0)

    # Supported extensions
    supported_exts = ("py", "pyi", "ts", "tsx", "js", "jsx", "go", "rs", "sh", "bash")
    if ext not in supported_exts:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    diag_output = run_diagnostic(str(full_path), ext)

    if diag_output:
        ctx = f"[lsp-gate] 编辑前诊断: {file_path}\n{diag_output}"
        print(ctx, file=sys.stderr)
        flywheel_event("pre_edit_lsp", "diagnostics_checked", "L2", f"ext={ext}")
    else:
        ctx = f"[lsp-gate] 🔍 编辑 {file_path} — 无本地诊断工具，请用 IDE getDiagnostics"
        print(ctx, file=sys.stderr)
        flywheel_event("pre_edit_lsp", "diagnostics_reminder", "L2", f"ext={ext}")

    # Inject diagnostics into AI context via additionalContext
    inject_text = ctx
    result = json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": inject_text
        }
    })
    print(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
