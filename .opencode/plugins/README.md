# OpenCode Plugins

## Active

| Plugin | Role |
|--------|------|
| `carror-hooks-compat.ts` | Event bridge: SessionStart, Stop, UserPromptSubmit, PostToolUseFailure |
| `session-guardian.ts` | Native TS gates: Edit/Permission/Privacy/Context (0 bash spawn) |

## Disabled (`.disabled` suffix)

Files with `.disabled` are deprecated and excluded from loading.

| File | Deprecated | Replaced by |
|------|-----------|-------------|
| `harness-config.ts.disabled` | 2026-05 | `harness_config.sh` (sourced by hooks) |
| `harness-kit.ts.disabled` | 2026-05 | OMO native + `carror-hooks-compat.ts` |
| `sylph-hooks.ts.disabled` | 2026-05-15 | `carror-hooks-compat.ts` |

To re-enable: remove `.disabled` suffix. But these are kept for reference only — do not enable without understanding the conflicts.
