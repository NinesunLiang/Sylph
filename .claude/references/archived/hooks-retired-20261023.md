# 已删除/退休 Hook 归档（2026-10-23 从 hooks/index.md 迁出）

> 回滚能力由 git 历史提供；本归档仅作删除依据留痕（少即是多：活跃文档不留墓碑）。

## 已删除 Hook（index15 降噪·ROI 清理）

| 已删除文件 | 删除原因 |
|------|------|
| `posttool-bash-audit.py` | 仅被 error-dna 注释提及，无实际注册/引用 |
| `session-resume.py` | 零引用死代码 |
| `token_writer.py` | harness.yaml 显式禁用（token_writer: false） |
| `turn-counter.py` | hc_enabled 门控但未启用 |
| `compound-verify-gate.py` / `verify_contract.py` | 文档描述但文件从未存在（虚构引用） |

## 已退休 Hook（还债·少即是多清理）

| 已删文件 | 原因 |
|------|------|
| `postcompact.py` | 纯记录型；resume-note 写入逻辑无门禁价值，会话恢复由 session-start.py 读 handoff 兜底 |
| `posttool-output-schema.py` | 纯提示型（warn-only）；输出 schema 校验无消费方 |

## index48 随 error-dna 机制删除

| 已删文件 | 原因 |
|------|------|
| `error-dna.py` | index48（2026-09-10 人类裁决）随 error-dna 采集机制整体移除 |
| `read-tracker.py` | 文件实际不存在；仅 harness.yaml 历史注释提及，从未独立注册 |
