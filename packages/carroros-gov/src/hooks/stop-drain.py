#!/usr/bin/env python3
"""
stop-drain.py — Stop — Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）

Role: Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input, output_continue,
    PROJECT_ROOT, STATE_DIR, HOME_DIR,
)


def sanitize(cmd: str) -> str:
    """Sanitize sensitive data from command strings."""
    if not isinstance(cmd, str):
        cmd = str(cmd) if cmd else ""

    # Mask sensitive flags
    cmd = re.sub(r'--password\s+\S+', '--password ***', cmd)
    cmd = re.sub(r'--token\s+\S+', '--token ***', cmd)
    cmd = re.sub(r'--secret\s+\S+', '--secret ***', cmd)
    cmd = re.sub(r'--key\s+\S+', '--key ***', cmd)

    # Mask API key env vars
    cmd = re.sub(
        r'(ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY|DEEPSEEK_BRIDGE_API_KEY|OPENAI_API_KEY|CODECLI_API_KEY|GEMINI_API_KEY)=\S+',
        r'\1=***', cmd
    )

    # Mask Authorization header
    cmd = re.sub(r"(Authorization:\s*Bearer\s+)[^\s\"'<>]+", r'\1***', cmd)

    # Mask tokens
    cmd = re.sub(r'(?:sk-|ghp_|xoxb-|xapp-)[a-zA-Z0-9_\-]{20,}', '***REDACTED***', cmd)
    cmd = re.sub(r'(?:eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{10,})', '***JWT***', cmd)

    # Mask lone surrogate escape sequences
    cmd = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', cmd)

    # Strip actual lone surrogate codepoints
    cmd = ''.join(c for c in cmd if not 0xD800 <= ord(c) <= 0xDFFF)

    return cmd


def classify(cmd: str) -> str:
    """Classify a command by type."""
    c = cmd.lower()
    if any(x in c for x in ['go build', 'npm run build', 'cargo build', 'tsc']):
        return 'build'
    if any(x in c for x in ['go test', 'npm test', 'pytest', 'jest']):
        return 'test'
    if 'git' in c:
        return 'git'
    if any(x in c for x in ['npm install', 'go get', 'pip install']):
        return 'dependency'
    if any(x in c for x in ['lint', 'eslint', 'golangci-lint']):
        return 'lint'
    if 'docker' in c:
        return 'docker'
    if any(x in c for x in ['curl', 'wget', 'http']):
        return 'network'
    if any(x in c for x in ['find', 'grep', 'sed', 'awk']):
        return 'file_ops'
    return 'runtime'


def main():
    if not hc_enabled("stop_drain"):
        output_continue()
        return

    flywheel_event("stop_drain", "active", "P2")

    input_str = read_input()

    # Parse transcript_path and session_id from stdin
    transcript = ""
    session_id = ""

    if input_str:
        try:
            data = json.loads(input_str)
            transcript = (data.get("transcript_path") or "").strip()
            session_id = (data.get("session_id") or "").strip()
        except (json.JSONDecodeError, Exception):
            pass

    if not transcript or not Path(transcript).exists():
        # Still run token tracking and state hygiene
        pass

    script_dir = _HOOKS_DIR
    state_dir = STATE_DIR

    # B1: Ghost mode detection + flywheel P0 events
    ghost_json = state_dir / "tokens" / "lx-ghost.json"
    ghost_auto = state_dir / "tokens" / "autonomous.active"
    exit_report = state_dir / "ghost-exit-report.md"
    pending = state_dir / "ghost-exit-pending"
    ghost_mode = False

    if ghost_json.exists():
        ghost_mode = True
        flywheel_buffer = HOME_DIR / ".claude" / "flywheel-buffer.jsonl"
        try:
            flywheel_buffer.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        if not exit_report.exists():
            entry = f"{time.strftime('%Y-%m-%d')},ghost_exit_report_missing,P0,{PROJECT_ROOT.name}\n"
            try:
                with open(str(flywheel_buffer), "a", encoding="utf-8") as f:
                    f.write(entry)
            except OSError:
                pass

        if pending.exists():
            entry = f"{time.strftime('%Y-%m-%d')},ghost_forced_close,P0,{PROJECT_ROOT.name}\n"
            try:
                with open(str(flywheel_buffer), "a", encoding="utf-8") as f:
                    f.write(entry)
            except OSError:
                pass

    # ── Layer 2: Scan transcript for error recovery ──
    if transcript and Path(transcript).exists():
        jsonl_path = state_dir / "error-signals.jsonl"

        # Load existing signatures for dedup
        seen = set()
        if jsonl_path.exists():
            try:
                with open(str(jsonl_path), encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                            seen.add((r.get("session_id", ""), r.get("signature", ""), r.get("ts", 0)))
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass

        recovered = 0
        try:
            with open(transcript, encoding="utf-8") as tf:
                for line in tf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Look for tool_result with is_error
                    content = None
                    if entry.get("type") == "user" and isinstance(entry.get("message"), dict):
                        content = entry["message"].get("content")

                    if not isinstance(content, list):
                        continue

                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") != "tool_result":
                            continue
                        is_error = item.get("is_error", False)
                        if not is_error:
                            continue

                        # Extract error content
                        result_content = item.get("content", "")
                        if isinstance(result_content, list):
                            result_content = " ".join(
                                c.get("text", "") for c in result_content if isinstance(c, dict)
                            )
                        result_content = str(result_content)[:500]

                        tool_use_id = item.get("tool_use_id", "")
                        cmd_clean = sanitize(f"[tool_use_id:{tool_use_id}]")
                        signature = hashlib.md5(cmd_clean.encode()).hexdigest()[:16]

                        # Timestamp fallback chain
                        ts = entry.get("timestamp", 0)
                        if isinstance(ts, str):
                            try:
                                ts = int(float(ts))
                            except (ValueError, TypeError):
                                ts = 0
                        elif not isinstance(ts, (int, float)):
                            ts = 0
                        if ts == 0:
                            try:
                                ts = int(os.path.getmtime(transcript))
                            except (OSError, ValueError):
                                ts = int(time.time())

                        key = (session_id, signature, ts)
                        if key in seen:
                            continue
                        seen.add(key)

                        # Sanitize result content
                        result_content_clean = sanitize(result_content)

                        record = {
                            "ts": ts,
                            "signature": signature,
                            "cmd": cmd_clean,
                            "exit_code": -1,
                            "error_type": classify(cmd_clean),
                            "message": result_content_clean[:200].replace("\n", " ").strip(),
                            "output_snippet": result_content_clean,
                            "session_id": session_id,
                            "session_start": ts - 3600,
                            "session_end": ts,
                            "origin": "stop-drain",
                            "mode": "ghost" if ghost_mode else "normal",
                        }
                        try:
                            state_dir.mkdir(parents=True, exist_ok=True)
                            with open(str(jsonl_path), "a", encoding="utf-8") as f:
                                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        except OSError:
                            pass
                        recovered += 1
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # ── Layer 3: Write token tracking ──
    token_parser = PROJECT_ROOT / ".claude" / "scripts" / "token_transcript_parser.py"
    if token_parser.exists():
        if transcript and Path(transcript).exists():
            try:
                subprocess.run(
                    [sys.executable, str(token_parser), "--parser", "claude_code",
                     "--transcript", transcript, "--write"],
                    capture_output=True, timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                subprocess.run(
                    [sys.executable, str(token_parser), "--write"],
                    capture_output=True, timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass

    # ── Layer 5: Write compact recovery memory ──
    extract_script = PROJECT_ROOT / ".claude" / "scripts" / "extract-compact-memory.py"
    if transcript and Path(transcript).exists() and extract_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(extract_script),
                 "--transcript", transcript,
                 "--handoff", str(state_dir / "session-handoff.md"),
                 "--dump", str(state_dir / "session-dump.json"),
                 "--output", str(state_dir / "todo-queue.md")],
                capture_output=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    # ── Layer 4: State directory hygiene ──
    if state_dir.exists():
        try:
            # Clean .tmp files
            for f in state_dir.glob("*.tmp.*"):
                try:
                    if time.time() - f.stat().st_mtime > 86400:
                        f.unlink()
                except OSError:
                    pass

            # Clean harness-smoke and snapshot files
            for pattern in ["harness-smoke-*.log", "snapshot-*.txt"]:
                max_keep = 3 if "snapshot" not in pattern else 5
                files = sorted(state_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[max_keep:]:
                    try:
                        f.unlink()
                    except OSError:
                        pass

            # Clean old completion evidence
            for f in state_dir.glob(".completion-evidence-*"):
                try:
                    if time.time() - f.stat().st_mtime > 86400:
                        f.unlink()
                except OSError:
                    pass
        except OSError:
            pass

    output_continue()


if __name__ == "__main__":
    main()
