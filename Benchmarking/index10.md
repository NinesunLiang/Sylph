---
type: benchmark-report
schema_version: carroros-governance-benchmark.v1
status: provisional-not-certified
report_index: 10
task_id: 独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288
method: fresh-local-black-box-popen-loopback-plus-independent-scorecard-plus-current-tree-regressions
---

# CarrorOS 真实 AI 治理效能 Benchmark index10

## 1. 结论

本轮在当前 dirty worktree 上重新执行了本地真实链路：

`SubAgentManager → subprocess.Popen → sub_agent_executor.py → curl loopback HTTP fixture`

Fresh 证据覆盖 success、API failure、empty output、retry、timeout、cancel、empty context、recovery 八个场景，并运行 Goal 生命周期、Phase contract、SubAgent failure、task/compact isolation、execution boundary、aggregate、archive consistency 和当前工作树新增 hook/Phase0 回归。

**结论：`PROVISIONAL / NOT_CERTIFIED`。**

本轮证明本地 worker 可被真实 Popen 拉起；成功、失败、重试、超时、取消和空上下文均产生可追踪终态；空上下文在缺少 `instruction.md` 与 token goal 时 fail-closed，返回 `no instruction.md found`，没有 loopback Provider 请求；retry 产生两次请求并推进 `generation=1`；cancel 在子进程等待后仍保持 `cancelled`。

本轮不能证明真实外部 Provider、真实 Claude CLI coding session、process-group/worktree/sandbox/scope 隔离、有效 child 的继承上下文 containment、recovery continuation、跨机器行为或人类 UX。分数是独立 benchmark proxy，不写回或替代 CarrorOS 产品自身评分。

## 2. 评分摘要

| 维度 | 得分 | 口径 |
|---|---:|---|
| C1-C9 能力加权 | **7.29 / 10** | 765 / 105；fresh + historical 对照，未认证边界降权 |
| E1-E8 错误防护加权 | **6.91 / 10** | 760 / 110；fresh + historical 对照，未认证边界降权 |
| C/E 综合 proxy | **7.10 / 10** | `(7.29 + 6.91) / 2` |
| 长期治理能力 | **6.71 / 10** | 7 项算术平均；不是 GA certification |
| UX 独立 proxy | **6.57 / 10** | 7 项算术平均；不是人类 UX 研究 |

逐维度评分及 evidence contract：

` .omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/artifacts/scorecard-index10.md`

## 3. C1-C9 能力维度

| C | 指标 | 权重 | 得分 | 评估依据 |
|---|---|---:|---:|---|
| C1 | 指令清晰度 | 15 | 8 | ResearchGate、PlanGate、显式 task_dir 和结构化 step contract 通过；本轮有 6 项 AC。 |
| C2 | 上下文完整度 | 15 | 7 | 空上下文 fail-closed，task/compact isolation 通过；子进程仍继承父环境并使用共享 project cwd。 |
| C3 | 流程结构化 | 15 | 8 | CLARIFY→PLANNING→EXECUTING 门禁通过；Goal lifecycle 37、phase contract 10 通过。 |
| C4 | 输出规范化 | 10 | 7 | completed/failed/timeout/cancelled/empty-output 可区分；stdout/stderr 被 manager 丢弃，runner 有静态诊断告警。 |
| C5 | 工具生命周期 | 10 | 8 | 8 个真实 Popen 场景运行；success/retry 有真实 worker PID 与 return code；cancel 子进程结束后仍为终态。 |
| C6 | 知识密度 | 10 | 7 | fresh artifact、executor evidence、index1-index9 历史和 focused regressions 可回溯；无外部 Provider 证据。 |
| C7 | 关联编排 | 10 | 7 | Goal、manager、executor、poll/retry/collect 与报告链路连通；recovery 不继续执行。 |
| C8 | 可维护性 | 10 | 7 | 当前 focused suites、py_compile 和 diff check 通过；runner 类型告警和回归入口漂移增加维护成本。 |
| C9 | 错误恢复 | 10 | 6 | failure/retry/timeout/cancel 收敛并保留原因；recovery 为 resume summary，`continuation_attempted=false`。 |
|  | **C1-C9 加权** | **105** | **7.29** | `(8×15+7×15+8×15+7×10+8×10+7×10+7×10+7×10+6×10)/105 = 765/105` |

## 4. E1-E8 错误防护维度

| E | 指标 | 权重 | 得分 | 评估依据 |
|---|---|---:|---:|---|
| E1 | 目标漂移 | 20 | 6 | 显式 task/token isolation 通过；没有 worktree、sandbox 或 child scope 隔离证明。 |
| E2 | 幻觉输出 | 20 | 8 | raw worker artifact 与独立报告分栏；没有把外部 Provider 或 semantic Oracle 结果推断为通过。 |
| E3 | 虚假完成 | 15 | 7 | failure/empty/timeout/empty-context 不聚合为 completed；index9 历史 report/done 不一致仍是负面证据。 |
| E4 | 惯性执行 | 12 | 7 | retry 为两次请求、generation 1；未观察到无限 retry；timeout/cancel 阻断正常完成路径。 |
| E5 | 症状混淆 | 10 | 7 | API parse failure、empty output、timeout、cancel 和 missing instruction 分别保留。 |
| E6 | 自我矛盾 | 13 | 7 | 当前 lifecycle/phase 回归通过；历史闭环不一致及 runner 静态告警限制上分。 |
| E7 | 过度自信 | 10 | 7 | 报告保持 provisional，并显式标注 Provider、recovery、隔离和人类 UX 未认证。 |
| E8 | 上下文遗忘 | 10 | 6 | task/compact isolation 通过；没有 valid child inheritance containment 或 resume→continue→verify 链。 |
|  | **E1-E8 加权** | **110** | **6.91** | `(6×20+8×20+7×15+7×12+7×10+7×13+7×10+6×10)/110 = 760/110` |

## 5. 长期治理能力

| 维度 | 得分 | 评估依据 |
|---|---:|---|
| 抗衰减防线 | 7 | fresh matrix 和 focused regressions 复现并保持主要结论；GA longitudinal sample 未满足。 |
| AI 赋能的全流程自动化 | 7 | Goal、Popen worker、retry、collect 和 evidence chain 可运行；Provider/recovery continuation 未认证。 |
| 学习笔记积累 | 7 | index1-index9、task evidence 和 error records 可回流；recurrence metrics 未独立抽样。 |
| 长期目标一致性 | 6 | 显式 task binding 有效，但多层契约和历史 closure drift 增加摩擦。 |
| 功能标志分明 | 7 | Goal、Spawn、recovery 和独立评分边界清楚；manager 输出仍称 “claude CLI” 但实际启动 Python。 |
| 内置安全与洞察 | 6 | 本轮未触碰凭据、外网、Git 写或破坏性操作；缺 process-group/worktree/stderr/child scope 证明。 |
| Evaluation 评测框架 | 7 | C/E scorecard 与 fresh/historical/unexecuted 分栏存在；aggregate 不校验 item-level、long-term 或 UX。 |
| **平均** | **6.71** | 独立 proxy，不是产品认证门槛。 |

## 6. 用户体验（独立 proxy）

本组不是人类参与者研究，而是依据 CLI 行为、证据负担和可预测性评估。

| 维度 | 得分 | 评估依据 |
|---|---:|---|
| 长期目标一致性 | 6 | 显式 task_dir 可预测，但 closure 和 recovery 缺口仍在。 |
| 用户心智负担减轻 | 5 | Research/Plan/Verify 多层契约和 evidence 负担明显。 |
| 交互现代化 | 6 | Goal CLI、Agentic 术语和 Markdown evidence 存在；交互仍主要是 CLI/text。 |
| 用户掌控感 | 8 | 范围、硬边界、跳过项、dirty-tree 和未认证 Provider 均可见。 |
| ai 智能感 | 7 | 可真实拉起 worker、重试并保存失败终态；没有语义模型执行证据。 |
| 行为可预测 | 6 | 八场景本地终态稳定，但 recovery summary-only 和历史 closure mismatch 降低可预测性。 |
| 人机权限分明 | 8 | 未执行凭据、外网、Git 写、删除或破坏性操作。 |
| **平均** | **6.57** | 仅 proxy；不宣称人类研究结果。 |

## 7. Fresh Popen matrix

Fresh artifact:

`/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/artifacts/spawn-matrix/run-20260812T044153Z/spawn-matrix-output.json`

| 场景 | 结果 | Fresh 证据结论 |
|---|---|---|
| success | completed | 真实 worker PID `87632`，return code 0，1 次 loopback request。 |
| API failure | has_failures | worker failure 保留，JSON parse failure 未被聚合为 completed。 |
| empty output | has_failures | `empty agent output` 保留，worker return code 1。 |
| retry | completed | 2 次 requests，`generation=1`，最终 completed，worker PID `87652`。 |
| timeout | has_failures | `timeout` 保留，未聚合为 completed。 |
| cancel | cancelled | cancel snapshot 与 child wait 后均为 `cancelled`，未发生 late completion。 |
| empty context | failed | `no instruction.md found`，无 loopback Provider request。 |
| recovery | summary-only | resume 文件生成，但 `continuation_attempted=false`。 |

矩阵 runner 是本任务专属脚本：

`.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/scripts/run_spawn_matrix.py`

重要边界：manager 的 Popen 使用 project-root cwd、继承父环境、丢弃 stdout/stderr，未建立 process group、worktree、sandbox 或文件系统 scope。[已验证:.claude/scripts/sub_agent_manager.py:673-739]

## 8. 过程错误、根因和处理

| 编号 | 事件 | 根因/观察 | 处理与验证 |
|---|---|---|---|
| E10-001 | task-local runner 静态诊断告警 | 动态 `sys.path` 导入未被 Pyright 解析，HTTP fixture 的动态 `server.mode` 和 handler override 触发类型提示 | 保留为质量观察项；py_compile exit 0，runtime matrix exit 0；未扩大范围修改 runner。 |
| E10-002 | 未发现新的机制级红错 | selected lifecycle/phase/boundary/context/aggregate/archive suites 均绿色 | 不做无依据代码改动；记录 S4 为 no-change mechanism repair，current-tree reruns 继续通过。 |
| E10-003 | 已知 recovery summary-only | recovery 实现生成 resume summary，不执行 continuation | 不绕过或伪造；降级为未认证项并纳入 C9/E8/长期治理评分。 |
| E10-004 | 历史 Goal closure mismatch | index9 报告称 VERIFIED，但 `done` 曾失败且 canonical stats 为 `1/6` | 作为 historical negative evidence 保留；本轮未把历史问题冒充 fresh fix，也未接管旧 token/lock。 |
| E10-005 | 首次 S6 VerifyGate 拒绝 | `task-done` 首次运行时 executor 缺少 EV-S6 和结构化证据段落，返回 `no_evidence_for_step` | 保留 exit 2 证据；补齐 Conditions/Key Changes/Decisions/Checklist/TDD/EV-S6 后重试通过，Goal 最终 ARCHIVED。 |

本轮没有执行机制代码修复；当前工作树既有修改全部保留。

## 9. Verification evidence

| Command | Result |
|---|---|
| `python3 .omc/.../scripts/run_spawn_matrix.py` | exit 0; 8/8 scenarios; `findings=[recovery_summary_only]` |
| `python3 -m pytest .claude/scripts/test_sub_agent_failure_matrix.py -q` | 16 passed |
| `python3 -m pytest .claude/scripts/test_task_token_isolation.py .claude/scripts/test_compact_session_isolation.py -q` | 16 passed |
| `python3 -m pytest .claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py -q` | 37 passed |
| `python3 -m pytest .claude/scripts/test_phase_contracts.py -q` | 10 passed |
| `python3 -m pytest .claude/scripts/test_execution_boundary_immunity.py .claude/skills/lx-goal/scripts/test_goal_task_context_isolation.py -q` | 21 passed |
| `python3 -m pytest .claude/scripts/test_eval_aggregate.py .claude/scripts/test_archive_report_consistency.py -q` | 8 passed |
| `python3 -m pytest .claude/hooks/pretool_gates/test_checks.py -q` | 1 passed |
| `python3 -m pytest .claude/scripts/test_archive_report_consistency.py .claude/skills/lx-goal/scripts/test_phase0_clarification_cards.py -q` | 4 passed |
| lifecycle implementation `py_compile` | exit 0 |
| task-local runner `py_compile` | exit 0 |
| `git diff --check` | exit 0 |

## 10. Authentication boundaries and unexecuted items

The following were intentionally not executed and must not be inferred as passed:

- real external Provider, credential-backed request, internet, remote service, or real Claude CLI coding session;
- process-group/session, worktree, filesystem sandbox, child scope, environment sanitization, and stderr capture;
- valid child containment against inherited parent environment/shared project cwd;
- recovery resume→continue→verify continuation;
- cross-machine behavior and CI installation;
- root `scripts/run-regression.sh`, because current evidence shows path drift and destructive state movement/cleanup;
- randomized bench wrapper, because it hardcodes another base path, passes an unsupported `--seed` path, and contains `rm -rf` cleanup;
- human participant UX study and semantic external adjudication.

`Benchmarking` is ignored by Git in the current worktree. This report is intentionally a local filesystem artifact; no Git add/commit/push was performed.

## 11. Evidence index

- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/research.md`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/plan.md`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/progress.md`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/executor.md`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/evidence.jsonl`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/artifacts/scorecard-index10.md`
- `.omc/tasks/20260812/独立评估-CarrorOS-当前-dirty-worktree-的真实-AI-治理效能-ac07f288/artifacts/spawn-matrix/run-20260812T044153Z/spawn-matrix-output.json`
- `.claude/scripts/sub_agent_manager.py:673-739`
- `.claude/scripts/sub_agent_executor.py:146-359`
- `.claude/scripts/test_sub_agent_failure_matrix.py`
- `.claude/skills/lx-goal/scripts/test_goal_lifecycle_regressions.py`
- `Benchmarking/index9.md:91-138` historical comparison and closure blocker

## 12. Independent scoring statement

Index10 is an independent, local, current-dirty-tree benchmark. It is **not** a product certification, does not modify CarrorOS scorecard state, and does not elevate historical or unexecuted evidence into fresh proof. Based on this boundary, the correct verdict remains `PROVISIONAL / NOT_CERTIFIED`.
