# Grok 4.5 裁决（反模式 / 攻击面）

> 角色：委员会攻击面审判。  
> 对象：`13-headless-lightweight-actions.md`（Design Doc 13）与前置的「单进程 launcher」讨论。  
> 结论：**Doc 13 整包否决；任何「按模式分叉治理」路径一律作废；在 P0 数据补齐前，不批准第二阶段施工。**

---

## ① 目标与不变式

### 目标
从**绕过路径**审查轻量化方案：是否引入自我豁免、证据链断裂、双规则语义、伪契约。只允许「同一套规则跑得更快」，禁止「弱规则另一侧」。

### 哲学自检
- 服务：`the less,the more`（路径唯一）> `验证`（证据门禁）> `守护`（不可自我降权）
- Doc 13 用「增益」压过前述三项 → **冲突时自动作废**（computed, not negotiated）。

### 不变式（攻击面红线）
1. **单一治理语义**：交互 / `claude -p` 不得走两套 gate 集。  
2. **被治理对象不可配置治理强度**：AI 可控 env / 文件 / 开关不得打出弱模式。  
3. **证据链不可按模式稀疏化**：PASS 可缓冲写，不可丢行、不可只留摘要。  
4. **契约强度必须名实相符**：WARN 不得被说成强制门禁。  
5. **不新增机制掩盖旧机制未完成**：僵尸的接线/删除二选一，禁止叠「headless 层」。  
6. **不因性能承诺而扩大 blast radius**：`runpy` 同进程可议，但不得静默吞掉 crash 隔离语义。

---

## 一、对 Design Doc 13 的攻击面画像

文档核心策略（证据：`13-headless-lightweight-actions.md` §2.1）：

1. headless 检测后跳过非契约强制 gate  
2. 合并 hook 进程  
3. 降低审计频率  

### A1. 反模式：「模式分叉 = 第二条法」

只要存在 headless 降级矩阵，攻击面就固定为：

> **让系统相信自己在弱侧。**

这不是实现 bug，是**结构**。检测再准也不能消掉「第二套法」的存在。满足 `the less,the more` 的解法只有：**同一路径提速**，不是「少跑 gate」。

Doc 用「少即是多 = 降冗余 gate」自我正名（§3.1）——这是**标签盗用**。少即是多指机制层收敛，不是治理覆盖收敛。

### A2. 致命误用：`sys.stdin.isatty()` 当安全信号

Hook stdin 是事件 JSON 管道。交互会话同样大概率 **非 TTY**。结果不是偶发误判，而是：

- 检测函数默认恒真 → **全局降级**  
- 交互模式零改动的承诺（§3.1）在结构上无法成立  

把恒定信号当身份凭证 = **死信号认证**，经典反模式。

### A3. 自我豁免开关：`CARROROS_FORCE_HEADLESS=1`

被治理对象能跑 Bash，就能：

```bash
export CARROROS_FORCE_HEADLESS=1
```

之后整条 hook 链继承弱治理。项目**已经**知道 env 污染风险：`run-regression.sh` 注释写明 `temp-bypass.json` 存在时全部门禁降级 BYPASS_ALLOW；launcher 侧也有对 `NIGHT_DENY_ROOT` 的 pop 处理经历。再引入一个**故意不 pop 的官方弱化开关**，等于把 `governance-bypass` 想防的东西产品化。

`CARROROS_FORCE_INTERACTIVE=1` 兜底（§3.2）只能由人类设；AI 没有动机设它。攻防不对称：**降权开关对攻击者有用，升权开关对攻击者无用**。

### A4. 「契约强制 gate」是纸盾

Doc 称降级后仍保留 gate-contract 强制 gate。但现役缺失/契约路径是 **WARN 语义**（前面委员会已指出：`missing_gate: WARN`，helpers 记录 `contract_warning` 后继续）。  
用 WARN 担保「强制」= **合规剧场（compliance theater）**。

在 contract 先改成 fail-closed 之前，**任何**「跳过非强制 gate」方案的安全论证都不成立。

### A5. 审计降频 = 自废证据门禁

§2.1 / §3.2：headless 下 PASS 只聚合、降频。

CarrorOS 门禁哲学是 **证据可机械回放**。PASS 摘要化后无法证明：

- 哪些 gate 实际跑过  
- 顺序是否被改写  
- 是否被中途短路  

攻击者目标经常是「让危险动作看起来像正常 PASS 噪声」。只全记 BLOCK/REDIRECT、稀疏化 PASS，正好符合「少留成功轨迹」的掩护策略。  
**缓冲写 + 退出 flush（行不丢）** 可接受；**降频丢行** 否决。

### A6. 根因与药方错位（打错靶也会开洞）

将 240s / exit 124 主要归因为 spawn + 审计 IO，却未给出：

- 每任务 tool call 次数  
- 单次 hook 链 wall-time  
- transcript 是否 AskUserQuestion 空转  

若真实根因是 headless 下「必须提问 → 无法提问 → 重试至超时」，则：

- 跳 gate：不修环，甚至减少中途拦截 → **更快撞墙或更危险地「成功」**  
- 降审计：丢失诊断超时所需的事件密度  

未证伪死循环假说前动刀 = **在错误故障树上切开安全控件**。

### A7. 违反工作约束 4

「不新增机制解决旧机制未完成」。  
现役已有 bypass / goal 状态、contract WARN、launcher 双进程等未收敛问题；再叠 headless 检测 + 降级矩阵 + 强制 env，是**层叠**，不是收敛。

**裁决：Design Doc 13 = 结构否决，不进入施工，不修修补补保留降级矩阵。**

---

## 二、对「单进程 runpy launcher」的攻击面意见

方向（同构、不改 gate 集、不改 settings matcher）**可继续谈**，但是**有条件放行**，不是无脑首刀。

### 收益方向（非安全反对）
launcher → 子 Python 是确定的冗余层；消除第二解释器减少冷启动，**不改变治理路径语义**，符合路径唯一。

### 新风险（必须写入不变式）

| 风险 | 攻击/失效模式 | 要求 |
|------|----------------|------|
| 同进程隔离丢失 | hook 调 `os._exit`、装信号、改全局 `sys.modules` / `cwd` | 捕获面不得只写 `SystemExit`；要明确禁区或恢复点 |
| 失败语义漂移 | 原子进程死变为 launcher 内异常；stdout 半句 JSON | 必须保持「非 0 且无 stdout → continue JSON」的现语义 |
| 静默合并诱惑 | 将来有人再把多 hook 同进程串联 | **本阶段不变式：launcher 一次仍只跑一个 hook 名** |
| 伪达标 | 以为省一半 spawn 就能过认证门槛 | 无 tool-call 次数与 wall-time 数据不得宣称达标 |

零设计空间要求：若做 launcher 改动，必须有：

1. 静态验收：不再出现 `[sys.executable, hook_path]`  
2. 行为验收： critical 缺失仍 exit 2；crash 仍 continue JSON  
3. **禁止**夹带 headless / gate 删除 / 审计降频  

未补隔离与 P0 测量前，**我撤销对「立即全量施工 runpy 补丁」的无条件背书**；可保留为「同构加速侯选 A」，但排序应低于测量与 contract 钉死。

---

## 三、Grok 视角：允许的唯一主线

```text
主线：同一套 gate + 同一套审计语义 → 只减解释器/重复 IO 成本
禁止支线：检测 headless / 跳 gate / 稀疏 PASS / 官方 FORCE_HEADLESS
```

**同构提速候选（攻击面可接受的上限）**  
1. **测量先行（零代码或只读命令）** — 必先  
2. launcher 单进程（侯选，有隔离约束）  
3. 重 import 惰性化（若 import 树证明昂贵）  
4. 审计内存缓冲 + 进程退出 flush（**零丢行**）  
5. 独立议题：`gate-contract` WARN → fail-closed（这是守护加固，不是性能借口）

**明确开出漏洞的「优化」**  
- `_is_headless()` 任何实现  
- 按模式裁剪 `L1_GATES` / `GATES`  
- PASS 聚合替代逐条 evidence  
- 靠 env 在运行时切换治理强度  

---

## 四、我缺的信息（约束 0：先采集再出施工六段式）

与 Opus 队列对齐，并加上攻击面特需项。

### P0（决定打哪棵故障树；缺则拒出大改施工单）

| ID | 要什么 | 为什么（攻击面/反模式） | 建议你跑的只读命令 |
|----|--------|------------------------|-------------------|
| **G-P0-1** | 两个 exit 124 任务 transcript **最后 40 条**（含 tool 名与 blocked/additionalContext） | 证伪 AskUserQuestion 死循环；若成立，任何降 gate 都是错药 | 指向该次 session 的 transcript / hook-evidence 尾部即可 |
| **G-P0-2** | 每任务 **工具调用次数** + hook 链占用 wall-time 占比 | 没有乘法因子就无法证明「省 spawn」有意义，也不能排除「优化剧场」 | 按 session 聚合 audit / hook-evidence |
| **G-P0-3** | `_append_audit` / `_record_gate_decision` 是否 **每行 open+fsync**；`.omc/state` 是否同步盘 | 「审计 IO 主因」数量级必须可证伪，否则 Doc 叙事是伪装 | `helpers.py` 相关函数全文 + `df`/`mount` 看state路径 |
| **G-P0-4** | 交互会话里 hook 收到事件时 **`stdin.isatty()` 实测** | 一锤钉死死信号；无需争论 | 临时在 launcher 打一行 stderr 只读探测（人类授权下），或用已知管道行为说明 |
| **G-P0-5** | A/B 时是否存在 `temp-bypass.json` / `autonomous.active` / `lx-goal.json` | 活体 bypass/goal 会污染对比基线（`run-regression.sh` 注释已定义这三种污染） | 检查当时 state；对照回归脚本的 stash 语义 |

### P1（只影响施工 diff 精度）

- `settings.json` **hooks 全段**（每个 matcher 的 command 数 → 真实进程上界）  
- `pretool-gate.py` 完整 `L1_GATES` / `GATES` 与短路顺序  
- `helpers.py` import 与 contract_warning 分支全文  
- `gate-contract.yaml` 全文（要上 fail-closed 必须原文）  
- `kernel.md` 冻结原文（人类独占边界）  
- `python3 -c pass` 冷启动中位数 ×20  
- `claude -p` 完整命令行（240s 是外部 timeout 还是 turns）

### 格式诚实声明
我侧检索块**无稳定行号**。后续六段式会用 `文件 + 符号/段落`；整合器落盘前用 `grep -n` 回填，**禁止编造行号冒充证据**。

---

## 五、阶段门控（你现在可以做什么）

### 现在立即（人类）
1. **轮换**已随 `settings.json` 外发的 API token；仓库内删除明文；改环境注入。  
2. **不要**批准 Doc 13 任何 diff。  
3. 回传 **G-P0-1 … G-P0-5** 的输出（可打码隐私，保留 tool 名与 gate 决策字段）。

### 我（Grok）在 P0 回来后的交付
- 若死循环假说成立 → 单独六段式：**高风险分支在无交互能力时确定性 BLOCK/REDIRECT**，不碰性能降级。  
- 若 spawn 确占数十秒量级 → 六段式：**仅 launcher 同构加速**（含隔离与机械验收），零 headless。  
- 若审计 fsync+同步盘成立 → 六段式：**缓冲+退出 flush，零丢行**。  
- contract 钉死 WARN→ERROR 作为**独立**守护方案，不与性能捆绑蒙混。

### 在信息齐之前
**本回合不产出可施工大补丁六段式**（避免零设计空间里夹带未证实根因）。  
本回合产出的是：**否定 Doc 13 的攻击面裁决 + 信息门禁清单 + 唯一允许主线**。

---

## 六、禁止事项（给整合器 / 施工模型）

1. 禁止落地 `_is_headless` / `isatty` 模式分支。  
2. 禁止 `CARROROS_FORCE_HEADLESS` / 任何 AI 可设的弱治理开关。  
3. 禁止按 headless 删除或跳过现役 L1/L2 gate。  
4. 禁止 PASS 审计降频或摘要替代逐条 evidence。  
5. 禁止把 `missing_gate: WARN` 写成强制安全网。  
6. 禁止在同一 PR 混装：launcher 提速 + gate 裁剪 + 审计策略。  
7. 禁止用「测试以后再补」绕过机械验收。  
8. 禁止复述或提交明文 token。  
9. 禁止把 goal/bypass 污染下的 A/B 当作干净基线。  
10. 缺 G-P0 数据时禁止宣称「已达认证耗时门槛」。

---

**一句话给人类：**  
Doc 13 不是「实现不精」，是**把可绕过的第二套法**写进了内核；这在攻击面审查下不可修补，只能换主线——**先测量、后同构加速，永不模式降权。**  

把 G-P0 五条结果甩回来，我出可 `git apply` 的下一份六段式。