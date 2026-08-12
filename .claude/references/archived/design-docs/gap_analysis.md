# Gap Analysis — 重构指导文档 vs 磁盘状态
> 复核时间：2026-07-10。用于精确执行；历史“已修复”声明必须以当前代码和验证结果为准。

## 一、来自 总结.md 的要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 1 | session-handoff.md 完整（四件套缺一） | ✅ carros_base.py 已写（init/verify/archive 自动写） | 已修复 |
| 2 | 7 个 bench README 填充 | ✅ 各有目标/预期文件/验证/证据/终态 | 已修复 |
| 3 | carros_base.py `--step` 参数 | ✅ 已有（L464-469 读取步骤列表） | 已修复？需确认 |
| 4 | omc_lint.py 第 4 项 audit jsonl 转正检查 | ✅ L126-144 已检查 json 可解析+完整性 | 已修复？需确认 |

## 二、来自 update.md 的要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 5 | Hook 输出 ≤2 行 | 6 个 hooks 已精简（每步 1 行 json） | ✅ 已查 |
| 6 | 文档与代码路径对齐 | AGENTS.md 引用路径需确认 | ⏳ |
| 7 | index.md 路由系统可调用 | index.md 44 行，引用 SUBAGENT.md 和 enhance/ | ⏳ |
| 8 | bench 最高优先级完成 | 7 个 README 已写 | ✅ |
| 9 | L1 完全闭环 | init→verify→archive 全链路通过 | ✅ |
| 10 | L1 从 AGENTS.md 引用 core 工具 | AGENTS.md 路由表引用 kernel/index/enhance | ⏳ |

## 三、来自 总结.md 和 data.md 的 L2 要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 11 | oracle-spec.md 从 stub 变可调用 | 36 行静态描述，无可执行函数 | ❌ 需补 |
| 12 | context-watermark.md 从 stub 变可检测 | 3 级水位描述，无实现 | ❌ 需补 |
| 13 | fallback-matrix.md 从 stub 变可执行 | 降级逻辑描述，无实现 | ❌ 需补 |

## 五、2026-07-10 复核后的真实残余差距

| # | 差距 | 当前证据 | 状态 |
|---|------|----------|------|
| 16 | README 主心智仍曾按“中低阶/高阶模型”区分 Base/Enhance | 已更新 README，后续需同步所有历史指导文档 | ⚠️ 文档迁移中 |
| 17 | MainAgent/SubAgent 模型未统一 | `.omc/scripts/sub_agent_executor.py` 有 `DEFAULT_MODEL = "deepseek-chat"`，SubAgent 可偏离主会话 | ❌ 未完成 |
| 18 | SubAgent 模型继承链不透明 | `sub_agent_manager.py` 只透传 `ANTHROPIC_BASE_URL`，未显式冻结/审计 resolved model | ❌ 未完成 |
| 19 | 代理协议参数映射不稳定 | 已观察到 `Unsupported parameter: max_output_tokens`；仓库调用使用 `max_tokens`，错误来自适配层或上游请求转换 | ❌ 未完成 |
| 20 | `.claude/` / `.omc/` 边界混杂 | handoff 写入 `.claude/session-handoff.md`，可复用脚本同时存在两侧 | ❌ 未完成 |
| 21 | 日期格式混用 | 代码使用 `%Y%m%d`，历史目录同时有 `YYYY-MM-DD` | ⚠️ 未统一 |
| 22 | lint 契约偏浅 | plan step 与 evidence 只做浅层文本检查，尚未完整解析 verify/evidence schema | ⚠️ 部分完成 |
| 23 | Skills 与 Base 命令面仍偏大 | active skills 和增强命令超过瘦身目标 | ⚠️ 可延后 |

### 错误归因规则

```text
403 model access denied
  = 当前凭据或代理无权访问 resolved model；不是 context 上限。

400 unsupported parameter
  = 请求字段与目标协议不兼容；不是 context 上限。

context/output token limit exceeded
  = 只有服务明确返回 token/context limit 时，才归因于窗口或输出上限。
```

因此，当前出现的 `deepseek-v4-flash` 403 与 `max_output_tokens` 400 都不能归因于“模型最大 180K”。前者是模型路由/权限问题，后者是参数协议映射问题。

