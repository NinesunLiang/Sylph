# GPT-5.6 Sol 视角：先做“实现真实性审计”，信息齐后再出正式评审

收到。当前我**先不下通过率、成熟度或 Go/No-Go 结论**，也不直接给重构方案。

我的评审视角会与前两位有所区别：

- **Grok**：偏 Token、Goal 状态机、长航时编排。
- **Opus**：偏约束、防作弊、补丁契约、证据门禁。
- **Sol**：重点检查这些模块是否在**真实运行路径中形成闭环**，而不是“类和配置都存在，但没有被调用”；同时评估无人 UI 还原的**观测—诊断—修改—验证—回滚—继续搜索**是否真的可执行。

当前技术路线维持不变：

```text
DeepSeek V4 Flash：主执行、任务规划、代码补丁、普通诊断
Kimi K3：视觉歧义判断、复杂遮挡/层级/区域语义辅助
确定性工具：截图、DOM/style probe、区域度量、Token 审计、Gate、Git/worktree
```

---

# 一、基于当前材料，可以确认的部分

目前给出的实施版已经覆盖了相当完整的**设计面**：

- `orchestrator.py`：Goal 编排入口
- `domain.py`：领域对象与状态
- `task_generator.py`：评分结果到任务的转换
- `scorer.py`：UIF 评分
- `convergence.py`：停滞、震荡与收敛
- `model_router.py`：Flash/Kimi 路由与视觉预算
- `token_bootstrap.py`、`token_refine.py`：Token 冷启动和提议
- `config.py`、`goal-manifest.template.yaml`：运行配置
- `night-loop.md`、`SOP.md`、`phase0-checklist.md`：控制面协议
- `scope_check.py`、`c7_check.py`、`evidence_check.py`
- `gate-contract.yaml`、`finalize_page.py`
- `run_all.py`：已有门禁和绕过攻击测试

这意味着 Opus 上一轮提出的“M2 门禁脚本可能不存在”，从当前知识库范围看，至少不能再按“缺失”判断：

```text
scope_check.py     已存在
c7_check.py        已存在
evidence_check.py  已存在
gate-contract.yaml 已存在
finalize_page.py   已存在
run_all.py         已存在攻击/绕过测试
```

但“文件存在”不等于“新 Goal Runner 的每条 accept 路径都强制经过它们”。  
这正是我下一阶段要核实的核心。

---

# 二、Sol 正式评审会检查的 8 条真实闭环

## 1. 编排闭环

检查真实调用链是否是：

```text
manifest
  → preflight/signoff/lock
  → orchestrator
  → scorer
  → task_generator
  → model_router
  → patch/apply
  → scope/build/c7/evidence/interaction
  → rescore
  → accept/revert
  → checkpoint
  → next iteration
```

重点不是有没有这些模块，而是：

- 谁调用谁？
- 调用失败是否 fail-closed？
- 是否存在旁路 accept？
- 是否仍有“修改一次就进入下一页”的早退路径？
- 恢复后是否从正确状态继续，而不是重新初始化评分历史？

---

## 2. 观测闭环

无人 UI 还原首先要有可靠观测。我会检查：

- 原型如何采集？
- actual 如何采集？
- 页面如何确定已经稳定？
- 动画、字体、图片、异步数据、Skeleton 是否被控制？
- viewport、DPR、浏览器、缩放、字体环境是否固定？
- Region bbox 来自 DOM、标注还是视觉推断？
- Portal、Modal、Popover、Dropdown 是否进入截图坐标系？
- 页面中间态与滚动到底状态如何采样？

如果观测本身不稳定，后面的 UIF 分数、模型诊断和收敛判断都不可信。

---

## 3. 评分闭环

我会逐维审查 `scorer.py`，重点不是“有 D1–D7 字段”，而是：

- 每一维是否有真实输入？
- 缺少输入时返回 `UNKNOWN/BLOCKED`，还是错误地给默认高分？
- 权重归一化是否正确？
- Region 与 State 如何聚合？
- 某个 Region 缺金标时是否被静默排除？
- D7 是否真由 assertion 执行结果计算？
- D6 是否真由源码 diff 与 Token index 计算？
- 0.94 交互封顶是否在最终合成层强制执行？
- 0.99 是否会被四舍五入或显示精度误判？
- 新旧分数是否在相同 viewport、state、mask 下计算？

我尤其关注三个反模式：

```text
missing evidence → 0 或 1
no assertions → 100% coverage
no regions → page score 默认通过
```

正确语义应该是：

```text
missing required evidence → BLOCKED / INCOMPLETE
empty required assertion set → Phase0 配置错误
empty required region set → NO-GO
```

---

## 4. 修改闭环

我会检查 DeepSeek V4 Flash 生成的到底是什么：

- 完整文件？
- unified diff？
- 结构化 patch？
- shell 命令？
- 自由文本后再由程序抽取？
- 是否在隔离 worktree 中应用？
- apply 失败后是否污染主工作树？
- reject 后是否一定回滚？
- accept 后 Git SHA 是否进入 checkpoint？

这里不预设必须使用 `ui-patch/2`。  
如果实施版已有另一套可靠契约，我会评估它，而不是为了和前案同名再造一套。

真正的最低要求是：

```text
可解析
可限域
可预检
可原子应用
可回滚
可哈希去重
可追踪到 evidence 和 score delta
```

---

## 5. 收敛闭环

我会重点审查 `convergence.py` 与 orchestrator 的组合语义：

- “收敛”是达到目标，还是只是最近几轮变化小？
- 平台期是否被误判成完成？
- 同一 patch、等价 patch、数字振荡如何识别？
- Job、Region、Page、Run 四层分别有什么 retry budget？
- REDIRECT×3 后是换策略、换区域、换页，还是结束整个 Goal？
- 被 BLOCK 的方向如何设置 TTL？
- checkpoint 恢复后 retry/redirect 计数是否保留？
- 无可执行任务时，是配置错误、证据不足，还是目标达成？

必须严格区分：

```text
GOAL_MET
STAGNATED
BLOCKED
EVIDENCE_MISSING
BUDGET_EXHAUSTED
AWAITING_HUMAN
CONFIG_INVALID
```

任何状态都不能被模糊映射成“完成”。

---

## 6. Token 闭环

我会沿着以下链路审查：

```text
原型/金标
 → token_bootstrap
 → candidate/source
 → 人工签署
 → codegen
 → token-index
 → Tailwind/AntD/CSS Variables
 → Worker 消费
 → D6 评分
 → c7_check
 → ProposeToken
 → 晨收
```

需要确认：

- Bootstrap 产物是否真能进入三端主题；
- source、generated、index 的 SSOT 关系；
- hash 覆盖哪些文件；
- `token_refine.py` 是只提案，还是可能直接改 source；
- D6 衡量的是“使用了 CSS var”，还是“使用了正确语义 Token”；
- Tailwind class 是否能反查 Token；
- AntD `ConfigProvider` token 是否进入命中率；
- 动态值、媒体查询、calc、百分比等是否有合理白名单。

单纯检查 `var(--ds-*)` 不足以证明 Token 正确。例如：

```css
color: var(--ds-color-bg-page);
```

虽然“使用了 Token”，但把背景 Token 用作文字颜色仍然是错误的。  
正式评审会区分：

1. **Syntax alignment**：是否使用 Token；
2. **Semantic alignment**：使用的 Token 语义是否正确；
3. **Prototype alignment**：最终表现是否接近金标。

---

## 7. 模型路由闭环

当前 Flash 主执行、Kimi 视觉辅助的方向合理，但要检查：

- 什么条件触发 Kimi？
- 是否先使用确定性工具，再升级视觉模型？
- Kimi 输出是裁定、诊断，还是直接修改代码？
- Kimi 的结论是否会被评分器验证？
- 同一视觉争议是否反复升级，烧穿预算？
- 超出 cap 后是否降级，而不是默认通过？
- 模型请求失败、超时、返回非 JSON 时如何处理？
- 视觉输入是否只裁切目标 Region，还是每次发送整页大图？
- 是否记录 prompt/version/model/usage/why_escalated？

推荐职责边界仍应是：

```text
确定性工具：测量、比较、验收
Kimi K3：解释复杂视觉差异
DeepSeek V4 Flash：根据证据生成最小修改
Gate：决定是否接受
```

模型不能既出题、又改题、再给自己打分。

---

## 8. CarrorOS 控制面闭环

当前材料显示已有较强的防绕过能力，包括动态路径拼接、删 marker、改 Hook、改 Gate 等攻击测试。正式评审会确认新 UI Goal Runner 是否真正处于这套控制面内：

- 启动前是否验证 signoff？
- `control_plane_lock` 是否覆盖新增 Python 模块？
- 夜间 marker 是否由 runner 正确创建和销毁？
- 子进程是否继承 night session 环境？
- 模型生成的 Python/shell 是否可能动态拼接绕过不可变路径？
- `scope_check.py` 是只检查 Git diff，还是也检查未跟踪文件？
- Finalize 是否调用 `evidence_check.py`？
- Gate envelope 缺失时是否 fail-closed？
- `finalize_page.py` 是否存在直接参数绕过？
- Goal Runner 是否能绕过 `run_all.py` 已测试的 Hook 路径？

---

# 三、当前最需要补齐的信息

下面不是要求重复上传所有文件，而是希望补齐**能证明实际运行路径**的材料。

## P0：没有这些，不能给最终评审

### S1. 实际仓库目录树

请提供实施代码所在目录的树形结构，建议：

```bash
tree -a -L 4 <实施目录>
```

或者至少给出：

```text
orchestrator.py 所在完整路径
scorer.py 所在完整路径
worker/apply/patch 相关文件
Playwright/截图/assertion 相关文件
token codegen 相关文件
artifacts 样例目录
```

原因：目前能看到文件集合，但看不到真实包边界、入口和是否还有未提供模块。

---

### S2. 真正启动命令与入口

请明确：

```text
短 dry-run 如何启动？
6h Goal 如何启动？
恢复 checkpoint 如何启动？
```

例如：

```bash
python -m scripts.ui_autopilot.orchestrator --manifest ...
```

还是：

```bash
python run_all.py ...
```

或者由 `/lx-goal` 间接启动。

必须确认唯一权威入口，避免文档链与运行链不一致。

---

### S3. 一次最小 dry-run 的完整 artifacts

这是最重要的材料。请提供一个**哪怕失败也可以**的单页短跑结果：

```text
manifest 快照
run 日志
初始 scoreboard
至少一个生成任务
模型原始响应
实际 diff/patch
gate envelopes
新 scoreboard
patch decision
checkpoint
finalize 或 morning report
```

优先打包：

```text
artifacts/goal/<run_id>/
```

有真实运行产物后，才能判断系统是“实现”还是“框架骨架”。

---

### S4. 修改和应用实现

请补充负责以下职责的文件：

```text
调用 DeepSeek V4 Flash
解析模型响应
应用代码修改
建立/使用 worktree
reject 回滚
accept/commit
```

如果都在 `orchestrator.py` 内，请指出对应函数名；如果有独立 Worker/Executor，请补文件。

这是当前最大的不确定点。

---

### S5. 截图与交互执行实现

请补充：

- Playwright runner；
- reference/actual capture；
- 页面稳定化；
- Region 定位；
- assertion catalog 或断言来源；
- Modal/Popover/Hover/Scroll 的执行器；
- 输出 assertion evidence 的代码。

如果当前尚未实现，请直接标“未实现”，无需补占位文件。

---

## P1：影响评分与 Token 结论

### S6. `scorer.py` 的真实输入样例

请给一份实际 scorer 输入和输出，例如：

```json
{
  "page_id": "...",
  "states": [],
  "regions": [],
  "assertions": [],
  "token_report": {}
}
```

以及对应 `scoreboard.json`。

特别需要看到：

- D1–D7 原始分；
- missing evidence；
- cap reason；
- hard gate；
- goal_met；
- Region/State 汇总。

---

### S7. Token 生成链

当前已有 `token_bootstrap.py` 和 `token_refine.py`，还需确认：

- 谁把 source 生成到 CSS/Tailwind/AntD？
- `token-index.json` 在哪里生成？
- 一份真实 source；
- 一份真实 generated；
- 一份真实 index；
- `token_set_hash` 的计算函数。

如果当前 Bootstrap 只生成候选报告，还没有前端 codegen，也请直接说明。

---

### S8. Manifest 完整实例，而不只是模板

请提供一个脱敏后的实际实例：

```text
goal-manifest.yaml
night-manifest.yaml
night-manifest.signoff.yaml
```

需要检查：

- page/state/region/assertion 的映射；
- edit scope；
- budgets；
- thresholds；
- model cap；
- immutable paths；
- token hash；
- signoff 与 lock。

---

## P2：用于生产级加固结论

### S9. 测试文件

除 `run_all.py` 外，希望看到实施模块的测试：

```text
test_orchestrator.py
test_scorer.py
test_convergence.py
test_task_generator.py
test_model_router.py
test_token_bootstrap.py
test_token_refine.py
```

尤其需要这些边界用例：

- assertions 空集；
- regions 空集；
- 分数 NaN；
- 模型非 JSON；
- patch apply 一半失败；
- Gate timeout；
- Kimi cap 耗尽；
- checkpoint 损坏；
- token hash 漂移；
- D1 上升但 D6 下降；
- interaction < 1 时总分封顶；
- REDIRECT×3 后继续下一 Region；
- 时墙结束后正常落盘。

---

### S10. 运行环境与样板应用

请确认：

```yaml
frontend:
  react:
  vite:
  antd:
  tailwind:
browser:
  chromium:
  viewport:
  device_scale_factor:
runtime:
  node:
  python:
models:
  flash_endpoint:
  kimi_endpoint:
  auth_mode:
```

不需要给密钥，只给版本和协议。

---

# 四、建议你最省事的补齐方式

不必逐个回答几十个问题，可以直接补以下四包：

## 包 A：运行链

```text
repo-tree.txt
entrypoint.txt
orchestrator.py
与 Worker/patch/apply/worktree 有关的全部文件
```

## 包 B：观测与评分链

```text
Playwright/capture/assertion 相关文件
scorer.py
一份 scorer 输入
一份 scoreboard 输出
一组 reference/actual/diff 示例
```

## 包 C：控制面和 Token 链

```text
scope_check.py
c7_check.py
evidence_check.py
finalize_page.py
gate-contract.yaml
token codegen/index/hash 相关文件
实际 manifest/signoff 脱敏实例
```

## 包 D：一次短跑产物

```text
artifacts/goal/<run_id>/ 整包
```

**如果只能先补一个，优先补包 D。**  
真实失败运行比更多设计文档更有评审价值。

---

# 五、我后续正式评审的输出结构

信息齐后，我会给出一份不重复前案的**实施审计报告**：

## A. 实际调用图

明确列出：

```text
哪些模块真在主路径
哪些模块存在但未接线
哪些 Gate 可被旁路
哪些文档声明与代码不一致
```

## B. 逐模块结论

对以下文件逐一给：

```text
职责是否单一
输入/输出契约
失败语义
状态持久化
幂等性
并发安全
安全边界
测试缺口
```

## C. 闭环断点清单

按严重性分：

- **P0：会导致错误 accept、夜间越权或虚假完成**
- **P1：会导致早退、震荡、分数失真或高成本**
- **P2：影响可维护性、可观测性和扩展性**

每项必须包含：

```text
证据文件/函数
触发条件
实际后果
最小修复
验收测试
```

## D. Flash + Kimi 路由评审

给出：

- 哪些任务必须规则化；
- 哪些由 Flash；
- 哪些允许升级 Kimi；
- Kimi 是否只能诊断；
- cap、缓存、去重和降级策略。

## E. 首个 Volume-0 验收方案

不是直接跑 6h，而是给一条可以证明闭环的最小路线：

```text
1 个页面
2 个状态
3 个 Region
至少 1 个 hover/overlay
至少 1 个 scroll-end
至少 2 次 accept
至少 1 次 reject+rollback
至少 1 次 checkpoint+resume
```

## F. 最终判决

只会落入以下之一：

```text
NO-GO：控制面或观测链不成立
CONDITIONAL-GO：允许短时 Volume-0，不允许 6h
GO-VOLUME-0：闭环成立，可做限定页面夜跑
GO-6H：长航时、恢复、预算、证据链均验证
```

---

# 六、当前临时结论

当前只能给出以下**非最终判断**：

> DeepSeek V4 Pro 实施版已经具备较完整的领域模型、编排、评分、Token 和模型路由骨架；CarrorOS 侧也已有 `scope_check`、`c7_check`、`evidence_check`、`finalize_page` 与绕过攻击测试基础。  
> 现在最大的未知不是“还缺哪些类”，而是：**主执行链是否真正把观测、补丁应用、C1–C3、交互断言、重评分、accept/revert、checkpoint 串成一个不可旁路的事务闭环。**

因此当前状态定为：

```text
评审状态：WAITING_FOR_RUNTIME_EVIDENCE
不是 NO-GO 判决
不是条件通过
更不是 GO-6H
```

请优先补 **一次最小 dry-run 的 artifacts（包 D）**，再补 **Worker/apply 与 Playwright/assertion 实现（包 A、B）**。收到后我再给完整 Sol 视角评审，不先猜测缺失，也不重复造已有门禁。