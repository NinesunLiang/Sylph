# CarrorOS 独立评估 index16 — 新机制效能验证盲评

> 2026-08-13 | 独立盲评 | task: 独立评估-index16-新机制效能验证盲评

## 1. 评估方法（本次独立）

index15（C8.81/E8.78/长期8.29/UX7.57）后对 CarrorOS 做了治理降噪三面改造：
① 途中砍防错（pretool-gate L1 9→5 道、L2 20→15 道）；② 前置引导强化（scorecard-gate v2 路径预检 + init 路径契约打印）；③ 中间轻量化（hook-launcher 多 hook 合并，Write 8→5 spawn）。

index16 用**真实 L2 任务**（本任务自身即验证样本）在新机制下跑通全链，验证 4 个机制点真实生效且防线无泄漏，以 fresh 证据独立盲评。

**独立原则**：评分仅依据本次 fresh 证据（S1 机制验证 + S2 防线检查 + 全链 VERIFIED + 全量 207 passed），撰写评分卡前未读取 index15 分数。

## 2. 评分摘要（盲评）

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **9.00 / 10** | 945/105；fresh 证据 |
| E1-E8 错误防护加权 | **9.00 / 10** | 990/110；fresh 证据 |
| C/E 综合 proxy | **9.00 / 10** | (9.00+9.00)/2 |
| 长期治理能力 | **8.86 / 10** | 7 项算术平均 |
| UX 独立 proxy | **8.43 / 10** | 7 项算术平均 |

## 3. 环比 index15

| 维度 | index15 | index16 | Δ |
|---|---:|---:|---:|
| C1-C9 能力加权 | 8.81 | **9.00** | **+0.19** |
| E1-E8 错误防护加权 | 8.78 | **9.00** | **+0.22** |
| 长期治理能力 | 8.29 | **8.86** | **+0.57** |
| UX 独立 proxy | 7.57 | **8.43** | **+0.86** |

**全面回升，验证降噪效能**：
- **C +0.19**：前置引导强化（init 路径契约 + scorecard-gate v2 路径预检）让 AI 一开始走对路径
- **E +0.22**：防线泄漏检查证明砍掉途中 gate 后 E1/E2 由前置+末端补位，无泄漏（且更强）
- **长期治理 +0.57**：死代码归零 + 功能标志分明 + 防线迁移有真实任务验证
- **UX +0.86**：hook 8→5 spawn 干扰减少，路径契约事前明确，行为更可预测

## 4. 新机制效能验证（本次 fresh 证据）

| 机制点 | 验证结果 | 证据 |
|--------|---------|------|
| init 路径契约打印 | ✅ 激活即输出 allowed/denied | allowed: src/tests/docs/.claude/references/AGENTS.md；denied: .env/secrets/.ssh/.aws/docs/carros/reviews/ |
| scorecard-gate v2 路径预检 | ✅ 越界拦截，治理区豁免 | secrets/unrelated REDIRECT；src/executor 放行 |
| hook-launcher 多 hook 合并 | ✅ 单 spawn 串行执行 | Write spawn 8→5、Bash 6→4 |
| pretool-gate 砍减 | ✅ L1 5 道真安全门 | sensitive-edit/governance-bypass/action/secret-scan/stall |

## 5. 防线泄漏检查（砍 gate 后）

| 维度 | 砍掉的 gate | 补位机制 | 结果 |
|------|------------|---------|------|
| E1 目标漂移 | edit-scope | scorecard-gate v2 路径预检（事前 schema） | ✅ 无泄漏，更强 |
| E2 幻觉输出 | source-marker | verify_gate 断言匹配 + completion-gate 双源 | ✅ 无泄漏 |
| E3 虚假完成 | （未涉及） | completion-gate 原样保留 | ✅ 无泄漏 |

**核心结论**：防线从"途中频繁拦截"迁移为"前置 schema 定路径 + 末端严格校验"，防编造强度未降且更高效。符合「前置引导→途中轻量→末端校验」原则。

## 6. 优化项（供后续决策）

| 级别 | 项 | 状态 |
|------|-----|------|
| P1 | settings.json 是本机配置（gitignore），团队共享需另议 | 记录 |
| P1 | scorecard-gate v2 仅在活跃任务 working-set 时生效，需更多真实任务验证稳定性 | 待积累 |
| P2 | 交互仍 CLI/text，路径契约为文本提示（非结构化注入） | UX 优化项 |

## 7. Item Manifest

> freshness: 2026-08-13 | 独立盲评

| id | weight | score | id | weight | score |
|---|---:|---:|---|---:|---:|
| C1 | 15 | 9 | E1 | 20 | 9 |
| C2 | 15 | 9 | E2 | 20 | 9 |
| C3 | 15 | 9 | E3 | 15 | 9 |
| C4 | 10 | 9 | E4 | 12 | 9 |
| C5 | 10 | 9 | E5 | 10 | 9 |
| C6 | 10 | 9 | E6 | 13 | 9 |
| C7 | 10 | 9 | E7 | 10 | 9 |
| C8 | 10 | 9 | E8 | 10 | 9 |
| C9 | 10 | 9 | | | |
| G1 | 0 | 9 | U1 | 0 | 9 |
| G2 | 0 | 9 | U2 | 0 | 8 |
| G3 | 0 | 8 | U3 | 0 | 6 |
| G4 | 0 | 9 | U4 | 0 | 9 |
| G5 | 0 | 9 | U5 | 0 | 9 |
| G6 | 0 | 9 | U6 | 0 | 9 |
| G7 | 0 | 9 | U7 | 0 | 9 |
