# 我对 Kimi 整合稿的看法

**总评：这是三份提案合成后，最接近“今晚能跑”的一版。**  
它不是又一篇治理论文，而是第一次把路线收成了：**睡前点什么、夜里跑什么、卡死时做什么、早上收什么**。

如果按“能否在 CarrorOS 现有骨架上落地”来打分，我会给：

- **可执行性：9/10**
- **风险控制：8/10**
- **架构自洽：8/10**
- **长期演进：6.5/10**
- **当前能否直接夜跑：还差 4 个补丁**

一句话先说清：

> **方向对，收敛也做得好；但少数几处“看起来很能干”的设计，会在无人值守夜里悄悄放大 residual risk。**

---

## 1. 它最强的地方：真正把三家争议收成了执行系统

Kimi 这版最大的价值，不是文风完整，而是它补上了三家原先都虚着的部分。

### 1.1 四个独创点，我认为三个可以直接保留

1. **真实命令映射**  
   映射到 `carros_base.py`、`lx-goal`、`.omc/tasks/`，这比抽象 Agent 角色表有用一个数量级。  
   没有映射到真实命令的治理文档，夜里一定会变成“模型即兴发挥”。

2. **J0 判断真空规则**  
   这是全文最值钱的部分。  
   三家原方案都隐含“必要时升级 GPT/Opus/Grok 裁决”，但用户硬约束已经锁死：**执行时没有高阶模型**。  
   Kimi 正视了这件事，把所有“没法判”的出口收成 5 种行为。  
   **这才是无人值守方案真正该补的中枢。**

3. **Phase 0 路由表预生成**  
   这一刀非常对。  
   夜间最大的共享冲突通常不是 CSS，而是 `router`、菜单、共享入口、路径常量表。  
   睡前一次生成空壳 + 路由，夜间 `files_allowed` 压到 `src/pages/{domain}/**`，直接把并行难题从“文件租约问题”降成“页内实现问题”。

4. **mock 风险坍缩**  
   方向正确，但我反对它被说得太满。  
   mock 能消掉“打坏真实后端 / 真实资金 / 真实权限系统”的危险，**消不掉**前端状态机写错、交互假通、验收自欺、public component 腐化这些危险。见后面第 3 节。

### 1.2 对三家提案的取舍，大体正确

| 取舍 | 我的判断 |
|---|---|
| 继承 C0–C8 / 证据绑 SHA / 防截图作弊 | 对 |
| 继承 AC 通过率、视觉与判断分离、Draft PR only | 对 |
| 继承失败分类路由、C7 机器门、输入治理优先 | 对，而且必须硬 |
| 砍掉 8 周组织路线、30 任务大 Benchmark | 对，先别组织设计空转 |
| 砍掉执行时高阶裁决 | 对，符合硬约束 |
| 把“升级模型裁决”改成“结构化阻塞转早晨” | 对，而且比三家都现实 |

从整合方法论看，这版已经从“模型会怎么办”前进到了“系统默认怎么办”。

---

## 2. 我明确支持并建议固化的硬原则

下面这些我建议直接升级成“不可协商”：

1. **执行期无高阶模型**  
   高阶模型只参与规则制定和早晨复查，不参与夜里临场裁决。  
   否则系统永远有一个隐形人工/高价大脑兜底，谈不上无人值守。

2. **K3 只做视觉诊断工具，不做裁判**  
   pass/fail 只能由确定性门禁给。  
   配额耗尽时降级，而不是阻塞整条流水线。这点非常成熟。

3. **功能门先于视觉门**  
   页面打不开、接口状态错、防重点不了，还谈像素，是在浪费钱。

4. **公共面夜间冻结**  
   `tokens` / `shared` / `router` / `auth` / 非预授权 `package.json` 全部 deny。  
   没有这条，Draft PR 也会变成“满仓库局部补丁”。

5. **单任务可死，流水线不停**  
   这比“尽力修好当前页”更符合无人值守现实。  
   夜里最贵的不是少做一页，而是卡死在一页上把整晚预算烧光。

6. **Draft PR only，永不默认合并**  
   继续坚持。自动合并是规模化后期的事，不是第一次夜跑的事。

---

## 3. 我认为还不够稳的地方

### 3.1 mock 风险坍缩被高估了

稿子说：

> 全部打在 mock 层 → B2 坍缩为 B1 → 夜间可跑

这只对了一半。

**mock 消掉的是外部副作用，不消掉内部逻辑风险。**

仍然高危的问题包括：

- 表单状态机假成功
- 筛选/重置/分页参数不同步
- Modal 关闭后脏状态残留
- 乐观更新写错
- 错误码映射错误
- 交互 spec 打到 mock 的 happy path 上，看起来全绿
- “功能完成”只是“mock 返回 200”

所以更准确的表述应该是：

> mock 把 **B2-数据破坏风险** 降下去了，但没有把 **B2-状态机/交互契约风险** 降成 B0。

**我的修订：**

- 夜间可以跑“写操作页面”
- 但不能因为 mock 就自动降级成 B0/B1 低审查
- 凡涉及提交/删除/状态流转/权限展示的页面，C4/C5 必须带：
  - 正常成功
  - 业务失败
  - 网络失败
  - 重复提交
  - 关闭回滚
  - 成功后列表/详情刷新  
- 否則这类页最多标 `NIGHT_CANDIDATE_WITH_E2E`，不要默认放行

### 3.2 J0 的“最小风险路径”还不够可机判

J0 说：

> 架构歧义时选最小风险路径

问题是夜里执行模型怎么判定“最小风险”？

如果没有机器规则，模型会把它解释成：

- 最少代码
- 最像自己熟悉的写法
- 最容易先让 build 过

这三者常常不是真最小风险。

**建议把“最小风险路径”定义成固定优先级：**

1. 复用仓库已有页面模式  
2. 不碰 shared / tokens / router  
3. 不新增依赖  
4. 可单页回滚  
5. 不改变全局交互语义  
6. 选择更少状态源，不引入跨页 store（除非 plan 预声明）

并且强制写进 `assumptions.yaml`：

- 候选方案 A/B
- 为什么选 A
- 回滚方式
- 早晨必复查标记

否则 J0 会从“治理规则”退化成“模型自由心证”。

### 3.3 Phase 0 被写得像 30 分钟，实际更像 90–180 分钟

稿子把 Phase 0 写成“睡前 30 分钟”，这是最大的乐观偏差之一。

真要夜跑稳，Phase 0 至少要完成：

- PRD / API / 原型三维对齐
- 每页 L/V/优先级标注
- antd 抉择
- 路由空壳预生成并人工确认
- 环境 smoke
- 预授权命令清单
- 每页 AC 是否可机测
- 关键状态截图是否齐全  
  （空态、加载、错误、权限不足、弹窗、抽屉）

如果这些没做完，夜里不是“自主开发”，是“自动化生产缺陷”。

**我的修订：**

- 首次正式夜跑前，**Phase 0 允许 2–3 小时**
- 一旦稳定后，再压缩到 30–45 分钟模板化操作
- 缺关键态截图的页面，**禁止标 V2/V3**，最多做功能还原

### 3.4 “页面内局部绕开 shared 缺陷”是双刃剑

J0 写公共组件/Token 需要变更时：

> 页面内局部绕开 + 记录

短期能保证流水线不停，长期会制造风格分裂。

如果连续 3 页都对同一个 shared 缺口做了局部绕开，早上醒来你会得到：

- 3 套近似按钮间距
- 3 套近似空状态
- 3 套近似表格筛选区

**建议加一条腐蚀熔断：**

- 同一种 shared gap 被 2 个页面局部绕开后，后续同类页直接 `BLOCKED_SCOPE`
- 早晨优先升成“公共组件补齐任务”，而不是继续让页面各写各的

无人值守可以容忍单页偏差，不能容忍系统性审美分叉。

### 3.5 失败分类路由方向对，但 Implementer/Fixer 分工还偏机械

稿子把：

- Pro = Implementer
- Flash = Fixer

这在预算上合理，在问题性质上不总合理。

有些失败根本不该交给 Flash“修”：

| 失败类型 | 正确处理 |
|---|---|
| 单文件 lint / 小类型错误 | Flash |
| 复杂跨组件状态错误 | 回 Pro，不要 Flash 乱补 |
| PRD/API 冲突 | J0 阻塞，不修 |
| 环境抖动 | 恢复流程，不改业务代码 |
| 视觉语义不清 | 先确定性 diff；不收敛再 K3 诊断 |
| shared 才能根治 | BLOCKED_SCOPE |

如果让 Flash 无差别修一切 fail，会出现“修到 build 绿、交互更错”。

---

## 4. antd 问题：Kimi 给了分叉，但我建议今晚先锁死 Patch A

Kimi 把 antd 做成 Patch A/B 二选一，作为工程方案是负责任的。  
但若目标是“尽快形成可复用夜跑系统”，我建议：

### 首选
**Patch A：自定义组件 + CSS Modules + tokens**

理由：

1. 与现有宪法一致
2. C7 红线可直接机器化
3. 视觉归属更干净
4. 不要在夜跑首周同时验证两套 UI 世界观

### Patch B 什么时候才开启
只有同时满足才值得：

- 产品明确要求 antd v6
- tokens → `ConfigProvider` theme 映射已在白天做好
- 表格/表单/弹窗规范已沉淀
- 首个夜跑不拿 Patch B 试错

**原则：系统验证期不要并行验证技术栈迁移。**

---

## 5. 我认为必须补的 6 个补丁，再谈“定稿可跑”

下面这 6 条，我建议作为整合稿 v1.1 的强制补丁。

### 补丁 1：完成定义改成“证据完成”，不是“步骤走完”
每页 `acceptance_report.md` 必须有：

- AC 列表
- 每条 AC 对应命令/用例
- 当前 commit SHA
- 截图或 trace 路径
- 未通过项与阻塞码
- assumptions 列表

没有证据链，一律不算完成。

### 补丁 2：C7 必须先有真实脚本，再开夜跑
不能只写 `scripts/c7-check.sh` 名字。  
至少先覆盖：

- `.tsx` / `.module.scss` 行数
- 裸色值
- 魔法 px
- 是否落在 `files_allowed`
- 截图是否落到 `.omc/screenshots/{task}/`

没有机器门的红线，等于夜间软提醒。

### 补丁 3：视觉门先做“可判定子集”，不要一开始全像素神教
首周建议验这些硬项：

- 主视口 1440 布局不崩
- 关键区域齐全
- 无横向溢出
- 无 console error
- 文本不截断到不可用
- Token 色/字号/间距大致契合并可测量

整页像素评分可以做，但不要让 K3 或 pixel diff 成为唯一放行条件。  
**先稳，再狠。**

### 补丁 4：突发事件分级，不要所有 BLOCKED 都一个姿态
建议至少分：

- `BLOCKED_INPUT`
- `BLOCKED_SCOPE`
- `BLOCKED_ENV`
- `BLOCKED_BUDGET`
- `BLOCKED_HUMAN`
- `BLOCKED_VISUAL_P0`

早晨报告按阻塞码聚合，而不是一大篇流水账。

### 补丁 5：Draft PR 的最小可审结构要固定
每个 Draft PR 描述固定四段：

1. 做了什么页面  
2. AC 通过了哪些 / 卡在哪里  
3. 有哪些 assumptions  
4. 明确没动哪些公共区域  

否则早上人类审核成本会吞掉夜间节省的时间。

### 补丁 6：首周只允许“串行夜跑”，不要一上来并行
即使路由已预生成，首周仍建议：

- 一晚最多 3 页
- 串行执行
- 一页 archive 后再开下一页

并行是吞吐优化，不是正确性前提。  
先证明控制面可靠，再追求 CPU 打满。

---

## 6. 兼容性判断：它和我之前的立场差在哪

和我前一版意见相比：

### 高度一致
- 先边界后自治
- AC 证据化
- Kimi 少用且只诊断
- 夜间不合并
- 输入缺陷必须停
- C7 机器化
- 公共面冻结

### 它比我更强的地方
- J0
- Phase 0 路由预生成
- 真实命令/状态机映射
- “单任务可死，流水线不停”
- 把方案压缩成可操作 runbook

### 它比我更危险的地方
- 对 mock 降险过度叙事
- Phase 0 时长过度乐观
- “局部绕开”缺少腐蚀熔断
- Fixer=Flash 的失败分派过粗
- 仍把 antd 分叉留在启动清单里，容易在仓促中选错

所以我的态度不是“推倒重来”，而是：

> **以 Kimi v1.0 为执行骨架，打上我列的 6 个补丁后升格为 v1.1 试跑版本。**

---

## 7. 如果让我给一个 Go / No-Go

### 现在：No-Go（还不能无补丁直接睡）
原因不是方向错，而是这 4 件事还没闭环：

1. antd 最终锁定了没有（我建议先 A）
2. `c7-check` / 视觉冒烟 / 证据模板是否已真实可跑
3. 首夜页面清单是否只有“输入完整 + 高 mock 可测”的页
4. J0 最小风险路径是否已写成机判优先级，而不是口号

### 满足以下条件后：有条件 Go
- Patch A 锁定
- 3 个以内页面
- 全是 V0–V2、无 B3
- PRD/API/关键态截图齐全
- 路由空壳已提交
- C1/C2/C3/C4 脚本可跑
- Draft PR 产出链路打通
- 全局关闭自动合并
- K3 默认可关，不为首夜刚需

---

## 8. 早晨验收我建议只看 8 个数字

别一上来看“做了多少页”。先看系统有没有失控：

1. **错误完成声明数 = 0**
2. **越界改动数 = 0**
3. **未授权公共面改动数 = 0**
4. **同指纹无效重试数**
5. **D2 被正确阻塞的数量**
6. **有证据 AC 通过率**
7. **Draft PR 可审比率**
8. **恢复/续跑是否靠状态文件而不是聊天记忆**

这 8 个交差，才配谈第二周加页、并行、开 K3、扩 V3。

---

## 9. 最终结论

Kimi 这版整合，我的真实评价是：

> **它已经从“模型比赛文案”升级成了“可落地控制面草案”。**  
> 三家提案里我最欣赏它的一点：**终于肯承认夜里没有神，只能靠 J0、门禁、预算、阻塞码和 Draft PR 活下去。**

但我不同意它直接被称为“定稿可执行版”。  
它现在是：

**v1.0 可评审执行骨架**

还不是：

**v1.1 可上夜班版本**

---

### 我建议的收口句式（可直接写进评审结论）

1. **采用 Kimi 整合稿作为唯一执行骨架。**  
2. **锁定 Patch A（自定义组件体系），Patch B 暂缓。**  
3. **接受 J0，但补机判化的最小风险优先级。**  
4. **接受 mock 降外部风险，但不接受自动业务降级。**  
5. **首周串行、少页、重证据、禁合并。**  
6. **先验控制面健康，再验页面产量。**

再压成一句：

> **这版可以成为 CarrorOS 前端无人值守的底板；先别急着证明 AI 多能写页面，先证明系统在没高阶模型时也不会撒谎、不会越界、不会停不下来、不会把公共层写脏。**

如果你们要，我下一步可以直接把这份 Kimi v1.0 收成一版 **`v1.1 补丁清单 + 首夜启用清单（Go/No-Go Checklist）`**，只保留能执行的句子，不再写长文。


# CarrorOS 前端无人值守 v1.1

> 基于 Kimi K3 整合稿 v1.0 的补丁升格版  
> 目标：把“可评审骨架”变成“首夜可启用版本”  
> 硬约束不变：**执行时无高阶模型；夜间只出 Draft PR；不自动合并**

---

## A. v1.1 补丁清单

### 使用方式
- 状态分：`必做` / `建议` / `首夜禁止`
- 未完成任一 `必做` → **No-Go**
- 全部 `必做` 完成，且清单勾选通过 → **有条件 Go**

---

### Patch-01｜锁定 UI 体系为 Patch A（必做）

**问题**  
antd A/B 分叉会让首夜同时验证两套 UI 世界观。

**v1.1 规定**
- 首夜及校准周 **只允许 Patch A**：自定义组件 + CSS Modules + `src/styles/tokens/`
- Patch B（antd v6）整包冻结，不进入 `night-manifest`
- `pre_authorized` 中删除任何 `pnpm add antd...`

**验收**
- [ ] `night-manifest.yaml` 中 `ui_stack: patch_a`
- [ ] deny 列表无 antd 例外
- [ ] 无 antd 依赖安装预授权

---

### Patch-02｜J0「最小风险路径」机判化（必做）

**问题**  
“选最小风险路径”不可机判，易变成模型自由心证。

**v1.1 固定优先级（从高到低）**
1. 复用仓库已有页面模式
2. 不碰 `shared` / `tokens` / `router` / `auth`
3. 不新增依赖
4. 可单页回滚
5. 不改变全局交互语义
6. 不新建跨页 store（除非 plan 预声明）

**强制产物**
```yaml
# assumptions.yaml 每条至少包含：
- id: A-01
  candidates: [方案A, 方案B]
  chosen: 方案A
  reason_priority: [1, 2, 4]   # 对应上面优先级编号
  rollback: git revert <sha> / 删除页面分支
  morning_review: required
```

**验收**
- [ ] J0 触发时必写 `assumptions.yaml`
- [ ] 无 `morning_review: required` 标记的假设，不允许静默带过

---

### Patch-03｜mock 只降外部风险，不自动降业务等级（必做）

**问题**  
“mock 后 B2→B1”叙事过度，状态机/交互假绿仍危险。

**v1.1 规定**
- mock 只证明：无真实后端破坏、无真实权限越权
- 涉及提交/删除/状态流转/权限展示的页面，仍按 **交互高风险页** 处理
- 这些页 C4/C5 最低集必须全绿：

| 必测态 | 要求 |
|---|---|
| 正常成功 | 成功反馈 + 列表/详情刷新 |
| 业务失败 | 错误可见、可恢复 |
| 网络失败 | 不白屏、可重试 |
| 重复提交 | 防重生效 |
| 关闭回滚 | Modal/Drawer 关闭后无脏状态 |
| 空/加载 | 不布局塌陷 |

**验收**
- [ ] 写操作页若缺上述用例 → 不得标 `DONE`
- [ ] 只能标 `NIGHT_CANDIDATE_WITH_E2E` 或 `BLOCKED_INPUT`

---

### Patch-04｜C7 / 范围 / 证据 必须机器门（必做）

**问题**  
只有红线文档、没有脚本 = 夜间软提醒。

**v1.1 最低机器门**

```bash
# 必须真实可跑，不允许“先写名后补实现”
scripts/c7-check.sh
scripts/scope-check.sh
scripts/evidence-check.sh
```

最低检查项：

| 脚本 | 至少覆盖 |
|---|---|
| `c7-check.sh` | `.tsx≤300`、`.module.scss≤300`、禁裸色值、禁魔法 px、截图路径合法 |
| `scope-check.sh` | `git diff` ⊆ `files_allowed`；deny 路径零命中 |
| `evidence-check.sh` | 每条 AC 有命令/用例 + 当前 SHA + 截图或 trace 路径 |

**验收**
- [ ] 三脚本本地 smoke 通过
- [ ] 故意造 1 个越界文件 / 1 个裸色值 / 1 条缺证据 AC，均能 fail

---

### Patch-05｜阻塞码体系固化（必做）

**问题**  
早上如果只看到“失败了”，审查成本会吞掉夜间收益。

**v1.1 阻塞码（仅允许这些）**

| Code | 含义 | 夜行为 |
|---|---|---|
| `BLOCKED_INPUT` | PRD/API/原型冲突或 D2 缺口 | 记 `open-questions.md`，跳下页 |
| `BLOCKED_SCOPE` | 需改 shared/tokens/router/auth | 禁止改公共面，跳下页 |
| `BLOCKED_ENV` | dev server/代理/浏览器/登录态 | 预授权恢复 1 次；仍失败则夜级熔断 |
| `BLOCKED_BUDGET` | 超调用/轮次/墙钟 | 停本页 |
| `BLOCKED_HUMAN` | 不可逆/无最小风险路径 | 停本页，早晨裁决 |
| `BLOCKED_VISUAL_P0` | 结构级视觉 P0 未收敛 | 记录 diff，不伪称完成 |
| `DONE_WITH_ASSUMPTIONS` | 功能过、有 D1 假设 | 可出 Draft PR，早晨必审假设 |

**验收**
- [ ] `acceptance_report.md` / 早晨报告只使用上述 code
- [ ] 禁止用“微调一下就好”替代阻塞码

---

### Patch-06｜shared 局部绕开腐蚀熔断（必做）

**问题**  
“页面内绕开 shared 缺陷”短期保吞吐，长期制造风格分裂。

**v1.1 规则**
- 允许单页局部绕开，必须记 `assumptions.yaml`
- **同一 shared gap 被 2 个页面绕开后**：
  - 后续同类页一律 `BLOCKED_SCOPE`
  - 早晨优先生成“公共组件补齐任务”
- 禁止第 3 页继续复制粘贴私有样式/私有按钮/私有空态

**验收**
- [ ] 有 `shared-gap-registry.yaml`（或等价登记）
- [ ] 同 gap 计数 ≥2 后自动/人工阻断后续绕开

---

### Patch-07｜完成定义 = 证据完成（必做）

**问题**  
“12 步走完”不等于“可验收完成”。

**每页 `acceptance_report.md` 最低字段**
```markdown
# FE-{domain}
- commit_sha:
- ac_total / ac_passed:
- gates: C1..C8 结果
- evidence:
  - AC-01 → command/spec + screenshot/trace
- assumptions: [A-01...]
- blocked_code: null | BLOCKED_*
- draft_pr:
- files_touched:
- files_denied_confirmed_clean: true
```

**验收**
- [ ] 缺 evidence 的 AC 一律不算 pass
- [ ] 无 SHA 绑定的截图一律作废

---

### Patch-08｜Draft PR 描述模板固定（必做）

**模板四段，缺一不可**
1. 做了什么页面（范围）
2. AC 哪些过 / 哪些卡（带 code）
3. assumptions 列表
4. 明确没动哪些公共区域（tokens/shared/router/auth）

**验收**
- [ ] 早晨打开 PR 3 分钟内能判断“能不能合 / 要不要改 / 要不要补公共层”

---

### Patch-09｜首周串行 + 少页校准（必做）

**v1.1 首夜上限**
- 页面数：**≤ 3**
- 执行方式：**串行**
- 并行：`首夜禁止`
- V 级：优先 V0–V2；V3 不超过 1 页且 K3 可关
- 业务级：无 B3；无真实后端写

**验收**
- [ ] `night-manifest.pages.length ≤ 3`
- [ ] `parallelism: 1`

---

### Patch-10｜视觉门先做可判定子集（必做）

**首夜视觉硬项（全要）**
- xl=1440 主视口布局不崩
- 关键区域齐全（筛选/列表/表单/主按钮等）
- 无横向溢出
- 无 console error
- 文本不截断到不可用
- Token 色/字号/间距可测量对齐（非整页审美分）

**首夜不做**
- 全像素神教唯一放行
- K3 作为必须裁判
- 自动更新视觉基线

**K3 策略**
- 默认 `visual_diagnosis: disabled`（首夜）
- 若开启：仅 V2≤1 / V3≤2，只诊断不写码，失败不阻塞流水线

---

### Patch-11｜失败分派按类型，不按“Flash 修一切”（必做）

| 失败类型 | 处理 |
|---|---|
| 单文件 lint / 小类型错 | Flash Fixer |
| 跨组件状态 / 交互根因不清 | 回 Pro Implementer |
| PRD/API 冲突 | `BLOCKED_INPUT`，不修 |
| 环境抖动 | 恢复流程，不改业务代码 |
| shared 才能根治 | `BLOCKED_SCOPE` |
| 视觉语义不清 | 先确定性 diff；可选 K3 诊断 |

---

### Patch-12｜Phase 0 时长与输入完整度现实化（必做）

**修订**
- 首次正式夜跑 Phase 0：**允许 90–180 分钟**
- “30 分钟”只适用于模板稳定后
- 缺关键态截图（空/加载/错误/弹窗/抽屉/无权限）的页面：
  - 不得标 V2/V3
  - 最多做功能还原

**验收**
- [ ] 每页都有可执行 AC
- [ ] 每页 API 契约齐全
- [ ] V2/V3 页关键态截图齐全

---

### Patch-13｜夜级熔断条件保留并收紧（必做）

**页级熔断（停本页，继续下页）**
- 同失败指纹 ×2 且无有效变化
- 超 `per_page_calls / fix_rounds / page_wall_clock`
- 越界 diff 两次
- D2 输入缺口

**夜级熔断（全停）**
- dev server 预授权重启后仍挂
- 连续 3 页同环境问题
- git 状态损坏 / 无法切干净分支
- 未授权触碰 deny 路径

---

### Patch-14｜组织与所有权补丁（建议，但首周就该有人）

即使首夜技术 Go，也建议明确：
- 前端治理 Owner：Design System / shared / tokens
- CarrorOS Owner：门禁脚本 / lx-goal / 状态恢复
- 任务 Owner：早晨 PR 审查与假设裁决

无 Owner 也能跑一晚；无 Owner 会在第 2 周脏掉。

---

## B. 首夜启用清单（Go / No-Go Checklist）

### 0. 总规则
- 下列 **P0 全绿** → 可启动
- 任一 P0 红灯 → **禁止 `lx-goal on`**
- P1 红灯可启动，但必须写入“已知风险”

---

### B1. 人类裁决（P0）

- [ ] **UI 体系锁定 Patch A**（禁用 antd Patch B）
- [ ] **首夜串行**，并行关闭
- [ ] **页面 ≤ 3**
- [ ] **无 B3**（资金/删除/权限/不可逆真实副作用）
- [ ] **不自动合并**；产物只能 Draft PR / 隔离分支
- [ ] **执行期无高阶模型**；裁决统一早晨人类

> 任一未勾选 → **No-Go**

---

### B2. 输入完整度（P0）

对计划夜跑的每一页：

- [ ] PRD 路径可用（目标/角色/区域/字段/动作/状态/AC）
- [ ] API 文档可用（method/path/字段/枚举/错误码/示例）
- [ ] 原型可访问
- [ ] 关键态截图：至少正常态；V2/V3 另需空/加载/错误/弹窗或抽屉
- [ ] 每页已标：`id / domain / L / V / priority / ac_count`
- [ ] D2 冲突已清空，或已明确“本页不跑”

> 目标页有 1 页输入不完整 → 剔除该页后再判  
> 剔除后无页可跑 → **No-Go**

---

### B3. Phase 0 产物（P0）

- [ ] `night-manifest.yaml` 已生成
- [ ] `base_sha` 已记录（`git rev-parse HEAD`）
- [ ] 路由与空壳已预生成并人工确认提交
  - `src/router/paths.ts`
  - `src/router/index.tsx`
  - `src/pages/{domain}/index.tsx` 空壳
- [ ] 每页 `files_allowed` 仅 `src/pages/{domain}/**`
- [ ] deny 已写入：
  - `src/styles/tokens/**`
  - `src/components/shared/**`
  - `src/router/**`
  - `src/auth/**`
  - `package.json`（除明确预授权行）
- [ ] budgets 已写：
  ```yaml
  budgets:
    per_page_calls: 20
    fix_rounds: 4
    visual_rounds: 3
    page_wall_clock_min: 90
    night_wall_clock_min: 600
    kimi_calls_total: 0   # 首夜建议 0
  visual_diagnosis: disabled
  parallelism: 1
  ui_stack: patch_a
  ```

---

### B4. 环境自检（P0）

```bash
# 全部应成功
lsof -i :9001 | grep LISTEN
curl -s http://127.0.0.1:9998/health
git status --short          # 应干净
# playwright 截图 smoke 1 次
# chrome-devtools 截图 smoke 1 次
```

- [ ] dev server `:9001` 在跑（AI 不得擅自启动新的长期服务）
- [ ] 模型代理健康（pro/flash 路由可用）
- [ ] Playwright smoke 通过
- [ ] chrome-devtools smoke 通过
- [ ] 若原型需登录：登录态已由人备好
- [ ] 工作区干净，无半成品脏改动

> 任一失败 → **No-Go**

---

### B5. 机器门可用性（P0）

- [ ] `pnpm typecheck` 在基线上可通过（或已知与本夜无关的基线债已记录）
- [ ] `pnpm lint` / `build` 可跑
- [ ] `scripts/c7-check.sh` 可跑且能故意 fail
- [ ] `scripts/scope-check.sh` 可跑且能故意 fail
- [ ] `scripts/evidence-check.sh` 可跑
- [ ] `carros_base.py init/status/verify/archive` 路径确认
- [ ] 失败指纹/record 机制可用（`failure.json` 或 Error DNA 等价物）

---

### B6. 预授权与红线（P0）

`night-manifest.pre_authorized` 最多允许：
- [ ] `pnpm dev --port 9001` 重启 **仅当** 9001 无监听且日志显示崩溃
- [ ] 无包安装；或仅有白天已审批的极小白名单（首夜建议为空）

必须 deny：
- [ ] tokens / shared / router / auth / 非预授权 package.json

明确禁止：
- [ ] 合并主干
- [ ] 发布生产
- [ ] 改权限模型
- [ ] 自动接受视觉基线更新
- [ ] 夜间“顺手重构”公共组件

---

### B7. 页面准入过滤器（P0）

每一页都必须满足：

- [ ] 可 mock 独立开发
- [ ] AC 可机测
- [ ] 不依赖夜间改 shared
- [ ] 不依赖真实后端联调
- [ ] L/V 与首夜策略匹配（≤3 页；V3≤1）

页面状态标签只允许：
- `READY_FOR_NIGHT`
- `NIGHT_CANDIDATE_WITH_E2E`
- `EXCLUDED`

> `EXCLUDED` 页不得进 night-manifest

---

### B8. 早晨回收机制（P0）

启动前确认明早能收到：
- [ ] `lx-goal report`（或等价总报告）
- [ ] 每页 `acceptance_report.md`
- [ ] Draft PR 列表
- [ ] 阻塞码聚合清单
- [ ] assumptions 清单
- [ ] 成本/调用统计

并预留早晨审查时间：
- [ ] 至少 45–90 分钟（3 页校准夜）

---

## C. Go / No-Go 判定表

### C1. No-Go（立刻禁止夜跑）

出现任意一条：

1. 未锁定 Patch A  
2. 想首夜并行  
3. 页面 > 3  
4. 路由空壳未预提交  
5. C7/scope/evidence 脚本不可跑  
6. dev server / 代理 / 浏览器 smoke 失败  
7. 目标页 PRD/API/原型缺关键输入  
8. 允许自动合并或允许改 auth/tokens/shared  
9. 工作区不干净 / base_sha 不清楚  
10. 无 Draft PR 产出路径

### C2. 有条件 Go（可启动）

同时满足：

1. 全部 P0 勾选通过  
2. 页面 1–3 个，串行  
3. Patch A  
4. mock 可跑，真实副作用为 0  
5. K3 默认关闭或配额 0  
6. 熔断码与 J0 已写入 manifest/runbook  
7. 早晨审查人已指定  

### C3. Full Go（首夜不追求）

以下不作为首夜目标：
- 并行  
- V3 大规模视觉追平  
- antd 迁移  
- 自动合并  
- 公共层自治修改  
- 高阶模型夜间裁决  

---

## D. 睡前 15 分钟最终口令册

按顺序执行，中断即停：

```bash
# 1) 再确认干净与基线
git status --short
git rev-parse HEAD

# 2) 环境
lsof -i :9001 | grep LISTEN
curl -s http://127.0.0.1:9998/health

# 3) 门禁 smoke（按你们真实脚本名）
bash scripts/c7-check.sh --smoke
bash scripts/scope-check.sh --smoke
bash scripts/evidence-check.sh --smoke

# 4) 确认 manifest
# - pages ≤ 3
# - parallelism: 1
# - ui_stack: patch_a
# - visual_diagnosis: disabled
# - deny 完整

# 5) 激活（仅当上面全绿）
python3 .claude/skills/lx-goal/scripts/lx-goal.py on "前端还原夜跑 {date}"
ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active
```

激活后只允许系统按页串行：
`init → research → plan 冻结 → 实现 → C1..C8 → verify → archive`

卡点只许：
`BLOCKED_* 记录后进入下一页`  
或  
`夜级熔断停机`

---

## E. 早晨 8 问（先问控制面，再看产量）

1. 错误完成声明数是否为 0？  
2. 越界改动数是否为 0？  
3. deny 公共面是否零触碰？  
4. 同指纹无效重试有多少？  
5. D2/输入冲突是否被正确 `BLOCKED_INPUT`？  
6. 有证据 AC 通过率多少？  
7. Draft PR 是否可 3 分钟看懂？  
8. 续跑/恢复是否依赖状态文件而非聊天记忆？  

**这 8 问不过，不允许靠“又做了几页”宣称成功。**

---

## F. 建议的首夜参数（直接可抄）

```yaml
night-manifest.yaml:
  base_sha: "<fill>"
  ui_stack: patch_a
  parallelism: 1
  pages:
    - { id: FE-demo-1, domain: demo1, L: L1, V: V1, files_allowed: ["src/pages/demo1/**"], ac_count: N }
    - { id: FE-demo-2, domain: demo2, L: L1, V: V1, files_allowed: ["src/pages/demo2/**"], ac_count: N }
    # 最多第 3 页
  pre_authorized:
    - "pnpm dev --port 9001 重启（仅当 9001 无监听且日志显示崩溃）"
  deny:
    - "src/styles/tokens/**"
    - "src/components/shared/**"
    - "src/router/**"
    - "package.json"
    - "src/auth/**"
  budgets:
    per_page_calls: 20
    fix_rounds: 4
    visual_rounds: 3
    page_wall_clock_min: 90
    night_wall_clock_min: 600
    kimi_calls_total: 0
  visual_diagnosis: disabled
  merge_policy: draft_pr_only
```

---

## G. 一句话收口

> **v1.1 不是让夜跑更猛，而是让夜跑更老实：**  
> 少页、串行、Patch A、机器门、J0 可机判、mock 不自欺、公共面冻结、Draft PR only。  
> **先证明系统不撒谎、不越界、可熔断、可回收，再谈产量。**

---

### 你现在只要做的最小动作
1. 用本清单逐项打勾  
2. 红灯项先补齐脚本/输入/路由空壳  
3. 全绿后再 `lx-goal on`  
4. 早晨只按 **E. 早晨 8 问** 验收控制面  

如果你要，我下一份可以直接给你：  
**`night-manifest.yaml` 空模板 + `acceptance_report.md` 空模板 + `assumptions.yaml` 空模板**（可直接落盘使用）。


# v1.1 落盘模板（可直接复制）

> 约定（与 AGENTS / Kimi 整合稿对齐）：
> - `night-manifest.yaml`：睡前总控，建议放 `.omc/night/{date}/night-manifest.yaml`
> - `acceptance_report.md`：每页一份，建议放 `.omc/task/{YYYY-MM-DD}/FE-{domain}/state/acceptance_report.md`
> - `assumptions.yaml`：每页一份（有 J0/D1 假设才写），建议放同任务目录 `state/assumptions.yaml` 或任务根目录

---

## 1. `night-manifest.yaml` 空模板

```yaml
# =============================================================================
# CarrorOS 前端无人值守 · night-manifest.yaml
# 版本: v1.1
# 路径建议: .omc/night/{YYYY-MM-DD}/night-manifest.yaml
# 规则:
#   - 缺任何 P0 字段 → 禁止 lx-goal on
#   - 夜间越 pre_authorized / deny → 熔断
#   - 首夜: parallelism=1, pages≤3, ui_stack=patch_a, merge_policy=draft_pr_only
# =============================================================================

schema_version: "1.1"
run_id: "FE-NIGHT-{YYYY-MM-DD}"          # 例: FE-NIGHT-2026-07-17
created_at: ""                            # ISO8601，Phase 0 填写
created_by: ""                            # 人类操作者
goal_title: "前端还原夜跑 {YYYY-MM-DD}"

# ---------- 仓库基线 ----------
repo:
  path: ""                                # 目标仓库绝对/相对路径
  base_sha: ""                            # git rev-parse HEAD（睡前冻结）
  branch_policy: "per_page_branch"        # per_page_branch | single_night_branch
  working_tree_clean_required: true

# ---------- 硬策略（首夜锁定） ----------
policy:
  ui_stack: "patch_a"                     # patch_a=自定义组件+CSS Modules+tokens；patch_b 首夜禁止
  parallelism: 1                          # 首夜必须 1
  merge_policy: "draft_pr_only"           # 禁止 auto_merge
  real_backend: false                     # 夜间全 mock
  high_order_model_at_runtime: false      # 执行期无高阶模型
  visual_diagnosis: "disabled"            # disabled | enabled（首夜建议 disabled）
  j0_enabled: true
  require_evidence_for_done: true

# ---------- 输入源（Phase 0） ----------
inputs:
  prd_path: ""                            # PRD 文档路径
  api_doc_path: ""                        # API 文档路径
  prototype:
    type: "dir"                           # dir | url
    path_or_url: ""
    login_required: false
    login_ready: false                    # 需登录时人类确认
  design_tokens_path: "src/styles/tokens/"
  notes: ""

# ---------- 环境自检记录（启动前人工/脚本填写） ----------
env_preflight:
  dev_server:
    port: 9001
    must_listen: true
    checked: false
    ok: false
  proxy:
    health_url: "http://127.0.0.1:9998/health"
    checked: false
    ok: false
  playwright_smoke:
    checked: false
    ok: false
  chrome_devtools_smoke:
    checked: false
    ok: false
  git_clean:
    checked: false
    ok: false
  all_green: false                        # 全 true 才允许启动

# ---------- 路由预生成（Phase 0 人类确认） ----------
phase0_scaffold:
  router_paths_committed: false           # src/router/paths.ts
  router_index_committed: false           # src/router/index.tsx
  page_shells_committed: false            # src/pages/{domain}/index.tsx 空壳
  menu_items_committed: false
  commit_sha: ""                          # 预生成提交 SHA（可与 base_sha 相同）

# ---------- 预授权 / 拒绝清单 ----------
pre_authorized:
  - "pnpm dev --port 9001 重启（仅当 9001 无监听且日志显示崩溃）"
  # 首夜不要放 pnpm add；patch_b 禁用

deny:
  - "src/styles/tokens/**"
  - "src/components/shared/**"
  - "src/router/**"
  - "src/auth/**"
  - "package.json"
  - "pnpm-lock.yaml"
  - ".env"
  - ".env.*"

# ---------- 预算 ----------
budgets:
  per_page_calls: 20
  fix_rounds: 4
  visual_rounds: 3
  page_wall_clock_min: 90
  night_wall_clock_min: 600
  kimi_calls_total: 0                     # 首夜建议 0

# ---------- 门禁开关 ----------
gates:
  C0_input: true
  C1_scope: true
  C2_code: true                           # typecheck / lint / build
  C3_architecture: true                   # c7-check
  C4_function: true
  C5_interaction: true
  C6_visual: true
  C7_evidence: true
  C8_archive: true
  scripts:
    c7_check: "scripts/c7-check.sh"
    scope_check: "scripts/scope-check.sh"
    evidence_check: "scripts/evidence-check.sh"

# ---------- 页面清单（首夜 ≤3） ----------
# status 仅允许:
#   READY_FOR_NIGHT | NIGHT_CANDIDATE_WITH_E2E | EXCLUDED
pages:
  - id: "FE-example"
    domain: "example"                     # → src/pages/example/**
    title: ""
    status: "EXCLUDED"                    # 就绪后改 READY_FOR_NIGHT
    priority: 1
    L: "L1"                               # L0|L1|L2|L3
    V: "V1"                               # V0|V1|V2|V3
    risk_notes: "write_ops_via_mock"      # 可选标注
    files_allowed:
      - "src/pages/example/**"
    # 可选：测试与产物相对路径
    paths:
      task_dir: ".omc/task/{YYYY-MM-DD}/FE-example/"
      spec: "tests/e2e/example.spec.ts"   # 按仓库实际改
      screenshots_dir: ".omc/screenshots/FE-example/"
    inputs:
      prd_section: ""
      api_refs: []                        # 例: ["GET /api/x", "POST /api/x"]
      prototype_refs: []                  # 关键截图/画板
    ac_count: 0
    ac_preliminary: []                    # 可选，plan 冻结前草稿
      # - id: AC-01
      #   text: ""
      #   type: functional|interaction|visual
    e2e_min_required:
      - success
      - empty
      - loading
      - business_error
      - network_error
      - double_submit
      - modal_close_rollback
    exit_criteria:
      must_pass_gates: ["C1", "C2", "C3", "C4", "C5", "C7"]
      visual_required: true
    branch_name: "draft/fe-example-{YYYY-MM-DD}"
    draft_pr_required: true

  # - id: "FE-xxx"
  #   domain: "xxx"
  #   ...

# ---------- J0 规则摘要（执行侧无裁决者） ----------
j0:
  on_prd_api_conflict: "BLOCKED_INPUT"
  on_architecture_ambiguity: "MIN_RISK_PATH + assumptions.yaml + morning_review"
  on_constitution_gap: "MIN_RISK_PATH + BLOCKED_HUMAN_if_irreversible"
  on_root_cause_judgement: "RECORD_ONLY"  # error-dna / failure.json，早晨人看
  on_shared_or_token_change: "BLOCKED_SCOPE"
  min_risk_priority:
    - reuse_existing_page_pattern
    - no_touch_shared_tokens_router_auth
    - no_new_dependency
    - single_page_rollback
    - no_global_interaction_semantic_change
    - no_cross_page_store_unless_planned

# ---------- 阻塞码（只允许下列枚举） ----------
blocked_codes:
  - BLOCKED_INPUT
  - BLOCKED_SCOPE
  - BLOCKED_ENV
  - BLOCKED_BUDGET
  - BLOCKED_HUMAN
  - BLOCKED_VISUAL_P0
  - DONE_WITH_ASSUMPTIONS

# ---------- 页级 / 夜级熔断 ----------
circuit_breakers:
  page:
    - same_failure_fingerprint_x2_without_change
    - exceed_per_page_calls
    - exceed_fix_rounds
    - exceed_page_wall_clock
    - out_of_files_allowed_x2
    - d2_input_gap
  night:
    - dev_server_restart_failed
    - three_pages_same_env_blocked
    - git_state_corrupted
    - unauthorized_deny_path_touch

# ---------- shared gap 腐蚀熔断 ----------
shared_gap_policy:
  registry_path: ".omc/night/{YYYY-MM-DD}/shared-gap-registry.yaml"
  max_local_workarounds_per_gap: 2
  on_exceed: "BLOCKED_SCOPE"

# ---------- 早晨交付物 ----------
morning_outputs:
  - "lx-goal report / 退出总报告"
  - "每页 acceptance_report.md"
  - "Draft PR 列表"
  - "阻塞码聚合清单"
  - "assumptions 清单"
  - "成本与调用统计"

# ---------- 人类确认 ----------
human_signoff:
  phase0_complete: false
  go_nogo: "NO_GO"                        # NO_GO | CONDITIONAL_GO | GO
  reviewer_morning: ""
  signed_at: ""
  notes: ""
```

---

## 2. `acceptance_report.md` 空模板

> 放在：`.omc/task/{YYYY-MM-DD}/FE-{domain}/state/acceptance_report.md`  
> 原则：**无 evidence 的 AC ≠ pass；无 SHA 的截图作废**

```markdown
# Acceptance Report · FE-{domain}

> schema: v1.1  
> task_id: `FE-{domain}`  
> run_id: `FE-NIGHT-{YYYY-MM-DD}`  
> 生成阶段: verify / archive  
> 规则: 完成 = 证据完成，不是步骤走完

---

## 0. 元信息

| 字段 | 值 |
|------|----|
| domain | `{domain}` |
| page_title | |
| branch | `draft/fe-{domain}-{YYYY-MM-DD}` |
| base_sha | |
| head_sha | |
| commit_shas（原子提交列表） | |
| draft_pr_url | |
| implementer_model | DeepSeek V4 Pro |
| fixer_model | DeepSeek V4 Flash |
| kimi_used | no / yes（次数: 0） |
| started_at | |
| finished_at | |
| wall_clock_min | |
| model_calls_total | |
| fix_rounds_used | |
| final_status | `DONE` / `DONE_WITH_ASSUMPTIONS` / `BLOCKED_*` / `NOT_STARTED` |

最终阻塞码（仅一个主码，可附次码）：

```text
primary_code: null
secondary_codes: []
```

---

## 1. 范围声明

### 1.1 files_allowed
```text
src/pages/{domain}/**
```

### 1.2 files_touched
```text
# git diff --name-only {base_sha}...{head_sha}
```

### 1.3 deny 区确认（必须全 clean）

| 路径 | 是否触碰 | 证据 |
|------|----------|------|
| src/styles/tokens/** | no | |
| src/components/shared/** | no | |
| src/router/** | no | |
| src/auth/** | no | |
| package.json | no | |

`files_denied_confirmed_clean`: `true|false`

### 1.4 越界处理记录
- 是否发生越界: `no|yes`
- 处理: `n/a|reverted|circuit_break`
- 说明:

---

## 2. 输入快照

| 类型 | 路径/引用 | 是否完整 |
|------|-----------|----------|
| PRD | | yes/no |
| API | | yes/no |
| 原型 | | yes/no |
| 关键态截图（空/加载/错误/弹窗等） | | yes/no/na |

D2 冲突: `none|见 open-questions.md`

---

## 3. Gate 总表（C1–C8）

| Gate | 结果 | 命令/脚本 | 日志或摘要路径 | 备注 |
|------|------|-----------|----------------|------|
| C1 范围 | PASS/FAIL/SKIP | `bash scripts/scope-check.sh` | | |
| C2 代码 | PASS/FAIL/SKIP | `pnpm typecheck && pnpm lint && pnpm build` | | |
| C3 架构/C7红