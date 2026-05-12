# Carror OS v6.1.9 Testing Guide

> **Version**: v6.1.9 | **Date**: 2026-05-13
> **HARNESS Score**: 127.2 / 130
> **Test Results**: BDD 10 PASS / 0 FAIL / 2 SKIP + L1~L4 inherited

---

## v6.1.9 Changes

| Change | Verification Command |
|:-------|:--------------------|
| plan-gate auto-detect rpe/ | `mkdir -p rpe/test && echo '## Step 1' > rpe/test/executor.md && echo '{"tool_input":{"file_path":"rpe/test/plan.md"}}' \| bash .claude/hooks/plan-gate.sh; echo $?` → 2 |
| bdd-harness-test.sh | `bash .claude/hooks/bdd-harness-test.sh` → 10P/0F/2S |

---

## BDD Scenario Tests

```bash
# Run all scenarios
bash .claude/hooks/bdd-harness-test.sh
# Run single scenario
bash .claude/hooks/bdd-harness-test.sh scenario_H_plan_gate_auto
# List all scenarios
bash .claude/hooks/bdd-harness-test.sh --list
```

**10 BDD Scenarios**:

| ID | Scenario | Type |
|:---|:---------|:----:|
| A | AI claims completion without evidence → Block | Auto |
| B | AI provides valid evidence → Allow | Auto |
| C | Out-of-scope file edit warning | SKIP (needs path) |
| D | Write at turn 20 → Rule re-injection | Auto |
| E | Drift word "顺便" → Escalation warning | Auto |
| F | AI executes git push → Block | Auto |
| G | User correction signal → Lesson reminder | Auto |
| H | rpe/ exists → plan-gate auto-enable | Auto (v6.1.3) |
| I | No rpe/ → plan-gate fail-open | Auto (v6.1.3) |
| J | Real AI conversation verification | SKIP (needs API) |

---

## plan-gate Auto-Detection

```bash
# Scenario H: rpe/ exists → auto-block
mkdir -p .omc/state rpe/my-feat
cat > rpe/my-feat/executor.md << 'EOF'
## Step 1 — Implement
EOF
INPUT='{"tool_input":{"file_path":"rpe/my-feat/plan.md","new_content":"test"}}'
echo "$INPUT" | bash .claude/hooks/plan-gate.sh; echo "exit: $?"
# Expected: exit: 2 (Research Gate BLOCKED)

# Scenario I: No rpe/ → fail-open
rm -rf rpe/
echo "$INPUT" | bash .claude/hooks/plan-gate.sh; echo "exit: $?"
# Expected: exit: 0 (Allow)
```

---

## Platform Compatibility

```bash
# Verify both files exist after install
ls -la AGENTS.md CLAUDE.md
# Verify CLAUDE.md uses @-include trampoline format
head -1 CLAUDE.md  # Expected: @AGENTS.md
# Verify AGENTS.md contains governance content
grep "Project 宪法|铁律|VERIFIED" AGENTS.md | wc -l  # Expected ≥5
```

**Platform Support Matrix**:

| Platform | Entry Point | Hooks Governance | Skill Support |
|:---------|:------------|:----------------:|:-------------:|
| Claude Code | CLAUDE.md (@AGENTS.md) | ✅ 30 hooks | ✅ |
| Codex CLI | `.codex/hooks.json` (auto) | ✅ 11 hooks | ❌ |
| Gemini CLI | `.gemini/settings.json` (auto) | ✅ 11 hooks | ❌ |
| Qwen Code | `settings.json` (auto) | ✅ 11 hooks | ❌ |
| Cursor | `.cursor/hooks.json` (auto) | ✅ 2 hooks | ❌ |
| OpenCode | AGENTS.md (native) | ✅ 5 hooks (plugin) | ✅ |
| CLAUDE.md-compatible IDE | CLAUDE.md (@AGENTS.md) | ❌ | ✅ |

---

**Carror OS — AI Native Developer Operating System.**
