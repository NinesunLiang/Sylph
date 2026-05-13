#!/usr/bin/env python3
"""
test_token_transcript_parser.py -- Unit tests for token_transcript_parser.py

Coverage:
  1. compute_metrics: Basic usage sequence
  2. compute_metrics: Empty sequence returns None
  3. compute_metrics: Compact detection (context drop >30%)
  4. compute_metrics: Context percentage calculation
  5. compute_metrics: Zero context limit handling
  6. ParserRegistry: Register, get, list
  7. ParserRegistry: Get non-existent returns None
  8. detect_platform: No platform detected
  9. ClaudeCodeParser: init and method existence
  10. OpenCodeParser: init and method existence
  11. write_state: Creates file with valid JSON
"""

import unittest
import json
import os
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from token_transcript_parser import (
    BaseParser, ParserRegistry, ClaudeCodeParser, OpenCodeParser,
    detect_platform, write_state, CONTEXT_LIMITS, STATE_DIR,
)


class TestComputeMetrics(unittest.TestCase):
    """Tests for BaseParser.compute_metrics()."""

    def test_basic_sequence(self):
        """Basic usage sequence produces correct totals."""
        usage_seq = [
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 100},
            {"input_tokens": 200, "cache_read_input_tokens": 50, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 250},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertIsNotNone(result)
        self.assertEqual(result["session_id"], "session-1")
        self.assertEqual(result["total_turns"], 2)
        self.assertEqual(result["total_input_tokens"], 300)
        self.assertEqual(result["total_cache_read_tokens"], 50)
        self.assertEqual(result["total_cache_create_tokens"], 0)
        self.assertEqual(result["total_output_tokens"], 150)
        self.assertEqual(result["peak_context"], 250)
        self.assertEqual(result["current_context"], 250)

    def test_empty_sequence(self):
        """Empty usage sequence returns None."""
        result = BaseParser.compute_metrics([], 200000, "session-1", "claude_code")
        self.assertIsNone(result)

    def test_compact_detection(self):
        """Context drop >30% is detected as a compact event."""
        usage_seq = [
            {"input_tokens": 1000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 1000},
            {"input_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 200},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertEqual(result["compact_events"], 1)
        self.assertEqual(result["compact_savings"], 800)

    def test_no_compact_detection(self):
        """Small context drop (<30%) is not a compact event."""
        usage_seq = [
            {"input_tokens": 1000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 1000},
            {"input_tokens": 800, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 800},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertEqual(result["compact_events"], 0)
        self.assertEqual(result["compact_savings"], 0)

    def test_context_increase_not_compact(self):
        """Context increase is not detected as compact."""
        usage_seq = [
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 100},
            {"input_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 200},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertEqual(result["compact_events"], 0)

    def test_context_percentage(self):
        """Context percentage is calculated correctly."""
        usage_seq = [
            {"input_tokens": 50000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 50000},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertAlmostEqual(result["context_pct"], 25.0)

    def test_zero_context_limit(self):
        """Zero context limit results in 0.0 percentage."""
        usage_seq = [
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 10, "context_used": 100},
        ]
        result = BaseParser.compute_metrics(usage_seq, 0, "session-1", "claude_code")
        self.assertEqual(result["context_pct"], 0.0)

    def test_multiple_compacts(self):
        """Multiple compact events are counted correctly."""
        usage_seq = [
            {"input_tokens": 1000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 1000},
            {"input_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 200},
            {"input_tokens": 800, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 100, "context_used": 800},
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 50, "context_used": 100},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertEqual(result["compact_events"], 2)

    def test_session_start_cost(self):
        """Session start cost equals first entry's context_used."""
        usage_seq = [
            {"input_tokens": 500, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 10, "context_used": 500},
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 20, "context_used": 100},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "claude_code")
        self.assertEqual(result["session_start_cost"], 500)

    def test_platform_field(self):
        """Platform field is preserved in result."""
        usage_seq = [
            {"input_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 10, "context_used": 100},
        ]
        result = BaseParser.compute_metrics(usage_seq, 200000, "session-1", "opencode")
        self.assertEqual(result["platform"], "opencode")


class TestParserRegistry(unittest.TestCase):
    """Tests for ParserRegistry."""

    def test_register_and_get(self):
        """Register and retrieve a parser class."""
        ParserRegistry.register("test_parser", ClaudeCodeParser)
        cls = ParserRegistry.get("test_parser")
        self.assertIs(cls, ClaudeCodeParser)

    def test_get_nonexistent(self):
        """Getting non-existent parser returns None."""
        cls = ParserRegistry.get("nonexistent_parser")
        self.assertIsNone(cls)

    def test_list_includes_defaults(self):
        """List includes default registered parsers."""
        names = ParserRegistry.list()
        self.assertIn("claude_code", names)
        self.assertIn("opencode", names)

    def test_list_is_copy(self):
        """List returns a copy, not the internal list."""
        names = ParserRegistry.list()
        ParserRegistry.register("ephemeral", ClaudeCodeParser)
        names2 = ParserRegistry.list()
        self.assertGreaterEqual(len(names2), len(names))


class TestDetectPlatform(unittest.TestCase):
    """Tests for detect_platform()."""

    def test_no_platform_detected(self):
        """When no platform data sources exist, returns None."""
        platform = detect_platform()
        # In a test environment, neither claude_code nor opencode should be detected
        self.assertIsNone(platform)


class TestClaudeCodeParser(unittest.TestCase):
    """Tests for ClaudeCodeParser."""

    def test_init_with_transcript_path(self):
        """Parser initializes with given transcript path."""
        parser = ClaudeCodeParser(transcript_path="/tmp/test.jsonl")
        self.assertEqual(parser.transcript_path, "/tmp/test.jsonl")

    def test_init_no_path(self):
        """Parser initializes without path."""
        parser = ClaudeCodeParser()
        self.assertIsNone(parser.transcript_path)

    def test_detect_returns_false_with_fake_path(self):
        """detect() returns False for non-existent path."""
        parser = ClaudeCodeParser(transcript_path="/nonexistent/path.jsonl")
        self.assertFalse(parser.detect())


class TestOpenCodeParser(unittest.TestCase):
    """Tests for OpenCodeParser."""

    def test_init_with_db_path(self):
        """Parser initializes with given db path."""
        parser = OpenCodeParser(db_path="/tmp/test.db")
        self.assertEqual(parser.db_path, "/tmp/test.db")

    def test_init_no_path(self):
        """Parser initializes without path."""
        parser = OpenCodeParser()
        self.assertIsNone(parser.db_path)

    def test_detect_returns_false_with_fake_db(self):
        """detect() returns False for non-existent db path."""
        parser = OpenCodeParser(db_path="/nonexistent/db.sqlite")
        self.assertFalse(parser.detect())

    def test_resolve_context_limit_default(self):
        """Unknown model ID returns default 200000."""
        limit = OpenCodeParser._resolve_context_limit("unknown-model-v42")
        self.assertEqual(limit, 200000)

    def test_resolve_context_limit_claude(self):
        """Model ID containing 'claude' returns 200000."""
        limit = OpenCodeParser._resolve_context_limit("anthropic.claude-sonnet-4-20250514")
        self.assertEqual(limit, CONTEXT_LIMITS["claude"])

    def test_resolve_context_limit_deepseek(self):
        """Model ID containing 'deepseek' returns 1000000."""
        limit = OpenCodeParser._resolve_context_limit("deepseek-chat-v3")
        self.assertEqual(limit, CONTEXT_LIMITS["deepseek"])

    def test_resolve_context_limit_gpt4(self):
        """Model ID containing 'gpt-4' returns 128000."""
        limit = OpenCodeParser._resolve_context_limit("gpt-4-turbo-2025")
        self.assertEqual(limit, CONTEXT_LIMITS["gpt-4"])

    def test_resolve_context_limit_case_insensitive(self):
        """Model ID matching is case insensitive."""
        limit = OpenCodeParser._resolve_context_limit("Claude-Opus-4")
        self.assertEqual(limit, CONTEXT_LIMITS["claude"])


class TestWriteState(unittest.TestCase):
    """Tests for write_state()."""

    def setUp(self):
        self.orig_state_dir = STATE_DIR
        self.temp_dir = Path(tempfile.mkdtemp())
        # Monkey-patch STATE_DIR
        import token_transcript_parser as ttp
        self.orig_ttp_state = ttp.STATE_DIR
        ttp.STATE_DIR = self.temp_dir

    def tearDown(self):
        import token_transcript_parser as ttp
        ttp.STATE_DIR = self.orig_ttp_state

    def test_write_state_creates_file(self):
        """write_state creates a valid JSON file."""
        data = {"session_id": "test", "total_turns": 5}
        result = write_state(data)
        self.assertTrue(result.exists())
        content = json.loads(result.read_text())
        self.assertEqual(content["session_id"], "test")
        self.assertEqual(content["total_turns"], 5)

    def test_write_state_returns_path(self):
        """write_state returns a Path object."""
        data = {"test": True}
        result = write_state(data)
        self.assertIsInstance(result, Path)


if __name__ == '__main__':
    unittest.main()
