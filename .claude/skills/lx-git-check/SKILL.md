---
name: lx-git-check
version: v1.0.0
description: "统一 Git 质量门禁 — 提交前检查（编译/测试/lint/审查）+ 推送前检查（commit规范/安全扫描/变更审计）。内部两个阶段：pre-commit 和 pre-push。"
when_to_use: "Use before git commit or git push. Triggers: 'pre-commit', 'commit check', 'pre-push', 'push check', '/lx-git-check'."
argument-hint: "commit | push [--prod-commit <hash>] [--skip-review]"
harness_version: ">=6.3.0"
status: stable
role: "Unified git quality gate — pre-commit (compile, test, lint, review) + pre-push (commit convention, security, change audit)"
execution_mode: stepwise
triggers:
  - "/lx-git-check"
  - "/lx-pre-commit"
  - "/lx-pre-push"
  - "pre-commit"
  - "pre-push"
  - "commit check"
  - "push check"
---

# lx-git-check — 统一 Git 质量门禁

> 合并自 lx-pre-commit v2.0.0 + lx-pre-push v2.0.0

## 原子化声明

### 通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 |
| auto_fixer | `../../nodes/auto_fixer.md` | P0 自动修复 |
| scanner | `../../nodes/scanner.md` | 安全扫描 |

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `scripts/detect_project.py` | 检测项目类型（go/node/python/rust） | pre-commit Step 0 |
| `scripts/run_checks.py` | 运行编译+测试门禁序列 | pre-commit Step 1 |
| `scripts/commit_convention.py` | commit 规范管理（learn/validate/show/reset） | pre-push Gate 0 |
| `scripts/get_changed_files.py` | 获取相对于 prod-commit 的变更文件 | pre-push Gate 1 |
| `scripts/validate_commits.py` | commit 批量验证 | pre-push Gate 0 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/commit-convention-guide.md` | 需要查看 commit 规范时 |

---

## 执行流程

### 阶段一：提交前检查 — `lx-git-check commit [--skip-review]`

#### Step 0 — 检测项目类型
```bash
python3 .claude/skills/lx-git-check/scripts/detect_project.py
```
读取 JSON → `type`（go/node/python/rust）+ `runner`（vitest/jest/npm）。未知类型 → 停止。

#### Step 0.5 — Skill 合规校验（检测到 skill 变更时自动执行）
若 git diff 中包含 `.claude/skills/` 目录变更，自动运行：
```bash
python3 .claude/skills/lx-validate-skill/scripts/validate_skill.py --skills-dir .claude/skills
```

#### Step 1 — 运行门禁检查
```bash
python3 .claude/skills/lx-git-check/scripts/run_checks.py --type {type} --runner {runner}
```
- `blocked: false` → 通过 → Step 2
- `blocked: true` → 阻塞提交

**降级**：脚本失败时直接调用 `go build ./...` / `npm test` 手动判断。

#### Step 2 — 代码审查（自动调用，除非 --skip-review）
P0 → 修复 → 重跑 Step 1。P1+ → 列出，不阻塞。

#### Step 3 — 输出概览
```
✅ lx-git-check commit 通过  类型：{go/node}  编译：✅  测试：{N} passed  审查：P0=0
```

---

### 阶段二：推送前检查 — `lx-git-check push <prod-commit-hash>`

#### Gate 0 — Commit Message 规范校验
```bash
python3 .claude/skills/lx-git-check/scripts/commit_convention.py validate-batch --prod $PROD_COMMIT
```
- `blocked: false` → Gate 0 通过
- `blocked: true` + `has_redline: true` → 必须修复

#### Gate 1 — 获取变更范围
```bash
python3 .claude/skills/lx-git-check/scripts/get_changed_files.py --prod-commit $PROD_COMMIT
```
无变更 → 结束。

#### Gate 2 — 测试覆盖 + 安全扫描
根据项目类型：
- 前端：`npm audit --production` + OWASP 审查
- 安全：🔴=0 才能通过，🟡 记录不阻塞

#### Gate 3 — 最终判定
```
📋 lx-git-check push 推送门禁结果
Gate 0 Commit格式： ✅ {N} commits 全部通过
Gate 1 变更范围：  {N} 文件，{N} commits
Gate 2 安全扫描：   🔴=0 🟡={N}
判定： [✅ 允许推送 / ❌ 阻塞推送]
```

---

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| lx-code-review 不可用 | 调用 skill | 跳过审查，标注"[已跳过]" |
| 测试超时（>120s） | 等待完成 | 超时后建议手动运行 |
| prod-commit 无效 | 脚本报错 | 提示用户重新提供 |
