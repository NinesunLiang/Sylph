---
name: lx-pre-commit
version: v2.1.0
description: "提交前轻量检查 — 编译+测试+基本lint。纯指令调用，不接入治理管线。每个任务一次。"
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

## 流程

1. 检测项目类型（go.mod / package.json / pyproject.toml / Cargo.toml）
2. 编译检查（`go build ./...` / `npm run build` / `python -m py_compile`）
3. 运行测试快照（`go test ./... -count=1 -timeout 60s` / `npm test -- --bail`）
4. 基本 lint（`gofmt -l` / `eslint` / `ruff`）
5. 输出概览：
   ```
   ✅ lx-pre-commit 通过  类型: {lang}  编译: ✅  测试: {N} passed   lint: ✅
   ```

## 降级

| 场景 | 降级 |
|------|------|
| 脚本不可用 | AI 手动执行编译+测试+lint |
| 测试超时(>60s) | 超时后提示手动跑 |
| 类型未知 | 跳过，提示用户自行检查 |
