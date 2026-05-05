"""Qwen Code adapter — generates hooks config in project settings.json"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class QwenAdapter(BaseAdapter):
    name = "Qwen Code"
    key = "qwen"

    def config_path(self, root: Path) -> Path:
        return root / "settings.json"

    def detect(self, root: bool) -> bool:
        """Check if Qwen Code is installed."""
        import shutil
        if shutil.which("qwen"):
            return True
        if (Path.home() / ".qwen").is_dir():
            return True
        return False

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> dict[str, Any]:
        """Generate Qwen Code hooks config.

        Qwen format (settings.json):
        {
          "hooks": {
            "PreToolUse": [
              {
                "hooks": [
                  { "type": "command", "command": "...", "timeout": 5000 }
                ]
              }
            ],
            ...
          }
        }

        Note: Qwen uses ms for timeout, others use seconds.
        """
        hooks_root = root / unified.get("meta", {}).get("hooks_root", ".claude/hooks")
        native: dict[str, list[dict]] = {}

        for hook_name, hook_def in hooks.items():
            events = hook_def.get("events", [])
            script = hook_def.get("script", "")
            timeout_ms = hook_def.get("timeout", 5000)  # Qwen uses ms

            for evt in events:
                native_event = event_map.get(evt)
                if native_event is None:
                    continue

                if native_event not in native:
                    native[native_event] = []

                entry = {
                    "type": "command",
                    "command": f"bash .claude/hooks/{script}",
                    "timeout": timeout_ms,
                }

                existing = native[native_event]
                dup = any(
                    h.get("command") == entry["command"]
                    for g in existing
                    for h in g.get("hooks", [])
                )
                if not dup:
                    existing.append({"hooks": [entry]})

        return {"disableAllHooks": False, "hooks": native}

    def install(self, root: Path, config: dict[str, Any]) -> list[Path]:
        """Write project settings.json with hooks config."""
        import json
        output_path = self.config_path(root)

        existing = {}
        if output_path.exists():
            try:
                existing = json.loads(output_path.read_text())
            except Exception:
                pass

        # Preserve non-hooks settings, merge hooks
        existing["disableAllHooks"] = config.get("disableAllHooks", False)
        existing.setdefault("hooks", {}).update(config.get("hooks", {}))

        with open(output_path, "w") as f:
            json.dump(existing, f, indent=2)

        return [output_path]
