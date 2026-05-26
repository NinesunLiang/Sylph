---
name: update-carror-os
version: v1.0.0
description: "Carror OS 安装/更新技能，自动保护 AGENTS.md 不被安装脚本污染。备份 → 安装 → 恢复 → 验证 4 步闭环。"
when_to_use: "When user says '更新 Carror OS', '安装 Carror OS', 'upgrade carror', '跑安装包', 'update-carror-os'. Also when user wants to install/refresh Carror OS harness."
argument-hint: "[enhanced]"
harness_version: ">=6.3.0"
role: "Carror OS install/upgrade with AGENTS.md protection — backup, install, restore, verify"
execution_mode: stepwise
triggers:
  - "/update-carror-os"
  - "更新 Carror OS"
  - "安装 Carror OS"
  - "upgrade carror"
  - "跑安装包"
  - "update-carror-os"
status: stable
---

# update-carror-os — Carror OS 安装/更新

> 解决安装脚本每次追加旧版 Carror OS 段落到 AGENTS.md 的问题。4 步闭环：备份 → 安装 → 恢复 → 验证。

## 执行流程

### Step 1：定位 AGENTS.md 并备份

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
BACKUP="/tmp/agents_carror_backup_$(date +%Y%m%d_%H%M%S).md"

cp "$AGENTS_FILE" "$BACKUP"
echo "✅ 已备份 AGENTS.md → $BACKUP（$(wc -l < "$BACKUP" | tr -d ' ') 行）"
```

### Step 2：运行 Carror OS 安装脚本

```bash
curl -sSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s enhanced 2>&1
```

> 安装完成后不要手动截断 AGENTS.md，直接进入 Step 3。

### Step 3：用备份恢复 AGENTS.md

```bash
cp "$BACKUP" "$AGENTS_FILE"
echo "✅ AGENTS.md 已恢复"
```

### Step 4：验证

```bash
echo "行数: $(wc -l < "$AGENTS_FILE" | tr -d ' ')"
echo "H1 数: $(grep -c '^# ' "$AGENTS_FILE")"
echo "L1分级表次数: $(grep -c 'L1 简单' "$AGENTS_FILE")"
```

**期望结果**：H1 数为 2（`# Carror OS — 元项目治理` + `# 代码执行内核`），L1分级表次数为 1。

## 注意事项

- 安装脚本末尾可能出现 `</persisted-output>`，属已知问题，不影响安装结果，忽略即可。
- 安装完成后需重启 OpenCode 使新版 hooks 生效。
- 备份文件保留在 `/tmp/`，带时间戳，可随时查看。
- 如果项目内有 `scripts/package-release.sh`，可直接运行该脚本，效果相同。
