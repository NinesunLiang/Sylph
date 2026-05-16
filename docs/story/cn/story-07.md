# OMA 铸造厂 — 金字塔瀑布流

一个 400 行的 Main PRD 被放在铸造厂的金字塔塔顶。它不是一份待办清单 — 它是一块**父石**。它要做的不是被"执行"，而是被**分裂**。

两个小时后，父石裂成 7 块 Sub PRD，散落在金字塔中层。每块 Sub PRD 再继续裂 — 变成 3-6 块 Feature，落在塔底。塔顶 1 块石头，中层 N 块，底层 N×M 块。越往下，石头越多、越细、越接近可执行的粒度。

这就是金字塔瀑布流的**结构**：上层压下层，父管控子。不是 A 做完传 B — 是每一块石头都是上一块的分身。

---

## 金字塔三层

```
              Main PRD (塔顶 · 1 块父石)
             /    |    \
    Sub PRD  Sub PRD  Sub PRD ... (中层 · N 块子石)
    / | \    / | \    / | \
   F  F F   F F F   F F F ... (底层 · N×M 块孙石)
```

| 层 | 来源 | 数量 | 粒度 |
|:--|:--|:--|:--|
| 塔顶 | 产品的原始需求 | 1 | "我们要做一个交易系统" |
| 中层 | lx-oma-hier 按功能域 MECE 分裂 | 3-8 | "用户认证" "订单管理" "支付" |
| 底层 | lx-oma-split 按 feature 正交分裂 | N×(3-6) | "登录接口" "Token 刷新" "权限校验" |

**上一层压着下一层** — 每个 Sub PRD 带着「父需求追溯」字段（模板字段，AI 生成时填充），映射回 Main PRD 的具体章节。每个 Feature 在模板头部标注 `所属 Sub PRD`。子不认父 = 孤儿 = gov audit 报漂移。

**正交性验证**：MECE 正交性检查是 AI 作为 skill 执行的一部分进行的自检（`lx-oma-hier/SKILL.md §3.2` MECE 校验摘要表 + `§7` 拆解质量的自我校验）。唯一的自动化脚本是 `verify_oma_interface_coverage.py` — 它检查接口/事件是否被 feature 覆盖，不检查 MECE 正交性。

证据：`lx-oma-hier/SKILL.md:211` — 父需求追溯模板字段。`governance-spec.md:374-381` — ID 孤儿检测。`lx-oma-split/SKILL.md §5.5` — 接口归属校验脚本（自动化）。

---

## 水：需求变更，不是站与站的传递

现实中没有人等 PRD 写完才开始开发。需求一边改，一边实现。如果每次改需求都推倒金字塔重来 — 没有人能活到交付。

所以水从塔顶注入。**水 = 新需求 / 需求变更**。

```
产品说："支付重试次数从 3 次改成 5 次"
    ↓ 水落在塔顶 (Main PRD)
Gov reconcile 检测到变更 → 分级 L1/L2/L3
    ↓ L1/L2 → 自动归并
    ↓ L3   → 人工裁决（涉及已有 REQ，不能自动覆盖）
Gov propagate --dry-run → 预览水流路径
    ↓
人工确认 → propagate --execute → 正式放水，写入 feature prd.md
    ↓
水流到底层：哪些 Feature 的 prd.md 需要追加 REQ 引用？
    ↓
CHG-ID 写入 sync-notes.md — 每滴水都有身份证，重复放水被幂等挡住
```

水不是漫灌。它**从塔顶分类，直接流向底层 Feature**，跳过 Sub PRD 文档。支付重试次数变更不会冲进用户认证的 Feature。Sub PRD 是一次性快照 — 若 Main PRD 重大变更，需重新运行 hier 更新。

证据：`lx-oma-gov/SKILL.md:194` — propagate --execute 为 v2 计划。`governance-spec.md:126-128` — 跨层读取允许，跨层追加允许（须绑定 CHG-ID），跨层写入禁止。`governance-spec.md:136-137` — propagate 写入目标为 Feature 层（追加）。

---

## Gov：包工头，不是纪委

开发周期长，石头多。三周后开发者自己也不知道：
- "这个 Sub PRD 拆了吗？"
- "支付模块的 Feature 是谁在做？"
- "需求改了，哪些 Feature 受影响？"

Gov 是**包工头**。他不砌砖 — 他手里有一张图，标记了金字塔上每一块石头的状态：

| 石头 | 当前状态 | 下一阶段 | Oracle |
|:--|:--|:--|:--|
| alert-engine (Sub PRD) | oma_done | gov_initialized | revised |
| notification (Sub PRD) | hier_done | oma_ready | approved |
| feat-alert-crud (Feature) | rpe_planned | in_dev | pending |
| feat-price-evaluation (Feature) | in_dev | dev_done | running |

当水（需求变更）从塔顶注入时，Gov 知道哪些石头会被打湿、哪些需要重新审视。他做三件事：

- **reconcile**：读塔顶 + 读所有层 → 检测变更 → 分级 L1/L2/L3 → 分配 CHG-ID
- **propagate**：预览水流路径（--dry-run）→ 实际写入 feature prd.md（--execute），CHG-ID 幂等
- **audit**（4/4 类型）：ID 孤儿检测 / 版本落后检测 / 冲突定义检测 / 孤立变更检测

**关键约束**：propagate 的目标是 feature 级 `prd.md`，**不经过 Sub PRD 文档**。Sub PRD 是 hier 拆分时生成的一次性快照 — 如果 Main PRD 发生重大变更，Sub PRD 需要重新运行 hier 来更新，不会由 gov propagate 自动同步。

证据：`lx-oma-gov/SKILL.md:194` — propagate --execute 为 v2 计划。`lx-oma-gov/SKILL.md:217` — audit v1 基础检测，v2 完整四类。`governance-spec.md:136-137` — propagate 写入目标为 Feature 层（追加），非 Sub PRD 层。

---

## Orch：态势感知图 + 规划路线

Gov 管的是「石头之间」— 水流对不对，子认不认父。

Orch 是一张**活地图**。他不推石头，不引水流。他只画路线、标关卡、显示每块石头当前在哪：

```
orch status：
  态势感知 — 全景显示金字塔上每一块石头的生命周期状态
  "alert-engine → oma_done，notification → hier_done，feat-alert-crud → in_dev..."

  这就是「开发到哪了」的答案。不需要翻文档、问人、猜 —
  一张图告诉你整座塔的当前状态。

orch advance：
  规划路线推进 — 当前阶段完成，检查路线上下一道 Oracle 关卡
    → approved → 沿路线推进到下一阶段
    → pending  → 输出审核清单，等待关卡放行

orch gate：
  关卡裁决 — 人工确认通过/拒绝，写入 pipeline.yaml
  不是 orch 在裁决 — 他只是把人的决定记在路线上

orch dev：
  并行路线管理 — 哪些 feature 可以同时开工？哪些互相阻塞？
```

新需求进来时，水沿着 orch 画的路线从塔顶流下：Main PRD → Sub PRD → Feature → 代码。Oracle 是路线上的关卡，水必须通过每一关才能继续往下流。

证据：`lx-oma-orch/SKILL.md:241` — "本 skill 不自行判断 Oracle 裁决结果"。`lx-oma-orch/SKILL.md:246` — "裁决逻辑由外部 Oracle 节点完成，本 skill 只负责编排和状态维护"。

---

## 金字塔 + 瀑布：完整图景

```
                     lx-oma-orch (态势感知图，画路线、标关卡)
                    /     status · advance · gate · dev
                   /      显示每块石头在哪，下一步往哪走
                  /
        ┌──── Main PRD ────┐  ← 塔顶：1 块父石
        │     /  |  \      │
        │  Sub  Sub  Sub   │  ← 中层：N 块子石（hier 分裂）
        │  /|\  /|\  /|\   │
        │  F F  F F  F F   │  ← 底层：N×M 块孙石（split 分裂）
        └──────────────────┘
              ↓
        lx-oma-gov (包工头，站在金字塔里)
          reconcile ↑ 检测上游变更
          propagate ↓ 逐层传播到受影响的石头
          audit —→ 巡查漂移

        Oracle (重力，独立于 orch 的质量裁决系统)
          每个阶段转换前 → Oracle 评估 → 产出 verdict
          orch gate 命令 → 人工将 Oracle verdict 写入 pipeline.yaml
```

**正向**：需求从塔顶注入 → 逐层分类 → 流向该去的 Feature（不需要推倒金字塔）。Sub PRD 文档是 hier 拆分时的一次性快照 — propagate 直接写入 Feature 级 prd.md，跳过 Sub PRD 层。若 Main PRD 发生重大变更，需重新运行 hier 更新 Sub PRD

**反向**：上游变更 → reconcile 检测 → propagate --dry-run 预览 → propagate --execute 实际写入

**节奏**：每块石头独立推进生命周期（hier_done → oma_done → rpe_planned → in_dev → dev_done）。Orch 检查 Oracle gate 状态，approved 则放行，pending 则拦住 — 但 orch 不自己裁决，裁决由独立的 Oracle 系统完成

**重力**：Oracle 门禁（哲学 #4 + #6 物化）— 每一步产出必须经独立质量评估才能落到下一层。上一层压着下一层 — 父需求追溯确保子不偏离父

**自动化脚本**：`oma_propagate.py`（变更传播） / `verify_oma_mece.py`（MECE 正交性校验） / `oma_audit.py`（4/4 漂移检测） / `oma_sub_prd_update.py`（Sub PRD 增量更新） / `verify_oma_interface_coverage.py`（接口归属校验）

---

## 铸造厂的地下设施

### oma_lock_manager.py — 分布式写锁

多个 AI 实例并行编辑文件时，如何防止互相踩踏？

oma_lock_manager.py 实现了基于文件系统的分布式锁，使用 `os.rename(tmp_file, lock_file)` — POSIX 原子操作，避免了 unlink + O_EXCL 两步操作的 TOCTOU 竞争窗口（rpe-014 教训）。生命周期：`acquire → heartbeat（定期续约）→ release`。

锁过期时，下一个请求者检测超时 → 原子替换锁文件 → 写后读验证所有权。只有唯一赢家。

### pretool-write-lock + posttool-write-lock — 锁的钩子执行者

pretool-write-lock 在每次 Edit/Write 前调用 oma_lock_manager 获取写锁。posttool-write-lock 在操作完成后释放锁。这两个 hook 是整个 OMA 并发安全的物理保障。

### race_manager.sh — 蜂群协调引擎

当金字塔底层的多个 Feature 可以并行开发时，race_manager.sh 充当蜂群协调器：`register → dispatch（分发给多个并行 agent）→ collect（收集结果）→ report（汇总报告）`。

它不做调度引擎 — 只做协调。子任务的调度由底层的 team skill 执行，race_manager.sh 关注的是**结果的一致性**：多个并行 Feature 的输出之间，有没有遗漏的交互点？有没有重复的功能点？race 不建写锁 — worker 写文件时 pretool-write-lock.sh 自动加锁。

---

## 可观测性

oma_lock_manager.py 使用 `tmp + os.rename` 原子写入 JSON 状态文件，确保并发读取端始终看到完整内容 — 不是部分写入的破碎 JSON。

金字塔的每一块石头、每一道水闸，都输出结构化状态，可被 lx-oma-orch 的 status 命令实时读取。

---

## 为什么叫 OMA？

一人成军，不是 AI 一个人完成所有工作 — 是**一个协议体系**让多个人（多个 AI 实例、多个用户、多个终端）像一个人一样协同。

金字塔保证了**结构**：父管控子，层级分明。
瀑布保证了**弹性**：需求变更从塔顶注入，逐层分类，不用推倒重来。
Orch 保证了**方向**：态势感知图让每个人知道自己在哪、下一步往哪走。
Gov 保证了**秩序**：每一滴水都有身份证，每一条路径都可追溯。

而金字塔最安静的时刻，是塔顶刚下过一场雨。五个匠人站在各自的石头旁，没人说话。包工头在层与层之间巡走，看着水位、闸门、流速。墙上的态势图无声地刷新——alarm-engine → oma_done，feat-price-evaluation → dev_done。水沿着路线流，该往哪走往哪走。

---

## 相关故事

- [双生之子](story-08.md) — lx-ghost/lx-goal 与 OMA 锁的协作：自主模式下写锁仍然生效
- [三重门神谕](story-11.md) — lx-oma-orch 管线上的 Oracle 门禁
- [圣器锻造所](story-14.md) — lx-rpe 是金字塔底层的执行器：Feature → 9步闭环 → 代码
- [金字塔瀑布](story-01.md) — 治理金字塔：哲学→铁律→Hook 的三层重力结构
