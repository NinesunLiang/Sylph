"""Base adapter interface for cross-platform hook config generation."""

from __future__ import annotations
from pathlib import Path
from typing import Any


class BaseAdapter:
    """Abstract base class for platform-specific hook adapters.

    Each adapter translates the unified event model + hook definitions
    into the platform's native configuration format.
    """

    # Display name for user-facing output
    name: str = ""
    # Config key in unified.yaml > platform_events mapping
    key: str = ""

    def config_path(self, root: Path) -> Path | None:
        """Return the path where the generated config should be written.

        Returns None if this platform doesn't use a file-based config.
        """
        return None

    def detect(self, root: Path) -> bool:
        """Detect whether this platform is available/configured in the project.

        Checks for platform-specific config files, directories, or CLI tools.
        """
        return False

    def generate(self, root: Path, unified: dict[str, Any],
                 hooks: dict[str, Any], event_map: dict[str, str]) -> Any:
        """Generate platform-specific config from unified definitions.

        Args:
            root: Project root directory
            unified: Full unified.yaml parsed dict
            hooks: Filtered hook definitions for this platform
            event_map: Mapping from universal event names to native event names
                       (already filtered: null entries removed)

        Returns:
            Platform-specific config. Type depends on the platform:
            - dict for JSON-based configs (Codex, Gemini, Qwen, Cursor)
            - str for code-based configs (OpenCode TypeScript plugin)
            - None if generation is not applicable (Claude Code uses existing harness.yaml)
        """
        return None

    def install(self, root: Path, config: Any) -> list[Path]:
        """Write the generated config to the correct location.

        Args:
            root: Project root directory
            config: Config object returned by generate()

        Returns:
            List of written file paths (empty if nothing written)
        """
        return []

    def summary(self, root: Path) -> dict[str, Any]:
        """Return a summary of this adapter's state.

        Returns dict with keys:
        - detected: bool
        - config_path: str or None
        - hook_count: int
        - events_used: list[str]
        """
        return {
            "detected": self.detect(root),
            "config_path": str(self.config_path(root)) if self.config_path(root) else None,
            "hook_count": 0,
            "events_used": [],
        }

    def _ensure_dir(self, path: Path) -> None:
        """Ensure parent directory exists."""
        path.parent.mkdir(parents=True, exist_ok=True)
