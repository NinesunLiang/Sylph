"""Gemini CLI adapter — generates .gemini/settings.json hook config"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class GeminiAdapter(BaseAdapter):
    name = "Gemini CLI"
    key = "gemini"

    def config_path(self, root: Path) -> Path:
        return root / ".gemini" / "settings.json"

    def detect(self, root: bool) -> bool:
        """Check if Gemini CLI is installed."""
        import shutil
        if shutil.which("gcli") or shutil.which("gemini"):
            return True
        if (Path.home() / ".gemini").is_dir():
            return True
        return False

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> dict[str, Any]:
        """Generate Gemini CLI hooks config.

        Gemini format (settings.json):
        {
          "hooks": {
            "BeforeTool": [
              {
                "matcher": "shell",
                "hooks": [
                  { "type": "command", "command": "...", "timeout": 5 }
                ]
              }
            ],
            "AfterTool": [...]
          }
        }
        """
        hooks_root = root / unified.get("meta", {}).get("hooks_root", ".claude/hooks")
        native: dict[str, list[dict]] = {}

        for hook_name, hook_def in hooks.items():
            events = hook_def.get("events", [])
            script = hook_def.get("script", "")
            timeout_s = hook_def.get("timeout", 5000) // 1000
            if timeout_s < 1:
                timeout_s = 1
            blocking = hook_def.get("blocking", False)

            for evt in events:
                native_event = event_map.get(evt)
                if native_event is None:
                    continue

                if native_event not in native:
                    native[native_event] = []

                entry = {
                    "type": "command",
                    "command": f"bash .claude/hooks/{script}",
                    "timeout": timeout_s,
                }
                if blocking:
                    entry["decision"] = "deny"

                # Add to appropriate matcher group
                group = {
                    "hooks": [entry],
                }
                # Add matcher based on event type
                if evt in ("shell:before", "shell:after"):
                    group["matcher"] = "shell"

                # Deduplicate
                existing = native[native_event]
                dup = False
                for g in existing:
                    for h in g.get("hooks", []):
                        if h.get("command") == entry["command"]:
                            dup = True
                            break
                    if dup:
                        break
                if not dup:
                    existing.append(group)

        hooks_config = {"hooks": native}
        return hooks_config

    def install(self, root: Path, config: dict[str, Any]) -> list[Path]:
        """Write .gemini/settings.json"""
        import json
        output_path = self.config_path(root)
        self._ensure_dir(output_path)

        # Merge with existing settings if present
        existing = {}
        if output_path.exists():
            try:
                existing = json.loads(output_path.read_text())
            except Exception:
                pass

        existing["hooks"] = config.get("hooks", {})
        with open(output_path, "w") as f:
            json.dump(existing, f, indent=2)

        return [output_path]
