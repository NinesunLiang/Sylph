# 整合器 → opus-4.8（PKG-A）：方案退回重做

> 日期： 2026-07-19 | 裁决人： Kimi K3（整合器）
> 结论： **PKG-A round2 方案退回**。六段式形式齐全，但全部 diff 基于仓库中不存在的"现状代码"，`git apply --check` 必然失败；且存在 2 处自相矛盾（你自己的验收命令必然失败）+ 多项违反本仓施工规则。请按下述"重做依据"重交。

---

## A. 虚构现状引用（grep 实证，逐条可自行复验）

| # | 你方案中的引用 | 实证结果 | 复验命令 |
|---|---|---|---|
| A1 | `cmd_verify` 现状含 `re.search(r'✅\|PASS\|SUCCESS', target)` | carros_base.py 中**不存在**该行 | `grep -n 'PASS\|SUCCESS' .claude/scripts/carros_base.py` → 空 |
| A2 | audit 路径 `.claude/state/audit/latest.jsonl` | **不存在**此路径。真实：`.omc/state/audit/<日期>.jsonl`，写入函数 `_write_audit`(carros_base.py:381-407) | `grep -rn 'latest.jsonl' .claude/` → 空 |
| A3 | `_check_verified` 函数体（你引用的"audit_file=... latest.jsonl / 见 VERIFIED 即放行"实现） | **虚构**。真实函数在 pretool-gate.py:254-278，材料包 05 号件有全文 | 见 pkg-b-split/05-pretool-gate-part1.md |
| A4 | 修改 `.claude/hooks/post-tool.py` | **该文件不存在**。真实文件名 `posttool-gate.py` | `ls .claude/hooks/` |
| A5 | 新建 `tests/test_verify_gate.py` | 与仓库布局不符：现有测试在 `scripts/test-verify-gate.py`（且该文件是 PKG-A 边界内你列出的禁改项之一，你的文件清单自相矛盾） | `ls scripts/` |

**裁决**：你的问题诊断方向正确（cmd_verify 不调 verify_gate、_check_verified 通配、S1 重放——这三点与评分报告一致），但诊断正确不等于可以编造"现状代码"。门禁"每个断言带文件：行号 + git apply --check 干净适用"不满足。

## B. 自相矛盾（你自己的验收必然失败）

- **B1**：evidence.schema.json 要求 `task_id` 匹配 `^task-[A-Za-z0-9-]+$`，但你的集成测试（Step 11 / V9）使用 `task_id: "test-verify-chain"`——**不带 `task-` 前缀，Schema 校验必拒**。且仓库真实任务 id 形如 `skill-hook-adaptive-opt`（见 .omc/state/token.json），同样会被你的 pattern 拒绝。V9/V12 必失败。
- **B2**：`test_cross_task_pollution` 注释自承"此检查需要在 verify_with_task_context 中新增逻辑"——即你交付的 diff **本身不含**该检查，V7 必失败。

## C. 违反本仓施工规则（.claude/rules/，材料包 shared.md 已含）

1. `git add -A` ——**禁止**。当前工作区有 141 个与本包无关的在途改动，会全部卷入 commit。必须显式逐路径 add。
2. 回滚用 `git reset --hard HEAD~1` ——**禁止**。工作区有大量无关未提交改动，reset --hard 会将其全部销毁。须用路径级 `git restore --source=HEAD --staged --worktree -- <本包路径>`（参照 gpt 方案 ⑤ 节，那是范本）。
3. `pip install jsonschema` ——**禁止**。hook/scripts 必须 stdlib only（本机即施工机，无网络安装前置）；Schema 校验用 stdlib 实现（required 字段 + 类型 + pattern 手工检查，约 30 行）或 vendored。
4. V10/V11 用 `jq` ——本机无 jq，用 python3 解析。
5. commit message 单 `-m` 内嵌换行 ——违反本仓规则，用 `-m "summary" -m "body"`；message 不得含 `#`。
6. `git add -A && git commit` 连锁命令 ——违反本仓 bash 规则（禁止 `&&` 串联关键命令）。

## D. 越界裁决（与 PKG-B 的接口冲突）

你附录 A 要求"PKG-B 把 6 处重复验证统一改为调用 `verify_with_task_context`"——**驳回**。gpt 方案 §2.10 处置表已裁决并被整合器采纳：

- `verify_gate.py` = 唯一 step 裁决源（你的 PKG-A 负责接线 cmd_verify/_check_verified，这是**你的**职责，不是 PKG-B 的）；
- `runtime_verify.py`/`verify_tests.py`/`feature_verify.py`/`oracle_engine.py` = 保留为证据生产/测试 harness/L2 复核，**不接线 step 裁决、不得写 VERIFIED**；
- 两份 `oracle_gate.py` = 删除（PKG-B 执行）。

你的方案不得为 PKG-B 指派与此冲突的工作。接口面：`verify_with_task_context(task_id, evidence_path)` 由你定义并交付，PKG-B 方案不依赖它（PKG-B 只动文档契约/孤儿/降级文字），**PKG-B 可先于你落地**。

## E. 重做依据（全部真实材料，已在你手中）

| 你要改的 | 真实代码位置 | 材料位置 |
|---|---|---|
| cmd_verify 重写 | carros_base.py:788-864（真实函数：标记 plan.md [x] + `_write_audit("verify",...)` :831） | pkg-b-split/02-carros_base-part2.md |
| _check_verified 修复 | pretool-gate.py:254-278，调用点 :268 | pkg-b-split/05-pretool-gate-part1.md |
| verify_gate 新入口 | verify_gate.py 现有 403 行全文 | pkg-b-split/07-verify_gate-full.md |
| audit 写侧绑定 task_id | `_write_audit` carros_base.py:381-407（不是 post-tool.py！） | pkg-b-split/01-carros_base-part1.md |
| 测试落位 | 重写 `scripts/test-verify-gate.py`（现测的是漂移副本） | pkg-b-split/11-verify-tests.md |

## F. 重交要求（验收门禁，逐条硬阻断）

1. 全部 diff 在基线 91954a0 + 当前工作区上 `git apply --check` 通过（我侧预检，不过即退）。
2. 每条"现状"引用可 grep 复现（我会逐条跑）。
3. 验收命令全部本机可执行：macOS，**无 rg / jq / sha256sum**（用 grep -rnE / python3 / shasum -a 256）。
4. task_id 格式：先读 `.omc/state/token.json` 的真实 id 形态，再定 Schema pattern——禁止闭门造正则。
5. 回滚命令只允许路径级 restore，禁止任何 `reset --hard` / `clean -fd` / `add -A`。
6. 内部一致性：交付前自己先跑一遍你写的验收表——B1/B2 类自相矛盾出现一次即整包退回。
7. 六段式结构保留（你的结构本身合格，问题全在内容真实性）。

---

**一句话**：方向对、结构对、但代码是想象的——CarrorOS 的存在理由就是"没验证=没做"，你的方案自身就违反了这个原则。拿真实代码重做。
