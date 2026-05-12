# Safe Migration & Data Transfer Guide

> **Version**: v6.1.9 | **Date**: 2026-05-13
> **Core Principle**: Upgrading the OS must never erase user data and configurations.
>
> Carror OS classifies all files as **System State** or **User Assets**. Understanding these boundaries keeps your project knowledge and progress safe across machine migration or cross-version hot updates.

---

## 1. Asset Classification & Protection Strategy

| Asset Type | Location | Contents | Upgrade/Migration Strategy |
|:-----------|:---------|:---------|:--------------------------|
| **System Kernel** | `.claude/hooks/*.sh` / `.opencode/plugins/` | 32 physical interceptors, probe scripts | **Overwrite** (hot-update to keep defenses current) |
| **Skills (Userland)** | `.claude/skills/lx-*/` / `.claude/nodes/` | 24 pipeline skills, Python scripts, References | **Overwrite** (hot-update to keep capabilities current) |
| **OS Config** | `.claude/harness.yaml` | Custom 80% fuse threshold, hook toggles | **Must preserve** (installer auto-backups and restores) |
| **Project Memory** | `.claude/claude-next.md` / `.claude/anti-patterns.md` | AI's learned lessons, project-specific anti-patterns | **Must preserve** (installer auto-backups and restores) |
| **Runtime State** | `.omc/state/` | Error DNA, task queue, DLP privacy Vault | **Naturally isolated** (installer never touches) |
| **RPE State** | `rpe/{feature_name}/state/` | Feature progress snapshots, evidence records | **Naturally isolated** (same as above) |

---

## 2. Cross-Version Hot Update

When upgrading from an older Carror OS version to the latest, **no manual backup is needed**.

Run the latest install command from your project root:

```bash
curl -fsSL https://raw.githubusercontent.com/your-username/carror-os/main/install.sh | bash -s -- enhanced
```

**The installer preserves your data by**:
1. Detects existing `.claude/` directory
2. Before extraction, copies `harness.yaml`, `claude-next.md`, `anti-patterns.md` to a secure temp directory
3. Runs `tar -xzf` to overwrite all kernel hooks and skill scripts
4. Restores your config and memory assets from the sandbox
5. Optionally prompts for manual comparison if the old `harness.yaml` is missing fields

---

## 3. Cross-Project Intelligence Transfer

A powerful real-world scenario: you've accumulated months of AI "training" in Project A, and now you start Project B with a similar tech stack. You want the AI to carry over Project A's wisdom and anti-pitfall knowledge.

### ✅ Required: Wisdom Assets

Copy these files from Project A's `.claude/` to Project B's:

1. **`.claude/claude-next.md`** (lesson log): Structured knowledge from past pre-commit failures and corrections. Contains tacit knowledge like "our team prefers `logrus` over standard `log`."
2. **`.claude/anti-patterns.md`** (anti-pattern blacklist): Code patterns that must never be used.

> This injects Project A's hard-won battle experience into Project B. The AI will show remarkable maturity and proactive pitfall-avoidance on first code write.

### ⚙️ Transferable: Config Presets

3. **`.claude/harness.yaml`** (system config): Custom 80% fuse thresholds, hook toggles — Project B inherits your refined protection settings.

### ❌ Never Transfer: Runtime State

**Never copy an entire `.claude/` or `.omc/` folder from Project A.** These files carry Project A's specific code paths and variable names, causing severe context confusion and hallucinations in Project B:

1. **`.omc/state/error-dna.json`**: Project A's specific stack traces and fix commands — full of A-specific file names.
2. **`.omc/state/todo-queue.md`**: Task queue — irrelevant to B.
3. **`.omc/state/skill-trace.jsonl` and `read-tracker.txt`**: Execution path profile and file read history — meaningless to transfer.

### ☢️ Extremely Dangerous: DLP Privacy Vault

4. **`.omc/state/varlock.json`**: Your local plaintext password-to-placeholder mapping table. **Never copy unless Projects A and B share identical test database passwords and external API keys.** Copying risks polluting B's network requests and creating security escalation vulnerabilities.
