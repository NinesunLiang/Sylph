# Screenshot & Video Asset Checklist

> **Purpose**: Capture all scenes needed for Carror OS launch assets (website, README, press kit, demo video).
> **Status**: Active
> **Last Updated**: 2026-05-04
> **Total Scenes**: 12 screenshots + 2 video demos

---

## Screenshots Required

| ID | Scene | What to Show | Priority | Reference |
|----|-------|-------------|----------|-----------|
| SS-01 | First Run After Install | CLAUDE.md `@AGENTS.md` import success, governance framework version displayed | P0 | `.claude/harness.yaml` |
| SS-02 | Permission Gate Intercept | AI attempts `rm -rf /tmp/test`, Hook blocks with numbered-choice menu | P0 | `.claude/hooks/permission-gate.sh` |
| SS-03 | Context Guard Warning | AI context ~80%, `context-guard.sh` fires with 3-option menu (continue/summary/emergency-summary) | P0 | `.claude/hooks/context-guard.sh` |
| SS-04 | lx-status Dashboard | Full 5-panel display: Token Trend + Error DNA + Flywheel + Feature Registry + Context | P0 | `.claude/scripts/carror_dashboard.py` |
| SS-05 | Completion Gate Intercept | AI claims "应该没问题了" / "should be fine", `completion-gate.sh` blocks and demands VERIFIED evidence | P0 | `.claude/hooks/completion-gate.sh` |
| SS-06 | Privacy Gate Intercept | AI attempts to read `.env` file, `privacy-gate.sh` blocks with DLP warning | P0 | `.claude/hooks/privacy-gate.sh` |
| SS-07 | lx-rpe State Panel | Active RPE task pipeline showing Phase progression (Research -> Plan -> Execute -> Verify) | P1 | `.claude/skills/lx-rpe/` |
| SS-08 | Error DNA Visualization | Error DNA dashboard showing categorized error patterns, severity, fix rate | P1 | `.claude/scripts/carror_error_dna.py` |
| SS-09 | Audit Dashboard Summary | Audit log aggregation across 5 sources: Git, Error DNA, Token Tracking, Session Logs, Handoff | P1 | `.claude/scripts/carror_audit.py` |
| SS-10 | /lx-status CLI Output | Raw terminal output of `/lx-status` command showing real-time defense metrics | P1 | `lx-status` skill |
| SS-11 | Progressive Disclosure L1 Load | L1 kernel files loading on session start: kernel.md + anti-patterns.md + claude-next.md (~120 lines) | P1 | Session Start Hook |
| SS-12 | README Project Homepage | Final README hero section with badges, architecture diagram, and "Give Your AI Brakes" tagline | P2 | `docs/marketing/README-draft.md` |

---

## Video Demos Required

### Demo 1: "Watch the Gates in Action" (60-90 seconds)

**Purpose**: Convince skeptics that Carror OS provides physical-level blocking, not prompt suggestions.

| Time | Scene | Narration |
|------|-------|-----------|
| 0:00-0:10 | User types `rm -rf /var/www` in Claude Code | "Every AI user has feared this moment." |
| 0:10-0:20 | Permission Gate blocks with Exit 2, shows numbered menu | "Carror OS doesn't ask — it blocks. Physically." |
| 0:20-0:30 | AI claims "done" without evidence, Completion Gate intercepts | "And it stops hallucinations at the tool-call layer." |
| 0:30-0:45 | /lx-status dashboard shows live defense stats | "Every intercept logged, every gate verified." |
| 0:45-0:60 | Side-by-side: Cursor (prompt ignored) vs Carror OS (blocked) | "Prompt vs. Physics. Choose your defense." |
| 0:60-0:90 | Install command + final "Brakes On" screen | "30 seconds. No daemon. No cloud. No subscription." |

### Demo 2: "Beyond Defense — The Skill Arsenal" (90-120 seconds)

**Purpose**: Show Carror OS is not just a blocker but a complete development operating system.

| Time | Scene | Narration |
|------|-------|-----------|
| 0:00-0:15 | /lx-rpe initiates a new feature pipeline | "Carror OS also orchestrates your workflow." |
| 0:15-0:30 | RPE pipeline: Research -> Plan -> Execute -> Verify progression | "From spec to shipped code, every step gated." |
| 0:30-0:45 | lx-code-review detects and fixes a code quality issue | "Automated reviews that shut down slop." |
| 0:45-1:00 | /lx-status shows cumulative token savings | "And every session compounds your savings." |
| 1:00-1:20 | Error DNA timeline: bugs found, fixed, verified | "Error patterns exposed and eliminated." |
| 1:20-1:45 | Audit dashboard: full traceability across sessions | "Every action auditable. Every claim verifiable." |
| 1:45-2:00 | Closing: logo + "Carror OS — Guard First, Arm Later" | "Brakes on. Ship with confidence." |

---

## Filming Setup

### Environment
- **Terminal**: iTerm2 with minimal theme (dark background)
- **Font**: JetBrains Mono Nerd Font (monospace, 14pt)
- **Window**: 120x40 chars, no title bar
- **Background**: Desktop clean, no personal files visible

### Capture Settings
- **Screenshots**: PNG, 1920x1080 or 2x Retina
- **Video**: MP4, 1920x1080 @ 30fps
- **Tool**: CleanShot X (macOS) or OBS Studio
- **Cursor**: Visible, default pointer (no custom themes)

### Branding
- Header bar in screenshots: optional "Carror OS v6.1.8" watermark bottom-right
- No other watermarks or logos in the capture area
- All terminal prompts should use the default `$` or `%` prompt

---

## Shooting Checklist

- [ ] Terminal font/theme consistent across all captures
- [ ] No personal/private info visible in any frame
- [ ] All captures show actual running Carror OS (not mockups)
- [ ] Error states show real error messages (not simulated)
- [ ] Timing/performance captures show real command output
- [ ] Demo 1: all P0 gates demonstrated
- [ ] Demo 2: at least lx-rpe + lx-code-review + lx-status visible
- [ ] Audio: clean voiceover or text captions for demos
- [ ] Resolution: minimum 1920x1080 for all assets
- [ ] File naming: `{category}-{id}-{description}.png` (e.g. `gate-ss02-permission-block.png`)
