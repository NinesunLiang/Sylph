---

name: lx-status

version: v1.0.0

description: "展示 Carror OS 系统的健康面板，包括执行效率、自愈力和渐进式披露 Token 节省。"

when_to_use: "Use when user says 'status', 'show dashboard', 'health check', 'lx-status', '面板', '状态'"

model: sonnet

argument-hint: "[--json | --watch]"

harness_version: ">=1.4.0"

---

# lx-status — Carror OS 健康面板

## 原子化声明

### scripts/（确定性执行层）| 脚本 | 用途 | 调用时机 ||------|------|---------|| `../lx-validate-skill/scripts/carror_dashboard.py` | 渲染系统状态仪表盘 | 执行时 |

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

```
bashpy
thon3 .claude/skills/lx-validate-skill/scripts/carror_dashboard.py
bashpython3 .claude/skills/lx-validate-skill/scripts/carror_dashboard.py

```
将控制台返回的看板直接透传展示给用户。

## 降级策略

| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|脚本执行失败 | 运行脚本 | 提示用户：由于底层状态文件缺失或环境限制，面板不可用。|
|无状态数据 | 报错返回 | 提示用户：系统处于初始状态，尚未产生任何执行记录，尝试进行一次 /lx-rpe 开发以生成记录。 |
