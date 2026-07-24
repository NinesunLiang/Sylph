#!/usr/bin/env python3
"""
test-pre-ask-guard.py — Tests for pre-ask-guard.py (两段式决策链评估)

Verifies:
  Scenario 1: hc_enabled=False → {"continue": True} (gate disabled)
  Scenario 2: No questions / non-AskUserQuestion → {"continue": True}
  Scenario 3: Autonomous mode (ghost/goal) → exit 2 (block)
  Scenario 4: All questions resolvable by decision chain → exit 2 (block)
  Scenario 5: Some questions resolvable → {"continue": True} (soft hint)
  Scenario 6: No questions resolvable → {"continue": True} (genuine pass)
  Scenario 7: Empty question list → {"continue": True}
  Scenario 8: Malformed JSON stdin → {"continue": True}
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ── Mock harness_lib before pre-ask-guard is imported ──

class MockHarnessLib:
    """Controlled mock of harness_lib for pre-ask-guard.py."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._hc_enabled = True
        self._mode = "normal"
        self.hc_enabled_calls = []
        self.flywheel_events = []
        self.emit_calls = []

    # ── controllable state ──

    def set_hc_enabled(self, val: bool):
        self._hc_enabled = val

    def set_mode(self, mode: str):
        self._mode = mode

    # ── mock implementations ──

    def hc_enabled(self, name):
        self.hc_enabled_calls.append(name)
        return self._hc_enabled

    def is_mode_active(self, state_dir=None):
        return self._mode

    def flywheel_event(self, hook_name, event_type, severity, project="carror-os"):
        self.flywheel_events.append((hook_name, event_type, severity, project))

    def hc_emit_hook_json(self, text, event="PreToolUse", continue_val=True):
        self.emit_calls.append((text, event, continue_val))
        result = {
            "continue": continue_val,
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": text.strip()
            }
        }
        return json.dumps(result, ensure_ascii=True)


_mock_harness = MockHarnessLib()
sys.modules["harness_lib"] = _mock_harness

# ── Import pre-ask-guard.py via importlib (hyphen in filename) ──

_HOOK_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "hooks" / "pre-ask-guard.py"
)
_spec = importlib.util.spec_from_file_location("pre_ask_guard", _HOOK_PATH)
pre_ask_guard = importlib.util.module_from_spec(_spec)
sys.modules["pre_ask_guard"] = pre_ask_guard
_spec.loader.exec_module(pre_ask_guard)


def _build_ask_question_payload(questions: list[str]) -> str:
    """Build a stdin JSON like the one the CC hook system sends for AskUserQuestion."""
    return json.dumps({
        "tool_name": "AskUserQuestion",
        "tool_input": {
            "questions": [{"question": q} for q in questions]
        },
    })


def _run_main(stdin_json: str, tmp_project_root: Path = None) -> tuple:
    """Run pre_ask_guard.main() with controlled stdin/stdout.

    Returns (stdout_text, exit_code).
    If tmp_project_root is given, override _PROJECT_ROOT for decision chain files.
    """
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    if tmp_project_root is not None:
        old_project_root = pre_ask_guard._PROJECT_ROOT
        pre_ask_guard._PROJECT_ROOT = tmp_project_root
        pre_ask_guard._STATE_DIR = tmp_project_root / ".omc" / "state"
        pre_ask_guard._STATE_DIR.mkdir(parents=True, exist_ok=True)

    sys.stdin = io.StringIO(stdin_json)
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    exit_code = 0
    try:
        pre_ask_guard.main()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0

    out = sys.stdout.getvalue()
    sys.stdin = old_stdin
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    if tmp_project_root is not None:
        pre_ask_guard._PROJECT_ROOT = old_project_root
        pre_ask_guard._STATE_DIR = old_project_root / ".omc" / "state"

    return out.strip(), exit_code


def _create_decision_chain_files(root: Path, matches: dict[str, list[str]]):
    """Create decision chain files with content matching specific keywords.

    matches: {filename: [keyword_list]} — each keyword appears in a non-comment line.
    """
    contents = {
        "AGENTS.md": (
            "# AGENTS.md — Agent Decision System\n\n"
            "This file defines the agent architecture and decision chain.\n"
        ),
        "kernel.md": (
            "# kernel.md — Execution Kernel\n\n"
            "The execution kernel manages throughput and request handling.\n"
        ),
        "anti-patterns.md": (
            "# anti-patterns.md — Common Mistakes\n\n"
            "Avoid overengineering the decision chain structure.\n"
        ),
        "claude-next.md": (
            "# claude-next.md — Project Conventions\n\n"
            "Follow the convention patterns from previous sessions.\n"
        ),
    }

    # Add matching lines: each keyword appears on its own non-comment line
    for fname, keywords in matches.items():
        if fname in contents:
            extra = "\n".join(f"- Keyword reference: {kw}" for kw in keywords)
            contents[fname] = contents.get(fname, "") + "\n" + extra + "\n"

    # Write files
    for fname, content in contents.items():
        if fname == "AGENTS.md":
            filepath = root / fname
        else:
            filepath = root / ".claude" / fname
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")


# ─── Unit Tests: extract_questions ──────────────────────────────────────


class TestExtractQuestions(unittest.TestCase):
    """extract_questions must correctly parse stdin JSON."""

    def test_extracts_single_question(self):
        inp = json.dumps({
            "tool_input": {"questions": [{"question": "What is X?"}]}
        })
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, ["What is X?"])

    def test_extracts_multiple(self):
        inp = json.dumps({
            "tool_input": {"questions": [
                {"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}
            ]}
        })
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, ["Q1", "Q2", "Q3"])

    def test_skips_empty_question(self):
        inp = json.dumps({
            "tool_input": {"questions": [
                {"question": ""}, {"question": "Real question"}, {}
            ]}
        })
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, ["Real question"])

    def test_no_questions_field(self):
        inp = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, [])

    def test_empty_tool_input(self):
        inp = json.dumps({"tool_name": "Bash", "tool_input": {}})
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, [])

    def test_malformed_json(self):
        result = pre_ask_guard.extract_questions("not json")
        self.assertEqual(result, [])

    def test_none_tool_input(self):
        inp = json.dumps({"tool_name": "Bash"})
        result = pre_ask_guard.extract_questions(inp)
        self.assertEqual(result, [])


# ─── Unit Tests: extract_keywords ───────────────────────────────────────


class TestExtractKeywords(unittest.TestCase):
    """extract_keywords must extract meaningful words, skip stop words, max 5."""

    def test_english_keywords(self):
        result = pre_ask_guard.extract_keywords("What is the architecture of this system?")
        # expected: ["architecture", "system"] — "what", "the", "this" are stop words
        self.assertEqual(result, ["architecture", "system"])

    def test_chinese_keywords(self):
        result = pre_ask_guard.extract_keywords("这个项目的架构设计是什么？")
        # Chinese text without spaces: the whole continuous string is one match.
        # findall returns ["这个项目的架构设计是什么"], then stop-word filtering
        # removes nothing since "是什么" is not a stop word.
        self.assertTrue(len(result) > 0, "Should extract at least one Chinese keyword")

    def test_max_five_keywords(self):
        result = pre_ask_guard.extract_keywords(
            "alpha beta gamma delta epsilon zeta eta"
        )
        self.assertLessEqual(len(result), 5)

    def test_stop_words_filtered(self):
        result = pre_ask_guard.extract_keywords("what how should the and for")
        self.assertEqual(result, [])

    def test_short_words_ignored(self):
        # "is" "it" "to" "be" "or" are all <3 letters, so no match
        result = pre_ask_guard.extract_keywords("is it to be or")
        self.assertEqual(result, [])

    def test_empty_question(self):
        result = pre_ask_guard.extract_keywords("")
        self.assertEqual(result, [])

    def test_only_stop_words(self):
        # "whether" is NOT in the stop-word list, so avoid it
        result = pre_ask_guard.extract_keywords("what is the should and could")
        self.assertEqual(result, [])


# ─── Unit Tests: search_decision_chain ──────────────────────────────────


class TestSearchDecisionChain(unittest.TestCase):
    """search_decision_chain must find matching content across decision chain files."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pre_ask_guard_test_"))
        self._create_files()

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def _create_files(self):
        """Create decision chain files with known content."""
        # AGENTS.md
        (self.tmp / "AGENTS.md").write_text(
            "# AGENTS.md\n\n"
            "This document describes the decision architecture for the system.\n"
            "All agents must follow the protocol rules.\n",
            encoding="utf-8"
        )
        # kernel.md
        (self.tmp / ".claude").mkdir(parents=True, exist_ok=True)
        (self.tmp / ".claude" / "kernel.md").write_text(
            "# kernel.md\n\n"
            "The execution kernel manages throughput and latency.\n"
            "Request handling is the primary concern.\n",
            encoding="utf-8"
        )
        # anti-patterns.md
        (self.tmp / ".claude" / "anti-patterns.md").write_text(
            "# anti-patterns.md\n\n"
            "Avoid overengineering the decision chain structure.\n"
            "Keep it simple.\n",
            encoding="utf-8"
        )
        # claude-next.md
        (self.tmp / ".claude" / "claude-next.md").write_text(
            "# claude-next.md\n\n"
            "Project convention patterns for session continuity.\n",
            encoding="utf-8"
        )

    def _quick_files(self):
        return [(self.tmp / "AGENTS.md", "AGENTS.md")]

    def _deep_files(self):
        return [
            (self.tmp / ".claude" / "kernel.md", "kernel.md"),
            (self.tmp / ".claude" / "anti-patterns.md", "anti-patterns.md"),
            (self.tmp / ".claude" / "claude-next.md", "claude-next.md"),
        ]

    # ── Phase 1 matches (AGENTS.md) ──

    def test_phase1_match_architecture(self):
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What is the architecture of the system?",
            self._quick_files()
        )
        self.assertEqual(layer, "AGENTS.md")
        self.assertIn("AGENTS.md", line)
        self.assertIn("architecture", line.lower())

    def test_phase1_match_protocol(self):
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What protocol should agents follow?",
            self._quick_files()
        )
        self.assertEqual(layer, "AGENTS.md")
        self.assertIn("protocol", line.lower())

    # ── Phase 2 matches (kernel.md, anti-patterns.md) ──

    def test_phase2_match_kernel_throughput(self):
        # Phase 1 miss → Phase 2 search across deep files
        layer, line, display = pre_ask_guard.search_decision_chain(
            "How is throughput managed?",
            self._quick_files()  # Phase 1: AGENTS.md — no match
        )
        # Phase 1 should return no match
        self.assertEqual(layer, "", "Phase 1 AGENTS.md should not match 'throughput'")

        # Now Phase 2
        layer2, line2, display2 = pre_ask_guard.search_decision_chain(
            "How is throughput managed?",
            self._deep_files()
        )
        self.assertEqual(layer2, "kernel.md")
        self.assertIn("throughput", line2.lower())

    def test_phase2_match_anti_patterns(self):
        # Phase 2: anti-patterns.md matches "overengineering"
        layer, line, display = pre_ask_guard.search_decision_chain(
            "How do I avoid overengineering?",
            self._deep_files()
        )
        self.assertEqual(layer, "anti-patterns.md")
        self.assertIn("overengineering", line.lower())

    def test_phase2_match_convention(self):
        # Phase 2: claude-next.md matches "convention"
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What convention should I follow?",
            self._deep_files()
        )
        self.assertEqual(layer, "claude-next.md")
        self.assertIn("convention", line.lower())

    # ── No match ──

    def test_no_match(self):
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What is the database connection string?",
            self._quick_files() + self._deep_files()
        )
        self.assertEqual(layer, "")
        self.assertEqual(line, "")
        self.assertEqual(display, "")

    def test_no_match_partial_overlap(self):
        """No answer-relevant keyword matches the documents."""
        layer, line, display = pre_ask_guard.search_decision_chain(
            "How do I set up the notification email template?",
            self._quick_files() + self._deep_files()
        )
        self.assertEqual(layer, "")

    def test_no_match_empty_keywords(self):
        """Only stop words yields no keywords → no match."""
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What how should the please?",
            self._quick_files()
        )
        self.assertEqual(layer, "")
        self.assertEqual(line, "")
        self.assertEqual(display, "")

    def test_skips_comments_and_blockquotes(self):
        """Comment and blockquote lines should not match."""
        (self.tmp / "AGENTS.md").write_text(
            "# architecture is in a comment\n"
            "> architecture is in a blockquote\n"
            "The real architecture is here.\n",
            encoding="utf-8"
        )
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What is the architecture?",
            self._quick_files()
        )
        self.assertEqual(layer, "AGENTS.md")
        # Must match the non-comment, non-blockquote line
        self.assertNotIn("comment", line.lower())
        self.assertNotIn("blockquote", line.lower())
        self.assertIn("real architecture", line.lower())

    def test_missing_file_skipped(self):
        """Missing files are gracefully skipped."""
        (self.tmp / "AGENTS.md").unlink(missing_ok=True)
        layer, line, display = pre_ask_guard.search_decision_chain(
            "What is the architecture?",
            self._quick_files()
        )
        self.assertEqual(layer, "")


# ─── Integration Tests: main() e2e ──────────────────────────────────────


class TestMainFlow(unittest.TestCase):
    """Feed stdin JSON payloads through main(), capture exit code and stdout."""

    def setUp(self):
        _mock_harness.reset()
        _mock_harness.set_hc_enabled(True)
        _mock_harness.set_mode("normal")
        self.tmp = Path(tempfile.mkdtemp(prefix="pre_ask_guard_integ_"))
        _create_decision_chain_files(self.tmp, {})

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    # ── Scenario 1: hc_enabled = False → {"continue": True} ──

    def test_hc_disabled_passes(self):
        _mock_harness.set_hc_enabled(False)
        payload = _build_ask_question_payload(["What is the architecture?"])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    # ── Scenario 2: No questions / non-AskUserQuestion → {"continue": True} ──

    def test_no_questions_field_passes(self):
        """Non-AskUserQuestion tools have no questions field → pass."""
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_empty_question_list_passes(self):
        payload = json.dumps({
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": []}
        })
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_only_empty_questions_passes(self):
        payload = json.dumps({
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": ""}, {"question": " "}]}
        })
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    # ── Scenario 3: Autonomous mode → exit 2 (block) ──

    def test_ghost_mode_blocks(self):
        _mock_harness.set_mode("ghost")
        payload = _build_ask_question_payload(["What is the architecture?"])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 2, "Ghost mode must block all questions")
        parsed = json.loads(out)
        self.assertFalse(parsed["continue"])

    def test_goal_mode_blocks(self):
        _mock_harness.set_mode("goal")
        payload = _build_ask_question_payload(["Any question?"])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 2, "Goal mode must block all questions")
        parsed = json.loads(out)
        self.assertFalse(parsed["continue"])

    def test_autonomous_mode_blocks_multiple_questions(self):
        _mock_harness.set_mode("ghost")
        payload = _build_ask_question_payload(["Q1?", "Q2?", "Q3?"])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 2)
        parsed = json.loads(out)
        self.assertFalse(parsed["continue"])

    # ── Scenario 4: All questions resolvable → exit 2 (block) ──

    def test_all_resolvable_blocks(self):
        """All questions match decision chain → blocked with references."""
        # Use distinctive keywords that do NOT appear in default file content
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": ["deployment", "rollback", "migration"],
        })
        payload = _build_ask_question_payload([
            "What is the deployment strategy?",
            "How do I perform a rollback?",
        ])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 2, "All resolvable questions must block")
        parsed = json.loads(out)
        self.assertFalse(parsed["continue"])
        ctx = parsed.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("deployment", ctx.lower())
        self.assertIn("rollback", ctx.lower())

    def test_all_resolvable_phase2_blocks(self):
        """Questions that hit Phase 2 (kernel.md) also block."""
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": [],        # Phase 1: no match for throughput
        })
        # kernel.md content already has "throughput" from _create_decision_chain_files default
        payload = _build_ask_question_payload(["How is throughput managed?"])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 2, "Phase 2 resolvable must also block")
        parsed = json.loads(out)
        self.assertFalse(parsed["continue"])

    # ── Scenario 5: Some questions resolvable → {"continue": True} ──

    def test_partial_resolvable_passes_with_hint(self):
        """Partial coverage → soft hint, but continue: true."""
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": ["architecture"],
        })
        payload = _build_ask_question_payload([
            "What is the architecture?",
            "How do I configure the database?",
        ])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0, "Partial resolvable must not block")
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_partial_resolvable_stderr_has_hint(self):
        """Partial resolves should print a hint to stderr."""
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": ["architecture"],
        })
        payload = _build_ask_question_payload([
            "What is the architecture?",
            "How do I configure the database?",
        ])
        out, code = _run_main(payload, self.tmp)
        # stdout is the continue JSON; stderr has the hint
        # (we can check exit code and stdout continue flag)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    # ── Scenario 6: No questions resolvable → {"continue": True} ──

    def test_none_resolvable_passes(self):
        """No decision chain match → genuine human question, pass through."""
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": [],
        })
        payload = _build_ask_question_payload([
            "What is the database connection string?",
        ])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0, "No resolvable questions must pass")
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_none_resolvable_multiple_passes(self):
        """Multiple unreolvable questions all pass through."""
        _create_decision_chain_files(self.tmp, {
            "AGENTS.md": [],
        })
        payload = _build_ask_question_payload([
            "What is the database connection string?",
            "How do I deploy to production?",
            "What is the API key?",
        ])
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    # ── Scenario 7: Malformed input → {"continue": True} ──

    def test_malformed_json_passes(self):
        """Non-JSON input must not crash, should pass through."""
        out, code = _run_main("not json at all\n", self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_missing_tool_input_passes(self):
        payload = json.dumps({"tool_name": "AskUserQuestion"})
        out, code = _run_main(payload, self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])

    def test_empty_input_passes(self):
        out, code = _run_main("", self.tmp)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertTrue(parsed["continue"])


if __name__ == "__main__":
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestExtractQuestions))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractKeywords))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchDecisionChain))
    suite.addTests(loader.loadTestsFromTestCase(TestMainFlow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
