# Carror OS Onboarding Guide

## First Time Use, Start Here

---

## What You Get

Carror OS is not a plugin. Not a prompt template. Not a new chat tool.

**It's a governance layer that runs underneath your AI tool.**

You keep working as usual. It runs in the background, intercepting at the points where things most often go wrong.

Most of the time, you won't notice it. What you might notice:
- AI falsely claiming completion becomes rare
- Sensitive files stay out of AI context automatically
- Rules don't drift in long conversations
- New sessions pick up where you left off
- You stop double-checking AI's output as often

---

## Two Versions

### Base (for first-time users)
- Install and work. That's it.
- 85% of mechanisms run silently.
- **Base version requires almost no configuration and zero prior learning.**
- Start here. Feel what it's like to have a system watching for you.

### Advanced (for deeper control)
- Mechanism toggles
- OMA concurrent development
- Full governance pipeline
- Fine-grained rule configuration

**Start with Base. Feel it first, then decide if you need more.**

---

## Step 1: Install

```bash
# Clone into your project
git clone https://github.com/[carror-os]/harness-kit .claude

# Initialize
bash .claude/install.sh

# Verify
bash .claude/scripts/harness-smoke-test.sh
```

If you see this, you're ready:

```
✅ harness-kit ready
✅ 32 hooks registered
✅ privacy-gate     active
✅ completion-gate  active
✅ error-dna        active
✅ context-guard    active
```

**That's it.** Open Claude Code and start working.

---

## Step 2: Work Normally

No need to test every feature. Just work as you normally do with Claude Code.

You don't need to "invoke" Carror OS. Its design is: **you work, it watches. It appears when it needs to.**

---

## Step 3: Your First Encounters

### Scene 1: AI says "done" — system asks for proof

As a task wraps up, AI marks completed. You see:

```
⛔ COMPLETION BLOCKED

Task marked completed, but no verification evidence found.

Please run verification and write results to:
  .omc/state/.completion-evidence-20260601

Evidence must include:
  · Actual command and output
  · Clear pass mark (exit 0 / PASS / ✅)
```

This isn't an error. This is the system asking AI: **"Did you really do it? Prove it."**

Before, "done" was declared by AI. Now, "done" is granted by the system.

### Scene 2: AI reaches for secrets — system blocks it

When AI tries to read `.env` or sensitive config:

```
🚫 [Privacy Gate Triggered]

Direct read of sensitive files blocked: .env

Plaintext keys entering AI context
is no longer safe.

Use environment variables instead.
```

The sensitive data never entered AI context. You don't need to wonder afterward. The system stopped it before it happened.

### Scene 3: Long conversation, but rules don't drift

By round 20, AI typically starts drifting. Carror OS re-anchors before every write:

```
📌 [Round 20·Rule Anchor]
① No fabrication — assertions must cite file:line
② VERIFIED evidence required before completion
③ Git operations need your approval
④ Modify current scope only
⑤ Max 3 repair rounds per issue
```

AI didn't suddenly become reliable. The system put the rules in front of it right before it needed them.

---

## Step 4: First New Session

Carror OS's value isn't just within one session. It's in "the next day."

Close the conversation. Open a new one the next day:

```
[Previous Session Snapshot]
Branch: feat/ecosystem-tab
Uncommitted: src/pages/ecosystem/index.tsx
Next step: Complete ResourceCard hover state

[Error Memory]
Unresolved errors:
  · [3 times] tsc: TS2345 — src/types/ecosystem.ts:47
  · [2 times] MSW handler not registered causing 404
```

Context picked up. Past errors remembered. You don't re-explain from scratch.

**Just continue working.**

---

## Step 5: After a Week

After a week, you might notice something: **you're not double-checking AI's output as often.**

Not because you blindly trust it more. Because you know:
- No evidence = can't pass completion gate
- Secrets can't be read
- Rules get re-injected in long conversations
- Past errors get picked up in new sessions

The "I don't knows" that used to hang in the background fade a little. Maybe not entirely. But enough to notice.

**That's what Base gives you.**

---

## Step 6: Going Further

Once you're comfortable, explore Advanced mode:

- **OMA (One-Man Army)**: Run multiple AI terminals in parallel
- **lx-rpe 9-step loop**: Structured feature development pipeline
- **Flywheel**: From error to system improvement
- **Knowledge Sublimation**: Turn recurring lessons into permanent rules

You don't need to learn everything at once. **Start, feel, then deepen.**

---

## What Happens After

### If you felt it working

Maybe it was a late night when completion gate stopped a false "done." Maybe it was a new session where error memory saved you from a known pitfall. Maybe it was a weekend when work anxiety didn't follow you home.

If any of that happened — welcome. Let's make it better together.

---

### If you haven't felt it yet

Maybe you haven't hit the scenarios. Maybe your workflow doesn't align yet.

That's fine. Keep using it. Carror OS is infrastructure — it shows its value at critical moments, not flashy ones.

---

### If you used it but didn't feel relief

If you're still tired. Still anxious. Still carrying the weight.

**Please don't donate.** Tell us what's not good enough.

This feedback matters more than any support. Because Carror OS exists to let you return from high-pressure work back to life. If it hasn't done that, it's not good enough yet.

**We need to know. Then we'll make it better.**

---

## Where to Go Next

If this is your first contact, follow this order:

1. Install Base
2. Run smoke test
3. Work normally
4. Wait for it to stop something for the first time
5. Then read the advanced docs

---

- GitHub: [link]
- Docs: [link]
- Advanced Guide: [link]
- Community / Feedback: [link]
