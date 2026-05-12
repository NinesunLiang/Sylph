# Gates (Gate 系统)

> **Physical interception at the AI-filesystem boundary.**

---

## What Is a Gate?

A Gate is not a suggestion. It is a **physical blocker** in the hook layer that intercepts an AI action before it reaches the filesystem.

Most AI safety tools use **prompt constraints** -- they insert rules into the system prompt and ask the AI to self-police. That fails because:
- The AI can ignore or forget the rules in a long conversation.
- The AI suffers from self-verification bias: it believes it is following the rules even when it is not.

A Carror OS Gate works differently. It sits between the AI and the tool call. When the AI tries to write a file, execute a command, or read sensitive data, the Gate intercepts the raw tool input and decides: **pass, block, or escalate.**

The AI cannot talk its way around a Gate. The Gate does not listen to prompts -- it reads raw tool inputs.

---

## The Four Gate Types

### completion-gate

Intercepts unverified completion claims. When the AI says "it's done" without providing evidence (test output, build logs), the Gate blocks the commit and forces verification.

Trigger: AI declares a task complete without attached evidence.

### permission-gate

Intercepts dangerous filesystem operations (`rm -rf`, `git push --force`, bulk delete). Requires explicit user confirmation before execution.

Trigger: Tool input matches a dangerous command pattern.

### privacy-gate

Intercepts reads of sensitive files (`.env`, `id_rsa`, `secret.yml`, credentials). Routes access through a local vault that masks credentials from the AI model entirely.

Trigger: File path matches sensitive file patterns.

### context-guard

Monitors session token consumption. At the **danger threshold** (default 80%) of the context window, physically terminates the session (`exit 2`) to prevent hallucination-driven destruction.

Trigger: Real token usage exceeds the danger threshold.
Config: `context_guard.warn_threshold` / `context_guard.danger_threshold` in `harness.yaml` (see [Context Control](./context-control.md)).

---

## Implementation

Each Gate is implemented as a hook script in `.claude/hooks/`. The hook receives the raw tool input via stdin, evaluates it against gate rules, and returns:
- `exit 0` -- pass (allow the action)
- `exit 2` -- block (reject with menu)
- `exit 1` -- error (hook itself failed)

For exact implementation details, see the hook scripts:

| Gate | Hook File |
| :--- | :-------- |
| completion-gate | `.claude/hooks/completion-gate.sh` |
| permission-gate | `.claude/hooks/permission-gate.sh` |
| privacy-gate | `.claude/hooks/privacy-gate.sh` |
| context-guard | `.claude/hooks/context-guard.sh` |
