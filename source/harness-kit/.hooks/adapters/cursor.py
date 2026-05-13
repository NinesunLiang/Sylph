"""Cursor adapter — generates .cursor/hooks.json"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class CursorAdapter(BaseAdapter):
    name = "Cursor"
    key = "cursor"

    def config_path(self, root: Path) -> Path:
        return root / ".cursor" / "hooks.json"

    def detect(self, root: bool) -> bool:
        """Check if Cursor is configured or installed."""
        if (Path.home() / ".cursor").is_dir():
            return True
        if (Path.home() / "Library" / "Application Support" / "Cursor").is_dir():
            return True
        return False

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> dict[str, Any]:
        """Generate Cursor hooks.json.

        Cursor has separate events for shell, MCP, and file operations,
        unlike the unified PreToolUse on other platforms.

        Format:
        {
          "beforeShellExecution": [...],
          "afterShellExecution": [...],
          "beforeMCPExecution": [...],
          ...
        }

        Each entry in the array:
        { "type": "command", "command": "...", "timeout": 5 }
        """
        hooks_root = root / unified.get("meta", {}).get("hooks_root", ".claude/hooks")
        native: dict[str, list[dict]] = {}

        for hook_name, hook_def in hooks.items():
            events = hook_def.get("events", [])
            script = hook_def.get("script", "")
            timeout_s = hook_def.get("timeout", 5000) // 1000
            if timeout_s < 1:
                timeout_s = 1

            for evt in events:
                native_event = event_map.get(evt)
                if native_event is None:
                    continue  # event not supported

                if native_event not in native:
                    native[native_event] = []

                entry = {
                    "type": "command",
                    "command": f"bash .claude/hooks/{script}",
                    "timeout": timeout_s,
                }

                # Deduplicate
                existing = native[native_event]
                if not any(e.get("command") == entry["command"] for e in existing):
                    existing.append(entry)

        return {"hooks": native}

    def install(self, root: Path, config: dict[str, Any]) -> list[Path]:
        """Write .cursor/hooks.json"""
        import json
        output_path = self.config_path(root)
        self._ensure_dir(output_path)
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        return [output_path]
