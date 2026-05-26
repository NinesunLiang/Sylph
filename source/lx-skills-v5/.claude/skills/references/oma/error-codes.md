# 错误码体系

> OMA 系列 skill 共享错误码。各 skill 前缀不同，语义模式统一。
> 引用：`@references/oma/error-codes.md`

## 前缀约定

| Skill | 前缀 | 超时 | 最大重试 |
|-------|:---:|:---:|:------:|
| lx-oma-hier | HIER | 5 min | 3 |
| lx-oma-orch | ORCH | 15 min（含子skill）| 2 |
| lx-oma-split | SPLIT | 3 min（校验30s）| 3 |
| lx-oma-gov | GOV | reconcile 10m / propagate 3m | 3 |

## 通用语义模式

| 码位 | 语义 | 处理 |
|:---:|------|------|
| `-01` | 缺少参数 | 提示命令格式 |
| `-03` | 路径/文件不存在 | 报错阻断 |
| `-10` | 文件读写失败 | 检查权限后重试 |
| `-20` | 状态冲突 | 输出当前状态+正确路径 |
| `-23` | 校验失败 | 修复后重新校验 |
| `-30` | 操作超时 | 检查输入规模后重试 |
| `-31` | 超过最大重试 | BLOCKED，报告已尝试方案 |
| `-32` | 并发写冲突 | 原子写入（tmp→rename） |
| `-90` | 依赖缺失 | 降级手动执行 |

## Skill 特定

| 错误码 | Skill | 场景 |
|--------|-------|------|
| ERR-HIER-23 | hier | MECE 校验失败 |
| ERR-ORCH-12 | orch | pipeline.yaml 解析失败 |
| ERR-ORCH-21 | orch | gate 裁决时 og-id 不存在 |
| ERR-ORCH-22 | orch | dev mark 的 feature-id 不存在 |
| ERR-SPLIT-23 | split | 接口归属校验 exit 1 |
| ERR-GOV-12 | gov | governance-report.yaml 写入失败 |
| ERR-GOV-21 | gov | L3 冲突未 resolve 尝试 propagate |
| ERR-GOV-23 | gov | reconcile 不一致且 --force 未传 |
