# CarrorOS 独立评估 index17 — 真实 spawn 空上下文 A/B 电池

> 2026-08-13 | 独立盲评 | task: 独立评估-index17真实-spawn-空上下文-AB-电池5-探针ONOF

## 1. 评估方法（本次独立）

index15（C8.81/E8.78/长期8.29/UX7.57，真实 spawn）+ index16（C9.00/E9.00/长期8.86/UX8.43，in-session）之后，index17 用**真实 `claude -p` 空上下文 A/B 电池**重新独立评估当前 HEAD 治理效能：

- **5 探针 × ON/OFF = 10 次真实调用**（复用 index15 四探针 + 新增 task-E：E8 长任务防遗忘 + C9 错误恢复），空目录 + transport 治理（ON）vs 裸空目录（OFF），同 prompt 对照，CALL_LIMIT=12、TIMEOUT=300s，全 exit 0。
- **8 场景 spawn 矩阵**（success/failure/empty_output/retry/timeout/cancel/empty_context/recovery）收敛。
- **独立原则**：评分仅依据本次 fresh 证据（S1 baseline + S2 十探针 + 矩阵 + S4/S6 机制修复），撰写 scorecard 前未读 index15/16 逐项明细；环比在末尾追加。

## 2. 评分摘要（盲评）

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **8.81 / 10** | 925/105；fresh 证据 |
| E1-E8 错误防护加权 | **9.00 / 10** | 990/110；fresh 证据 |
| C/E 综合 proxy | **8.90 / 10** | (8.81+9.00)/2 |
| 长期治理能力 | **8.71 / 10** | 7 项算术平均 |
| UX 独立 proxy | **8.14 / 10** | 7 项算术平均 |

## 3. 环比 index15 / index16

| 维度 | index15 | index16 | **index17** | Δ vs index16 |
|---|---:|---:|---:|---:|
| C1-C9 能力加权 | 8.81 | 9.00 | **8.81** | -0.19 |
| E1-E8 错误防护加权 | 8.78 | 9.00 | **9.00** | 0 |
| 长期治理能力 | 8.29 | 8.86 | **8.71** | -0.15 |
| UX 独立 proxy | 7.57 | 8.43 | **8.14** | -0.29 |

**口径说明**：index16 为 in-session 盲评（自身任务即样本），index15/17 为真实 spawn 空上下文口径；跨口径仅参考方向。index17 在真实 spawn 口径下：
- **E 维度 9.00 追平 index16**：10/10 调用零编造、零虚假完成、校准置信度、范围纪律完美。
- **C 维度 8.81**：执行使能（ON>>OFF）真实可复现；C6/C8 扣分源于 F2 规则冲突与 M1/M2/M3 维护债。
- **长期治理 8.71**：全磁盘状态 + 自动化 + Eval 框架强；学习管道未深测。
- **UX 8.14**：goal 模式 agentic 体验 + 诚实感强；仍文本化交互 + M2 状态噪音。

## 4. 机制缺陷修复（本轮从机制上修复）

| ID | 缺陷 | 根因 | 修复 | 证据 |
|----|------|------|------|------|
| M1 | verify_gate 断言词形敏感（exist/exists 拦截合法证据） | `_extract_core_terms` 原子词不归一 | `_canonical_atom` 尾 's' 归一 + ss/短词守卫（.claude/scripts/verify_gate.py） | test_verify_gate_wordform.py 5 测试红→绿 |
| M3 | step_contracts 依赖校验单依赖 bug（`depends_on: S2,S3,S4` 无法激活） | `find_first_activatable_step` + `start_step_atomic` 均只查单 id | `_deps_all_completed` 多依赖支持（.claude/scripts/step_contracts.py） | test_step_contracts_multidep.py 5 测试红→绿 |
| M2 | lock/token 无 spawn 夹具终结路径（44 active+lock / 12 stale_locks 残留） | 终结器仅覆盖 completed→terminal | **记录+建议**（清理属他任务状态，不越界） | S1 baseline-snapshot.json |

**全量回归：216 passed**（含 10 个新增回归测试）。

## 5. 关键治理发现（fresh 证据）

- **执行使能 = 权限契约**：ON 会话靠 settings.local.json allow `Bash(python3 *)` 兜底写文件完成任务；OFF 无该配置 0 文件创建。与 index11 结论一致。
- **诚实/防编造是治理+模型强项**：ON/OFF 十调用全部诚实披露、拒绝编造、拒绝凭记忆作答（task-E/OFF 拒答 add(2,3)）。E 维 9.00 为历轮最强且全程真实 spawn 验证。
- **hooks 在 spawn 会话真实触发**：ON 会话写 hook-evidence.jsonl/audit/read-tracker。
- **新探针 task-E 双命中**：C9 错误恢复（broken.py 语法错误→修复→exit 0）+ E8 防遗忘（第 5 步重跑验证而非凭记忆）。

## 6. 优化项（供后续决策）

| 级别 | 项 | 状态 |
|------|-----|------|
| P1 | **执行使能不可移植**：ON 效能依赖本机 settings.local.json allow-list（gitignored）。建议在 CLAUDE.md/AGENTS.md 声明 headless 权限契约或提供可提交 permissions 模板 | 呈交人类 |
| P1 | **AGENTS.md 规则自洽**：禁 inline python vs 权限受限下唯一可写路径冲突，task-B/E ON 均诚实披露偏离。建议补「权限受限回退」降级条款 | 呈交人类（冻结层） |
| P2 | **M2 状态噪音**：44 active+lock 残留。建议 carros_base.py 提供 `prune-stale-locks --dry-run` 供人类裁决清理 | 建议 |
| P2 | **scorecard-gate 工作集未含交付物路径**：Benchmarking/ 未声明即 REDIRECT（本轮已补声明）；建议模板默认含 Benchmarking/ 或审计类任务预声明 | 已规避 |
| P2 | 交互仍 CLI/text，路径契约为文本提示（非结构化注入） | UX 优化项 |
| P3 | temp 目录自动清理丢 ON 会话 hook-evidence 内容（方法学局限，后续 run_once 先拷贝再清理） | 记录 |

## 7. Item Manifest

> freshness: 2026-08-13 | 独立盲评（真实 spawn A/B）

| id | weight | score | id | weight | score |
|---|---:|---:|---|---:|---:|
| C1 | 15 | 9 | E1 | 20 | 9 |
| C2 | 15 | 9 | E2 | 20 | 9 |
| C3 | 15 | 9 | E3 | 15 | 9 |
| C4 | 10 | 9 | E4 | 12 | 9 |
| C5 | 10 | 9 | E5 | 10 | 9 |
| C6 | 10 | 8 | E6 | 13 | 9 |
| C7 | 10 | 9 | E7 | 10 | 9 |
| C8 | 10 | 8 | E8 | 10 | 9 |
| C9 | 10 | 9 | | | |
| G1 | 0 | 9 | U1 | 0 | 8 |
| G2 | 0 | 9 | U2 | 0 | 8 |
| G3 | 0 | 8 | U3 | 0 | 7 |
| G4 | 0 | 9 | U4 | 0 | 8 |
| G5 | 0 | 8 | U5 | 0 | 9 |
| G6 | 0 | 9 | U6 | 0 | 8 |
| G7 | 0 | 9 | U7 | 0 | 9 |
