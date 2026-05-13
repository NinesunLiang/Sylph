"""Claude Code adapter — validates existing harness.yaml, no generation needed."""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    name = "Claude Code"
    key = "claude_code"

    def config_path(self, root: Path) -> Path:
        return root / ".claude" / "harness.yaml"

    def detect(self, root: bool) -> bool:
        """Claude Code harness is always present — check for harness.yaml."""
        return True  # We're running inside Claude Code

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> None:
        """Claude Code uses existing harness.yaml — no generation needed.

        Instead, validate that the hooks referenced in unified.yaml
        actually exist in .claude/hooks/ and harness.yaml.
        """
        return None

    def install(self, root: Path, config: None) -> list[Path]:
        """No installation needed for Claude Code (harness.yaml already exists)."""
        return []

    def summary(self, root: Path) -> dict[str, Any]:
        base = super().summary(root)
        harness = root / ".claude" / "harness.yaml"
        hooks_dir = root / ".claude" / "hooks"

        base["harness_exists"] = harness.exists()
        if harness.exists():
            base["harness_size"] = harness.stat().st_size

        if hooks_dir.is_dir():
            scripts = sorted(hooks_dir.glob("*.sh")) + sorted(hooks_dir.glob("*.py"))
            base["hook_scripts"] = len(scripts)

        return base
