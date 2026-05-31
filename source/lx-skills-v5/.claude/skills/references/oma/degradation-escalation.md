# 降级 & 升级策略

> OMA 系列 skill 通用降级/升级表。各 skill 引用：`@reference/oma/degradation-escalation.md`
> 原 `degradation-strategies.md` 已合并至此，新增升级路径。

## 降级路径 (Degradation)

> 主路径不可用时 → 降级到次优方案，不阻断流程。

### 通用

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 输入路径不存在 | 报错 | 提示用户补充路径 |
| 输入为空文件 | 报错 | "内容为空，无法处理" |
| 输出目录已存在 | 覆盖写入 | 询问是否覆盖或指定新目录 |
| 子 skill 不可用 | 委托调用 | 告知手动执行对应命令 |
| Oracle Agent 不可用 | spawn agent | AI 按 Oracle 检查清单自审 |
| Meta-Oracle 不可用 | spawn opus critic | 跳过，标注 `[Meta-Oracle 跳过]` |

### 编排层 (orch)

| 场景 | 主路径 | 降级 |
|------|--------|------|
| pipeline.yaml 不存在 | 报错 | 提示 `/lx-oma-gov init` 创建 |
| 无可推进阶段 | "管线已完成" | 退出 |
| Oracle gate 未裁决 | 提示 gate 命令 | `--force` 跳过 |
| 子 skill 调用失败 | 报告错误 | 保留 pipeline 当前状态 |

### 治理层 (gov)

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 治理目录不存在 | 报错 | 提示先 init |
| reconcile 无变更 | "无差异" | 快速 done |
| L3 冲突无裁决 | 挂起+裁决提示 | 非阻塞继续 L1/L2 |
| propagate 目标缺失 | 跳过+报告 | 列出缺失 feature |

### 并发层 (race)

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 无子任务 | register | "无独立子任务"，退出 |
| Task() 不可用 | Task 派发 | run_in_background 并行 |
| 后台不可用 | run_in_background | 顺序执行 |
| race_manager.sh 缺失 | 脚本执行 | 提示重新安装 |
| 全部失败 | 聚合报告 | 报告原因，不阻断父任务 |

---

## 升级路径 (Escalation)

> 问题严重性超过当前层处理能力 → 升级到更高权威。

| 触发条件 | 当前层 | 升级到 | 说明 |
|---------|--------|--------|------|
| Oracle REVISE ×3 | Oracle Agent | Meta-Oracle | 3 轮修复仍不通过 → Meta-Oracle 终审 |
| Meta-Oracle REJECT ×2 | Meta-Oracle | 人类 | 连续 2 次 REJECT = 事实阻断 |
| 铁律 #1 违反（编造） | Hook | BLOCKED（硬阻断） | 不升级，直接阻断 |
| 修复 3 轮仍失败 | Step 执行 | 上报用户 | 记录已尝试方案 + 失败证据 |
| L2 降级路径也失败 | Skill | 上报用户 | 两条路径都走不通 |
| 不可逆操作 | 任何层 | 人类审批 | 删除/发布/支付等，强制人类确认 |
| 跨子系统架构变更 | Skill | Meta-Oracle G1 | 涉及 ≥2 子系统 |
| 哲学冲突无法裁决 | AI 自检 | 人类 | 两哲学同等优先级且结论相反 |

## 升级协议

```
升级时携带：
  1. 问题描述（根因分析）
  2. 已尝试路径（含证据）
  3. 为什么当前层无法解决
  4. 建议的升级后处理方案
```
