# Resume Capsule 模板

> 此为 handoff.md 的推荐模板。每行字段不可随意更改，文件整体是 **导航** 非状态源。

## ⚠️ NOT SOURCE OF TRUTH
Resume engine MUST load token.json (CAS) first.
This handoff is navigation only. Do not parse current state from this file.

generated: {timestamp}
task_id: {task_id}

## Goal
{任务目标原文，来自 plan.md 第一行}

## Confirmed Decisions
- {决策1}
- {决策2}

## Next Action
step: {当前step} | status: {任务状态}

## Changed Files
- {文件1}
- {文件2}

## Required Reads
- token.json (CAS)
- plan.md

## Do Not Reload
- 全部旧 transcript
- docs/reviews/**
- 完整测试日志
