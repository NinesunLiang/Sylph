# Research: sh → py 轻量化迁移

## 调用链路

### P0 — Skill 入口（直接调用）
| 源文件 | 大小 | 调用方 | 操作 |
|--------|------|--------|------|
| `.claude/skills/lx-ghost/scripts/lx-ghost.sh` | 19KB | `lx-ghost` skill | **转 .py** |
| `.claude/skills/lx-goal/scripts/lx-goal.sh` | 15KB | `lx-goal` skill | **转 .py** |
| `.claude/skills/lx-stepwise/scripts/lx-stepwise.sh` | 369B | `lx-stepwise` skill | **转 .py** |

### P1 — 间接引用
| 源文件 | 大小 | 调用方 | 操作 |
|--------|------|--------|------|
| `.claude/profiles/merge-profile.sh` | 8KB | `source/install.sh` 引用 | **转 .py** |
| `.claude/scripts/validate-skill.sh` | 657B | `lx-skillify` / `lx-learner` | **转 .py** |

### 死代码 — 直接删除
| 文件 | 理由 |
|------|------|
| `.claude/hooks/hook-launcher.sh` | hook-launcher.py 已替代 |
| `.claude/hooks/statusline-command.sh` | 任何 settings.json 未引用 |
| `.claude/hooks/stop-lifecycle-wrapper.sh` | 任何 settings.json 未引用 |
| `.claude/hooks/tests/run_pkg_c_acceptance.sh` | 测试产物 |
| `.claude/workflow-standard/provision.sh` | 未引用 |
| `.claude/workflow-standard/deprovision.sh` | 未引用 |

### 冗余镜像 — 直接删除
| 目录 | 数量 |
|------|------|
| `.claude/_reserve/backup/` | ~55 个 .sh |
| `template/**/*.sh` | 4 个 |
| `source/lx-skills-v5/**/*.sh` | 4 个 |
| `source/harness-kit/**/*.sh` | 4 个 |
| `.claude/scripts/auto-score.sh` | 1 个 (已有 .py) |
| `.claude/scripts/meta-oracle-agent-spawn.sh` | 1 个 (已有 .py) |
| `.claude/scripts/score-self-check.sh` | 1 个 (已有 .py) |
| `.claude/scripts/provision-worktree-hooks.sh` | 1 个 (一次性) |

### 不在此次范围
| 目录 | 理由 |
|------|------|
| `install.sh` + `source/install.sh` | 安装入口，需零依赖 |
| `scripts/*.sh` (22个) | 运维辅助，非核心 |
| `packages/**/*.sh` | 独立分发渠道 |
| `.opencode/**/*.sh` | OpenCode 镜像 |

## 约束
- 每步独立 commit，Gate-E 验证后下一步
- SKILL.md 引用必须同步更新
- `install.sh` 中 `merge-profile.sh` → `.py` 引用需更新
- 轻量化：P5/P6 不碰

## 风险
- 低：skill 脚本独立入口，无跨模块依赖
- merge-profile.sh (8KB) 逻辑复杂需逐行审计
