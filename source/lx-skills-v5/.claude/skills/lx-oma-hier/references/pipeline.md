# OMA 全生命周期管线

> 本文件为 lx-oma-hier 的管线集成参考。完整契约见 `@../../references/oma/pipeline-contract.md`。

## PRD 全生命周期

hier 是 PRD 全生命周期的起点：

```
初始化路径（一次性，新项目启动）:

  lx-oma-hier    →     lx-oma-split       →     lx-rpe
  (主PRD→SubPRD)     (SubPRD→RPE)        (特性开发)

  用法:
    1. /lx-oma-hier docs/master-prd.md      # 拆出 Sub PRD
    2. /lx-oma-split sub-prds/domain-xxx.md # 拆出 feature RPE
    3. /lx-rpe <feature-name>               # 启动特性开发

治理路径（长期，主 PRD 变更时）:

  lx-oma-gov      →   lx-oma-split / lx-rpe
  (reconcile/       (变更后重新拆解或直接开发)
   propagate/
   audit)
```

## 联动 lx-oma-split（Level 2）

完成后向用户报告：

```
# 📋 分层拆解完成

共拆分为 N 个功能域，详见 {output_dir}/

## 下一步
每个 Sub PRD 可独立进入特性级拆解。
/lx-oma-split {output_dir}/domain-xxx.md
```

- 不修改 `lx-oma-split` 原有代码
- Sub PRD 目录和 `prd/` 目录可共存
- 长期治理使用 `lx-oma-gov`，见 `.claude/skills/lx-oma-gov/SKILL.md`

## Pipeline 集成（编排模式）

> `--pipeline` 模式：入口检查 + 出口写入。

### 入口检查

当传入 `--pipeline <sub_prd_id>` 时：
1. 读取 `state/pipeline.yaml`
2. 检查 sub_prd 的 `status` 是否为 `hier_done` 或更早

### 出口写入

拆解完成后更新 `state/pipeline.yaml`：
- `sub_prds[].{id, path, status: hier_done, oracle: pending, features: []}`
- `stages.hier = completed`
- 新增 Oracle gate：`{id: og-NNN, from_stage: hier_done, to_stage: oma_ready, status: pending}`

## 交付方向指引

输出报告后追加：

```
─── 方向指引 ───
📍 分层拆解完成。你现在位于 PRD 全生命周期的起点。

建议下一步:
  1. /lx-oma-split sub-prds/domain-{name}.md → 对核心域进行特性级拆解
  2. /lx-orch status → 查看 PRD 全景管线状态
  3. 继续拆分其余 Sub PRD
  4. 自定义操作

  · 依赖链上游的域优先拆解（如 auth→order→payment）
  · 无依赖的域可并行推进
```
