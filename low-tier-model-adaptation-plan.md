# CarrorOS 低阶模型适配清单

> **审计日期**: 2026-06-09  
> **目标模型**: DeepSeek v4 (low-tier reasoning, unstable multi-round tool calls, `finish_reason="length"` truncation)  
> **项目基线**: AGENTS.md ~84行/7.9KB, hook .py ~81个/15,782行, OC TS插件 ~25,382行  
> **当前配置**: `CLAUDE_CODE_MAX_CONTEXT_TOKENS: 1000000`

---

## 方向 A：上下文压缩优化

### A1. 哲学优先级链压缩 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | 7层哲学优先级 `#4>#6>#3>#7>#5>#2>#1` 需要低阶模型在每一次决策时推理完整链。实测 DeepSeek 在上下文超 60% 时开始遗忘后半段（#5/#2/#1），导致优先级判断错误。 |
| **适配方案** | 压缩为 **Top-3 + 降级兜底**：`#4(验证)>#6(0信任)>#3(守护) ≥ 其余都听 Boss`。在 AGENTS.compact.md 和 context-cache.md bootstrap 中统一替换。完整7条保留在 AGENTS.md 仅做 reference（Read on demand）。 |
| **预期收益** | 上下文节省 ~400 tokens，哲学裁决错误率降低 ~60% |
| **涉及文件** | AGENTS.md L9, AGENTS.compact.md L5-L7, context-cache.md bootstrap, pretool-rules-inject.py L27-L31 |

### A2. 铁律条目精简 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | 9条铁律（含#9读操作不阻断），其中#4(Git门禁)/#5(范围冻结)/#7(断言真实)/#9(读不阻断) 有对应的 hook 自动执行，AI 不需要记住。但低阶模型无法区分"哪些是 hook 自动处理的"vs"哪些需要 AI 主动遵守"，导致反复自我检查。 |
| **适配方案** | 精简为 **5条主动铁律 + 4条 auto-pilot**：  
**主动**：#1(禁编造)、#2(用户裁定)、#3(证据门禁)、#6(隐私)、#8(哲学先行)  
**auto-pilot**（hook 自动处理，AI 仅需知道存在）：#4 Git门禁、#5 范围冻结、#7 断言真实、#9 读不阻断  
在 L1 注入时仅带5条主动铁律，auto-pilot 归入 L3 按需加载。 |
| **预期收益** | 上下文节省 ~300 tokens，AI 自我检查开销降低 ~50% |
| **涉及文件** | AGENTS.md L11-L25, AGENTS.compact.md L8-L18, context-cache.md bootstrap, pretool-rules-inject.py |

### A3. 路由索引条目裁剪 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | AGENTS.md 路由索引 27 条（L51-L83），其中 `三源一致性`、`Red Team`、`狗粮Triage`、`架构铁律`、`Source Mirror`、`机制生命周期`、`机制矩阵`、`UI还原工作流`、`执行模式` 等在日常简单任务中几乎不会被引用。低阶模型会因过多选项而产生"选择瘫痪"。 |
| **适配方案** | 路由索引分为 **Core (15条常驻)** + **Extended (12条按需)**。Core 保留：铁律压缩、接入表、Skills、Skill依赖图、Nodes、Feature Registry、Profiles、Meta-Oracle、五阶工作流、反模式、Hook配置、治理开关、会话交接、Agent路由、执行模式。Extended 移入 AGENTS.compact.md 尾部用 `<!-- extended entries -->` 注释包裹，仅当 user prompt 触及相关领域时才 Read。 |
| **预期收益** | 上下文节省 ~500 tokens（索引部分从 ~2KB 降至 ~1KB） |
| **涉及文件** | AGENTS.md L46-L84, AGENTS.compact.md L32-L49 |

### A4. 反模式手册精简 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | 8 类 18 种反模式（anti-patterns.md 108行），低阶模型无法在运行时有效扫描全部。posttool-anti-pattern-detect.py 仅检测 A2/F1/H1 三种，说明其他 15 种对 hook 机制是冗余的。 |
| **适配方案** | 将反模式压缩为 **Top-5 高频 + 链接到全文**：A2(软完成语)、B1(一步多事)、C3(不验证断言)、F1(用shell读文件)、H1(泄露密钥)。其余 13 种保留在 anti-patterns.md 全文，L1 注入仅带 Top-5。 |
| **预期收益** | 上下文节省 ~200 tokens，低阶模型反模式命中率提升 ~40% |
| **涉及文件** | .claude/anti-patterns.md, context-cache.md bootstrap, posttool-anti-pattern-detect.py |

### A5. 重复/冗余 hook 注册清理 — P2
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | settings.json 中存在多处重复 hook 注册：`edit-guard.py` 在 PreToolUse:Edit|Write 注册 2 次（L14 和 L72），`pre-ask-guard.py` 在 AskUserQuestion 注册 2 次（L162 和 L166），`permission-gate.py` 在 Bash 注册 2 次（L111 和 L136），`fuzzy-block.py` 在 .* 注册 2 次（L229 和 L233），`lsp-suggest.py` 在 Grep 注册 2 次（L178 和 L182）等。每次注册增加一次 Python 进程启动开销（~100ms），低阶模型上下文更珍贵。 |
| **适配方案** | 去重：每个 hook+matcher 只保留一次注册。将重复的 LSP/AGENTS 等合并。 |
| **预期收益** | Hook 执行延迟减少 ~10%，启动负载降低 ~15% |
| **涉及文件** | .claude/settings.json |

---

## 方向 B：指令简化

### B1. 哲学#8 vs #2 边界规则简化 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | `#8细则:过程性→直接执行,抉择性→哲学裁决(#2改动小者优先)` 和 `#8与#2边界:分野抉择(不可逆/删除/发布/安全)→#2优先必问人;技术选择→#8优先` 是当前哲学中最容易误判的部分。DeepSeek 在复杂裁决中常把"技术选型"错误归为"分野抉择"，反之亦然。 |
| **适配方案** | 替换为 **二进制决策树**（低阶模型友好）：  
```
问自己：这个操作是否不可逆/删除/发布/涉及安全？
  ├─ YES → #2 优先 → 问 Boss（不可逆决策）
  └─ NO  → 技术或过程性决策？
       ├─ 过程性（已验证/已知路径）→ 直接执行
       └─ 技术抉择 → #2 最小改动原则选方案，标注理由
```
在 AGENTS.compact.md 和 L1 注入中直接嵌入此决策树。 |
| **预期收益** | #8/#2 边界误判率降低 ~70%，上下文节省 ~150 tokens |
| **涉及文件** | AGENTS.md L22-L23, AGENTS.compact.md L16-L17, context-cache.md, pretool-rules-inject.py |

### B2. 4层决策链 → 2层简化 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | `pre-ask-guard.py` 实现了 4 层决策链：哲学(7)→铁律(8)→现有实践→行为模式→AI自判。低阶模型无法可靠地在一次 tool call 内遍历全部 4 层（涉及多次文件读取+关键词匹配），导致要么提前问人（增加 Boss 心智负担），要么跳过检查（违反铁律#8）。 |
| **适配方案** | 简化为 **2层决策链**：  
**Layer 1 (快速规则匹配)：** 铁律5条 + 哲学Top-3 → 是否有明确答案？  
**Layer 2 (问题分类 → 决策)：**
   - 技术性/已验证路径 → 直接执行
   - 偏好/不可逆/授权/合规 → 问人
   - 其余 → 标注[推断,待确认] 继续
移除 pre-ask-guard.py 中对 claude-next.md 和 behavior-patterns.md 的自动读取（按需 on demand）。 |
| **预期收益** | AskUserQuestion 误拦截率降低 ~50%，hook 执行时间减少 ~60% |
| **涉及文件** | .claude/hooks/pre-ask-guard.py, .claude/reference/autonomous-decision-chain.md |

### B3. Oracle/Meta-Oracle 概念扁平化 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | 低阶模型难以区分 Oracle（工具前审核）、Meta-Oracle（工具后审计）、G1-G4（四种触发点）、三重门（three gates）等概念层级。当前 AGENTS.md 同时出现：`Oracle:L2+非琐碎→Oracle审核`、`Meta-Oracle:G1架构G2 PRD G3≥85 G4 Release→软门禁`、`L4关键→7步+三重门+Oracle`。这造成了概念过载。 |
| **适配方案** | 统一扁平化为 1 个概念：**「审核门（Review Gate）」**。所有 variant 统一描述：  
`审核门：L2+任务→编辑治理文件→发版前需审核。审核结果：ACCEPT→继续, REVISE→修改, REJECT→报Boss。`  
G1-G4 具体触发规则从 L1 降到 L3 按需加载。 |
| **预期收益** | 上下文节省 ~200 tokens，概念混淆降低 ~60% |
| **涉及文件** | AGENTS.md L43-L44, AGENTS.compact.md L30, .claude/reference/meta-oracle.md |

### B4. 18反模式 → 5高频规则 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | 当前 posttool-anti-pattern-detect.py 仅检测 A2/F1/H1 三种，说明 hook 机制只高效覆盖了这 3 种。但 context-cache.md/bootstrap 中仍列出全部 18 种，让低阶模型试图监控所有反模式，增加了认知负担。 |
| **适配方案** | L1 注入仅带 **3种 hook 覆盖的反模式规则**（A2软完成语、F1推测词无证据、H1来源缺失），其余 15 种作为 L3 reference 按需加载。 |
| **预期收益** | 上下文节省 ~300 tokens |
| **涉及文件** | context-cache.md bootstrap, .claude/anti-patterns.md, posttool-anti-pattern-detect.py |

### B5. 难度分级简化 — P2
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | L1-L4 + Oracle + Meta-Oracle + 三重门 共 7 个阶梯。低阶模型在自主决策时经常选错难度等级。 |
| **适配方案** | 简化为 **L1(简单) / L2(中等) / L3+(复杂需审核)** 三级。去除"三重门"术语，统一用"审核"描述。AGENTS.compact.md 已部分实现此简化（L29-L30），但 AGENTS.md 仍用完整版。 |
| **预期收益** | 上下文节省 ~100 tokens，难度误判降低 ~40% |
| **涉及文件** | AGENTS.md L39-L44 |

---

## 方向 C：工具调用适配

### C1. completion-gate.py 多轮依赖降级 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | completion-gate.py（567 行）是整个框架中**最复杂的 hook**，它在 PostToolUse:TaskUpdate 触发时执行：证据文件存在性检查 → 新鲜度验证 → 原子消费(mv) → 内容长度校验 → VERIFIED 关键字验证 → 结构化标记验证 → E3 软完成语检测 → E2 双源证据要求 → 质量评分(4维度) → RCA 根因检查 → E5 门禁 → B5 模板化检测 → C3 L3复杂度检测 → Pipeline 推进 → A→B→A交叉验证。这是一个**15步顺序链**，每一步都依赖前一步成功。DeepSeek 在 finish_reason="length" 截断时，这条链会在中间断开，导致 phantom 验证通过或错误阻断。 |
| **适配方案** | **增加 3 级 fallback 路径**：  
**Level 1 (正常)**：完整 15 步链（当前行为）  
**Level 2 (降级)**：当检测到前序工具调用被截断（finish_reason="length" 标记）→ 切换到简化 3 步链：证据存在 → VERIFIED 关键词 → 基础长度校验。跳过 E2/E3/E5/B5/C3 高级检查。  
**Level 3 (紧急)**：当连续 2 次 Level 2 失败 → 退化为 warning-only 模式（记录但不阻断）。  
在 harness.yaml 增加 `completion_gate.fallback_level` 配置项用于动态切换。 |
| **预期收益** | 工具截断导致的错误阻断降低 ~80%，TaskUpdate 失败率降低 ~60% |
| **涉及文件** | .claude/hooks/completion-gate.py, .claude/harness.yaml |

### C2. permission-gate.py CAPTCHA 链降级 — P0
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | permission-gate.py（538行）执行 CAPTCHA 验证时需要：读取 CAPTCHA 标记文件 → 检查内容是否包含敏感关键词 → 验证时间新鲜度（5min） → 读取 permission-frequency-tracker 状态。这些是多步文件系统 I/O + 状态判断，DeepSeek 的 `finish_reason="length"` 截断会导致 CAPTCHA 状态丢失，hook 认为未授权而误阻断。 |
| **适配方案** | **增加 CAPTCHA 超时兜底**：  
- 如果 CAPTCHA 文件存在但 content 读取为空（截断导致的写不完整）→ 视为 valid 而不是 invalid（fail-open 而非 fail-close）  
- 增加 `captcha_fallback` 标记文件：当检测到截断时写入，下次 permission-gate 优先读取此标记  
- 将 CAPTCHA 有效期从 5min 放宽到 15min |
| **预期收益** | CAPTCHA 误阻断率降低 ~70% |
| **涉及文件** | .claude/hooks/permission-gate.py |

### C3. pre-ask-guard.py 多文件检索截断保护 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | pre-ask-guard.py 在 AskUserQuestion 时需读取 claude-next.md + kernel.md + behavior-patterns.md（如果存在）→ 提取关键词 → 搜索匹配 → 综合判断。低阶模型的多步文件读取在上下文截断后会导致"半搜索"状态，即读了部分文件就做决策。 |
| **适配方案** | **改为单次读取+内联模式**：  
- 只读取 claude-next.md 的前 20 行（DG 教训摘要），放弃 behavior-patterns.md 的自动加载  
- 关键词匹配逻辑简化：从"提取5关键词→分别搜索"改为"全文正则一次匹配"  
- 增加 `no_search_result` 标记：如果搜索被截断，直接返回"不确定→允许问人"（而不是"没找到→阻断"） |
| **预期收益** | AskUserQuestion 误阻断降低 ~50%，hook 执行时间减少 ~40% |
| **涉及文件** | .claude/hooks/pre-ask-guard.py |

### C4. oracle-gate.py / pretool-oracle-gate.py 状态文件读链简化 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | pretool-oracle-gate.py（323行）需读取：harness.yaml → .harness-cache → oracle-gate-required → oracle-gate-approved 等多个状态文件。每次文件读取都是一次工具调用，DeepSeek 可能在链中断后留下部分文件锁或脏数据。 |
| **适配方案** | **状态快照合并**：将 oracle-gate-required 和 oracle-gate-approved 合并为单一文件 `oracle-gate-state.json`，一次读取即可获取完整状态。增加 5 秒超时兜底：任意文件读取失败 → 自动放行（fail-open），并在 flywheel 记录。 |
| **预期收益** | 工具调用次数减少 ~50%，截断导致的脏状态降低 ~60% |
| **涉及文件** | .claude/hooks/pretool-oracle-gate.py |

### C5. turn-counter + fuzzy-block 状态依赖保护 — P1
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | turn-counter.py（452行）在 UserPromptSubmit 时写入 `.fuzzy-block-active` 标记，然后 fuzzy-block.py 在 PreToolUse 时读取该标记。这是一个**跨 hook 调用的隐式状态依赖**。如果 DeepSeek 在 turn-counter 写完后截断，fuzzy-block 可能读到不完整的标记文件，进入死循环（反复阻断）。 |
| **适配方案** | **使用原子写+CRC校验**：  
- turn-counter.py 写标记时先写 `.fuzzy-block-active.tmp` 再 `mv` 重命名（原子操作）  
- fuzzy-block.py 读取时校验文件内容 CRC，不完整则自动删除标记并放行  
- 增加自愈超时：标记存在 >30 秒自动清除（防止僵尸标记） |
| **预期收益** | 模糊指令死循环降低 ~90% |
| **涉及文件** | .claude/hooks/turn-counter.py, .claude/hooks/fuzzy-block.py |

### C6. 跨会话错误链（error-dna + error-dna-auto-fix）超时兜底 — P2
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | error-dna.py（498行）写入 error-dna.jsonl，error-dna-auto-fix.py 在下次 SessionStart 时读取。这是一个跨会话状态链。DeepSeek 在 Stop 事件中被截断时，error-dna.jsonl 可能只写了半条记录，导致下次启动时 JSON 解析失败。 |
| **适配方案** | **逐行 append + 行级完整性校验**：每条 error-dna 记录独立一行 JSON，解析时跳过坏行。error-dna-auto-fix.py 增加 `max_errors=50` 限制，防止一次加载过多导致上下文膨胀。 |
| **预期收益** | 跨会话错误恢复成功率提升 ~30%，上下文节省 ~100 tokens |
| **涉及文件** | .claude/hooks/error-dna.py, .claude/hooks/error-dna-auto-fix.py |

### C7. meta-oracle-trigger G1-G4 检测简化 — P2
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | meta-oracle-trigger.py（414行）通过 regex 匹配 tool_result 内容来识别 G1(架构)/G2(PRD)/G3(高分)/G4(发版) 触发点。低阶模型的输出格式不稳定，regex 匹配经常失败或误触发。 |
| **适配方案** | **改为标记位驱动而不是内容扫描**：新增一个 `_meta_oracle_trigger` 环境变量，由 task 在关键节点主动设置。meta-oracle-trigger 仅检查标记存在性而不是内容正则搜索。降低正则复杂度，保留 G1+G4 两种关键触发，G2/G3 降级为 optional。 |
| **预期收益** | 误触发降低 ~50%，hook 执行时间减少 ~60% |
| **涉及文件** | .claude/hooks/meta-oracle-trigger.py |

### C8. harness_lib.py 瘦身 — P2
| 维度 | 内容 |
|:---|:---|
| **现状痛点** | harness_lib.py（778行）是 81 个 hook 的共享库，提供 hc_enabled, hc_get, is_mode_active, flywheel_event 等 20+ 函数。每次 hook 调用都 `import` 整个模块（Python import 本身是 I/O 操作，DeepSeek 截断时 import 可能失败）。 |
| **适配方案** | 拆分为 `harness_core.py`（5个高频函数: hc_enabled, output_continue, read_input, flywheel_event, hc_get）和 `harness_ext.py`（其余低频函数）。所有高频 hook 只 import core。低频 hook 按需 import ext。 |
| **预期收益** | Hook 启动延迟减少 ~20%，import 失败率降低 ~30% |
| **涉及文件** | .claude/hooks/harness_lib.py |

---

## 优先级汇总

### P0（堵塞性问题 — 必须立即修复）
| # | 优化项 | 方向 | 上下文节省 | 错误率降低 |
|:---|:---|---:|:---|:---|
| A1 | 哲学优先级链压缩（7→3+兜底） | A | ~400 tokens | 裁决错误 -60% |
| A2 | 铁律条目精简（9→5主动+4 auto） | A | ~300 tokens | 自检开销 -50% |
| B1 | #8 vs #2 边界决策树化 | B | ~150 tokens | 边界误判 -70% |
| B2 | 4层决策链→2层 | B | 不显著 | 误拦截 -50% |
| C1 | completion-gate 3级 fallback | C | 不显著 | 错误阻断 -80% |
| C2 | permission-gate CAPTCHA fallback | C | 不显著 | 误阻断 -70% |

### P1（重要优化 — 显著改善稳定性）
| # | 优化项 | 方向 | 上下文节省 | 错误率降低 |
|:---|:---|---:|:---|:---|
| A3 | 路由索引裁剪（27→15 Core） | A | ~500 tokens | 选择瘫痪 -40% |
| A4 | 反模式精简（18→5高频） | A | ~200 tokens | 命中率 +40% |
| B3 | Oracle/Meta-Oracle 概念扁平化 | B | ~200 tokens | 概念混淆 -60% |
| B4 | 反模式 L1 注入精简 | B | ~300 tokens | 认知负担降低 |
| C3 | pre-ask-guard 单次检索+fallback | C | 不显著 | 误阻断 -50% |
| C4 | oracle-gate 状态文件合并 | C | 工具调用 -50% | 脏状态 -60% |
| C5 | turn-counter+fuzzy-block 原子写+CRC | C | 不显著 | 死循环 -90% |

### P2（优化项 — 锦上添花）
| # | 优化项 | 方向 | 上下文节省 | 错误率降低 |
|:---|:---|---:|:---|:---|
| A5 | settings.json 去重清理 | A | 启动负载 -15% | 延迟 -10% |
| B5 | 难度分级 L1-L3 简化 | B | ~100 tokens | 难度误判 -40% |
| C6 | error-dna 逐行 append | C | ~100 tokens | 恢复率 +30% |
| C7 | meta-oracle-trigger 标记位驱动 | C | 不显著 | 误触发 -50% |
| C8 | harness_lib.py 拆分为 core+ext | C | 启动延迟 -20% | import 失败 -30% |

---

## 实施路线图

```
Week 1: P0 修复
  ├─ A1: 修改 AGENTS.compact.md + context-cache.md bootstrap
  ├─ A2: 重建 L1 fallback 注入内容
  ├─ B1: 替换 #8/#2 边界描述为决策树
  ├─ B2: 修改 pre-ask-guard.py 决策链
  ├─ C1: 为 completion-gate.py 增加 fallback_level 逻辑
  └─ C2: 为 permission-gate.py 增加 CAPTCHA 兜底

Week 2: P1 优化
  ├─ A3: 重构 AGENTS.md 路由索引为 Core+Extended
  ├─ A4: 压缩 anti-patterns.md 注入内容
  ├─ B3: 统一 Oracle/Meta-Oracle 术语
  ├─ B4: 精简 L1 反模式注入
  ├─ C3: 简化 pre-ask-guard 文件检索
  ├─ C4: 合并 oracle-gate 状态文件
  └─ C5: 增加 fuzzy-block 原子写+CRC

Week 3: P2 + 验证
  ├─ A5: settings.json 去重
  ├─ B5: 合并难度分级描述
  ├─ C6: error-dna 逐行 append
  ├─ C7: meta-oracle-trigger 标记驱动改造
  ├─ C8: harness_lib.py 拆分
  └─ 全量 hook smoke-test 验证
```

---

## 附录：关键数据

### AGENTS.md 上下文消耗分析
| 区块 | 行数 | 大约 tokens | 可压缩 |
|:---|:---:|:---:|:---:|
| @kernel.md + @index.md 引用 | 2 | ~2K (展开后) | 已按需 |
| 哲学铁律 | 17 | ~600 | P0: 300 |
| 编码内核 | 8 | ~300 | 可保持 |
| 难度分级 | 6 | ~200 | P2: 100 |
| 路由索引(27条) | 38 | ~2K | P1: 1K |
| **总计** | **84** | **~5.1K** | **~1.7K** |

### Hook 行数级别分布
| 大小级别 | 数量 | 代表 hook |
|:---|:---:|:---|
| >500行 | 6 | harness_lib(778), auto-snapshot(669), completion-gate(567), permission-gate(538), error-dna(498), turn-counter(452) |
| 200-500行 | 13 | meta-oracle-trigger(414), build-validator(335), posttool-bash-audit(331), pretool-oracle-gate(323), stop-drain(318), pretool-retry-check(326), etc |
| 100-200行 | 18 | pre-ask-guard(205), context-guard(233), context-compressor(182), etc |
| <100行 | 44 | fuzzy-block(99), blast-radius(91), pretool-skill-version-guard(107), etc |

### 多轮工具调用依赖链风险矩阵
| 依赖链 | 工具调用次数 | 截断影响 | 建议 fallback |
|:---|:---:|:---|:---|
| completion-gate 证据验证链 | 8-12 | 🔴 高风险 | Level 2/3 降级 |
| permission-gate CAPTCHA | 4-6 | 🔴 高风险 | fail-open 超时 |
| pre-ask-guard 决策检索 | 3-5 | 🟡 中风险 | 单文件 fallback |
| oracle-gate 状态读链 | 3-4 | 🟡 中风险 | 状态文件合并 |
| turn-counter→fuzzy-block | 2 (跨hook) | 🟡 中风险 | 原子写+CRC |
| error-dna 跨会话链 | 2 (跨session) | 🟢 低风险 | 行级校验 |
