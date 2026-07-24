CarrorOS Round 7「9+」审核方案——材料准入裁决版

状态：方案边界已确定，但当前上下文不足以签发可施工 diff
裁决者：GPT
基线：R6 官方并账提交 6dcfb90（证据：supplement-round2.md:§二.4）
当前分：1931/2220 = 8.70（证据：supplement-round2.md:§二.3）
目标：≥1998/2220 = 9.00，至少增加 67 分（证据：brief.md:§三）
前置纠错

上一版未完成的长方案不得施工。其中存在以下不可接受问题：

在没有逐行源码的情况下构造了 session-start.py、pretool-user-approve.py 和 verify_gate.py 的 hunk，不能证明 git apply --check 可通过。
拟新增 active_token_reader.py，但材料只证明存在两个 reader，尚未证明哪个现有 reader应成为唯一来源；这违反“优先复活现有机制，不新增机制覆盖旧机制”。
拟新增 calibration-report.py、audit-query.py 等文件，但没有先证明现有 audit/report runner 无法承载这些职责。
只选择部分 8 分项，不能满足 brief.md:§三 的“10 个主 rubric 8 分项全部要动”条件。
把“一份改动影响多个指标”直接等同于多项提分，没有逐项证明独立残留缺口闭合。
测试中出现“注释说应由生产代码阻断，但测试本身只检查测试数据”的自证逻辑，不能作为机械证据。
没有真实源码行号，因此违反 CarrorOS 的证据文化。
以下方案先机械冻结正确的审核边界；只有提取真实、带行号的源码后，Kimi 才能把第二段替换为可应用 diff。

① 目标与不变式

1.1 双目标

Round 7 必须同时通过：



weighted_points >= 1998
AND
10 个主 rubric 的 8 分项全部达到 >= 8.6
已知需处理的主项为：



C4
E1
E4
E5
E7
治理项 × 5
证据：brief.md:§三。

两个 UX 7 分项独立处理，不得由后端 hook 改动代替 UX 证据；证据同为 brief.md:§三。

1.2 算术不变式

当前：



C = 935/1050
E = 938/1100
G = 58/70
Total = 1931/2220 = 8.70
证据：supplement-round2.md:§二.3、current-score.json。

目标增量：

1998 - 1931 = 67

但是，+67 只是总分必要条件，不是充分条件。由于 10 个主项全部为 8，任何一个仍停留在 8，都不能满足主项最低 8.6 门禁。

因此 Round 7 的选择规则不是“选择权重合计至少 67 的若干项”，而是：



10 个主 8 分项全部必须有独立提分裁决
且被接受的加权增量合计 >= 67
1.3 安全前件

R6-B 仍属于人类独占操作。AI 不得：

吊销旧 token；
生成或轮换新 token；
调用旧 token 测活；
接触明文 token；
伪造控制台回执。
冻结文档、rm、Git 写、密钥和明文 token 均为物理禁区；证据：brief.md:§四.1-2。

R6-B 未闭环时可以完成 Round 7 的代码施工和测试，但不得输出：



FINAL_ACCEPTED
ALL_GATES_PASSED
CARROROS_9_PLUS_CLOSED
1.4 生产不变式

ID	不变式	服务哲学
R7-I1	磁盘状态是唯一真相源	验证、零信任
R7-I2	同一状态不能有两个独立选择算法	验证、零信任
R7-I3	hook 机械后果不能由文档提示替代	验证、守护
R7-I4	解析失败和证据缺失不能记为成功	验证、零信任
R7-I5	不新增第二套 reader、audit store 或 regression runner	验证、少
R7-I6	僵尸机制必须接线或删除	验证、文档
R7-I7	每个提分项必须关闭独立事故路径	验证
R7-I8	测试必须调用生产入口	验证、零信任
R7-I9	冻结文档只能由人类裁决	人本、守护
R7-I10	分数由 accepted evidence 计算，不能手填	验证
1.5 十项审核方向

下表只冻结审核目标，不预先批准实现：

维度	必须证明的 9 分事实	禁止的伪提分
C4	同一状态只有一种规范写格式；旧格式仅兼容读或正式删除	只补格式说明
E1	运行中操作绑定当前 task/step/revision，漂移被机械阻断或升级	只输出“目标可能漂移”提示
E4	已完成、失败或等待人类状态不能因惯性继续推进	只记录继续执行日志
E5	根因证据与症状描述分离；无根因证据不得宣称已修复	只要求模型写 root cause
E7	VERIFIED claim 必须绑定证据；后续反证可关联原 claim	只增加自报 confidence 数字
治理·自动化	所有生产入口使用同一 active-token 选择契约	新增第三个 reader
治理·内置安全	人工吊销旧 token，当前树和历史扫描闭环	AI 代办或仅清理当前树
治理·文档质量	运行时契约与文档漂移可检测；冻结文档仍由人类修改	AI 自动改冻结文档
治理·可观测性	BLOCK/ESCALATE/VERIFY 可按 task/step/claim 追溯	新建第二套 audit 数据库
治理·模块化	hook 通过明确公共边界调用，不复制状态解析和策略	只移动文件或改名字
② 文件清单：路径 → 操作 → 精确内容

2.1 本轮允许进入调查集的文件

路径	操作	用途
session-start.py	inspect；预计 edit	active-token reader 使用方
pretool-user-approve.py	inspect；预计 edit	active-token reader 使用方
carros_base.py	inspect；预计 edit	公共函数和 audit writer 候选 SSOT
verify_gate.py	inspect；预计 edit	claim/evidence 验证生产路径
pretool-gate.py	inspect；预计 edit	E1/E4/E5/E7 机械门
hook-launcher.sh	inspect；仅在 cwd/错误透传存在缺口时 edit	hook 生产入口
run-regression.sh	inspect；预计 edit	唯一回归 runner
statusline.py	inspect；仅作状态消费方	不得成为第二真相源
settings.json	inspect-only	本地私有、不得重新纳入 Git
test-oracle-gate.py	inspect；预计 edit	Gate 7 对抗回归
current-score.json	inspect-only	当前评分基线
gap-dossier.md	inspect-only	各项挡 9 根因
codebase-map.md	inspect-only	生产入口和所有权
brief.md	inspect-only	目标与禁区
settings.json 已移出版本控制并由 .gitignore 防回潮；证据：commits-since-r6.txt:1-2。因此 Round 7 不得把它重新添加到提交包。

2.2 当前唯一可签发的新审核文件

在未获得真实源码行号前，只批准新增一个施工输入快照，不批准生产代码 diff。

路径：



improve_plan/round7/source-evidence.txt
操作：

new

该文件必须由以下机械命令生成，不能人工编辑：



{
  for f in \
    session-start.py \
    test-oracle-gate.py \
    carros_base.py \
    settings.json \
    verify_gate.py \
    pretool-user-approve.py \
    run-regression.sh \
    hook-launcher.sh \
    pretool-gate.py \
    statusline.py \
    gap-dossier.md \
    codebase-map.md \
    brief.md \
    current-score.json
  do
    printf '\n===== FILE: %s =====\n' "$f"
    nl -ba "$f"
  done
} > improve_plan/round7/source-evidence.txt
如果真实文件带目录，必须使用仓库中 git ls-files 返回的精确路径，禁止猜测。

2.3 为什么此刻不签发生产 diff

当前注入给 GPT 的检索结果只有：

文件名称；
brief.md 的目标和约束片段；
supplement-round2.md 的材料索引；
commits-since-r6.txt；
若干旧 PKG-B 片段。
没有返回以下文件的逐行正文：



session-start.py
pretool-user-approve.py
carros_base.py
verify_gate.py
pretool-gate.py
run-regression.sh
因此无法机械保证：

git apply --check

任何此刻声称“精确 diff 可直接应用”的方案都属于无证据猜测，自动违反“验证 > 零信任”。

2.4 后续 diff 的冻结规则

Kimi 在生成 source-evidence.txt 后，必须按以下规则分包，文件集不得交叉：

PKG-R7-A：状态真相源与自动化

候选所有权：



session-start.py
pretool-user-approve.py
carros_base.py
对应 reader 测试
要求：

在两个既有 reader 中确定一个公共实现；
公共实现可复用则接线；
非公共实现删除其重复逻辑；
禁止新增第三个选择算法；
malformed、duplicate、missing 状态的行为必须确定。
PKG-R7-B：行为治理

候选所有权：



pretool-gate.py
test-oracle-gate.py
覆盖：



E1
E4
E5
E7
要求四项分别有独立事故与独立测试，不能仅凭同一个 BLOCK 用例四项一起提分。

PKG-R7-C：验证、可观测性与模块化

候选所有权：



verify_gate.py
hook-launcher.sh
run-regression.sh
对应测试
覆盖：



治理·可观测性
治理·模块化
治理·文档质量的漂移检测部分
C4 的验证契约部分
HUMAN-R7

仅人类可操作：



R6-B token 吊销与轮换
冻结文档修改
rm
git add/commit/revert
UX 人类评审
③ 精确命令序列

3.1 定位真实路径



set -euo pipefail

git rev-parse --show-toplevel
git rev-parse HEAD
git status --short

git ls-files | grep -E \
'(^|/)(session-start\.py|test-oracle-gate\.py|carros_base\.py|settings\.json|verify_gate\.py|pretool-user-approve\.py|run-regression\.sh|hook-launcher\.sh|pretool-gate\.py|statusline\.py|r6a-evidence\.md|supplement-round2\.md|current-score\.json|commits-since-r6\.txt|README\.md|codebase-map\.md|gap-dossier\.md|brief\.md)$' \
| LC_ALL=C sort
期望 exit 0。

settings.json 因已移出版本控制，可能不在 git ls-files 输出；这不是失败。它必须通过下节单独检查。

3.2 验证 settings 安全状态



test -f settings.json || test -f .claude/settings.json

if git ls-files --error-unmatch settings.json >/dev/null 2>&1; then
  echo "FAIL: settings.json tracked"
  exit 2
fi

if git ls-files --error-unmatch .claude/settings.json >/dev/null 2>&1; then
  echo "FAIL: .claude/settings.json tracked"
  exit 2
fi

git check-ignore -v settings.json 2>/dev/null ||
git check-ignore -v .claude/settings.json
期望 exit 0，最后一条 stdout 必须显示由 .gitignore 规则命中。

3.3 生成带行号证据

先由上一步结果确定真实路径，然后执行：



mkdir -p improve_plan/round7

FILES="$(
  git ls-files | grep -E \
  '(^|/)(session-start\.py|test-oracle-gate\.py|carros_base\.py|verify_gate\.py|pretool-user-approve\.py|run-regression\.sh|hook-launcher\.sh|pretool-gate\.py|statusline\.py|r6a-evidence\.md|supplement-round2\.md|current-score\.json|commits-since-r6\.txt|README\.md|codebase-map\.md|gap-dossier\.md|brief\.md)$' \
  | LC_ALL=C sort
)"

: > improve_plan/round7/source-evidence.txt

for f in $FILES; do
  printf '\n===== FILE: %s =====\n' "$f" \
    >> improve_plan/round7/source-evidence.txt
  nl -ba "$f" >> improve_plan/round7/source-evidence.txt
done

test -s improve_plan/round7/source-evidence.txt
期望 exit 0。

3.4 扫描重复机制



grep -RInE \
'active.*token|token.*active|rglob\(.*json|glob\(.*json|st_mtime|mtime|date.*dir|sort.*token' \
.claude .omc scripts 2>/dev/null \
> improve_plan/round7/token-reader-sites.txt || true

grep -RInE \
'audit|jsonl|claim_id|evidence_ids|VERIFIED|BLOCKED|ESCALATE' \
.claude .omc scripts 2>/dev/null \
> improve_plan/round7/audit-sites.txt || true

grep -RInE \
'run-regression|test-oracle-gate|verify-gate|hook-launcher' \
.claude .omc scripts .githooks 2>/dev/null \
> improve_plan/round7/regression-sites.txt || true

test -s improve_plan/round7/token-reader-sites.txt
test -s improve_plan/round7/audit-sites.txt
test -s improve_plan/round7/regression-sites.txt
期望 exit 0。

3.5 建立当前回归基线

使用材料确认的唯一 runner：

bash run-regression.sh

如果真实路径不是仓库根：



RUNNER="$(git ls-files | grep '/run-regression\.sh$' | head -n 1)"
test -n "$RUNNER"
bash "$RUNNER"
期望 exit 0。

禁止以历史日志代替本次实跑。

3.6 生成施工补丁

施工者完成各零交叉包后，只允许生成 patch，不得由 AI 执行 Git 写：



git diff -- \
  <PKG-R7-A-文件列表> \
  > improve_plan/round7/pkg-r7-a.patch

git diff -- \
  <PKG-R7-B-文件列表> \
  > improve_plan/round7/pkg-r7-b.patch

git diff -- \
  <PKG-R7-C-文件列表> \
  > improve_plan/round7/pkg-r7-c.patch
补丁必须在干净基线副本中检查：



git apply --check improve_plan/round7/pkg-r7-a.patch
git apply --check improve_plan/round7/pkg-r7-b.patch
git apply --check improve_plan/round7/pkg-r7-c.patch
期望全部 exit 0。

④ 逐条机械验收

A-R7-01：评分基线一致



python3 - <<'PY'
import json
from pathlib import Path

p = next(Path(".").rglob("current-score.json"))
d = json.loads(p.read_text(encoding="utf-8"))

text = json.dumps(d, sort_keys=True)
assert "1931" in text, text
assert "2220" in text, text

print("R7_SCORE_BASELINE_PASS points=1931 denominator=2220")
PY
期望 exit 0，stdout：



R7_SCORE_BASELINE_PASS points=1931 denominator=2220
如果 JSON 采用分项而非总数字字段，最终脚本必须根据真实 schema 重写为字段求和，禁止仅字符串搜索作为终验；上述命令仅用于材料准入。

A-R7-02：十个主项全部入选

最终提分清单必须包含：



C4
E1
E4
E5
E7
governance_automation
governance_builtin_security
governance_documentation
governance_observability
governance_modularity
验收：



python3 - <<'PY'
import json
from pathlib import Path

p = Path("improve_plan/round7/selection-freeze.json")
d = json.loads(p.read_text(encoding="utf-8"))

expected = {
    "C4", "E1", "E4", "E5", "E7",
    "governance_automation",
    "governance_builtin_security",
    "governance_documentation",
    "governance_observability",
    "governance_modularity",
}
actual = {x["dimension"] for x in d["selected_items"]}

assert actual == expected, {
    "missing": sorted(expected - actual),
    "unexpected": sorted(actual - expected),
}
print("R7_ALL_MAIN_DIMENSIONS_SELECTED count=10")
PY
期望 exit 0。

A-R7-03：不存在第三个 active-token reader

施工前先把 reader 生产入口写入：



improve_plan/round7/token-reader-sites.txt
施工后执行相同扫描。验收脚本必须证明：



reader_definition_count = 1
production_callers >= 2
duplicate_scanners = 0
期望 stdout：



ACTIVE_TOKEN_SSOT_PASS definitions=1 callers>=2 duplicates=0
任何调用方仍自行使用 rglob/glob + mtime/date 选择 token，验收失败。

A-R7-04：reader 故障矩阵

必须通过生产入口覆盖：

无 active token；
单一有效 token；
跨天 token；
同 task 多 token；
malformed JSON；
revision 冲突；
显式 task 与 token task 不一致；
从仓库外 cwd 启动。
期望：



ACTIVE_TOKEN_ADVERSARIAL_PASS cases=8 failed=0 skipped=0
不得通过测试重新实现一遍选择算法。

A-R7-05：E1 目标漂移

必须证明：



payload.task_id != active_token.task_id → BLOCK/ESCALATE
payload.step_id != active_step → BLOCK/ESCALATE
payload.revision < disk.revision → BLOCK/ESCALATE
同时证明匹配状态正常 PASS。

期望：



E1_GOAL_DRIFT_PASS positive>=1 adversarial>=3
A-R7-06：E4 惯性执行

至少覆盖：



task=DONE 后继续写 → BLOCK
step=BLOCKED_HUMAN 后继续执行 → BLOCK/ASK_USER
前一步验证失败后推进下一步 → BLOCK
有效 active step 正常执行 → PASS
期望：

E4_INERTIA_GUARD_PASS cases=4

A-R7-07：E5 症状与根因

只有当现有 task/verify schema 已存在根因字段或 evidence 分类时才能接线；不得另建第二套 diagnosis store。

必须证明：



仅有 symptom evidence → 不得 VERIFIED_FIXED
root-cause claim 无 evidence ID → BLOCK
根因证据与修复验证齐全 → PASS
期望：

E5_ROOT_CAUSE_GATE_PASS cases=3

A-R7-08：E7 断言可反证

必须复用现有 audit writer；只有现有 schema 无法表示关联时，才允许在同一 JSONL entry 中增加字段。

最少覆盖：



VERIFIED 无 evidence_ids → BLOCK
refutation 指向不存在 claim → BLOCK
原 claim 后续被反证 → audit 可关联
同一 claim 同时 confirmed/refuted → 状态冲突失败
期望：

E7_CALIBRATION_PASS cases=4

禁止新增独立 calibration 数据库。

A-R7-09：C4 写格式唯一

机械扫描所有 token、handoff、receipt 的生产 writer：



grep -RInE \
'write_text|json\.dump|json\.dumps|yaml\.dump|open\(.*["'\'']w' \
.claude .omc scripts 2>/dev/null
提分条件：



同一状态类型只有一个 canonical writer
兼容 reader 不得反写旧格式
malformed legacy 状态不得静默规范化为有效状态
期望：



C4_CANONICAL_WRITE_PASS duplicate_writers=0
A-R7-10：治理·可观测性

不得以“新增查询脚本”单独提分。生产 audit 必须包含足够关联字段：



timestamp
event
task_id
step_id
decision
reason
claim 类事件还必须包含：



claim_id
evidence_ids
验收：



OBSERVABILITY_TRACE_PASS task_to_step=PASS step_to_claim=PASS claim_to_evidence=PASS
A-R7-11：治理·模块化

必须证明：



状态选择算法定义数 = 1
audit writer 定义数 = 1
回归 runner 定义数 = 1
hook launcher 生产入口 = 1
兼容 wrapper 可以存在，但只能委托公共实现，不能复制策略。

期望：



MODULE_BOUNDARY_PASS duplicated_policy=0
A-R7-12：治理·文档质量

冻结文档不得由 AI 修改。文档质量提分只能来自：

生产 registry 与文档声明可机械对账；
漂移时失败；
人类批准后才修改冻结文档。
验收首先检查冻结文件无 AI diff：



git diff --exit-code -- \
  '**/AGENTS.md' \
  '**/kernel.md' \
  '**/index.md'
期望 exit 0。

如需要更新冻结文档，状态必须是：

BLOCKED_HUMAN_DOCUMENT_UPDATE

不能由其他提分抵消。

A-R7-13：内置安全

必须由人类提供脱敏证据后执行：



旧 token 已吊销
新 token 未跟踪
当前树扫描通过
历史扫描已对账
settings.json 保持 ignored/untracked
AI 不得自行验证旧 token 有效性。

期望：



R6_B_SECURITY_PASS owner=human secret_material_exposed=0
A-R7-14：现有 9 分项反向抽查

至少抽查：

VerifyGate 生产入口是否真接线；
Oracle Gate 是否可被 shell 变体绕过；
hook launcher 是否从外部 cwd 工作；
malformed hook payload 是否 fail-closed；
handoff JSON 与展示层是否一致。
期望：



NINE_SCORE_CHALLENGE_PASS challenged=5 downgraded=0
发现真实漏报时必须先降分，修复后才能恢复。

A-R7-15：总分和最低线

最终评分必须从逐项 verdict 计算：



points >= 1998
10 个主项 final_score >= 8.6
R6-B = PASS
期望：



ROUND7_SCORE_PASS points>=1998/2220 main_min>=8.6
A-R7-16：全量回归



bash "$(git ls-files | grep '/run-regression\.sh$' | head -n 1)"
期望 exit 0，且：



failed=0
skipped=0
R6 已有的 Oracle 31/31、VerifyGate 20/20、launcher 3/3 均不得退化；这些


# CarrorOS Round 7「9+」审核方案（续）

> 以下内容从上一版 **④ A-R7-16：全量回归** 的中断处继续；不重复前四节。  
> 上一版末句应补全为：R6 已有 Oracle `31/31`、VerifyGate `20/20`、launcher `3/3` 均不得退化；这些数字来自既有 R6 验收材料，不得替代本轮实跑证据。

---

## ④ 逐条机械验收（续）

### A-R7-16：全量回归

先定位仓库中唯一的回归入口：

```bash
set -euo pipefail

mapfile -t REGRESSION_RUNNERS < <(
  git ls-files |
  grep -E '(^|/)run-regression\.sh$' |
  LC_ALL=C sort
)

test "${#REGRESSION_RUNNERS[@]}" -eq 1 || {
  printf 'FAIL: expected exactly one tracked run-regression.sh, got %s\n' \
    "${#REGRESSION_RUNNERS[@]}" >&2
  printf '%s\n' "${REGRESSION_RUNNERS[@]}" >&2
  exit 2
}

REGRESSION_RUNNER="${REGRESSION_RUNNERS[0]}"
bash "$REGRESSION_RUNNER" |
tee improve_plan/round7/full-regression.log

test "${PIPESTATUS[0]}" -eq 0
```

期望：

```text
exit code: 0
stdout 末尾包含:
回归结果: <pass> 过 / 0 败 (共 <pass> 套件)
```

`run-regression.sh` 自身已经以 `rc_all` 汇总套件状态，并在失败时输出：

```text
ERROR: 存在失败套件,逐套日志见 /tmp/carros-regression.*.log
```

随后以 `exit "$rc_all"` 返回。这一现有聚合机制必须保留，不得新增第二个总回归 runner。

机械检查日志：

```bash
python3 - <<'PY'
import re
from pathlib import Path

p = Path("improve_plan/round7/full-regression.log")
text = p.read_text(encoding="utf-8")

matches = re.findall(
    r"回归结果:\s*(\d+)\s*过\s*/\s*(\d+)\s*败\s*"
    r"\(共\s*(\d+)\s*套件\)",
    text,
)
assert len(matches) == 1, (
    "expected exactly one regression summary, "
    f"found {len(matches)}"
)

passed, failed, total = map(int, matches[0])
assert failed == 0, matches[0]
assert passed == total, matches[0]
assert total > 0, matches[0]

print(
    f"FULL_REGRESSION_PASS "
    f"passed={passed} failed={failed} total={total}"
)
PY
```

期望 exit `0`，stdout：

```text
FULL_REGRESSION_PASS passed=<N> failed=0 total=<N>
```

#### 裁决规则

1. 历史日志只能用于确认基线，不能代替本轮日志。
2. runner 中任何被选中的套件缺失，必须失败，不能打印 warning 后继续。
3. `SKIP`、`XFAIL` 或“未安装依赖”不能折算成 PASS。
4. `/tmp/carros-regression.*.log` 只用于定位失败，最终证据必须复制到 Round 7 evidence 目录并计算 SHA-256。
5. 该项服务**验证**；若与速度或便利性冲突，速度和便利性自动让位。

---

### A-R7-17：测试必须绑定生产入口

禁止测试复制生产判定逻辑后自证。每个提分维度必须在 manifest 中声明：

```json
{
  "dimension": "E1",
  "production_entry": "真实路径:真实符号",
  "registered_entry": "真实 settings/launcher 注册路径",
  "test_entry": "真实测试路径:真实用例",
  "invocation_kind": "subprocess_or_import_production_symbol"
}
```

验收：

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("improve_plan/round7/evidence-manifest.json")
data = json.loads(path.read_text(encoding="utf-8"))
items = data["dimensions"]

required = {
    "C4",
    "E1",
    "E4",
    "E5",
    "E7",
    "governance_automation",
    "governance_builtin_security",
    "governance_documentation",
    "governance_observability",
    "governance_modularity",
}

assert set(items) == required, {
    "missing": sorted(required - set(items)),
    "unexpected": sorted(set(items) - required),
}

for dimension, evidence in items.items():
    for key in (
        "production_entry",
        "registered_entry",
        "test_entry",
        "invocation_kind",
    ):
        assert evidence.get(key), f"{dimension}: missing {key}"

    assert evidence["invocation_kind"] in {
        "subprocess_production_entry",
        "import_production_symbol",
    }, f"{dimension}: invalid invocation_kind"

print("PRODUCTION_TEST_BINDING_PASS dimensions=10")
PY
```

期望 exit `0`，stdout：

```text
PRODUCTION_TEST_BINDING_PASS dimensions=10
```

此外必须对测试源码执行反向检查。出现以下模式时，整合器必须检查其是否复制了生产策略：

```bash
grep -RInE \
'def (find|select|resolve)_.*token|st_mtime|rglob\(.*json|glob\(.*json|decision *=|BLOCK.*PASS' \
scripts .claude 2>/dev/null |
tee improve_plan/round7/test-policy-scan.txt
```

该命令本身允许 exit `0` 或 `1`；最终验收脚本必须逐条对账。任何测试文件中重新实现 token 选择、Oracle 分类或 verify 判定，即：

```text
PRODUCTION_TEST_BINDING_FAIL copied_policy=<path:line>
```

并以 exit `2` 失败。

---

### A-R7-18：故障注入不能静默放行

对所有本轮改动的生产入口，至少注入以下故障：

| 故障 | 必须结果 |
|---|---|
| malformed hook payload | BLOCK 或非零退出 |
| malformed token JSON | BLOCK 或非零退出 |
| audit writer 写入失败 | 不得将动作记为成功 |
| subprocess timeout | BLOCK/ESCALATE，不得 PASS |
| production module ImportError | hook 整体失败 |
| active state 缺失 | 明确 PASS、BLOCK 或 no-active 契约；不得伪造状态 |
| registry 指向不存在脚本 | 回归失败 |
| evidence 文件不存在 | VERIFIED 被拒绝 |

Round 7 统一故障测试必须输出：

```text
FAILURE_INJECTION_PASS cases=8 failed=0 skipped=0
```

执行命令由真实 runner 路径决定，但终验固定为：

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("improve_plan/round7/failure-injection-result.json")
d = json.loads(p.read_text(encoding="utf-8"))

assert d["total"] >= 8, d
assert d["failed"] == 0, d
assert d["skipped"] == 0, d
assert d["silent_pass"] == 0, d

required = {
    "malformed_hook_payload",
    "malformed_token_json",
    "audit_write_failure",
    "subprocess_timeout",
    "production_import_error",
    "active_state_missing",
    "missing_registered_script",
    "missing_evidence",
}
actual = {x["id"] for x in d["cases"]}
assert required <= actual, sorted(required - actual)

print(
    f"FAILURE_INJECTION_PASS "
    f"cases={d['total']} failed=0 skipped=0"
)
PY
```

期望 exit `0`。

该项服务**验证、零信任、守护**。任何仅在正常路径成立的“9 分机制”不得提分。

---

### A-R7-19：僵尸机制清零

施工中识别出的重复 reader、旧 writer、废弃 matcher、未注册 hook 或未调用脚本，必须二选一：

```text
接入唯一生产路径
或
提交人类删除清单
```

由于删除属于人类专属，AI 不得执行 `rm`。AI 只允许生成：

```text
improve_plan/round7/human-delete-manifest.json
```

格式固定为：

```json
{
  "schema_version": 1,
  "entries": [
    {
      "path": "真实路径",
      "reason": "被哪个唯一来源替代",
      "references_before": 0,
      "registered_before": false,
      "owner": "human",
      "status": "PENDING_HUMAN_DELETE"
    }
  ]
}
```

若没有待删除项：

```json
{
  "schema_version": 1,
  "entries": []
}
```

机械验收：

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("improve_plan/round7/zombie-mechanism-report.json")
d = json.loads(p.read_text(encoding="utf-8"))

assert d["unresolved"] == 0, d
assert d["connected"] + d["pending_human_delete"] == d["found"], d

print(
    "ZOMBIE_MECHANISM_PASS "
    f"found={d['found']} "
    f"connected={d['connected']} "
    f"pending_human_delete={d['pending_human_delete']} "
    "unresolved=0"
)
PY
```

注意：

- `pending_human_delete > 0` 时，工程包可以验收；
- 在人类实际删除并重跑回归前，不得宣告最终 9+ 收口；
- 禁止把僵尸文件留在原处并仅加 `deprecated` 注释。

---

### A-R7-20：冻结文件和 settings 安全不回潮

#### 冻结文档

```bash
set -euo pipefail

git diff --exit-code -- \
  ':(glob)**/AGENTS.md' \
  ':(glob)**/kernel.md' \
  ':(glob)**/index.md'
```

期望 exit `0`、无 stdout。

如确需修改，必须进入：

```text
BLOCKED_HUMAN_DOCUMENT_UPDATE
```

#### settings.json

已有提交记录表明：

- `settings.json` 已移出版本控制；
- `.gitignore` 防回潮；
- 后续由 owner 手工去重 ignore 条目。

证据：`commits-since-r6.txt` 中 `61ad241` 与 `9cc7278`。

机械验收：

```bash
set -euo pipefail

if git ls-files |
   grep -Eq '(^|/)settings\.json$'; then
  echo "FAIL: settings.json is tracked" >&2
  exit 2
fi

SETTINGS_PATH=""
for candidate in settings.json .claude/settings.json; do
  if test -f "$candidate"; then
    SETTINGS_PATH="$candidate"
    break
  fi
done

test -n "$SETTINGS_PATH" || {
  echo "FAIL: local settings.json not found" >&2
  exit 2
}

git check-ignore -q "$SETTINGS_PATH"

echo "SETTINGS_UNTRACKED_IGNORED_PASS path=$SETTINGS_PATH"
```

期望 exit `0`，stdout：

```text
SETTINGS_UNTRACKED_IGNORED_PASS path=<真实路径>
```

不得把本地 `settings.json` 内容复制进 evidence 包。只允许记录：

```text
路径
tracked=false
ignored=true
脱敏后的 hook 名称对账
文件 SHA-256（仅在 hash 本身不构成敏感信息时）
```

---

### A-R7-21：未归因 hash drift 为零

生成施工后的受管文件清单：

```bash
git diff --name-only |
LC_ALL=C sort \
> improve_plan/round7/changed-files.txt
```

每个文件必须在 evidence manifest 中绑定：

```text
owner_package
dimension
pre_hash
post_hash
reason
acceptance_log
```

验收：

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

changed = {
    line.strip()
    for line in Path(
        "improve_plan/round7/changed-files.txt"
    ).read_text(encoding="utf-8").splitlines()
    if line.strip()
}

manifest = json.loads(
    Path(
        "improve_plan/round7/evidence-manifest.json"
    ).read_text(encoding="utf-8")
)

records = {
    item["path"]: item
    for item in manifest["changed_files"]
}

missing = changed - set(records)
extra = set(records) - changed

assert not missing, {"unattributed": sorted(missing)}
assert not extra, {"not_actually_changed": sorted(extra)}

for path in sorted(changed):
    item = records[path]
    for key in (
        "owner_package",
        "dimension",
        "pre_hash",
        "post_hash",
        "reason",
        "acceptance_log",
    ):
        assert item.get(key), f"{path}: missing {key}"

    current = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert current == item["post_hash"], {
        "path": path,
        "manifest": item["post_hash"],
        "actual": current,
    }

    assert Path(item["acceptance_log"]).is_file(), {
        "path": path,
        "missing_log": item["acceptance_log"],
    }

print(
    f"HASH_DRIFT_PASS "
    f"changed={len(changed)} unattributed=0"
)
PY
```

期望 exit `0`。

禁止覆盖 R5 或 R6 原 hash 基线。R7 必须建立独立文件，例如：

```text
improve_plan/round7/hash-drift-r7.json
```

---

### A-R7-22：包间文件集零交叉

三个施工包的文件清单：

```text
improve_plan/round7/pkg-r7-a.files
improve_plan/round7/pkg-r7-b.files
improve_plan/round7/pkg-r7-c.files
```

验收：

```bash
python3 - <<'PY'
from pathlib import Path

names = ("a", "b", "c")
sets = {}

for name in names:
    path = Path(f"improve_plan/round7/pkg-r7-{name}.files")
    values = {
        x.strip()
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    }
    assert values, f"PKG-{name.upper()} file set empty"
    sets[name] = values

for i, left in enumerate(names):
    for right in names[i + 1:]:
        overlap = sets[left] & sets[right]
        assert not overlap, {
            "packages": [left, right],
            "overlap": sorted(overlap),
        }

print(
    "PACKAGE_FILE_OWNERSHIP_PASS "
    f"A={len(sets['a'])} "
    f"B={len(sets['b'])} "
    f"C={len(sets['c'])} "
    "overlap=0"
)
PY
```

期望 exit `0`。

测试文件也属于文件所有权范围，不能由两个包共同修改。若一个公共测试 runner 必须纳入多包测试，由整合器建立单独的 integration patch；三个施工模型不得同时编辑它。

---

### A-R7-23：补丁可干净应用

在人类准备的干净 worktree 或临时 clone 中执行。不得在有未提交改动的工作树直接验收。

```bash
set -euo pipefail

for patch in \
  improve_plan/round7/pkg-r7-a.patch \
  improve_plan/round7/pkg-r7-b.patch \
  improve_plan/round7/pkg-r7-c.patch
do
  test -s "$patch"
  git apply --check "$patch"
done

echo "ROUND7_PATCH_CHECK_PASS patches=3"
```

期望 exit `0`，stdout：

```text
ROUND7_PATCH_CHECK_PASS patches=3
```

如果存在整合器专属 integration patch，则固定追加：

```bash
test -s improve_plan/round7/pkg-r7-integration.patch
git apply --check improve_plan/round7/pkg-r7-integration.patch
```

此时期望：

```text
ROUND7_PATCH_CHECK_PASS patches=4
```

不能通过刷新 patch 上下文掩盖施工包建立在错误基线上的事实。若 hunk 不适用，包必须回到原施工者重做。

---

### A-R7-24：评分不能手填

`final-score.json` 必须从以下三类输入计算：

1. `current-score.json`；
2. 逐项 verdict；
3. 固定权重。

每个提分项只有 verdict 为 `ACCEPT` 才可增加分数。

终验：

```bash
python3 - <<'PY'
import json
from decimal import Decimal
from pathlib import Path

score = json.loads(
    Path("improve_plan/round7/final-score.json")
    .read_text(encoding="utf-8")
)

assert score["denominator"] == 2220, score
assert score["total_points"] == sum(
    item["final_points"]
    for item in score["dimensions"]
), score

accepted_delta = sum(
    item["weighted_delta"]
    for item in score["dimensions"]
    if item["verdict"] == "ACCEPT"
)
rejected_delta = sum(
    item["weighted_delta"]
    for item in score["dimensions"]
    if item["verdict"] != "ACCEPT"
)

assert score["total_points"] == 1931 + accepted_delta, score
assert rejected_delta == 0, (
    "non-accepted dimension carries score delta",
    rejected_delta,
)

average = (
    Decimal(score["total_points"]) /
    Decimal(score["denominator"]) *
    Decimal(10)
)
reported = Decimal(str(score["weighted_average"]))
assert abs(average - reported) < Decimal("0.000001"), {
    "calculated": str(average),
    "reported": str(reported),
}

print(
    "SCORE_RECOMPUTE_PASS "
    f"points={score['total_points']}/2220 "
    f"average={reported}"
)
PY
```

期望 exit `0`。

> 如果 `current-score.json` 的真实评分算法不是“基线 1931 + accepted weighted delta”，整合器必须根据其真实 schema 修改计算脚本；不得保留与真实评分模型不一致的上述公式。修改依据必须标注 `current-score.json:行号`。

---

### A-R7-25：Round 7 最终合取门

最终门禁必须同时检查：

```text
R6-B 人类安全门通过
10 个主项全部 >=8.6
总分 >=1998/2220
全量回归 0 失败
Round 7 对抗测试 0 失败、0 跳过
未归因漂移 = 0
未处置僵尸机制 = 0
冻结文档无未授权修改
settings.json 未跟踪且被忽略
```

固定执行：

```bash
python3 scripts/round7-final-gate.py \
  --score improve_plan/round7/final-score.json \
  --evidence improve_plan/round7/evidence-manifest.json \
  --human improve_plan/round7/human-only.json \
  --regression improve_plan/round7/full-regression.log \
  --drift improve_plan/round7/hash-drift-r7.json \
  --zombies improve_plan/round7/zombie-mechanism-report.json
```

若仓库已有最终门脚本，必须扩展既有脚本，禁止新增 `round7-final-gate.py`。上面文件名仅表示固定调用契约，实际方案应在读取真实源码后改成仓库已有入口。

唯一允许的通过输出：

```text
ROUND7_FINAL_ACCEPTED
points=<N>/2220
weighted_average=<X>
main_dimensions=10/10
main_minimum>=8.6
regression_failed=0
round7_failed=0
round7_skipped=0
unattributed_drift=0
unresolved_zombies=0
human_security=PASS
```

期望 exit `0`。

失败状态必须精确区分：

| Exit code | 状态 |
|---:|---|
| `0` | `ROUND7_FINAL_ACCEPTED` |
| `2` | `ROUND7_ENGINEERING_GATE_FAILED` |
| `3` | `ROUND7_BLOCKED_HUMAN_SECURITY` |
| `4` | `ROUND7_SCORE_GATE_FAILED` |
| `5` | `ROUND7_EVIDENCE_INCOMPLETE` |

不得使用“部分成功”的 exit `0`。

---

## ⑤ 回滚命令

### 5.1 回滚原则

回滚服务于**守护、人本**：

1. AI 不执行 Git 写操作；
2. AI 不执行 `rm`；
3. AI 只生成回滚命令和影响清单；
4. 实际 `git revert` 由人类或获得明确授权的整合器执行；
5. 禁止破坏工作树的命令；
6. 每个包独立回滚；
7. 回滚后必须重跑全量回归和评分门。

---

### 5.2 未提交补丁的回滚

若 DeepSeek 只生成了 patch、尚未由人类应用：

```bash
git apply --check \
  improve_plan/round7/pkg-r7-a.patch

git apply --check \
  improve_plan/round7/pkg-r7-b.patch

git apply --check \
  improve_plan/round7/pkg-r7-c.patch
```

此时不需要修改仓库；人类只需拒绝应用对应 patch。

禁止 AI 删除 patch。需要废弃时，由人类将 manifest 中状态改为：

```text
REJECTED_NOT_APPLIED
```

---

### 5.3 已应用但未提交的包

由人类在确认文件所有权后执行反向补丁：

```bash
git apply -R \
  improve_plan/round7/pkg-r7-a.patch
```

或：

```bash
git apply -R \
  improve_plan/round7/pkg-r7-b.patch
```

或：

```bash
git apply -R \
  improve_plan/round7/pkg-r7-c.patch
```

执行前必须检查：

```bash
git apply --check -R \
  improve_plan/round7/pkg-r7-a.patch
```

期望 exit `0` 后才允许真正反向应用。

不得使用：

```bash
git checkout -- .
git restore .
git reset --hard
git clean -fd
```

因为这些命令可能销毁不属于 Round 7 的人类改动。

---

### 5.4 已提交包的回滚

每个包必须是独立提交。由人类执行：

```bash
git revert --no-edit <PKG_R7_A_COMMIT>
```

或：

```bash
git revert --no-edit <PKG_R7_B_COMMIT>
```

或：

```bash
git revert --no-edit <PKG_R7_C_COMMIT>
```

如果存在 integration commit，回滚顺序固定为：

```text
1. integration commit
2. PKG-R7-C
3. PKG-R7-B
4. PKG-R7-A
```

对应命令：

```bash
git revert --no-edit <R7_INTEGRATION_COMMIT>
git revert --no-edit <PKG_R7_C_COMMIT>
git revert --no-edit <PKG_R7_B_COMMIT>
git revert --no-edit <PKG_R7_A_COMMIT>
```

禁止把多个包压成一个无法独立归因的提交。

---

### 5.5 回滚后机械验收

```bash
set -euo pipefail

git diff --check

REGRESSION_RUNNER="$(
  git ls-files |
  grep -E '(^|/)run-regression\.sh$'
)"
test "$(printf '%s\n' "$REGRESSION_RUNNER" |
       sed '/^$/d' |
       wc -l |
       tr -d ' ')" -eq 1

bash "$REGRESSION_RUNNER" |
tee improve_plan/round7/post-rollback-regression.log

test "${PIPESTATUS[0]}" -eq 0
```

然后重新计算评分：

```bash
python3 scripts/calculate-round7-score.py \
  --baseline current-score.json \
  --verdicts improve_plan/round7/verdicts.json \
  --output improve_plan/round7/final-score.json
```

如果真实仓库已有评分入口，必须使用既有入口。

回滚任一提分包后，最终状态不得继续保留 `ROUND7_FINAL_ACCEPTED`。必须根据实算结果改为：

```text
ROUND7_REOPENED_AFTER_ROLLBACK
```

或：

```text
ROUND7_SCORE_GATE_FAILED
```

验收：

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(
    Path("improve_plan/round7/final-score.json")
    .read_text(encoding="utf-8")
)

assert d["status"] != "ROUND7_FINAL_ACCEPTED", d
print(
    "ROLLBACK_STATE_RECOMPUTED "
    f"status={d['status']} "
    f"points={d['total_points']}/2220"
)
PY
```

期望 exit `0`。

---

### 5.6 人类删除操作的回滚

僵尸机制删除必须由人类在独立提交中完成。

若删除后需要恢复，由人类执行：

```bash
git revert --no-edit <HUMAN_DELETE_COMMIT>
```

不得让 AI 根据记忆重建被删除文件；恢复必须来自 Git 历史，保证内容精确。

---

### 5.7 R6-B 不可逆操作不得“回滚”

旧 token 吊销属于不可逆安全裁决，不存在恢复旧 token 的回滚命令。

正确处理是：

```text
旧 token 吊销后保持失效
新 token 如有问题则由人类再次轮换
不得重新启用旧 token
```

任何要求“为回滚而恢复旧密钥”的方案自动拒绝。

---

## ⑥ 禁止事项

### 6.1 施工者禁止即兴

DeepSeek-V4 不得：

1. 在未获得真实源码行号时自行猜测 hunk。
2. 修改方案未列出的生产文件。
3. 把一个包的文件转交另一个包共同编辑。
4. 自行新增 helper、runner、数据库或状态目录。
5. 把重复逻辑保留为 fallback。
6. 把“兼容”作为保留双真相源的理由。
7. 在测试里复制生产算法。
8. 为通过测试增加仅测试环境生效的旁路。
9. 调整权重、分母、目标分或当前基线。
10. 把历史日志当作本轮实跑结果。
11. 把 warning、hint、audit-only 当作机械治理提分。
12. 将异常、timeout、ImportError 或 malformed JSON 转为 PASS。
13. 看到失败后刷新 hash 基线。
14. 删除反证、失败日志或旧冻结值。
15. 把同一行为改动自动计入多个维度；必须逐项提交独立证据。
16. 修改冻结文档。
17. 跟踪或输出 `settings.json`。
18. 接触、打印、复制或测试任何明文 token。
19. 执行 `rm` 或任何 Git 写操作。
20. 执行网络请求验证旧 token 是否有效。

---

### 6.2 不得新增机制解决旧机制未完成

以下新增默认禁止：

```text
新的 active-token reader
新的 audit 数据库
新的 regression runner
新的 hook launcher
新的 approval store
新的 bypass 文件
新的 score truth source
新的文档同步守护进程
```

只有在材料证明：

```text
现有机制不存在
或
现有机制已正式删除
```

并由 Kimi K3 给出单一真相源裁决后，才能新增。

---

### 6.3 禁止虚假提分

以下均不构成 8→9：

| 行为 | 裁决 |
|---|---|
| 只更新 README 或 rubric 描述 | 拒绝 |
| 只新增测试但生产行为不变 | 拒绝 |
| 只记录 audit，不改变危险动作后果 | 拒绝 |
| 只增加 confidence 数字 | 拒绝 |
| 只增加 CLI 查询脚本 | 拒绝 |
| 只把代码移动到新文件 | 拒绝 |
| 只增加更多关键词 | 拒绝 |
| 自建 mock 证明自建实现正确 | 拒绝 |
| 没有失败注入 | 最高维持 8 |
| 有 skipped 测试 | 不接受 |
| 未经过生产注册入口 | 不接受 |
| 未关闭僵尸机制 | 不接受 |
| R6-B 没有人类回执 | 内置安全保持原分 |

---

### 6.4 禁止破坏性命令

施工者不得执行：

```bash
rm
rm -rf
git add
git commit
git push
git reset --hard
git clean -fd
git checkout -- .
git restore .
git rebase
git filter-repo
git filter-branch
```

如需执行删除、提交、历史清理或密钥轮换，状态必须转为相应的人类门：

```text
BLOCKED_HUMAN_DELETE
BLOCKED_HUMAN_GIT_WRITE
BLOCKED_HUMAN_HISTORY_REWRITE
BLOCKED_HUMAN_SECURITY_ROTATION
BLOCKED_HUMAN_DOCUMENT_UPDATE
```

---

### 6.5 禁止掩盖失败

不得：

- 用 `|| true` 包裹验收命令；
- 用 `set +e` 继续最终门禁；
- 只检查 stdout、不检查 exit code；
- 只检查 exit code、不检查副作用；
- 丢弃 stderr；
- 把“测试未发现”写成“机制已证明不存在缺口”；
- 在失败后删除 `/tmp/carros-regression.*.log`；
- 把 `0 tests collected` 记为成功；
- 允许 `skipped > 0`；
- 用人工口头确认替代唯一机械证据。

调查命令允许使用 `|| true` 的唯一场景，是 grep 可能无匹配；该结果不得直接作为提分证据。

---

### 6.6 禁止越过人类独占边界

以下裁决永远由人类独占：

1. 吊销和轮换密钥；
2. 不可逆删除；
3. Git 写入和发布；
4. 修改冻结哲学文档；
5. 接受真实风险例外；
6. UX 主观质量最终判定；
7. 是否执行历史重写；
8. 是否批准不可逆迁移。

AI 可以生成证据、命令和影响分析，但不能代替裁决。

---

# Round 7 审核结论

## 1. 当前准入状态

根据已返回材料，可以确认：

- 当前评分口径为 `1931/2220 = 8.70`；
- 目标至少为 `1998/2220 = 9.00`；
- `settings.json` 已移出版本控制且由 `.gitignore` 防回潮；
- 已存在统一 `run-regression.sh`，其末尾机械汇总套件结果并按 `rc_all` 返回；
- E5 在旧终评中为 8；
- E7 在 R5 时因 hint-only 停留 7，后续 R6 已完成精确分层施工；
- R6-B 仍必须依赖人类不可逆安全闭环。

但在没有把返回的完整源码逐行固定为 `source-evidence.txt` 之前，**不批准任何猜测性生产 diff**。

当前允许状态：

```yaml
round7:
  planning_boundary: ACCEPTED
  production_diff: PENDING_SOURCE_LINE_FREEZE
  engineering_execution: NOT_YET_AUTHORIZED
  r6_b_security: BLOCKED_HUMAN
  final_9_plus: NOT_ACCEPTED
```

---

## 2. 施工授权条件

只有以下命令全部通过后，Kimi K3 才能签发三个零交叉施工包：

```text
SOURCE_EVIDENCE_PASS
BASELINE_REGRESSION_PASS
PACKAGE_FILE_OWNERSHIP_PASS
SELECTION_FREEZE_PASS
R6_B_OWNER_ACKNOWLEDGED
```

其中：

- `R6_B_OWNER_ACKNOWLEDGED` 只允许开始工程施工；
- `R6_B_SECURITY_PASS` 才允许最终收口。

---

## 3. 最终唯一成功状态

```yaml
decision: ROUND7_FINAL_ACCEPTED
required:
  score:
    points: ">=1998/2220"
    weighted_average: ">=9.00"
  main_dimensions:
    selected: "10/10"
    minimum: ">=8.6"
  security:
    r6_b_owner: human
    old_token_revoked: true
    redacted_receipt: present
    current_tree_scan: pass
    history_scan: reconciled
    secret_material_exposed: 0
  regression:
    failed: 0
    skipped: 0
  evidence:
    production_path_binding: pass
    unattributed_hash_drift: 0
    unresolved_zombies: 0
    document_only_score_increases: 0
  boundaries:
    frozen_document_ai_changes: 0
    tracked_settings_json: 0
    unauthorized_git_writes: 0
```

## 4. 一句话终裁

**Round 7 必须先将返回材料机械固化为带行号源码证据，再对十个主 8 分项逐项关闭独立事故路径；总分、最低项、人类安全门、全量回归、漂移归因和僵尸清零全部合取通过后，才允许宣告 CarrorOS 达到 9+。**