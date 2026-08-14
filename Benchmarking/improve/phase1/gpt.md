# GPT 第二轮联合审核裁决

> 对象：Design Doc 13 V2、`review-request.md`、`governance_cost_probe.py` 及 ON/PERM 产物  
> 结论：**V1 的 headless 降级架构继续永久否决；V2 的根因方向成立为主假说，但当前证据尚未闭合；A/B/C 不得合并施工。**

## ① 目标与不变式

### 目标

验证 V2 是否真正实现：

1. 单一路径、同一套 gate、同一套审计语义。
2. 解决权限阻塞导致的重复尝试，而不是削弱治理。
3. 仅在有实测证据时实施 launcher、惰性 import 或缓冲写优化。
4. 维持磁盘状态为唯一真相源。

### 哲学合规

| 方案 | 服务哲学环节 | 裁决 |
|---|---|---|
| 删除 headless 分叉 | `the less,the more`、验证、守护 | 批准 |
| 权限阻塞修复 | 增益、人本 | 仅允许人类预置路径，不得运行时自扩权 |
| 成本度量 | 验证 | 批准，但不得反向触发降级 |
| launcher 同构提速 | 增益 | 有条件批准 |
| `gate-contract WARN → fail-closed` | 守护、验证 | 独立高优先级，不能并入性能改动 |

### 不变式

1. 不得出现 `_is_headless`、`isatty()` 分支、`FORCE_HEADLESS` 或按模式选择 gate。
2. gate 数量、执行顺序、决策字段、阻塞语义不得改变。
3. 审计逐条记录不得丢失、合并或降频。
4. AI 不得修改 `settings.local.json`、权限 allowlist 或治理契约。
5. transcript 的成功叙述不得替代磁盘产物。
6. `claimed_created ⊆ disk_created`，否则测量结果必须标记 `EVIDENCE_GAP`。
7. launcher 一次只执行一个 hook，不得顺手合并多个 hook。
8. Design Doc 13 不得同时保留「否决 V1」和仍可照抄施工的 V1 正文。

---

## ② 文件清单：路径 → 操作 → 精确要求

本轮**不批准直接修改冻结代码**。当前只能进行证据补齐和文档清理。

| 路径 | 操作 | 精确要求 |
|---|---|---|
| `.claude/references/design-docs/13-headless-lightweight-actions.md` | edit | 删除正文中所有可施工的 headless 检测、gate 裁剪、审计降频、`FORCE_HEADLESS` 内容；V1 只能保留在标题明确为 `SUPERSEDED — DO NOT IMPLEMENT` 的附录 |
| `Benchmarking/improve/phase1/review-request.md` | edit | 将「真主因」「铁证」「根因最终确认」改为「待证实主假说」；加入 `PERM created_files=[] => EVIDENCE_GAP` |
| `.omc/scripts/governance_cost_probe.py` | edit | 增加磁盘产物对账：运行结束后必须输出 `created_files`；若 transcript 声称创建文件而磁盘不存在，退出非零 |
| `.omc/scripts/governance_cost_probe.py` | edit | ON/PERM 使用同一工作目录权限剖面；唯一变量必须是治理 hook 是否加载 |
| `.omc/scripts/governance_cost_probe.py` | edit | audit 必须绑定本次 session 或 work，禁止读取主仓库未过滤的全局 audit 作为唯一计数 |
| `Benchmarking/improve/phase1/gpt.md` | new | 写入本裁决；不得写入未验证的施工 diff |
| `.claude/hooks/hook-launcher.py` | no-op | 在补齐全文、关键异常语义、critical hook 列表前禁止修改 |
| `.claude/hooks/pretool-gate.py` | no-op | 禁止加入 headless 分支或权限自动放行 |
| `.claude/hooks/pretool_gates/helpers.py` | no-op | 禁止加入审计降频、摘要化或自扩 allow 逻辑 |
| `scripts/carroros-gates/gate-contract.yaml` | no-op | `WARN → fail-closed` 单独立项，不得与 Doc 13 性能方案混改 |

当前不能给出 launcher 或权限 allowlist 的精确 diff，因为缺少其完整源码、现行 allow 段和目标路径规则。编造 diff 将违反零设计空间和证据文化要求。

---

## ③ 精确命令序列

施工模型必须按以下顺序执行。命令中的 `<WORK>` 必须替换为实际绝对路径，不得自行猜测。

```bash
git status --short
```

```bash
python3 -m json.tool .omc/governance-cost-probe/ON/meta.json
python3 -m json.tool .omc/governance-cost-probe/PERM/meta.json
```

```bash
find .omc/governance-cost-probe/ON -maxdepth 3 -type f -print | sort
find .omc/governance-cost-probe/PERM -maxdepth 3 -type f -print | sort
```

```bash
sed -n '1,240p' .claude/settings.local.json
sed -n '1,260p' .claude/hooks/hook-launcher.py
```

```bash
find <WORK> -maxdepth 2 -type f -print | sort
```

```bash
rg -n 'FORCE_HEADLESS|FORCE_INTERACTIVE|isatty|_is_headless|headless|降级|审计降频|仅.*BLOCK|摘要' \
  .claude/references/design-docs/13-headless-lightweight-actions.md
```

```bash
rg -n 'missing_gate|WARN|ERROR|enforcement' scripts/carroros-gates/gate-contract.yaml
```

补齐证据后，才允许生成单主题施工方案：

1. 先修 probe 证据对账。
2. 再单独处理 `gate-contract` fail-closed。
3. 再单独处理 thrash 停止策略。
4. 最后才审查 launcher、缓冲写和惰性 import。

---

## ④ 逐条机械验收

### 当前材料验收结果

| 验收 | 期望 | 当前结果 |
|---|---|---|
| ON/PERM meta 可解析 | exit `0` | 通过 |
| ON 任务未创建文件 | `created_files=[]` | 已证实 |
| PERM transcript 声称创建文件 | 磁盘存在对应文件 | **失败** |
| PERM `created_files` 非空 | 至少包含 `data_check.py`、`test_data_check.py` | **失败** |
| 根因可称为最终确认 | 盘证闭合 | **失败，必须 EVIDENCE_GAP** |
| V1 内容物理移除 | `rg` 无可施工降级段 | **尚未通过** |
| launcher 可给零设计空间 diff | 有完整源码和异常语义 | **尚未通过** |
| A/B 变量仅为治理 hook | ON/PERM 使用同一权限剖面 | **尚未通过** |

### 允许进入施工的机械门槛

以下命令全部必须返回 exit code `0`：

```bash
test -f <WORK>/data_check.py
test -f <WORK>/test_data_check.py
python3 <WORK>/test_data_check.py
```

期望 stdout 至少包含：

```text
PASS
```

并且：

```bash
python3 - <<'PY'
import json
from pathlib import Path

for name in ("ON", "PERM"):
    data = json.loads(
        Path(".omc/governance-cost-probe", name, "meta.json")
        .read_text()
    )
    assert "EVIDENCE_GAP" not in data.get("status", "")
    assert set(data["created_files"]) >= {
        "data_check.py",
        "test_data_check.py",
    }
print("evidence-ok")
PY
```

期望 stdout：

```text
evidence-ok
```

V1 清理验收：

```bash
! rg -n \
  'CARROROS_FORCE_HEADLESS|CARROROS_FORCE_INTERACTIVE|isatty|_is_headless|跳过.*gate|审计.*降频|仅.*BLOCK|摘要.*审计' \
  .claude/references/design-docs/13-headless-lightweight-actions.md
```

期望 exit code：

```text
0
```

任何一个验收失败，都不得进入 launcher 或权限方案施工。

---

## ⑤ 回滚命令

本轮不应产生代码改动。若施工者仅修改了审核文档和 probe，回滚必须使用精确文件恢复，且不得影响其他未相关修改：

```bash
git diff -- .claude/references/design-docs/13-headless-lightweight-actions.md
git diff -- Benchmarking/improve/phase1/review-request.md
git diff -- .omc/scripts/governance_cost_probe.py
```

在确认这些文件中的改动全部属于本轮后，才允许：

```bash
git restore --source=HEAD -- \
  .claude/references/design-docs/13-headless-lightweight-actions.md \
  Benchmarking/improve/phase1/review-request.md \
  .omc/scripts/governance_cost_probe.py
```

禁止对冻结 hook、settings 或契约文件执行未经人类授权的回滚或覆盖。

---

## ⑥ 禁止事项

1. 禁止恢复任何 headless 模式分叉。
2. 禁止使用 `isatty()` 判断治理强度。
3. 禁止新增 `CARROROS_FORCE_HEADLESS`、`CARROROS_FORCE_INTERACTIVE` 或等价开关。
4. 禁止因权限阻塞而自动放行 Write、Bash 重定向或动态路径。
5. 禁止让 agent 修改 `settings.local.json`、allowlist 或 gate contract。
6. 禁止把 CarrorOS BLOCK、Claude Code 权限拒绝、night-deny 拒绝混写成同一类事件。
7. 禁止用 transcript、stdout 或 agent 自述证明文件存在。
8. 禁止在 `created_files=[]` 时宣称 PERM 已成功落盘。
9. 禁止把 86 秒与 45.9 秒直接解释为纯治理开销，除非 ON/PERM 权限面完全一致。
10. 禁止把 launcher、权限修复、thrash 上限和 contract fail-closed 合并到同一 PR。
11. 禁止在没有 `hook-launcher.py` 完整内容时生成 runpy 施工 diff。
12. 禁止在没有 `settings.local.json` 权限段和实际绝对路径时生成动态 allowlist diff。
13. 禁止把成本度量结果自动连接到 gate 删除、gate 跳过或审计降频。
14. 禁止保留 V1 可被施工模型误读的正文。
15. 禁止宣称已达到 240 秒认证门槛。

**最终裁决：**  
V2 的方向比 V1 正确，但当前只能批准「证据修复与文档去僵尸化」。权限根因暂定为主假说，PERM 盘证未闭合；launcher、动态权限和 contract fail-closed 均不得在证据补齐前进入施工。