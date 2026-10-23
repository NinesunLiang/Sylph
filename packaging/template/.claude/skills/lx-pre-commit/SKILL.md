---
name: lx-pre-commit
version: v3.0.0
description: "提交前轻量检查 — 必要性/语法/格式，只看改动内容，秒级完成。纯指令调用，每次 commit 前执行。"
when_to_use: "Use before git commit. Lightweight, change-scoped, seconds. One check per commit."
argument-hint: "[--staged]"
harness_version: ">=6.3.0"
status: stable
role: "Pre-commit lightweight gate — necessity, syntax, format. Change-scoped, no external tools."
execution_mode: stepwise
triggers:
  - "/lx-pre-commit"
---
# lx-pre-commit — 提交前轻量检查

> 纯指令调用，不接入治理管线。**每次 commit 前**跑一次（高频、秒级）。

## 定位（index50 重建）

**轻、聚焦改动、不猜、不依赖外部工具。**

| 旧版问题 | 新版 |
|---|---|
| 靠「检测项目类型」——本仓无 go.mod/package.json/pyproject.toml → **未知类型直接跳过，等于没查** | 按**文件后缀**逐个处理，不依赖项目文件存在 |
| 编译/测试**跑全量** | 只查**本次改动的文件** |
| 无「必要性」 | **必要性作为第一道**（阻断） |
| 本仓测试命令非 `pytest -x` | 由脚本按改动内容决定，不写死命令 |

## 执行

```bash
# 检查工作区 + 未跟踪的新文件
python3 ".claude/scripts/pre_commit_check.py"

# 只看暂存区
python3 ".claude/scripts/pre_commit_check.py" --staged
```

## 三项检查

| # | 检查 | 内容 | 失败行为 |
|---|---|---|---|
| 1 | **必要性** | 有实际改动？是否只是在提交缓存/生成物？ | ❌ **阻断**（无可提交内容） |
| 2 | **语法** | 改动文件能否解析（py/json/yaml/sh，用标准库） | ❌ **阻断**（附文件名+错误） |
| 3 | **格式** | 行尾空白 / 末尾缺换行 / tab 与空格混用 | ⚠️ 提示不阻断 |

## 只看改动，不看全量

`git diff` 只能看到**已跟踪**文件的改动——**新建的未跟踪文件看不到**。脚本已并入
`git ls-files --others`，避免把「新增文件」误判成「无改动」（实跑踩过）。

## 降级

| 场景 | 处理 |
|---|---|
| 无改动 | 必要性 ❌ 阻断（本来就没东西可提交） |
| 只有缓存/生成物 | 必要性 ✅ 但告警（提示通常不必提交） |
| 某类型不做语法检查（如 .png） | 跳过该项，不阻断 |
| 脚本不可用 | AI 手动执行三项检查（按本表逐条） |
