---

name: lx-pre-push

version: v2.0.0

description: "推送前深度门禁：commit message 规范校验（骨架驱动，通用）→ 测试覆盖 → 安全扫描 → 判定。"

when_to_use: "Use when user says 'pre-push', 'push check', '推送前检查', or before git push."

model: sonnet

argument-hint: "<prod-commit-hash>"

harness_version: ">=1.1.0"

---

# lx-pre-push — 推送前深度门禁

## 原子化声明

### 使用的通用节点| 节点 | 路径 | 用途 ||------|------|------|| behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 || scanner | `../../nodes/scanner.md` | 安全扫描 |

### scripts/（确定性执行层）| 脚本 | 用途 | 调用时机 ||------|------|---------|| `scripts/commit_convention.py` | commit 规范管理（learn/validate/show/reset）| Gate 0 || `scripts/get_changed_files.py` | 获取相对于 prod-commit 的变更文件 | Gate 1 前 |

### references/（按需加载）| 文件 | 加载时机 ||------|---------|| `references/commit-convention-guide.md` | commit 规范学习和管理指南 |

---

## 前置条件

用户提供线上版本 commit hash（`$PROD_COMMIT`）：

```
/lx-pre-push <prod-commit-hash>

```
获取方式提示（用户不知道时给出）：

```
bashg
it
log --oneline origin/master -1 # master 分支线上版本git rev-list -n 1 <tag> # 指定 tag
```

---

## 执行流程

### Gate 0 — Commit Message 规范校验（骨架驱动）

```
bash
# 如尚未设置规范，先从示例学习（一次性操作）：# python3 .claude/skills/lx-pre-push/scripts/commit_convention.py learn "<示例commit>"
python3 .claude/skills/lx-pre-push/scripts/commit_convention.py validate-batch \ --prod $PROD_COMMIT
```
读取 JSON：
- `blocked: false` → Gate 0 通过 → Gate 1
- `blocked: true` → 输出违规 commit 列表 + 修复建议 → **阻塞推送**
- `has_redline: true` → 红线违规（feat/perf 缺 Issue-ID）→ **必须修复**
违规时建议：`git rebase -i $PROD_COMMIT` 修改 commit message。如需查看完整规则：加载 `@scripts/../references/ank-commit-rules.md`

### Gate 1 — 获取变更范围

```
bashpy
thon
3 .claude/skills/lx-pre-push/scripts/get_changed_files.py \ --prod-commit $PROD_COMMIT
bashpython3 .claude/skills/lx-pre-push/scripts/get_changed_files.py \ --prod-commit $PROD_COMMIT

```
读取 JSON → 得到 `go_files` / `ts_files` / `commit_count`。无变更文件 → 提示"无变更，无需检查" → 结束。

### Gate 2 — 测试覆盖 + 安全扫描

AI 根据 Gate 1 的项目类型判断执行：
**Go 项目**：
- 调用 `Invoke the Skill tool with skill: "lx-security-review"` 传入变更文件
- 执行 `go test -race -coverprofile=coverage.out ./...`，检查覆盖率
**前端项目**：
- `npm audit --production`
- 调用 `Invoke the Skill tool with skill: "lx-security-review"`
安全扫描：🔴=0 才能通过，🟡 记录不阻塞。

### Gate 3 — 最终判定

```
📋 lx-pre-push 推送门禁结果
Gate 0 Commit格式：✅ {N} commits 全部通过Gate 1 变更范围： {N} 文件，{N} commitsGate 2 测试覆盖： ✅ / ❌Gate 2 安全扫描： 🔴=0 🟡={N}
判定：[✅ 允许推送 / ❌ 阻塞推送]阻塞原因：{如有}
```

---

## 降级策略

| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|lx-security-review 不可用 | 调用 skill | 执行 `govulncheck ./...`，标注"[降级扫描]"|
|prod-commit 无效 | 脚本报错 | 提示用户重新提供，说明获取方法|
|测试超时 | 等待 | 120s 后标注"[测试超时，建议手动验证]"，不阻塞 |
