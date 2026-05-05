---

name: lx-status

version: v2.0.0

description: "Carror OS 健康面板 v2.0：Token 趋势、Error DNA 状态、Flywheel P0 事件、Feature Registry 注册表、上下文状态。底部追加 audit dashboard 摘要（5 源聚合）。覆盖 AC-12.1~12.5 + AC-13.2。"

when_to_use: "Use when user says 'status', 'show dashboard', 'health check', 'lx-status', '面板', '状态'"

model: sonnet

argument-hint: "[--json | --watch]"

harness_version: ">=1.4.0"

---

# lx-status — Carror OS 健康面板

## 原子化声明

### scripts/（确定性执行层）| 脚本 | 用途 | 调用时机 ||------|------|---------|| `../lx-validate-skill/scripts/carror_dashboard.py` | 渲染 5 面板健康仪表盘（Token/Error DNA/Flywheel/Feature Registry/Context） | 执行时 || `../../scripts/audit_dashboard.py --summary` | 审计聚合摘要（5 源：read-tracker/session-turns/token-tracking/error-dna/session-snapshot） | 执行时追加

---

## 触发条件与路由
**哲学：少，即是多**
| 输入 | 语义 | 行为|
|------|------|------|
|`/lx-status`（无参数）| 查看健康面板 | 直接输出面板内容|
|`/lx-status --json` | 机器可读格式 | 输出 JSON 数据|
|`/lx-status --watch` | 实时监控模式 | 终端下运行，动态刷新 |

## 执行
路由命中 `/lx-status` 请求时：

```bash
python3 .claude/skills/lx-validate-skill/scripts/carror_dashboard.py
echo ""
python3 .claude/scripts/audit_dashboard.py --summary
```
将控制台返回的看板直接透传展示给用户。carror_dashboard.py 渲染 5 面板健康仪表盘，audit_dashboard.py --summary 追加一行审计摘要（5 源聚合状态）。

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
| Token 趋势数据缺失 | 读取 token-tracking-index.json | 显示 degraded 状态 + 提示 RPE-003 修复后启用 |
| Error DNA 数据未就绪 | 读取 error-dna.jsonl | 显示 degraded 状态 + 提示执行 lx-rpe 后自动生成 |
| Flywheel P0 无记录 | 读取 ~/.claude/flywheel.log | 显示 degraded 状态 + 显示"无 P0 事件记录" |
| Feature Registry 缺失 | 读取 .claude/feature-registry.yaml | 显示 degraded 状态 |
| 上下文数据缺失 | 读取 token-tracking-index.json | 显示 degraded 状态 |
| 脚本执行失败 | 运行 Python 脚本 | 提示用户：由于底层状态文件缺失或环境限制，面板不可用。|
