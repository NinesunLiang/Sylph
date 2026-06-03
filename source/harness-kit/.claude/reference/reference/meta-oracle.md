# Meta-Oracle — 最后守门员

> Meta-Oracle 的完整设计理念、攻防博弈实录、与 Oracle 的分工协议，
> 详见 `docs/guides/cn/oracle-meta-oracle-adversarial-review.md`。
>
> 本文档为索引入口，确保客户端 AI 可发现。

## 核心概念

Meta-Oracle 是 Source III + Source I 交叉验证器。
使用**运行时验证**（> 静态检查）寻找 Oracle 的盲区。

## 分工

| Oracle（常规守门员） | Meta-Oracle（最后守门员） |
|---------------------|--------------------------|
| 静态检查 + 文件存在性 | 运行时验证 + 烟雾日志 |
| 每阶段（L2+ 强制） | 仅 G1-G4（~5% 任务） |
| 硬门禁 | 软门禁 |

## G1-G4 触发点

| # | 触发点 | 条件 |
|---|--------|------|
| G1 | 架构决策终审 | ≥2 子系统 + 不可逆变更 |
| G2 | PRD/方案最后一步 | Oracle 已 ACCEPT |
| G3 | Oracle ACCEPT + ≥8.5 分 | 最高虚高场景 |
| G4 | Release 门禁 | package-release.sh 前 |

## 裁决协议

```
[Meta-Oracle: ACCEPT]   → 继续
[Meta-Oracle: ADVISORY] → AI 自行判断
[Meta-Oracle: REJECT]   → 需书面理由覆写，×2 → 事实阻断
```

## 8.6 门禁阈值来源

v6.2.0 审计时 Boss 设定的目标分数：从 6.61 → 8.6。
后续通过 DG-28 静态检测降权校准（`--calibrated` 参数）。

## 同源盲区

方法论解决：A≠B≠Oracle≠Meta-Oracle 四个不同模型族。
工程上因摩擦成本选择低成本方案（同模型+角色切换）。
三源文档 §28-32 已记录此取舍。

## 详细文档

→ `docs/guides/cn/oracle-meta-oracle-adversarial-review.md`（222 行，7 次 agent 调用、46 项发现实录）
