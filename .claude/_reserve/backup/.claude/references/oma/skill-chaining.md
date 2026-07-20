# 技能链式承接

> OMA 4-skill 管线的声明式路由和链式委托协议。

## 4-Skill 管线

```text
lx-oma-hier       lx-oma-split      lx-rpe
(Level 1 分层) → (Level 2 拆解) → (特性级开发)
        ↓                ↓
   lx-oma-gov (治理 reconcile/propagate)
        ↑
   lx-oma-orch (管线编排 + Oracle 门禁)
```

## 链式委托

| 上游 Skill | 下游 Skill | 委托时机 | 数据契约 |
|-----------|-----------|---------|---------|
| lx-oma-hier | lx-oma-split | 每个 Sub PRD 拆解完成 | Sub PRD 目录 + INDEX.md |
| lx-oma-split | lx-rpe | 每个 Feature 脚手架完成 | `prd/{sub_prd}/feat-XXX/prd.md` |
| lx-oma-gov | lx-oma-orch | reconcile/propagate 完成 | governance-report.yaml |

## 路由规则

| 目标 | 路由 Skill | 示例命令 |
|------|-----------|---------|
| Sub PRD | lx-oma-hier | `/lx-oma-orch run <sub_prd>` |
| Feature | lx-oma-split | `/lx-oma-orch run <feature>` |
| 治理 | lx-oma-gov | `/lx-oma-orch run --gov reconcile` |
| RPE | lx-rpe | `/lx-oma-orch run <feature> --feature feat-xxx` |

## Pipeline 状态传递

```yaml
# orch 写入 pipeline.yaml，各 skill 只读
stages:
  hier: {status: completed}
  split: {status: running}
sub_prds:
  - name: domain-auth
    status: split_done
features:
  - id: feat-auth-crud
    stage: oma_created
```

## 模式兼容

| 模式 | 链式行为 |
|------|---------|
| **goal** | 自动推进，skip-risk 处理阻塞 |
| **ghost** | 单向探索，不触发 full pipeline |
| **手动** | 用户显式 `/lx-oma-orch advance` |
