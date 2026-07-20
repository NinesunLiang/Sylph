---
name: lx-stepwise
version: v1.0.0
description: "卡片推进器 — 一句话任务描述 → AI 自行收集信息(无法自决才问人) → 一张一张过卡 → 干净闭环。状态机机械门禁: 当前卡未闭环绝不进下一张。入口: `/lx-stepwise` 或自然语言'逐步推进/过卡片'"
when_to_use: "Use when user says 'lx-stepwise', '过卡片', '逐步推进', 'stepwise', wants a frontend/治理变更按卡推进, or needs 当前卡未闭环不进下一张 的机械执行保障"
argument-hint: "[一句话任务描述]"
harness_version: ">=6.3.0"
status: stable
role: "Card-engine — one card at a time, self-collect first, ask only when undecidable, no advance without closure"
execution_mode: stepwise
triggers: ["/lx-stepwise", "过卡片", "逐步推进"]
nodes:
  - behavior_rules      # 铁律(证据门禁/防编造)贯穿每张卡
  - execute_node        # 降级触发与自洽检查
  - context_collector   # C01-C05 信息自查优先级落地
schemas:
  - atomic/verdict      # C14 final_status 判定口径
---

# lx-stepwise — 稳定干净的卡片推进器

**一句话任务进来 → 按 [stepwise_cards](../../references/templates/stepwise_cards/_schema.yaml) 21 张卡逐张闭环 → 任务干净交付。**

论述源: `.claude/workflows/front-stepwise/origin.md`(完整设计);运行骨架: `.claude/references/templates/stepwise_cards/`;状态机: `scripts/lx-stepwise.py`。

**核心原则: 一次只抽一张卡;能检查就不问,不能决定才问;当前卡未闭环,绝不进入下一张。**

## 与 lx-goal 的分工

lx-goal 是**无人值守**(问完就走,不再交互);lx-stepwise 是**有人在场推进**(能自查就自查,真不能决定才问)。用户给一句话任务、希望看着 AI 一卡一卡推进 → 本 skill。lx-goal 的依赖链/异构子任务引擎路由条目指向本 skill。

## 运行协议(每张卡固定)

1. `status` 看当前卡 → 按卡面 `auto_checks` **自行收集信息**(信息优先级见 [_schema.yaml](../../references/templates/stepwise_cards/_schema.yaml): 用户已给 > 治理文档 > 代码/配置/测试 > Git > 命令实测 > 推断标记 > 最后才问人)
2. 能确定的全确定 → 逐项完成 `exit_criteria` 与 `outputs.required`
3. 过卡:
```bash
python3 .claude/skills/lx-stepwise/scripts/lx-stepwise.py pass-card \
  --card C0X --confirm 1 2 3 --evidence "证据: 文件/符号/命令结果/用户决定" \
  --output key=value ...
```
4. 无法自行决定 → `fail-card --route Q01`(或命中其他异常路由) → `ask --question "..." --options "A..|B.."` → 等用户 → `resolve --answer "..."`
5. 回到来源卡继续,直到 C14 pass → `off` 干净收官

**⚠️ 状态即真相**: 当前卡、已过卡、用户决定、契约范围全在 `.claude/references/templates/stepwise_cards/.state/<task_id>.json`。每轮操作前先 `status` 对齐,不凭记忆推进——配合 [execute_node](../../nodes/execute_node.md) 的自洽检查与 [behavior_rules](../../nodes/behavior_rules.md) 的证据门禁: 无证据不过卡。

## 机械门禁(状态机强制,违反即拒绝)

| 门禁 | 规则 |
|------|------|
| 禁跳卡 | `pass-card` 的卡号必须等于 `current_card` |
| 禁缺项 | `exit_criteria` 未全 `--confirm`、outputs.required 未全 `--output` → 拒绝 |
| C07 契约门 | C07 未 passed,拒绝 pass C08+ 任何卡(未冻结不动代码) |
| C09 验证门 | C09 未 passed,拒绝 pass C13(未验证不宣称完成) |
| C14 闭环门 | C14 未 passed,拒绝 `off`(交付记录未闭环不收官) |
| 唯一问询口 | 仅 `ask` 可置 `waiting_user`;waiting 中一切 pass/fail 拒绝,先 `resolve` |
| 合法回跳 | `resolve --goto` 仅白名单(X04→C06/C08,X01/X03→C07),回跳后目标及之后主卡全部退回重做 |

## 卡组地图

主卡 15 张: C00 启动 → C01 基线 → C02 需求澄清 → C03 模块定位 → C04 依赖数据流 → C05 影响面 → C06 方案 → **C07 变更契约(硬门禁)** → C08 实施(可循环) → **C09 机械验证(硬门禁)** → C10 独立审查 → C11 影响回归 → **C12 仓库清洁(硬门禁)** → C13 用户验收 → C14 交付闭环。

异常卡 6 张: Q01 用户问询 / X01 范围升级 / X02 基线异常 / X03 兼容性决策 / X04 修复决策 / X05 工作区冲突——只能从当前卡 `failure_routes` 进入,闭环后回来源卡。

## C08 实施安全线(卡面 stop_conditions 命中即 fail-card)

不新增依赖(用户明确批准除外);不改 package.json/lockfile/路由/权限/全局状态/公共 hook/公共类型(X01/X03 批准除外);不跑全仓库格式化;不用 any/ts-ignore/eslint-disable 藏问题;不删除/reset/checkout 用户已有改动;临时分析制品写仓库外。

## 原子化声明

### 通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` | 证据门禁/防编造,贯穿每张卡 |
| execute_node | `../../nodes/execute_node.md` | 自洽检查与降级触发 |
| context_collector | `../../nodes/context_collector.md` | C01-C05 信息自查优先级落地 |

### 共享 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | C14 final_status 判定口径 |

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 卡片模板缺失/损坏 | 状态机读模板推进 | 立即停推报缺卡,人工修复模板——不凭空造卡 |
| PyYAML 不可用 | import yaml 解析卡面 | 脚本直接退出报依赖缺失——不降级为弱解析 |
| .state 损坏(多 live 任务) | _active 单任务断言 | 报错并列出现场,人工清理 .state/——不自动合并 |
| 用户长时间不答复 | waiting_user 挂起 | 状态保持不自动 resolve,下次 status 提示待答问题 |
| C10/C11 无 subagent 环境 | fresh-context 独立审查 | 主会话执行,输出标注"[主会话审查,独立性降级]" |

## 上下文治理与抗 compact

C03-C05 大量工具结果先落盘(任务目录),只把结论写回状态文件 outputs——无损可回滚;C10/C11 建议 fresh-context subagent 执行,避免调查污染实施上下文。交付判定口径对齐 [verdict](../../schemas/atomic/verdict.yaml): READY / READY_WITH_KNOWN_LIMITATIONS / NOT_READY。

**抗 compact 双保险**: ① 全量状态(current_card/passed/outputs/契约/用户决定)外置 `.state/<task_id>.json`——compact 摘要有损不可逆,但状态文件不经过摘要;② SessionStart hook 扫描 `.state/` 自动注入 `[Active Stepwise] task=… card=…` 恢复入口——compact/新会话后第一轮即见,AI 不会忘记有任务在推进。恢复后第一条命令永远是 `status` 对齐磁盘态。
