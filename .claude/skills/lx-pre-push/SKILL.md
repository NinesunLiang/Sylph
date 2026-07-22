---
name: lx-pre-push
version: v2.2.0
description: "推送前安全检查 — commit规范校验 + 安全扫描 + 变更审计。纯指令调用，不接入治理管线。每次push前执行。"
when_to_use: "Use before git push. Pure command trigger. One check per push."
argument-hint: ""
harness_version: ">=6.3.0"
status: stable
role: "Pre-push security gate — commit convention, security scan, change audit. Command-only."
execution_mode: stepwise
triggers:
  - "/lx-pre-push"
---
# lx-pre-push — 推送前安全检查

> 纯指令调用，不接入治理管线。每次 push 前执行一次重度检查。

## 流程

> 每个 Gate 失败时必须设置 `exit code = 1`。任一 Gate 🔴 即停止后续检查，立即输出**阻塞推送**。

### Gate 0 — Commit Message 规范校验

检查待推送 commits 的 message 格式。

范围：
1. 当前分支名 → 确定目标分支（`git branch -a` 含 `main` / `master` / `develop`）
2. `git log origin/<target-branch>..HEAD --oneline --no-merges`
3. 目标分支不存在或新分支无 upstream → 跳过 Gate 0，**不阻塞**（首次推送无历史可对比）
4. 降级 `git log @{push}..HEAD --oneline`（仅当 upstream 已建立）

```regex
^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .{1,72}
```

不规范 → 列出具体不符的 commit hash + message → **阻塞推送**。

### Gate 1 — 安全扫描

按项目类型执行：

| 类型 | 命令 | 🔴阻断 | 🟡不阻塞 |
|------|------|:------:|:--------:|
| Go | `go vet ./...` + `gosec ./...`（如已安装 gosec） | 有 vet / gosec 错误 | — |
| Node | `npm audit --production` | 有 critical 漏洞 | 有 high 漏洞 |
| Python | `pip-audit` 或 `pip list --outdated` | 有已知漏洞 | 有版本过期 |

**安全扫描不可用或失败 → 🔴 阻塞推送**。不跳过，不标注放行。

### Gate 2 — 变更审计

用 `git diff origin/main..HEAD --stat --name-only` 检查待推送变更：

- `.env*` / `*.pem` / `*.key` / `id_rsa*` / `credentials*` / `secret*` / `token*` → **🔴 阻塞推送**
- 二进制文件 `>1MB`（扩展名: .exe .dll .so .dylib .bin .dat .zip .tar.gz .img .iso） → **🟡 警告不阻塞**
- 注释中的 `TODO`/`FIXME`/`DEBUG`/`console.log`/`print()` → **🟡 警告不阻塞**

### 最终判定

**每一门独立执行。任一 Gate 标记 🔴，立即 exit 1，不继续执行后续 Gate。**

```
📋 lx-pre-push 推送门禁结果
Gate 0 Commit格式:  ✅ / ❌ {N} commits 检查
Gate 1 安全扫描:    ✅ / ❌ / 🟡={N} 警告
Gate 2 变更审计:    ✅ / ❌ / 🟡={N} 警告
判定: [✅ 允许推送 / ❌ 阻塞推送]
```

**任何一门标记 🔴 必须阻塞推送。**

## 降级

| 场景 | 降级 |
|------|------|
| `git log` / `git diff` 无目标分支 | 用 `@{push}` 替代 |
| 安全扫描工具缺失 | ❌ **阻塞**（不跳过） |
| 命令超时(>120s) | ⏱️ 超时后建议手动检查，但仍**阻塞推送** |
| 项目类型未知 | 跳过安全扫描，但**阻塞推送**提醒手动检查 |
