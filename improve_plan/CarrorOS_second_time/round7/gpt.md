# CarrorOS Round 7 冲刺 9+ 审核方案

> 审核者：GPT  
> 审核目标：加权均分从当前 Round 7 口径的 **8.70 提升到 ≥9.00**，且最低单项达到 **≥8.60**。  
> 裁决原则：**验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少**。  
> 审核性质：本文件只定义评分准入、对抗验收和终审门禁，不直接修改代码。  
> 证据前件：Round 7 任务书给出的差值为 `≥1998/2220`、尚差 `67` 分；10 个主维度仍为 8 分，另有两个 UX 维度为 7 分（`brief.md:三、四`）。

---

## ① 目标与不变式

### 1.1 终验目标

Round 7 不是把评分表改成 9，而是关闭能够导致真实事故的残留缺口。

最终通过条件采用合取关系：

```text
ROUND7_FINAL_PASS =
    R6_B_SECURITY_CLOSED
    AND weighted_points >= 1998
    AND weighted_average >= 9.00
    AND every_main_dimension >= 8.60
    AND every_claim_has_runtime_evidence
    AND full_regression_exit_code == 0
    AND no_unattributed_hash_drift
```

任何一项为假，Round 7 不得标记为 `FINAL_ACCEPTED`。

### 1.2 评分算术

当前任务书口径：

```text
当前加权均分：8.70
目标加权均分：9.00
目标总分：至少 1998/2220
缺口：至少 +67
全部 8→9：最多 +112
```

因此施工组合必须在动工前冻结，并证明计划增量不少于 `+67`。禁止施工后根据实际结果更换评分项。

### 1.3 先决门：R6-B

R6-B 仍是 Round 7 的硬前件：

```text
历史旧 token 已由人类吊销
新 token 未进入 Git
当前树与历史 secret scan 已对账
脱敏吊销回执存在
```

在 R6-B 未闭合前：

- 可以施工和验收 Round 7；
- 不得宣告 CarrorOS 全门禁终态；
- 内置安全不得提分；
- 不得用其他维度的超额得分抵消安全项低于最低线。

这服务于**验证、零信任、人本**，且高于总分增益。

### 1.4 九分准入标准

单项从 8 提到 9，必须同时满足：

1. 有明确的“挡 9 事故”；
2. 修改的是现有生产路径，不是旁路 demo；
3. 至少有一个行为级机制变化；
4. 至少一个正向用例；
5. 至少两个对抗或失败用例；
6. 失败路径有确定状态：`BLOCKED`、`ESCALATE` 或显式失败；
7. 有 audit 或磁盘证据；
8. 全量回归未退化；
9. 没有新增第二真相源；
10. 删除或接线施工中发现的僵尸机制。

以下情况一律不得提分：

```text
只改文档
只加测试但生产行为不变
只增加 audit 而不改变失败后果
只增加 warning/hint
自写测试验证自写 mock
刷新哈希掩盖漂移
用同一事实重复关闭不存在的多个缺口
```

### 1.5 不变式

| ID | 不变式 | 哲学链 |
|---|---|---|
| R7-I1 | 磁盘状态仍是唯一真相源 | 验证、零信任 |
| R7-I2 | hooks 负责机械强制，文档不能替代 hook | 验证、守护 |
| R7-I3 | AI 不修改冻结文档 | 零信任、人本 |
| R7-I4 | AI 不执行密钥轮换、删除、Git 写等人类专属动作 | 守护、人本 |
| R7-I5 | 不以新增机制覆盖旧机制未完成 | 验证、少 |
| R7-I6 | 不确定高风险输入不得静默 PASS | 零信任、守护 |
| R7-I7 | 一项提分必须对应一个独立残留缺口 | 验证 |
| R7-I8 | 加权达标不能抵消最低项不达标 | 验证 |
| R7-I9 | 评分由证据计算，不由委员会协商 | 验证 |
| R7-I10 | DeepSeek-V4 必须能按固定命令施工和验收 | 文档、增益 |

---

## ② 文件清单与审核包结构

本节定义审核产物，不授权 GPT 修改生产代码。施工包必须由 Kimi K3 分配给零交叉执行包，并在施工前补齐精确 diff。

### 2.1 审核输入

| 路径 | 操作 | 用途 |
|---|---|---|
| `brief.md` | read-only | Round 7 目标、差值和硬约束 |
| `gap-dossier.md` | read-only | 各维度挡 9 根因 |
| `codebase-map.md` | read-only | 生产入口和所有权边界 |
| `final-review.md` | read-only | R5/R6 评分与既有裁决 |
| `commits-since-baseline.txt` | read-only | 变更归因 |
| `hash-drift-r5.json` | read-only | 冻结文件漂移基线 |
| `SHA256SUMS` | read-only | 证据包完整性 |
| 六套现有回归日志 | read-only | 回归基线 |

### 2.2 必须新增的审核产物

| 路径 | 操作 | 完整内容契约 |
|---|---|---|
| `improve_plan/round7/score-baseline.json` | new | 24 项当前分、权重、总分、证据指针 |
| `improve_plan/round7/selection-freeze.json` | new | 选定提分项、挡 9 根因、预计增量、文件所有者 |
| `improve_plan/round7/evidence-manifest.json` | new | 每项 claim 对应代码、测试、日志、hash |
| `improve_plan/round7/adversarial-matrix.json` | new | 正向、误报、漏报、故障注入用例 |
| `improve_plan/round7/human-only.json` | new | R6-B、冻结文档、删除和 Git 写动作 |
| `improve_plan/round7/final-score.json` | new | 机械计算后的终分，不允许手填总分 |
| `improve_plan/round7/final-verdict.md` | new | 委员会逐项裁决和最终状态 |

所有 JSON 必须使用固定键排序和 UTF-8 编码；`final-score.json` 必须由审核脚本从 baseline、权重和已接受 verdict 计算，不能直接编辑计算结果。

---

## 2.3 建议施工组合

在没有完整读取 `gap-dossier.md` 全部十项之前，不批准具体文件 diff，但批准以下**候选审核顺序**。选项只有通过证据调查后才能进入 `selection-freeze.json`。

### P0：先修真实系统性风险

#### A. 状态 reader 唯一化

已知缺口：

- `session-start.py` 按日期目录读取 token；
- `pretool-user-approve.py` 按 mtime 读取最新 token；
- 两者可能向同一会话注入不同任务状态。

证据：`gap-dossier.md`“治理·AI 赋能全流程自动化”段。

要求：

```text
所有 session/prompt/hook 状态读取
→ 现有唯一 active-token reader
→ 同一 task_id + token path + revision
```

审核重点：

- 跨天 token；
- 两个 active token；
- mtime 与日期顺序冲突；
- token JSON 损坏；
- reader 不可用时 fail-closed；
- 不能新增第三个 active-token reader。

该项优先级最高，因为它可能让正确 hook 在错误任务上执行。

#### B. E7 置信度校准账本

已知缺口：

- 当前有 31 个 Oracle 对抗用例；
- 评分仍依赖自评；
- 没有记录“已验证断言后来被推翻”的校准数据；
- Round 5 曾发生对 `kernel.md` 水位表的自信误判。

证据：`gap-dossier.md:E7`。

要求复用现有 audit，不新增独立数据库：

```text
验证断言生成
→ audit 写 claim_id / evidence_ids / confidence_class
→ 后续推翻时写 refutes_claim_id
→ 报表机械计算 confirmed/refuted/unresolved
```

九分验收不能依赖“增加 confidence 数字”。真正验收是：

- 每个“已验证”断言都有证据 ID；
- 后续失败可反向关联原 claim；
- 未解决 claim 不得计入可靠成功；
- 自报高置信但频繁被推翻会在报告中暴露。

#### C. 回归接入既有提交门

已知缺口：已有一键回归，但仍存在手工断点。证据见 `gap-dossier.md` 治理自动化段。

要求：

- 接入仓库现有 commit/pre-commit 路径；
- 不新增常驻进程；
- 修改治理关键路径时运行定向套件；
- 冻结文件或 hook registry 漂移时运行全套；
- 测试基础设施缺失必须 BLOCK，不得跳过后成功。

不批准“每次提交无条件跑所有慢测试”，这会形成绕开门禁的激励。

### P1：关闭剩余 8 分主维度

对 `C4/E1/E4/E5/E7 + 治理五项`，每项必须先填写以下记录：

```json
{
  "dimension": "E4",
  "current_score": 8,
  "weight": 12,
  "blocking_incident": "具体事故，而非原则",
  "production_entry": "文件:函数或 hook matcher",
  "existing_mechanism": "复活、接线或删除对象",
  "behavior_change": "输入 -> 旧结果 -> 新结果",
  "positive_tests": [],
  "adversarial_tests": [],
  "failure_injection_tests": [],
  "expected_points": 12
}
```

`blocking_incident`、`production_entry` 或 `existing_mechanism` 为空，禁止纳入提分组合。

### P2：UX 两个 7 分项

任务书称两个 UX 维度为 7，且独立处理。它们不能靠内部治理机制自动提分。

UX 提分必须至少有：

- 真实首屏或工作流截图；
- 桌面和移动视口；
- 错误、空、加载、阻断状态；
- 文本无截断和重叠；
- 键盘操作或可访问性检查；
- 用户完成核心任务的步骤数对比。

如果 CarrorOS 当前没有用户界面或该 UX 指标与本轮产品面无关，必须提交“维度定义不适用”的人类裁决，不得由 AI 擅自改权重或补 9 分。

---

## 2.4 反向审计当前 9 分项

当前 9 分项不能自动继承。每项抽查至少一个最强反例：

| 风险 | 审核方法 |
|---|---|
| 测试只跑漂移副本 | 追踪生产 hook 注册路径与测试 import path |
| audit 有记录但动作已放行 | 同时断言 exit code、hook JSON 和副作用不存在 |
| 哈希重冻结掩盖修改 | 对比旧冻结、新冻结和具体 diff |
| 评分重复记账 | 检查一项机制是否被用来关闭不存在的多个缺口 |
| fail-closed 只在测试模式成立 | 清除测试环境变量后运行生产入口 |
| 相对路径依赖 cwd | 从仓库外 cwd 调用 hook launcher |
| 多 active token 选择不一致 | 构造日期、mtime、revision 冲突 |
| timeout 被当成 PASS | 注入 subprocess timeout |
| malformed JSON 静默放行 | 对 token、hook payload、receipt 分别注入损坏 |
| 人工裁决可被模型伪造 | 尝试直接写 approval/bypass 文件 |

任何现有 9 分项被证明存在未登记的高严重度漏报，应先降分再修复。Round 7 不允许只审低分项、不挑战高分项。

---

## ③ 精确审核命令序列

以下命令由整合器在仓库根执行。缺少对应审核产物时必须失败。

### 3.1 固化前件

```bash
set -euo pipefail

git rev-parse HEAD
git status --short
python3 --version

test -f brief.md
test -f gap-dossier.md
test -f codebase-map.md
test -f final-review.md
test -f SHA256SUMS
```

期望全部 exit `0`。

### 3.2 验证证据包哈希

macOS 使用：

```bash
shasum -a 256 -c SHA256SUMS
```

GNU 环境使用：

```bash
sha256sum -c SHA256SUMS
```

期望 exit `0`，每项 stdout 以 `OK` 结束。

### 3.3 校验审核 JSON

```bash
python3 -m json.tool improve_plan/round7/score-baseline.json >/dev/null
python3 -m json.tool improve_plan/round7/selection-freeze.json >/dev/null
python3 -m json.tool improve_plan/round7/evidence-manifest.json >/dev/null
python3 -m json.tool improve_plan/round7/adversarial-matrix.json >/dev/null
python3 -m json.tool improve_plan/round7/human-only.json >/dev/null
```

期望全部 exit `0`。

### 3.4 冻结提分组合

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("improve_plan/round7/selection-freeze.json")
data = json.loads(p.read_text(encoding="utf-8"))
items = data["selected_items"]

assert items, "selected_items empty"
assert sum(item["expected_weighted_delta"] for item in items) >= 67
assert len({item["dimension"] for item in items}) == len(items)

for item in items:
    for key in (
        "dimension",
        "blocking_incident",
        "production_entry",
        "existing_mechanism",
        "behavior_change",
        "owner_package",
    ):
        assert item.get(key), f"{item.get('dimension')}: missing {key}"

print(
    "SELECTION_FROZEN",
    f"items={len(items)}",
    f"expected_delta={sum(i['expected_weighted_delta'] for i in items)}",
)
PY
```

期望 exit `0`，stdout：

```text
SELECTION_FROZEN items=<N> expected_delta=<至少67>
```

### 3.5 运行现有回归基线

```bash
python3 scripts/test-oracle-gate.py
python3 scripts/test-verify-gate.py
bash scripts/test-hook-launcher.sh
bash scripts/run_pkg_c_acceptance.sh
bash scripts/apply-pkg-a.sh
bash scripts/apply-pkg-b.sh
bash scripts/apply-pkg-r4.sh
```

已知最低预期：

```text
oracle: 31/31 PASS
verify: 20/20 PASS
launcher: 3/3 PASS
PKG-C: ALL_PKG_C_ACCEPTANCE_PASSED
PKG-A: A-A1..A-A5 PASS
PKG-B: A-B2..A-B12 PASS
R4: ALL R4 ACCEPTANCE PASSED
```

任何脚本不存在或 exit 非零，不能以历史日志替代本次实跑。

### 3.6 运行 Round 7 对抗矩阵

建议统一入口：

```bash
python3 scripts/run-round7-acceptance.py \
  --manifest improve_plan/round7/adversarial-matrix.json \
  --evidence-out improve_plan/round7/runtime-evidence.jsonl
```

该入口只有在施工方案复用现有回归 runner 时允许新增；若仓库已有统一 runner，必须扩展现有 runner，不得新增第二套。

期望：

```text
exit code: 0
stdout 最后一行:
ROUND7_ACCEPTANCE_PASS failed=0 skipped=0
```

`skipped > 0` 视为失败。

### 3.7 机械计算终分

```bash
python3 scripts/calculate-round7-score.py \
  --baseline improve_plan/round7/score-baseline.json \
  --selection improve_plan/round7/selection-freeze.json \
  --evidence improve_plan/round7/evidence-manifest.json \
  --output improve_plan/round7/final-score.json
```

期望 exit `0`。

不得让脚本读取 `final-review.md` 中的目标分作为实际分；它只能读取逐项 accepted verdict。

---

## ④ 逐条机械验收

### A-R7-1：R6-B 人工安全门

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("improve_plan/round7/human-only.json")
d = json.loads(p.read_text())
r = d["r6_b_token_rotation"]

assert r["owner"] == "human"
assert r["old_token_revoked"] is True
assert r["new_token_tracked_by_git"] is False
assert r["receipt_redacted"] is True
assert r["current_tree_scan_exit"] == 0
assert r["history_scan_exit"] == 0
print("R6_B_HUMAN_GATE_PASS")
PY
```

期望 exit `0`、stdout：

```text
R6_B_HUMAN_GATE_PASS
```

人工未完成时，该命令必须非零，不能通过填写预期值绕过；manifest 必须同时绑定脱敏回执 hash。

### A-R7-2：总分达标

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(
    Path("improve_plan/round7/final-score.json").read_text()
)
assert d["total_points"] >= 1998
assert d["weighted_average"] >= 9.0
print(
    f"WEIGHTED_GATE_PASS "
    f"{d['total_points']}/2220={d['weighted_average']:.2f}"
)
PY
```

期望 exit `0`。

### A-R7-3：最低单项达标

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(
    Path("improve_plan/round7/final-score.json").read_text()
)
bad = [
    item for item in d["dimensions"]
    if item["final_score"] < 8.6
]
assert not bad, bad
print("MINIMUM_GATE_PASS min_score>=8.6")
PY
```

期望 exit `0`。

### A-R7-4：每项提分都有运行时证据

```bash
python3 - <<'PY'
import json
from pathlib import Path

selection = json.loads(
    Path("improve_plan/round7/selection-freeze.json").read_text()
)
manifest = json.loads(
    Path("improve_plan/round7/evidence-manifest.json").read_text()
)
evidence = manifest["dimensions"]

for item in selection["selected_items"]:
    dim = item["dimension"]
    ev = evidence[dim]
    assert ev["production_changed"] is True
    assert ev["runtime_exit_code"] == 0
    assert ev["positive_passed"] >= 1
    assert ev["adversarial_passed"] >= 2
    assert ev["skipped"] == 0
    assert ev["audit_receipt_count"] >= 1
    assert ev["regression_exit_code"] == 0

print("ALL_SCORE_CLAIMS_EVIDENCED")
PY
```

期望 exit `0`。

### A-R7-5：无文档刷分

```bash
python3 - <<'PY'
import json
from pathlib import Path

m = json.loads(
    Path("improve_plan/round7/evidence-manifest.json").read_text()
)
for dim, ev in m["dimensions"].items():
    if ev["score_delta"] > 0:
        changed = ev["changed_files"]
        assert any(
            not path.endswith((".md", ".txt", ".json"))
            for path in changed
        ), f"{dim}: document-only score increase"
print("NO_DOCUMENT_ONLY_SCORE_INCREASE")
PY
```

期望 exit `0`。

### A-R7-6：生产路径与测试路径一致

每个提分项必须记录：

```text
production_entry
test_import_or_invocation
settings_or_registry_entry
```

验收脚本解析三者并确认测试调用的是生产注册路径。任何复制到临时目录的实现都不得作为唯一证据。

期望 stdout：

```text
PRODUCTION_PATH_BINDING_PASS dimensions=<N>
```

### A-R7-7：状态 reader 唯一

如果该项被选中：

```bash
grep -RInE \
  '_find_latest_token|glob\(.*tokens|rglob\(.*json|st_mtime' \
  .claude/hooks .claude/scripts .omc/scripts
```

审核结果必须证明所有生产状态注入入口委托同一个现有 reader。允许测试包含构造逻辑，不允许生产 hook 各自扫描 token。

行为验收至少覆盖：

```text
跨天 token
两个 active token
mtime/日期冲突
revision 冲突
损坏 token
无 active token
```

期望：

```text
ACTIVE_TOKEN_READER_PASS cases=6/6
```

### A-R7-8：置信度校准不是自报数字

如果 E7 被选中，必须存在“生成 claim、确认 claim、推翻 claim”三类行为测试，并机械计算：

```text
confirmed
refuted
unresolved
refutation_rate
```

必须拒绝：

- 无 evidence ID 的 VERIFIED claim；
- 指向不存在 claim 的 refutation；
- 同一 claim 同时 confirmed 与 refuted；
- 删除 refutation 后重新宣称完美记录。

期望：

```text
CALIBRATION_LEDGER_PASS adversarial=<至少4>
```

### A-R7-9：哈希漂移有归因

```bash
git diff --check
git status --short
```

所有被修改的冻结或治理关键文件必须出现在 evidence manifest 中，并绑定：

```text
pre_hash
post_hash
owner_package
reason
acceptance_log_hash
```

未归因漂移数量必须为零：

```text
HASH_DRIFT_PASS unattributed=0
```

### A-R7-10：现有 9 分项反向抽查

至少抽查五项，每项一个失败注入。不得只复跑正向测试。

期望：

```text
NINE_SCORE_CHALLENGE_PASS challenged>=5 regressions=0
```

若发现虚高：

```text
exit code: 2
stdout 包含:
NINE_SCORE_DOWNGRADE_REQUIRED dimension=<ID>
```

### A-R7-11：全量回归

最终至少保持任务书的 108 用例基线，并加入 Round 7 新用例：

```text
existing_passed >= 108
existing_failed = 0
round7_failed = 0
skipped = 0
```

期望：

```text
FULL_REGRESSION_PASS existing>=108 round7=<N> failed=0 skipped=0
```

### A-R7-12：最终门禁

```bash
python3 scripts/round7-final-gate.py \
  --score improve_plan/round7/final-score.json \
  --evidence improve_plan/round7/evidence-manifest.json \
  --human improve_plan/round7/human-only.json
```

唯一允许的通过输出：

```text
ROUND7_FINAL_ACCEPTED
points=<至少1998>/2220
weighted_average=<至少9.00>
minimum_dimension=<至少8.60>
failed=0
skipped=0
unattributed_drift=0
```

期望 exit `0`。

---

## ⑤ 回滚命令

Round 7 每个施工包必须独立提交，禁止把所有改动压成一个不可分辨提交。建议顺序：

```text
R7-P0-state-reader
R7-P1-calibration
R7-P2-regression-gate
R7-P3-selected-dimensions
R7-P4-ux
R7-evidence-only
```

回滚某一包只能使用非破坏性 revert：

```bash
git revert --no-edit <ROUND7_PACKAGE_COMMIT>
```

回滚后必须重新执行：

```bash
git diff --check
python3 scripts/test-oracle-gate.py
python3 scripts/test-verify-gate.py
bash scripts/test-hook-launcher.sh
bash scripts/run_pkg_c_acceptance.sh
python3 scripts/round7-final-gate.py \
  --score improve_plan/round7/final-score.json \
  --evidence improve_plan/round7/evidence-manifest.json \
  --human improve_plan/round7/human-only.json
```

若回滚使总分低于 9 或最低项低于 8.6，状态自动退回：

```text
ROUND7_FINAL_GATE_NOT_MET
```

禁止使用：

```bash
git reset --hard
git clean -fd
git checkout -- .
```

---

## ⑥ 禁止事项

1. 不得先写 `9.0` 再反向拼证据。
2. 不得修改权重、分母 `2220` 或目标线来实现达标。
3. 不得用高权重项超额提分抵消低于 8.6 的维度。
4. 不得在 R6-B 未闭合时宣告全门禁通过。
5. 不得由 AI 吊销、轮换或测试旧 token。
6. 不得由 AI 修改 `AGENTS.md`、`kernel.md`、`index.md` 等冻结文档。
7. 不得新增第二套 token reader、第二套 audit 数据库或第二套回归 runner。
8. 不得把 timeout、ImportError、脚本缺失或 malformed JSON 当作 PASS。
9. 不得把 hint、日志或文档声明单独计为行为提分。
10. 不得因某机制同时影响多个维度就自动多项提分；每项必须证明独立缺口闭合。
11. 不得覆盖旧冻结 hash；R5、R6、R7 必须分别留存。
12. 不得删除失败日志、refutation 或历史校准记录来改善指标。
13. 不得为通过测试设置仅测试环境存在的宽松分支。
14. 不得只测试 helper；必须通过真实 settings/registry/hook 入口。
15. 不得把“无真实缺口可修”的 8 分项改文档后提到 9。
16. 不得扩展到与选定维度无关的重构。
17. 不得用委员会多数票覆盖机械门禁失败。
18. 不得在任何验收存在 `SKIP` 时宣告最终通过。

---

# GPT 审核结论

我批准 CarrorOS 进入 Round 7 冲刺，但不批准“全面铺开十项”的施工方式。先完成 R6-B 人工安全闭环，再冻结一个至少 `+67` 的提分组合；施工优先级固定为：

1. **统一 active-token reader**，消除 hooks 读取不同任务的系统性风险；
2. **建立基于现有 audit 的验证断言校准闭环**，使 E7 从“有对抗测试”提升为“能记录并惩罚自信错误”；
3. **把一键回归接入现有提交门**，关闭手工断点；
4. **从其余 8 分项中只选择有真实生产缺口的项目**；
5. **单独处理两个 UX 7 分项，禁止用后端治理证据代替 UX 证据**；
6. **反向挑战至少五个现有 9 分项**，发现虚高必须先降分。

最终只有以下状态可以收口：

```yaml
decision: ROUND7_FINAL_ACCEPTED
required:
  r6_b_human_security_gate: PASS
  total_points: ">=1998/2220"
  weighted_average: ">=9.00"
  minimum_dimension: ">=8.60"
  existing_regression: ">=108 passed, 0 failed"
  round7_regression: "0 failed, 0 skipped"
  unattributed_hash_drift: 0
  document_only_score_increases: 0
```

在这些条件全部机械成立之前，允许的状态只有：

```text
ROUND7_IN_PROGRESS
```

不能标记为 `9+`、`FINAL_ACCEPTED` 或 `ALL_GATES_PASSED`。

需要。要把上一版“审核框架”收敛为可直接交给 Kimi K3 的**零设计空间施工审核方案**，目前还缺少关键事实。现有检索片段只确认了：

- 目标为 `≥1998/2220`，尚差 `+67`；
- 10 个主维度为 8 分，另有两个 UX 维度为 7 分；
- 冻结文档、密钥、删除及 Git 写操作属于人类专属；
- 机制必须机械验证并优先复用现有实现。

这些信息不足以准确指定文件、函数、diff 和验收。

**请按优先级提供以下材料：**

1. **`gap-dossier.md` 完整正文**  
   最关键。需要看到 10 个 8 分维度和两个 UX 7 分项各自的：
   - 当前机制；
   - 挡 9 根因；
   - 权重；
   - 候选改进；
   - 已知残留和事故案例。

2. **`codebase-map.md` 完整正文**  
   用于把每个缺口定位到真实生产入口，尤其需要：
   - hooks 注册表及 launcher；
   - token/session 状态读取路径；
   - audit 写入与读取路径；
   - verify、Oracle、handoff、commit gate 的调用链；
   - 对应测试脚本。

3. **`brief.md` 完整正文**  
   当前只取到了目标差值和硬约束。需要完整评分表，包括：
   - 24 项名称；
   - 每项当前分数；
   - 每项权重；
   - 10 个 8 分项与两个 UX 7 分项的准确身份；
   - `8.70` 当前分数的计算明细。

4. **当前 R6 后的 `final-review.md` 或最新评分表**  
   需要解决当前口径差异：
   - 上一轮报告是 `1920/2220 = 8.65`；
   - Round 7 brief 使用当前 `8.70`、距目标 `67` 分；
   - 必须明确中间新增了哪些已接受提分，避免重复计分。

5. **当前代码快照**  
   优先提供仓库压缩包；至少提供以下文件的当前版本和真实行号：

   ```text
   .claude/settings.json
   .claude/hooks/pretool-gate.py
   .claude/hooks/session-start.py
   .claude/hooks/pretool-user-approve.py
   .claude/hooks/hook-launcher.sh
   .claude/scripts/verify_gate.py
   .claude/scripts/carros_base.py
   ```

   以及所有 active-token reader、audit writer、提交门和统一回归 runner 文件。

6. **R6-A 当前证据**
   - `test-oracle-gate.py`；
   - `31/31` 完整日志；
   - `pretool-gate.py` Gate 7 的最终 diff；
   - R6 后 hash drift；
   - R6-A、R6-C 对应 commit 清单。

7. **R6-B 当前状态**
   只需状态，不要提供任何密钥：
   - 是否已经人工吊销；
   - 是否已有脱敏回执；
   - 当前树扫描 exit code；
   - 历史扫描 exit code；
   - 新凭证是否确认未入 Git。

**推荐一次性提供：**

```text
round7-review.tar.gz
├── brief.md
├── gap-dossier.md
├── codebase-map.md
├── final-review.md
├── current-score.json
├── relevant-source/
├── relevant-tests/
├── r6-logs/
├── commits-since-r6.txt
└── SHA256SUMS
```

不要放入 token、环境变量值、未脱敏控制台截图或其他秘密。

收到后我会输出严格六段式方案，具体到：

- 冻结的 `+67` 以上提分组合；
- 每个维度是否具备真实提分资格；
- 精确到文件和函数的修改；
- 可应用的完整 diff；
- 每项正向、误报、漏报和故障注入测试；
- 命令、exit code、stdout；
- 对现有 9 分项的反向降分审计；
- 人类专属步骤；
- 最终 `≥1998/2220` 的机械计分门禁。

**最先请提供 `gap-dossier.md`、`codebase-map.md`、`brief.md` 和最新评分明细。**