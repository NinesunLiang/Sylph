# 平台适配指南 — Claude Code + OpenCode

> 双平台支持：Claude Code（主要）和 OpenCode（备选）

---

## 平台对比

| 维度 | Claude Code | OpenCode |
|:----|:-----------|:---------|
| 配置入口 | `.claude/settings.json` | `opencode/carroros.json` |
| Hook 机制 | 原生支持 PreToolUse / PostToolUse / UserPromptSubmit | Plugin 体系 |
| 上下文水位 | posttool-gate.py + precompact-lifecycle.py | observer.py (SQLite 只读) |
| Token 系统 | `.omc/tokens/` (共享) | `.omc/tokens/` (共享) |
| 任务治理 | 全量 Hooks + 脚本 | 聚合配置 + 脚本引用 |
| 推荐用途 | 日常开发主力 | 备用 / 轻量场景 |

## 配置结构

### Claude Code (`.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [{...}],
    "PostToolUse": [{...}],
    "UserPromptSubmit": [{...}]
  }
}
```

### OpenCode (`opencode/carroros.json`)

```json
{
  "carroros": {
    "level": "L2_ENHANCE",
    "observer": {
      "path_env": "OPENCODE_SQLITE_PATH",
      "watermark_strategy": "approx_chars_div_4"
    }
  }
}
```

## 切换平台

1. **从 CC 切到 OC**：确保 `opencode/carroros.json` 存在
   - 设置环境变量 `OPENCODE_SQLITE_PATH` 指向 OpenCode 的 SQLite 数据库
   - 设置 `CARROROS_ROOT` 指向项目根目录
   - observer：`python3 opencode/observer.py`

2. **从 OC 切回 CC**：确保 `.claude/settings.json` 存在
   - Hook 系统会自动注册 posttool-gate.py / pretool-gate.py / pretool-user-approve.py
   - 共享 `.omc/` 下的所有状态文件

## 注意事项

- **共享状态**：Token (`.omc/tokens/`)、Plan (`.omc/tasks/`)、Audit (`.omc/audit/`) 两个平台共用，切换无迁移成本
- **治理等级**：L2_ENHANCE 配置在 OC 侧保持与 CC 一致
- **环境变量**：OC 需要 `OPENCODE_SQLITE_PATH` 显式设置，CC 不需要
- **安装**：`bash install.sh` 在安装 `packages/carroros-base` 时同时包含 `.claude/` 和 `opencode/` 两个目录
- **Observer 依赖**：OC observer 依赖 Python 标准库 (`sqlite3`, `json`, `pathlib`)，无需 pip 安装

## 快速验证

```bash
# CC 验证
python3 .claude/scripts/carros_base.py status

# OC 验证（需设置 OPENCODE_SQLITE_PATH）
OPENCODE_SQLITE_PATH=/path/to/opencode.db python3 opencode/observer.py
```
