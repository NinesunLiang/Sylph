"""Cross-platform hook adapters for AI Coding CLI tools."""

from .base import BaseAdapter
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .gemini import GeminiAdapter
from .qwen import QwenAdapter
from .cursor import CursorAdapter
from .opencode import OpenCodeAdapter

__all__ = [
    "BaseAdapter",
    "ClaudeCodeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "QwenAdapter",
    "CursorAdapter",
    "OpenCodeAdapter",
]

# All adapters in priority order (most portable first, Claude Code last)
ADAPTERS: list[BaseAdapter] = [
    CodexAdapter(),
    GeminiAdapter(),
    QwenAdapter(),
    CursorAdapter(),
    OpenCodeAdapter(),
    ClaudeCodeAdapter(),  # Claude Code last — references existing harness.yaml
]
