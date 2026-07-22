---
name: lx-pre-commit
version: v2.1.0
description: "提交前轻量检查 — 编译+测试+基本lint。纯指令调用，不接入治理管线。每个任务一次。"
when_to_use: "Use before git commit. Pure command trigger. One check per task."
argument-hint: "[--staged] [--skip-review]"
harness_version: ">=6.3.0"
status: stable
role: "Pre-commit quality gate — compile, test, basic lint. Lightweight, command-only."
execution_mode: stepwise
triggers:
  - "/lx-pre-commit"
---
# lx-pre-commit — 提交前轻量检查

> 纯指令调用，不接入治理管线。每个任务执行一次轻量检查。

## 流程

1. 检测项目类型（go.mod / package.json / pyproject.toml / Cargo.toml）
2. `--staged` 模式：只检查 `git diff --cached --name-only --diff-filter=ACM` 中的暂存文件。无暂存文件时跳过。
3. 编译检查（`go build ./...` / `npm run build` / `python -m py_compile`）
4. 测试快照（`go test -count=1 -timeout 120s` / `npm test -- --bail` / `pytest -x`）
5. 基本 lint（`gofmt -l` / `eslint` / `ruff check` / `cargo clippy`）
6. 输出概览：
   ```
   ✅ lx-pre-commit 通过  类型: {lang}  编译: ✅  测试: {N} passed   lint: ✅
   ```

## 失败行为

| 结果 | 行为 |
|------|------|
| 编译失败 | ❌ 阻断提交，输出错误 |
| 测试失败 | ❌ 阻断提交，输出失败测试名 |
| Lint 警告 | ⚠️ 不阻断，输出格式问题 |
| 超时 | ⏱️ 超时后提示手动跑 |
| 未知项目类型 | ⚠️ 跳过 |

## 降级

| 场景 | 降级 |
|------|------|
| 工具不可用 | AI 手动执行编译+测试+lint |
| 测试超时 | 超时后提示手动跑 |
| 类型未知 | 跳过，提示用户自行检查 |
