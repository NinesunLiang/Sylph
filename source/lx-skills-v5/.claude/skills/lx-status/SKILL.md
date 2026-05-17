---

name: lx-status

version: v2.0.0

description: "Carror OS 健康面板 v3.0：Token 节省、任务通过率、拦截的错误、升华的知识点 + ROI 量化面板。底部追加 audit dashboard 摘要（5 源聚合）。"

complexity: beginner
when_to_use: "Use when user says 'status', 'show dashboard', 'health check', 'lx-status', '面板', '状态'"

model: haiku

argument-hint: "[--json | --watch]"

harness_version: ">=1.4.0"
status: draft
role: "Carror OS health dashboard — system status panel"
execution_mode: race

triggers:
  - "/lx-status"
  - "status"
  - "dashboard"
---

# lx-status — Carror OS 健康面板

## 原子化声明

### scripts/（确定性执行层）| 脚本 | 用途 | 调用时机 ||------|------|---------|| `../lx-validate-skill/scripts/carror_dashboard.py` | 渲染 4 面板健康仪表盘（Token 节省/任务通过率/拦截的错误/升华的知识点） | 执行时 || `../../scripts/audit_dashboard.py --summary` | 审计聚合摘要（5 源：read-tracker/session-turns/token-tracking/error-dna/session-snapshot） | 执行时追加

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

1. 直接使用 **Bash 工具** 运行脚本（ANSI 颜色码由 Bash 工具渲染）：

```bash
# 检查依赖 skill 脚本是否存在
if [ -f ".claude/skills/lx-validate-skill/scripts/carror_dashboard.py" ]; then
    python3 .claude/skills/lx-validate-skill/scripts/carror_dashboard.py
else
    echo "⚠️ carror_dashboard.py 缺失（lx-validate-skill 未安装或已移除）"
    echo "   降级: 手动读取状态文件..."
    python3 .claude/scripts/audit_dashboard.py --summary 2>/dev/null || echo "   audit_dashboard.py 也不可用"
fi
```

carror_dashboard.py 渲染 4 面板健康仪表盘 + Audit 摘要（5 源聚合状态），全部内联输出。

2. **ROI 量化面板**（新增）— 在健康面板后追加：

```bash
if [ -f ".claude/scripts/roi-dashboard.py" ]; then
    python3 .claude/scripts/roi-dashboard.py
else
    echo "   ROI 面板不可用（roi-dashboard.py 缺失）"
fi
```

roi-dashboard.py 读取 `.omc/state/roi-scores.json`，展示 Top 10 高价值组件 + Bottom 5 低价值组件（瘦身候选）。

> **注意**：用户需使用 `claude --verbose` 启动以绕过 3 行截断，否则面板内容默认折叠，需按 Ctrl+O 展开。

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
| Token 节省数据缺失 | 读取 token-tracking-index.json + total-ops.txt | 显示 degraded 状态 |
| Error DNA 数据未就绪 | 读取 error-dna.jsonl + total-ops.txt | 显示 degraded 状态 |
| Flywheel P0 无记录 | 读取 ~/.claude/flywheel.log | 显示 degraded 状态 + "无 P0 事件记录" |
| 升华知识点数据缺失 | 读取 claude-next.md + kernel.md | 显示 degraded 状态 |
| 脚本执行失败 | 运行 Python 脚本 | 提示用户：底层状态文件缺失或环境不完整 |

### 关联技能
| 技能 | 关联关系 |
|------|---------|
| [lx-validate-skill](../lx-validate-skill/SKILL.md) | lx-status 调用其 carror_dashboard.py 渲染健康面板 |
| [lx-todo](../lx-todo/SKILL.md) | 状态面板与 Todo 队列联动展示任务进度 |
| [lx-rpe](../lx-rpe/SKILL.md) | RPE 实例状态是健康面板的数据来源之一 |


