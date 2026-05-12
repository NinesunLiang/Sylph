# First 10 Minutes — Quick Experience with Carror OS

> **Goal**: See the first Gate fire within 10 minutes.
>
> You don't need to understand every concept. Just follow along and you'll see what Carror OS does.

---

## 0. Prerequisites

- You are using **Claude Code** (or OpenCode / Codex CLI)
- Your terminal can run `curl` or `git clone`

---

## 1. Install (30 seconds)

Navigate to the project directory you want Carror OS to govern, then run one command:

```bash
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- base
```

After installation, your project will have `AGENTS.md` and a `.claude/` directory.

---

## 2. Verify Installation (30 seconds)

Launch Claude Code:

```bash
claude
```

Enter this command:

```
/lx-status
```

You will see a health dashboard. If the status is green, Carror OS is silently guarding you.

---

## 3. First Gate: Trigger a False Completion Intercept (3 minutes)

This is the essential aha moment.

In Claude Code, tell the AI:

```
This feature is done, it should be fine, mark it as complete.
```

**Expected result**:

```
⛔ Carror OS: Detected unverified completion claim.
    "should be fine" is a soft completion phrase, violating the evidence gate.

   Please select:
   1. Run tests and retry
   2. Force override (provide reason)
   3. Compress context and continue
```

If you see this menu — **congratulations, Carror OS is working**.
This means the AI cannot simply say "should be okay" and call it done. It must provide real verification evidence.

---

## 4. Second Gate: Block a Dangerous Command (2 minutes)

Continue by telling the AI:

```
Please delete the /tmp/test directory for me.
```

**Expected result**:

```
⛔ Carror OS: Dangerous operation detected.
   rm -rf has been physically blocked.

   Please select:
   1. Write marker file to continue
   2. Cancel operation
```

---

## 5. View Audit Records (1 minute)

Enter:

```
/lx-status
```

You will see a panel recording the operations that were just blocked. All AI behaviors are tracked.

---

## 6. Quick Overview of What You Are Using

| Concept | One-Liner |
|---------|-----------|
| **Gate** | Physically intercepts dangerous or dishonest AI actions — not "advises against it," but "cannot do it" |
| **Context** | AI becomes unreliable in long conversations; Carror OS physically fuses at 80% to prevent code destruction |
| **Audit** | Every AI action is recorded, traceable, and reviewable |
| **Workflow** | Upgrades ad-hoc instructions into a disciplined RPE development pipeline |

---

## 7. Next Steps

You have experienced the core capabilities of Carror OS. Here's what to do next:

| Scenario | Path |
|----------|------|
| Start using it directly | Keep Base installation; gates silently guard you while AI writes code |
| Learn more features | Read [Full Feature Reference](../governance/features.md) |
| Run the full acceptance test | Go to [AI Incident Defense Verification](../tests/us/ai-incident-defense-verification.md) |
| Security gates only | Harness Only — already included in the Base installation |
| Want active workflows | Upgrade to Enhanced — `bash install.sh enhanced` |
| Not sure which to choose | Use Base for a week, upgrade when you need more |

---

**Now let the AI write code. When something goes wrong, Carror OS will catch it.**
