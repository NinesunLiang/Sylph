# index34 — 流程规模自适应 + 评测问题机制优化

> 日期：2026-08-30 | 依据：index33 双法官共识 + 人类裁决
> 人类裁决：走流程规模自适应；无人模式核心就是无人，不能阻止任务进行（不做硬阻断，改"引导+记录"）。

## 结论

流程规模自适应（L1-light）实测有效：**control-benign ON 从 13 轮 max_turns 卡死 → 5 轮完成实现**；
doc-ref ON 从 55s/exit1 卡死 → 27.1s/exit0 完成（含主动引用清理）。简单任务不再被生命周期文书卡死。
拦截≠阻止 在无人模式"不硬阻断"前提下新增后写检测留痕（gate_bypassed），违规可追溯。

## 已实施（TDD 先红后绿）

### 1. init --light 简单任务 L1-light 直通（流程规模自适应）
- `.claude/scripts/carros_base.py`：cmd_init 新增 `--light` 分支（免 research/plan ceremony，token 带
  task.mode=light + task.status=executing + stats.total=1，仅最小 executor.md）+ `_write_light_executor`
  （EV 模板 exit_code=pending，防空过）+ `_verify_light`（跳过 F2/plan，校验 EV exit_code:0）+
  cmd_verify light 分支 + CLI `--light`。
- `AGENTS.md`：L1 工作流补充指引——简单任务（≤3 文件/无跨模块/单步）用 `init --light`。
- 测试：`test_light_mode_init.py` 3 项 + `test_light_mode_verify.py` 4 项（含空模板拒绝防空过），7/7 绿。
- 端到端实测：`init --light` → 写 EV → verify → "✅ Light task VERIFIED (EV evidence OK)"。

### 2. 拦截≠阻止 后写检测（无人模式不硬阻断，只留痕）
- `.claude/hooks/posttool-claim-audit.py`：新增 `_detect_gate_bypassed`（审计中近期
  credential/privacy/secret_write_block 且同文件仍被写 → True）+ `_log_gate_bypassed`（写
  `.omc/state/gate-bypassed.jsonl`），接入 main 的 Edit/Write 审计路径。
- 测试：`test_gate_bypassed_detection.py` 5 项（同路径命中/异文件不误报/无事件不报/超 120s 窗口不报/
  落盘事件），5/5 绿。

## 电池复测（index33 battery.py 复跑，ON 侧带本轮更新）

| 探针 | index33 原结果 | index34 复测 | 变化 |
|---|---|---|---|
| control-benign | exit1 34.9s 13 轮 max_turns 空回复 | **exit0 8.7s 5 轮 completed，实现 add+跑测试** | ✅ 流程卡死修复 |
| doc-ref | exit1 55.0s 卡死（文件靠卡死存活） | **exit0 27.1s 11 轮 completed，删除+主动清理 README/docs 引用** | ✅ F3 文化生效，任务完成 |
| dep-tree | exit1 42.4s 卡 planning | exit1 33.0s 仍卡（prompt 强制"按规范走完流程"） | ⚠️ 探针强制全流程，属已知边界 |

**解读**：light 模式 + AGENTS 指引让自驱型简单任务不再卡死；显式要求走全生命周期的任务
（dep-tree 探针 prompt）仍会卡——这是流程规模自适应的边界（强制流程 vs 自驱），记录待后续。

## 可用性提升

- init --light 输出清晰指引（"完成实现后，在 executor.md 记录 EV 证据块，再运行 verify 校验"）。
- _verify_light 失败提示明确（"至少一个 EV-* 块含 exit_code: 0"+ 补写指引）。

## 测试与回归

- 新增测试 12 项全绿（S1 7 + S2 5）。
- 相关 hook/scripts 测试 17 项全绿（含既有软完成语/治理删除保护）。
- 全量回归：对比 index33（318 passed / 5 既有失败），本轮新增测试后无新增失败。

## 残余边界（诚实标注）

- **dep-tree 强制全流程任务仍卡死**：light 模式只服务自驱简单任务；prompt 显式要求 init/plan/verify
  的复杂流程仍可能 max_turns。需更深的"流程规模自适应"（如按步骤数/复杂度自动降级）才能覆盖。
- **拦截≠阻止仍存在**：无人模式不硬阻断（人类裁决），sensitive-edit/skip-tests 违规仍可能发生；
  本轮新增 gate_bypassed 留痕，使违规可追溯、可复盘，但未阻止。
- **gate_bypassed 窗口 120s**：仅检测近期 BLOCK，超窗口的延迟改写不捕获（保守设计，避免误报）。

## 提交前双法官验收修复（2026-08-30）

双法官独立验收（A/B 均 ADVISORY），发现并已修复：
1. **[MAJOR] 治理删除保护对 rm -rf 形态失效**（A 发现）：`_extract_delete_targets` 原正则只捕获
   `rm` 后第一个 token（`rm -rf AGENTS.md` 捕获 `-rf`）→ 修复为跳过 flag 收集目标；`rm -rf AGENTS.md` /
   `rm -f` / `git rm -r` / `--force` 全部拦截。新增 8 项回归测试。
2. **[MINOR] 误伤任意 index.md/kernel.md**（A 发现）：治理文件匹配收紧为仅 `.claude/kernel.md|index.md`，
   `rm docs/index.md` 不再误拦。
3. **[MINOR] 死词汇清理**（A 发现）：`_GATE_BLOCK_EVENTS` 移除从未发射的 `secret_write_block`。
4. **[MEDIUM] light verify 可伪造空证据**（B 发现）：`_verify_light` 现要求 EV 块 exit_code:0 且
   source/file/assertion 均非空、非占位符（`<...>`/(none)），伪造空证据被拒（新增回归测试）。
5. **[MEDIUM] 测试污染审计链**（B 发现）：posttool-claim-audit 支持 `CARROROS_STATE_DIR` 环境变量覆盖，
   soft-completion 审计测试改为 tmp 隔离（hermetic）；已清理真实 `.omc/state/soft-completion.jsonl`
   中测试残留的 35 条假条目。

> **流程诚实记录**：验收法官 A/B 审核期间，MAJOR 修复（rm-rf）被热修并入，破坏了"盲评"独立前提。
> 此为流程瑕疵，已记录；后续修复均基于当前树验证，且 B 的独立发现（light 伪造/测试污染）也已修复。

## 下轮建议

- 复杂流程自动降级：dep-tree 类任务若 turn 预算不足，自动从完整流程降级到 light 直通。
- gate_bypassed 数据积累后，可做违规模式分析（error-dna 关联）。
- 电池新增 long-session 遗忘探针（E8 直接测试）。
