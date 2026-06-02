# 五阶段工作流行为标准 v4.0

> CarrorOS 治理层。状态机 + Hook 强制执行。抗 context compaction。
> 部署在 cc/oc 之上，无需修改宿主代码。

──────────────────────
## 快速开始

```bash
# 部署到当前 cc/oc 项目
bash .claude/workflow-standard/provision.sh

# 卸载
bash .claude/workflow-standard/deprovision.sh
```

──────────────────────
## 结构

```
.claude/workflow-standard/
├── hooks/
│   ├── pretool-workflow-gate   ← PreToolUse:Edit|Write|Bash 阶段门禁
│   ├── checkpoint              ← PostToolUse:TaskUpdate 自动推进
│   ├── session-inject          ← SessionStart 上下文注入（抗compact）
│   └── state-recovery          ← SessionStart 腐蚀恢复+Gate超时
├── state/
│   └── workflow-state.json.template
├── provision.sh                ← 一键部署
├── deprovision.sh              ← 一键卸载
└── README.md
```

──────────────────────
## 机制

### 状态机

```
workflow-state.json  →  持久化当前阶段/checkpoint/Gate/ROI
         │
    SessionStart  →  state-recovery（腐蚀+超时）→ session-inject（注入上下文）
         │
    PreToolUse   →  pretool-workflow-gate（阶段门禁阻断）
         │
    PostToolUse  →  checkpoint（自动推进）
```

### 抗 compact

状态文件在磁盘上持久化。每次 SessionStart（含 compact 后重启），`session-inject` 从状态文件重新注入工作流上下文。不会因为本轮对话被 compact 而丢失阶段信息。

### Gate 超时

Gate 1/2/3 等待人类确认超过 60 分钟 → `state-recovery` 自动转入 idle 状态。

### 腐蚀恢复

`workflow-state.json` JSON 损坏 → `state-recovery` 备份损坏文件 + 重置为 inactive。

──────────────────────
## 依赖

- python3
- CarrorOS `harness_config.sh`（flywheel_event 可选）

──────────────────────
## 版本

- v4.0: 自包含包→独立部署于 cc/oc。抗 compact。Gate 超时。腐蚀恢复。
