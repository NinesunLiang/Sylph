# Grok 4.5 第二轮联合审核裁决

> 角色：攻击面 / 反模式 / 证据诚实性审判  
> 对象：Design Doc 13 **V2** + `review-request.md` + `governance_cost_probe` 产物  
> 结论总览：**V1 否决项已正确吸收；根因方向基本成立；但测量诚实性有洞、支柱 C 必须防自我扩权、Doc 正文仍含 V1 僵尸、A 可条件放行但收益已降为次要。**

---

## ① 目标与不变式（本轮）

### 目标
在**不引入第二套治理法**的前提下，判断 V2 三支柱是否可进施工，以及根因修复会不会把「benchmark 可写」偷换成「运行时自我扩权」。

### 哲学链自检
| 支柱 | 服务环节 | 与更高项冲突？ |
|------|----------|----------------|
| A 同构提速 | 增益（在验证/守护不变时） | 无（gate 集/语义不变才合法） |
| B 成本透明 | 验证（可观测） | 无（只度量、不降权） |
| C 动态目录可写 | 增益 + 人本（任务能完成） | **有风险**：扩写权若可被 agent 影响 → 冲击 `守护` |

冲突裁决：`守护` > `增益`。C 只允许**人类预置/人类批准的路径模板**，禁止运行时由模型改写 allowlist。

### 本轮红线不变式
1. 单一治理语义（继续禁止 headless 分叉）——V2 已遵守 ✅  
2. 证据链零丢行 ——V2 缓冲 flush 方向 ✅  
3. **磁盘状态为唯一真相**：transcript 声称落盘 ≠ meta `created_files` 有文件 → 测量未闭合  
4. **权限扩面人类独占**：不可变成 AI 可触发的 soft-bypass  
5. 僵尸机制二选一：Doc 13 正文 V1 段必须删除或整章替换，不许「顶上否决、底下仍教人降级」  

---

## 二、对 P0 根因叙述的采信程度

### 2.1 我采信的部分（有盘证）

| 断言 | 证据 | 采信 |
|------|------|------|
| 审计/单链 gate 非 240s 主因 | review：20-gate wall **1.97ms**；无 fsync + 本地盘 | **高** — 关闭第一轮「IO 主因」 |
| 冷启动 alone 不够解释 240s | 14ms×5≈70ms/调用；×100≈7s | **高** — A 降为次要摩擦，不是主药 |
| ON 会话在写通道上失败并停 | ON `meta.json`：86.0s / exit 0 / `created_files: []`；transcript：Write×3、heredoc、tee 全拦，求人类授权 | **高** — 权限/harness 阻塞是真实现象 |
| ASK_USER 死循环在该探测场景不成立 | 13.2s 收敛、无 ASK_USER 审计 | **中高** — 证伪「该场景」；不证明一切 headless 任务永无空转 |

### 2.2 必须降权的部分（证据不闭合）

**PERM 声称成功落盘，但磁盘计数为空：**

```text
PERM meta: created_files: [] , elapsed 45.9s, exit 0
PERM transcript: 称 data_check.py / test_data_check.py 已写、pytest PASS
```

CarrorOS 核心是 **磁盘唯一真相**。  
`transcript` 成功叙事 + `created_files: []` = **测量未通过证据门**。可能原因：

- 写入落在 work 外 / 被过滤规则误伤  
- 进程结束前文件消失  
- 经典 claim 无源（agent 用 `Bash(python3 *)` 通道「好像写了」）  
- probe 的 `rglob` 与真实 cwd 不一致  

在复跑并 `ls` 出两个文件（或修 probe）之前：  
**「PERM 45.9s 成功落盘 vs ON 86s 权限墙」只可当作强假说，不可当最终根因铁证。**

### 2.3 根因归因的精确化（攻击面措辞）

ON transcript 用语是 *「haven't granted it yet」* / *Output redirection blocked* ——这是 **Claude Code harness / `settings.local.json` 权限层**，不是 CarrorOS `pretool-gate` 的 BLOCK JSON 语义。

因此更准确的命题是：

> **index13 / probe 的 ON 慢超时，很大一块是「把完整治理拷进临时 work，但权限白名单仍是主仓写死路径」→ 任务目录不可写 → agent  thrash（587 gate_decision 量级）+ 等人授口。**  
> 这首先是 **A/B 与 probe 装置失效（外部权限配置未随 work 动态化）**，其次才是报表上的「治理贵」。

它**解释**虚假「治理统一过重」；它**不证明**「生产交互也必须放开写」。  
二者必须切开，否则 C 会从「修 benchmark」滑成「拆守护」。

### 2.4 与第一轮假说的关系

| 第一轮 | 本轮 | Grok 处置 |
|--------|------|-----------|
| 审计 IO 主因 | 已否 | 关闭 |
| spawn 主因 | 次要（~7s/100 calls） | 降级为卫生项 |
| AskUserQuestion 死循环 | 本探测证伪 | 降为残留风险，不主驱动 |
| （新）权限白名单 vs 动态 work | 主叙事 | **条件采信**，先补 PERM 盘证 |

---

## 三、五问逐条裁决

### Q1. 同构提速三件套可否批准施工？runpy 隔离怎么满足？

**裁决：有条件批准 A，且降级为「卫生 / 减摩擦」，不再宣传为认证门槛特效药。**

| 件 | 裁决 | 条件 |
|----|------|------|
| 单进程 launcher（runpy） | ✅ 条件可施工 | 见下隔离契约；**单独 PR**；零 headless、零改 gate 集、零改 settings matcher |
| 惰性 import | ⚠️ 可查再改 | 先 `python -X importtime` 或等价证明 yaml 等是成本；禁止无证据大搬 import |
| 缓冲写 + 退出 flush | ✅ 条件可施工 | **零丢行、零改字段语义**；进程正常/异常路径都要 flush 或等价不丢；独立测 crash 半写 |

**runpy 隔离契约（满足第一轮 Grok 投诉的最低集）：**

1. **一次 launcher 仍只跑一个 hook 名**（禁止顺手合并多 hook 同进程）。  
2. 子 hook 不得再靠「进程死」做控制流：文档+测试锁定——`SystemExit` / 非 0 语义与现网一致；若代码存在 `os._exit`，必须先清掉或包一层，**不得让 launcher 被带走**。  
3. 进入 `runpy` 前快照并在 `finally` 恢复：`sys.path`、`os.getcwd()`、关键 `env` 若 hook 会改（能恢复的才允许同进程）。  
4. stdout 协议不变：合法 JSON 决策 / 空+非0 → continue 的现语义必须有机械测。  
5. critical hook 缺失仍 **exit 2**（fail-closed 点不许漂）。  
6. 验收：`git apply --check` + 现网 hook 单测 + 故意让子 hook `raise` / `sys.exit(1)` / 打印半截 JSON 的用例。

**收益预期（按你们自己的数）**：量级秒～十余秒/长任务，**填不满 240s，也解释不了 86 vs 46 的 thrash**。批准理由是路径同构与减抖动，不是「过认证」。

---

### Q2. 根因修复（权限白名单覆盖动态目录）是否正确优先？动态白名单 vs 环境注入？

**裁决：优先方向正确，但实现选型必须锁死，否则开巨大攻击面。**

#### 正确优先的含义
- **第一优先修的是测量与任务可完成性装置**（probe / index 基线的 `settings.local.json` 与 work 路径对齐），让 A/B 比较的是治理，不是「租了房没钥匙」。  
- **不是**第一优先把生产默认改成「凡 cwd 皆可写」。

#### 实现选型（攻击面排序）

| 方案 | 安全性 | 对根因 | Grok |
|------|--------|--------|------|
| **H1. 人类预生成 benchmark/profile：启动探针时由脚本写入只含该次 `work/**` 的 allow** | 高（一次性、目录绑定、实验结束可弃） | 直接修 probe/ON | **首选** |
| **H2. 文档+清单：人类在交互里手动 campaign 授 `Write`/`Bash` 于该 work** | 最高（人类独占） | 修真实会话 | 产品默认 |
| **H3. 环境注入只读路径列表**（如 `CARROROS_TASK_ROOT`），*hooks 只读它做提示，不改 CC allow* | 中高 | 只改善 agent 行为/提示 | 可辅 |
| **X1. 运行时 agent 可改 `settings.local.json` / 自拓 allow** | **不可接受** | 看起来「灵」 | **否决** — 治理自我豁免 |
| **X2. 全局 `Write(./**/*)` / 全盘 Bash 重定向放行** | **不可接受** | 粗暴 | **否决** |
| **X3. 以 CarrorOS gate 去「代替」CC 权限否决**（gate 见拒就自动 PASS） | 混乱双法 | 假修 | **否决** |

**推荐部署切面：**

```text
仅适用于：Benchmarking / governance_cost_probe / index 认证装置
不适用于：默认真人交互配置自动扩权
人类独占：生产 allow 变更
```

动态「覆盖」= **实验脚手架生成器**（Python 写好本次 work 的 allow 文件），不是 hook 里检测 headless 后改规则，也不是模型调 Bash 去改 settings。

---

### Q3. 治理成本透明化是否合理？

**裁决：合理，且必须服从证据文化；禁止做成新治理层。**

允许：
- 只读聚合：每次任务 `tool_calls`、`gate_decision` 计数、wall-time、thrash 指标（同 tool 重复 BLOCK/deny 次数）  
- 产物落 **磁盘 JSONL/summary**，可供 hook 机械读  
- 纠偏 **探针本身**（如本次 `created_files` 与 claim 对账）

禁止：
- 为了「好看」抽样丢 PASS  
- 新 daemon / 新实时旁路  
- 用度量结果自动降 gate（度量 → 自动弱化 = 登机后又把 V1 从窗缝塞入）

建议一条机械不变量：

> `claimed_created ⊆ disk_created`，否则 probe 标记 `EVIDENCE_GAP` 且不得写入「根因最终确认」。

本次 PERM 就应打上 `EVIDENCE_GAP`，而不是进 V2 叙事当铁证。

---

### Q4. 若真主因是权限阻塞 → 反复尝试 + 请求授权，正确解法（非降治理）？

**正确解法栈（顺序强制）：**

1. **修装置（H1）**  
   probe/ON 传输治理时，同步生成/覆盖 **绑定该 work 绝对路径** 的权限剖面；PERM/ON **同一可写面**，变量只剩 hooks 是否加载。  
   → 重跑后才有资格谈「治理增量 = 86−46」。

2. ** thrash 显式化（不降权）**  
   对同一 path/同一 tool 的 harness-deny 或 gate-BLOCK，超过 N 次 → **确定性停机 + 一条人类裁决题**（你们 ON transcript 已走对人形式，应产品化，而不是继续 587 次空转烧时间）。  
   这服务 `验证/守护`，且能直接砍 240s 假超时。

3. **信道说明**  
   区分三层拒绝并写进 additionalContext（若有）：CC 未授权 / CarrorOS BLOCK / night-deny。避免模型在错误故障树重试。

4. **同构提速 A**  
   只减每跳固定成本，不解决 thrash 次数。

5. **禁止**  
   跳过 gate、降审计、FORCE_HEADLESS、自改 allow、把「请求授权」自动变「当已授权」。

**一句话：**  
正确解法是 **对齐可写面 + 限 thrash + 人类授口**，不是让治理变瘦。

---

### Q5. gate-contract WARN→fail-closed 优先级？

**裁决：独立高优先级守护项；排在「对外宣传性能达标」之前；不与 A/C 混 PR。**

理由：  
- V1 曾妄称「contract 强制 gate」当降级安全网，而 enforcement 仍是 WARN → 合规剧场。  
- 即使 V2 不再降级，**WARN 缺失仍使「契约」名不副实**，与 `验证` 冲突。  
- 改 fail-closed 可能暴露现网已缺线 gate → 这是**发现真相**，不是性能回归；应用 flag/清单分批，但语义必须 ERROR。

建议序：

```text
0. token 轮换（若仍未做）
1. 修 probe 盘证 + H1 权限剖面（否则根因叙事不立）
2. contract WARN→ERROR（独立）
3. thrash 上限 / 明确拒绝分层
4. A：launcher runpy → buffer flush →（有证据再）lazy import
```

---

## 四、对 V2 文档本身的治理意见（约束 4）

上一轮否决条写在文首 ✅，但 crawler 所见正文 **仍大段保留 §2 headless 检测 / 降级矩阵 / FORCE 开关 / 审计降频**。  

这是**僵尸方案**：顶栏 computed 否决，躯干仍可被施工模型当说明书。  
**要求整合器：V2 必须整章重写为唯一正文**；V1 仅可进 `附录/废案`，且标注 `SUPERSEDED — DO NOT IMPLEMENT`。  
`status: REVISED` 不够；**路径唯一包含文档路径唯一**。

另：`13-...` 文件名仍叫 headless-lightweight ——建议后续 rename 为 `isomorphic-governance-cost` 类，避免语义走私（非本轮阻塞，但是 the less 的清洁项）。

---

## 五、测量脚本攻击面快评（`governance_cost_probe.py`）

| 点 | 风险/缺口 | 要求 |
|----|-----------|------|
| ON rsync 全量 `.claude`，PERM 只拷 `settings.local.json` | 对比维不纯（hooks+权限+其它配置纠缠） | 报告里写清；最终对比应「同 allow，差 hooks」 |
| audit 读 **主仓** `.omc/state/audit` | 可能串场；587 含不含他会话？ | 绑定 work 内 audit 或 session id 过滤 |
| `created_files` 与 claim 未对账 | 证据门失败 | 失败则 `EVIDENCE_GAP`，禁止「最终确认」 |
| `env=dict(os.environ)` | 继承主会话 token/脏 env | 可接受但需记录；勿把 FORCE_* 残留测进去 |
| 超时 180 vs 认证 240 | 床位不一致 | 对齐或说明 |

这些修完，B 才算真「透明」。

---

## 六、第二轮总裁决（给整合器）

| 项 | 裁决 |
|----|------|
| V1 headless 全家桶 | 维持 **永久否决**（V2 已声明移除 — 必须从正文物理删除） |
| 支柱 A | **条件批准**，小步、隔离契约、不承诺过认证 |
| 支柱 B | **批准方向**；先修 probe 对账，禁止度量→自动降权 |
| 支柱 C | **批准「修装置/人类剖面」**；**否决一切运行时自我扩 allow** |
| 「根因最终确认」措辞 | **降级为「主假说 + EVIDENCE_GAP」**，直到 PERM 盘上有文件且 ON/PERM 同 allow 复测 |
| 可立即六段式施工 | **仅 A 的 launcher 或 buffer-flush（单主题 PR）**；C/H1 需先贴现行 `settings.local.json` 允许段 + 目标绝对路径规则后才能零设计空间 |
| contract fail-closed | **独立高优先**，不塞进 13 号性能 PR |

### 在出可 `git apply` 大补丁前，Grok 仍要的最小补料

1. PERM `work/` 真实 `ls -la`（或复跑 meta `created_files` 非空）  
2. 当前 `.claude/settings.local.json` **permissions/allow 相关段**（可打码密钥）  
3. `hook-launcher.py` 全文（或至少 subprocess 段 + critical 列表）——否则 runpy 六段式做不到零设计空间  
4. Doc 13 **删光 V1 降级段后的 V2 唯一正文**草案  

---

## 七、禁止事项（本轮对施工模型）

1. 禁止以任何形式复活 `_is_headless` / FORCE_HEADLESS / 按模式裁 gate / PASS 降频。  
2. 禁止 agent 可写路径去改 `settings.local.json` 或扩 allow。  
3. 禁止全局 Write/重定向放行当作「根因修复」。  
4. 禁止在证据 `created_files: []` 时写「PERM 成功落盘铁证」。  
5. 禁止 A+C+contract 混装同一 PR。  
6. 禁止宣称同构提速解决 240s 认证项。  
7. 禁止保留 Doc 13 双躯干（否决横幅 + 可施工 V1 正文）。  
8. 禁止用度量仪表盘反向自动跳 gate。  

---

### 直接回答整合器的安排问题

你们已备好第二轮材料；**不需要再问「能否发线上」——本回合即 Grok 的正式回复**，请落盘为：

`Benchmarking/improve/phase1/grok.md`

人类侧：继续手动把各模型回复放回 `phase1/{gpt,opus,grok}.md` 即可；我**不**要、也**不应**经手 API 密钥。

---

**一句话：**  
V2 走对了「取消第二套法」；真问题是 **实验/任务目录没有合法钥匙 + thrash**，不是 hook 算太慢。  
修钥匙必须 **人类/脚手架预置且目录绑定**；同构提速可以做，但别再把它裱成救赎。  
先补 PERM 盘证与 allow 剖面，再让我出可 apply 的六段式施工单。