"""Codex CLI adapter — generates .codex/hooks.json"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class CodexAdapter(BaseAdapter):
    name = "Codex CLI"
    key = "codex"

    def config_path(self, root: Path) -> Path:
        return root / ".codex" / "hooks.json"

    def detect(self, root: Path) -> bool:
        """Check if Codex is installed or configured."""
        config_dir = Path.home() / ".codex"
        config_toml = config_dir / "config.toml"
        project_hooks = root / ".codex"
        # Detect by: codex CLI in PATH, or existing .codex dir
        import shutil
        if shutil.which("codex"):
            return True
        if config_dir.is_dir() or project_hooks.is_dir():
            return True
        return False

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> dict[str, Any]:
        """Generate Codex hooks.json from unified definitions.

        Codex format:
        {
          "hooks": {
            "EventName": [
              {
                "hooks": [
                  { "type": "command", "command": "...", "timeout": N }
                ]
              }
            ]
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

            for evt in events:
                native_event = event_map.get(evt)
                if native_event is None:
                    continue  # event not supported on this platform

                if native_event not in native:
                    native[native_event] = []

                rel_path = f".claude/hooks/{script}"
                entry = {
                    "type": "command",
                    "command": f"bash {rel_path}",
                    "timeout": timeout_s,
                }

                # Check if this event group already has this hook
                existing_groups = native[native_event]
                found = False
                for group in existing_groups:
                    for h in group.get("hooks", []):
                        if h.get("command") == entry["command"]:
                            found = True
                            break
                    if found:
                        break

                if not found:
                    existing_groups.append({"hooks": [entry]})

        return {"hooks": native}

    def install(self, root: Path, config: dict[str, Any]) -> list[Path]:
        """Write .codex/hooks.json and warn about config.toml."""
        import json
        output_path = self.config_path(root)
        self._ensure_dir(output_path)
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        return [output_path]

    def summary(self, root: Path) -> dict[str, Any]:
        base = super().summary(root)
        config_toml = Path.home() / ".codex" / "config.toml"
        hooks_enabled = False
        if config_toml.exists():
            try:
                content = config_toml.read_text()
                hooks_enabled = "codex_hooks = true" in content
            except Exception:
                pass
        base["hooks_enabled_in_config"] = hooks_enabled
        base["needs_config_toml"] = not hooks_enabled
        base["setup_help"] = (
            'Add to ~/.codex/config.toml:\n'
            '  [features]\n'
            '  codex_hooks = true'
        )
        return base
