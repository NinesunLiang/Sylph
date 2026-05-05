# Execute

# RPE Version: v1.0 | 最后更新: [日期]

Status: Draft / Final

## 0. 模式标记

- 本次模式：Standard / Handover

## 1. 交付概览

- 完成内容：
- 未完成内容（原因）：
- 与计划偏差（类型 / 影响 / 处置方式）：

## 1.5 遗留问题与接管记录（Handover 必填）

- 接管时遗留问题清单：
- 处理结果（已修复/未修复）：
- 未修复原因与后续建议：
- 接管前后 Evidence 对比：[state/evidence/handover-before-xxx vs handover-after-xxx]

## 2. 变更清单

- 模块/文件：
- 接口/Schema：
- 配置变更：

## 3. 验证证据（Evidence）

- typecheck（命令：[xxx]，输出：[state/evidence/typecheck-xxx]）：
- lint（命令：[xxx]，输出：[state/evidence/lint-xxx]）：
- tests（命令：[xxx]，输出：[state/evidence/tests-xxx]）：
- 手工验证（步骤：[xxx]，截图/日志：[state/evidence/manual-xxx]）：
- 覆盖率对比（变更前：[N%]，变更后：[M%]，来源：[state/tests/coverage-xxx]）：

## 4. Task 执行记录### T-x.x [名称]

- 状态：pending / in_progress / done / blocked
- 开始时间：
- 完成时间：
- Evidence（含时间戳）：
  - typecheck/lint/tests 命令及结果
  - 截图或日志路径（state/evidence/T-x.x-xxx）
- 失败留痕（如有）：
  - 原因：
    - 证据：[state/evidence/T-x.x-fail-xxx]
    - 修正建议：
    - 是否回滚：是/否
  - 回滚动作：

## 5. Blocker 报告（超 SLA 必填）

- 阻塞任务：
- 持续时间：
- 阻塞原因：
- 已尝试：
- 备选路径 A/B/C（含最小风险方案）：
- 是否请求回 Plan：

## 6. 回滚演练记录| Task | 演练时间 | 回滚动作 | 结果 | Evidence ||---|---|---|---|---|| T-x.x | | | 成功/失败 | [state/evidence/rollback-xxx] |

## 7. Known Limitations| # | 描述 | 影响 | 缓解措施 | 接受状态 ||---|---|---|---|---|| 1 | | | | 已接受/待确认 |

## 8. 上线后观察计划（Gate-E 通过前必须完成规划，上线后按实际执行）

- 核心成功指标（业务）：
- 错误率阈值（如 5xx/异常率）：
- 时延阈值（P95/P99）：
- 吞吐/资源阈值（QPS/CPU/内存）：
- 告警规则与通知通道：
- 观察时窗（30min/24h/7d）：
- 回滚触发阈值：

## 9. 复盘

- 有效做法：
- 可优化点：

## Gate-E 结果（强制）

- [ ] typecheck 通过
- [ ] lint 通过
- [ ] tests 通过（按计划范围）
- [ ] Evidence 完整（可复现，state/evidence/）
- [ ] Rollback Drill 完成（含演练证据）
- [ ] Known Limitations 已记录并沟通
- [ ] 上线后观察指标已定义并可执行
- [ ] （Handover）接管遗留问题已闭环或获接受 结论：未全部勾选前，不得标记整体 ✅
