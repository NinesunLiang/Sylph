---
name: lx-pre-commit
version: v2.2.0
description: "提交前轻量检查 — 编译+测试+基本lint。纯指令调用，不接入治理管线。每个任务一次。新增可执行脚本+安装+配置。"
when_to_use: "Use before git commit. Pure command trigger. One check per task."
argument-hint: "[--skip-review]"
harness_version: ">=6.3.0"
status: stable
role: "Pre-commit quality gate — compile, test, basic lint. Lightweight, command-only."
execution_mode: stepwise
triggers:
  - "/lx-pre-commit"
---
# lx-pre-commit — 提交前轻量检查

> 纯指令调用，不接入治理管线。每个任务执行一次轻量检查。

## 安装

```bash
# 方式A: 直接运行
bash .claude/skills/lx-pre-commit/scripts/lx-pre-commit.sh

# 方式B: 安装到系统（自动创建git hook）
bash .claude/skills/lx-pre-commit/scripts/install.sh
```

安装后 `lx-pre-commit` 命令全局可用，git commit 时自动触发。

## 流程

1. 检测项目类型（go.mod / package.json / pyproject.toml / Cargo.toml）
2. 编译检查（`go build ./...` / `npm run build` / `python -m compileall`）
3. 运行测试快照（配置超时，默认120s）
4. 基本 lint（`gofmt -l` / `eslint` / `ruff` / `clippy`）
5. 输出概览

## 失败行为

| 结果 | 行为 | exit code |
|------|------|:---------:|
| 编译失败 | ❌ 阻断提交，输出具体错误 | 1 |
| 测试失败 | ❌ 阻断提交，输出失败测试名 | 1 |
| Lint 警告 | ⚠️ 不阻断，输出格式问题 | 0 |
| 超时 | ⚠️ 超时输出提示 | 124 |
| 未知项目类型 | 跳过，exit 0 | 0 |

## 配置（可选）

项目根目录创建 `.lx-pre-commit.yml`：

```yaml
timeout:
  build: 120    # 编译超时(秒)
  test: 120     # 测试超时(秒)
lint: true       # 是否运行 lint
skip_tests: false # 是否跳过测试
```

无配置文件时使用默认值：build 120s / test 120s / lint 60s。

## 降级

| 场景 | 降级 |
|------|------|
| 脚本不可用 | AI 手动执行编译+测试+lint |
| 测试超时 | 超时后提示手动跑 |
| 类型未知 | 跳过，提示用户自行检查 |
| 配置解析失败 | 使用默认配置 |
