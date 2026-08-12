# Design Doc 13 — 治理成本治理（isomorphic-governance-cost）

> 状态：`V2（第二轮联合审核后）/ 待证据闭合 + 人类授权`
> 主题：降低 CarrorOS 治理的**执行成本**（非治理强度），不引入第二套治理法。
> 日期：2026-08-12
> 涉及冻结边界：`.claude/hooks/*`、`.claude/settings.json` hook 注册 → **实施需人类授权**

---

## 附录 A：V1（SUPERSEDED — DO NOT IMPLEMENT）

V1 曾提议 **headless 检测 + 分级降级 + 审计降频**。经第一轮联合审判（GPT-5.6 Sol / Opus 5 / Grok 4.5）**永久否决**，理由：
- `sys.stdin.isatty()` 在 hook 场景恒 False → 交互模式也被降级（致命）；
- `CARROROS_FORCE_HEADLESS` 是自我豁免开关（AI 可 export 一次即弱治理）；
- 模式分叉 = "让系统相信自己在弱侧"的攻击面，检测再准也消不掉；
- 审计降频废证据门禁（PASS 摘要化无法证明 gate 跑过）。

**V1 结论**：不做 headless 检测、不做模式分叉、不做审计降频。V2 遵此。

---

# V2 — 治理成本治理（安全的轻量化行动）

## 0. V2 原则

| 第一轮否决项 | V2 处理 |
|------------|--------|
| headless 检测（isatty 恒 False） | ❌ **完全不做** |
| 模式分叉（两套 gate 集） | ❌ **完全不做**——单一路径 |
| FORCE_HEADLESS 自我豁免开关 | ❌ **完全不做** |
| 审计降频丢行 | ❌ **完全不做**——缓冲写 + flush 零丢行 |
| 用 WARN contract 当安全网 | ⚠️ 独立前置项 |

**V2 方向**：不改变治理语义，只做**同一套 gate 跑得更快** + **治理成本透明** + **修测量装置**。

## 1. V2 三支柱

### 支柱 A：同构提速三件套（条件批准）

| 改动 | 文件 | 效果 |
|------|------|------|
| 单进程 launcher（runpy） | `hook-launcher.py` | 消二次 Python 启动（5→2 进程/调用） |
| 惰性 import | `pretool-gate.py`/`helpers.py` | 延迟重模块（yaml 等） |
| 缓冲写 + 退出 flush | `helpers.py _append_audit` | 零丢行，减 syscall |

**不变式**：gate 集不变（L1=9/L2=20）、审计内容不变、阻塞行为不变、settings 注册不变、launcher 一次只跑一个 hook。

**收益预期**（诚实）：秒级～十余秒/长任务，**不解决 240s 认证项**（它解释不了 thrash）。批准理由是路径同构与减抖动。

### 支柱 B：治理成本透明化（批准，先修探针）

- 只读聚合：工具调用次数、gate_decision 计数、wall-time、thrash 指标
- 产物落磁盘 JSONL，hook 机械可读
- **禁止**：度量 → 自动降 gate / 抽样丢 PASS

### 支柱 C：修测量装置 + 权限剖面（根因修复，人类预置）

**受控测量发现**：治理 ON 下 agent 卡在**权限白名单不含动态工作目录写权限** → 反复尝试（587 gate）+ 请求授权。

**正确解法栈**（Grok 排序）：
1. **修装置（H1）**：probe/ON 传输治理时同步生成绑定 work 绝对路径的权限剖面；ON/PERM 同一可写面，唯一变量是 hooks 是否加载
2. **thrash 显式化**：同 path/同 tool 多次 deny → 确定性停机 + 人类裁决题（不空转）
3. **信道说明**：区分 CC 未授权 / CarrorOS BLOCK / night-deny

**禁止**：运行时 agent 改 allowlist / 自扩权；全局 Write 放行；gate 代替 CC 权限否决。

## 2. 关键证据（P0 + 受控测量）

| 测量 | 结果 | 结论 |
|------|------|------|
| 审计 IO | 无 fsync，20-gate 链 1.97ms | 非主因 |
| AskUserQuestion 死循环 | 受控探测 13s 收敛无死循环 | 该场景证伪 |
| hook 进程 spawn | ~70ms/次调用（5 进程） | 次要因素 |
| **治理成本 ON vs PERM** | ON 86s vs PERM 45.9s | 治理增量 ~1.9x |
| **权限阻塞（主假说）** | ON 无法落盘请求授权；PERM 成功落盘 | **主假说（待 v2 复跑闭合）** |

## 3. V2 TDD 计划

| 测试 | 验证 |
|------|------|
| launcher 单进程 | runpy 生效，无 `[sys.executable, hook_path]` |
| 缓冲写零丢行 | 审计行数不变，内容完整 |
| gate 集不变 | L1=9 / L2=20 断言 |
| probe 盘证 | `claimed_created ⊆ disk_created`，否则 EVIDENCE_GAP |
| 回归 | run-regression.sh 全绿 |

## 4. 第二轮联合审核结论（2026-08-12）

GPT-5.6 Sol / Opus 5 / Grok 4.5 一致：

| 议题 | 三方共识 |
|------|---------|
| V1 headless 全家桶 | 永久否决（已移入附录） |
| 根因方向 | **成立为主假说**，但测量证据未闭合（PERM created_files=[] → EVIDENCE_GAP） |
| 支柱 A | 条件批准，小步单主题 PR，不承诺过认证 |
| 支柱 B | 批准，先修探针 |
| 支柱 C | 批准"修装置/人类剖面"，**否决运行时自扩权** |
| contract fail-closed | 独立高优先级，不与性能混 PR |

**⚠️ 重要修正**：三方指出 `PERM created_files=[]` 与 transcript 声称矛盾 → EVIDENCE_GAP。经核实，该矛盾源于**探针脚本 bug**（`p.parts` 含父级 `.omc` 误伤全部文件），非 agent 说谎；磁盘上 PERM 确实落盘成功、ON 失败。**修正后根因结论加强**（权限阻塞成立），但按证据门仍需用修正后的 probe **复跑 n≥3** 闭合。

**⚠️ 安全事项**：`settings.json` 含明文 `ANTHROPIC_AUTH_TOKEN`，需人类立即轮换、改环境注入、删明文。

## 5. V2 决策请求（给人类）

1. 授权修改冻结 hook（launcher/helpers）做同构提速（支柱 A，单主题 PR）？
2. 确认"修装置（H1）+ thrash 上限 + 权限剖面人类预置"方向（支柱 C）？
3. gate-contract WARN→fail-closed 是否立为独立前置项？
4. 是否复跑修正后的 probe（n≥3）闭合根因证据？
