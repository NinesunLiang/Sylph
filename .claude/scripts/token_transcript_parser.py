#!/usr/bin/env python3
"""
token-transcript-parser.py — 多平台 token 耗用解析器 v2.0

支持平台：
  claude_code — 解析 transcript.jsonl (assistant message usage 字段)
  opencode    — 解析 SQLite DB (part 表 step-finish tokens 字段)

架构：ParserRegistry + 平台 parser 注册
detect_platform() 自动识别，--parser 手动指定覆盖

输出：
  stdout: JSON 摘要
  .omc/state/token-tracking-real.json: 持久化记录（--write 时）

通用输出 schema：
  session_id, total_turns, current_context, peak_context, session_start_cost,
  total_input_tokens, total_cache_read_tokens, total_cache_create_tokens,
  total_output_tokens, total_context_used, compact_events, compact_savings,
  context_limit, context_pct, last_updated, platform
"""

import argparse
import json
import os
import sqlite3
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(".omc/state")
PROJECT_DIR = Path.cwd()
HOME = Path.home()

# Model → context limit mapping (token budget for context_pct calculation)
CONTEXT_LIMITS = {
    "claude": 200000,
    "deepseek": 1000000,
    "gpt-4": 128000,
    "gpt-3.5": 16385,
    "gemini": 2000000,
    "command": 128000,
}


class ParserRegistry:
    """Registry of platform-specific token parsers."""
    _parsers = {}

    @classmethod
    def register(cls, name, parser_cls):
        cls._parsers[name] = parser_cls

    @classmethod
    def get(cls, name):
        return cls._parsers.get(name)

    @classmethod
    def list(cls):
        return list(cls._parsers.keys())


class BaseParser(ABC):
    """Base class for platform-specific token parsers."""

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this platform's data source is available."""
        ...

    @abstractmethod
    def parse(self) -> dict | None:
        """Return parsed data in common schema, or None on failure."""
        ...

    @staticmethod
    def compute_metrics(usage_seq: list[dict], context_limit: int,
                        session_id: str, platform: str) -> dict | None:
        """Compute all metrics from a sequence of usage records."""
        if not usage_seq:
            return None

        total_input = sum(u["input_tokens"] for u in usage_seq)
        total_cache_read = sum(u["cache_read_input_tokens"] for u in usage_seq)
        total_cache_create = sum(u["cache_creation_input_tokens"] for u in usage_seq)
        total_output = sum(u["output_tokens"] for u in usage_seq)
        peak_context = max(u["context_used"] for u in usage_seq)
        current_context = usage_seq[-1]["context_used"]
        session_start_cost = usage_seq[0]["context_used"]
        total_context_used = total_input + total_cache_read + total_cache_create

        # Compact detection: consecutive context_used drop > 30%
        compact_events = 0
        compact_savings = 0
        for i in range(1, len(usage_seq)):
            prev_ctx = usage_seq[i - 1]["context_used"]
            curr_ctx = usage_seq[i]["context_used"]
            if prev_ctx > 0 and curr_ctx < prev_ctx * 0.7:
                drop = prev_ctx - curr_ctx
                compact_events += 1
                compact_savings += drop

        context_pct = 0.0
        if context_limit > 0 and current_context is not None:
            context_pct = round(current_context * 100 / context_limit, 1)

        return {
            "session_id": session_id,
            "total_turns": len(usage_seq),
            "current_context": current_context,
            "peak_context": peak_context,
            "session_start_cost": session_start_cost,
            "total_input_tokens": total_input,
            "total_cache_read_tokens": total_cache_read,
            "total_cache_create_tokens": total_cache_create,
            "total_output_tokens": total_output,
            "total_context_used": total_context_used,
            "compact_events": compact_events,
            "compact_savings": compact_savings,
            "context_limit": context_limit,
            "context_pct": context_pct,
            "last_updated": datetime.now().isoformat(),
            "platform": platform,
        }


# ══════════════════════════════════════════════════════════════════════
# Claude Code Parser
# ══════════════════════════════════════════════════════════════════════

class ClaudeCodeParser(BaseParser):
    """Parse Claude Code transcript JSONL files."""

    name = "claude_code"

    def __init__(self, transcript_path: str | None = None):
        self.transcript_path = transcript_path

    def detect(self) -> bool:
        if self.transcript_path and Path(self.transcript_path).exists():
            return True
        candidates = self._find_transcripts()
        return len(candidates) > 0

    def _find_transcripts(self) -> list[Path]:
        """Find transcript files for current project, sorted by mtime DESC."""
        encoded_cwd = "-".join(PROJECT_DIR.resolve().parts).lstrip("/")
        transcript_dir = HOME / ".claude" / "projects" / encoded_cwd

        if not transcript_dir.exists():
            # Fallback: search all project dirs
            all_projects = HOME / ".claude" / "projects"
            candidates = []
            for pdir in all_projects.iterdir():
                if pdir.is_dir():
                    for f in sorted(pdir.glob("*.jsonl"),
                                    key=lambda x: x.stat().st_mtime, reverse=True):
                        candidates.append(f)
            return sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True)[:3]

        return sorted(transcript_dir.glob("*.jsonl"),
                      key=lambda x: x.stat().st_mtime, reverse=True)

    def parse(self) -> dict | None:
        path = self._resolve_path()
        if not path:
            return None

        usage_seq = []
        session_id = path.stem
        context_limit = 200000  # default for Claude

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue

                msg = entry.get("message", {})
                usage = msg.get("usage", {})

                inp = usage.get("input_tokens", -1)
                if inp < 0:
                    continue

                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_create = usage.get("cache_creation_input_tokens", 0)
                output = usage.get("output_tokens", 0)

                # Claude Code always uses Claude API — fixed 200k limit
                # (transcript model field may show proxy/custom name)
                usage_seq.append({
                    "input_tokens": inp,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_create,
                    "output_tokens": output,
                    "context_used": inp + cache_read + cache_create,
                })

        if not usage_seq:
            return None

        result = self.compute_metrics(usage_seq, context_limit,
                                      session_id, "claude_code")
        result["transcript_path"] = str(path.resolve())
        return result

    def _resolve_path(self) -> Path | None:
        if self.transcript_path and Path(self.transcript_path).exists():
            return Path(self.transcript_path)
        candidates = self._find_transcripts()
        return candidates[0] if candidates else None



# ══════════════════════════════════════════════════════════════════════
# OpenCode Parser
# ══════════════════════════════════════════════════════════════════════

class OpenCodeParser(BaseParser):
    """Parse OpenCode SQLite DB for token usage.

    Data source: ~/.local/share/opencode/opencode.db
    Table: part (column: data, JSON with type="step-finish", tokens field)
    """

    name = "opencode"

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def detect(self) -> bool:
        path = self._resolve_db()
        return path is not None and path.exists()

    def _resolve_db(self) -> Path | None:
        if self.db_path:
            return Path(self.db_path)
        default = HOME / ".local" / "share" / "opencode" / "opencode.db"
        return default if default.exists() else None

    def parse(self) -> dict | None:
        db_path = self._resolve_db()
        if not db_path:
            return None

        cwd_str = str(PROJECT_DIR.resolve())
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            # 1. Find project_id for current working directory
            cursor = conn.execute(
                "SELECT id FROM project WHERE worktree = ?", (cwd_str,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            project_id = row["id"]

            # 2. Find most recent session for this project
            cursor = conn.execute(
                """SELECT id, slug, model FROM session
                   WHERE project_id = ? ORDER BY time_created DESC LIMIT 1""",
                (project_id,),
            )
            session = cursor.fetchone()
            if not session:
                return None

            session_id = session["id"]

            # 3. Parse model for context limit
            model_id = ""
            if session["model"]:
                try:
                    model_info = json.loads(session["model"])
                    model_id = model_info.get("id", "")
                except json.JSONDecodeError:
                    pass
            context_limit = self._resolve_context_limit(model_id)

            # 4. Get all step-finish parts ordered by time
            cursor = conn.execute(
                """SELECT p.data FROM part p
                   WHERE p.session_id = ? AND p.data LIKE '%step-finish%'
                   ORDER BY p.time_created ASC""",
                (session_id,),
            )

            usage_seq = []
            for row in cursor:
                try:
                    data = json.loads(row["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if data.get("type") != "step-finish":
                    continue

                tokens = data.get("tokens")
                if not tokens:
                    continue

                inp = tokens.get("input", -1)
                if inp < 0:
                    continue

                cache_read = tokens.get("cache", {}).get("read", 0)
                cache_create = tokens.get("cache", {}).get("write", 0)
                output = tokens.get("output", 0)

                usage_seq.append({
                    "input_tokens": inp,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_create,
                    "output_tokens": output,
                    "context_used": inp + cache_read + cache_create,
                })

            if not usage_seq:
                return None

            result = self.compute_metrics(usage_seq, context_limit,
                                          session_id, "opencode")
            result["db_path"] = str(db_path)
            result["slug"] = session["slug"]
            result["model"] = model_id
            return result

        finally:
            conn.close()

    @staticmethod
    def _resolve_context_limit(model_id: str) -> int:
        mid = model_id.lower()
        for key, limit in CONTEXT_LIMITS.items():
            if key in mid:
                return limit
        return 200000


# ══════════════════════════════════════════════════════════════════════
# Registry + auto-detect
# ══════════════════════════════════════════════════════════════════════

ParserRegistry.register("claude_code", ClaudeCodeParser)
ParserRegistry.register("opencode", OpenCodeParser)


def detect_platform() -> str | None:
    """Auto-detect which platform we're running on.

    Priority: claude_code > opencode > None
    Claude Code transcripts are ephemeral but more precise;
    OpenCode DB is persistent but may lag.
    """
    for name in ParserRegistry.list():
        parser_cls = ParserRegistry.get(name)
        parser = parser_cls()
        if parser.detect():
            return name
    return None


def write_state(data: dict) -> Path:
    """Write token-tracking-real.json to state dir."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / "token-tracking-real.json"
    state_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )
    return state_file


def main():
    parser_names = ParserRegistry.list()
    ap = argparse.ArgumentParser(
        description="Parse token usage from AI coding assistant transcripts"
    )
    ap.add_argument(
        "--parser", "-p", choices=parser_names,
        help="Parser to use (default: auto-detect)"
    )
    ap.add_argument(
        "--transcript", "-t",
        help="Claude Code transcript path (claude_code parser)"
    )
    ap.add_argument(
        "--db",
        help="OpenCode SQLite DB path (opencode parser)"
    )
    ap.add_argument(
        "--write", "-w", action="store_true",
        help="Write to token-tracking-real.json"
    )
    ap.add_argument(
        "--list", action="store_true",
        help="List available parsers and exit"
    )
    args = ap.parse_args()

    # --list: just list parsers
    if args.list:
        print("Available parsers:")
        for name in parser_names:
            print(f"  - {name}")
        return

    # Auto-detect or use specified parser
    parser_name = args.parser
    if not parser_name:
        parser_name = detect_platform()

    if not parser_name:
        print(json.dumps({"error": "No supported platform detected",
                          "note": "Checked: " + ", ".join(parser_names)},
                         ensure_ascii=False))
        sys.exit(1)

    # Instantiate
    parser_cls = ParserRegistry.get(parser_name)
    if parser_name == "claude_code":
        instance = parser_cls(transcript_path=args.transcript)
    elif parser_name == "opencode":
        instance = parser_cls(db_path=args.db)
    else:
        instance = parser_cls()

    # Parse
    result = instance.parse()
    if result is None:
        print(json.dumps({"error": f"No usage data found ({parser_name})"},
                         ensure_ascii=False))
        sys.exit(1)

    # Persist
    if args.write:
        written = write_state(result)
        result["state_file"] = str(written)

    # Output
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
