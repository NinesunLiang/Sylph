# PKG-B 整改方案：验证契约唯一来源、孤儿 Oracle 清除、R6 与 Pipeline 契约纠偏

> **适用基线**：`91954a0b01f9c53edf94965238308fcb080818eb`，并以材料包记录的当前工作区内容为施工前件。  
> **文件边界**：PKG-B 不修改 PKG-A 负责的 `.claude/scripts/carros_base.py`、`.claude/scripts/verify_gate.py`、`.claude/hooks/pretool-gate.py` 和 `scripts/test-verify-gate.py`。  
> **裁决结论**：
>
> 1. 唯一验证裁决源固定为 `.claude/scripts/verify_gate.py`。
> 2. `cmd_verify` 和 `_check_verified` 只是生产者入口与证据消费者，不再各自定义验证语义；该接线由 PKG-A 完成。
> 3. 两份 `oracle_gate.py` 均删除。现行生产 Oracle 路径已经整合进 `pretool-gate.py`，旧脚本既未注册又允许基于时效文件绕过硬边界，不能保留为僵尸。
> 4. `lx-validate-skill` 的 R6 从“只允许 `.py`”改为“脚本类型必须进入显式白名单且可机械语法检查”，消除与现存受支持 `.sh` wrapper 的矛盾。
> 5. `lx-oma split --pipeline` 保留为唯一合法 `--pipeline` 入口；`lx-rpe` 不接收、不读写 `pipeline.yaml`。
> 6. 所有“脚本不存在则人工验证”的降级文字改成 fail-closed；人工可以决定暂停、撤回或承担不可逆裁决，但不能伪造机械验证通过。

---

## ① 目标与不变式

### 1.1 目标

| ID | 目标 | 哲学链服务项 | 证据 |
|---|---|---|---|
| B-G1 | 验证裁决语义只有一个实现来源：`.claude/scripts/verify_gate.py` | **验证**、零信任、少 | `.claude/scripts/verify_gate.py:5-20` 已声明其职责、结果集合和 E3/E2/E1/E0 等级 |
| B-G2 | 删除未接入生产 hook 的两份 `oracle_gate.py` | **验证**、零信任、守护、少 | `.claude/settings.json:20-85` 未注册该脚本；`.claude/hooks/pretool-gate.py:574-607` 已内置生产 Oracle 提示门 |
| B-G3 | 禁止 Oracle bypass 文件把硬边界变成时效授权 | **验证**、零信任、守护、人本 | `.claude/scripts/oracle_gate.py:46-58,79-82` 允许 24 小时 bypass；同文件 `:91-95` 又声称执行硬阻断，二者矛盾 |
| B-G4 | R6 接受仓库正式支持的 `.py` 与 `.sh`，同时机械拒绝其他脚本类型 | **验证**、文档、增益、少 | `.claude/skills/lx-validate-skill/SKILL.md:66` 现规定 scripts 仅 `.py`；`.claude/skills/lx-goal/scripts/lx-goal.sh:1-6` 是正式 Python wrapper；`.claude/hooks/hook-launcher.sh:46-52` 也明确支持 `.sh` |
| B-G5 | `--pipeline` 只有 OMA 编排层拥有，RPE 只接收 `BASE_DIR` | **验证**、零信任、文档、少 | `.claude/skills/lx-oma/SKILL.md:8,26,86,168` 声明 `split --pipeline`；`.claude/skills/lx-rpe/SKILL.md:94-96` 声明 RPE 不读写 pipeline |
| B-G6 | 校验脚本缺失时不得降级成“人工校验通过” | **验证**、零信任 | `.claude/skills/lx-oma/SKILL.md:180-186` 存在“校验脚本不存在→手动校验”；同文件 `:112-118` 又把脚本 exit code 作为质量证据，语义冲突 |

### 1.2 不变式

1. **INV-B1：磁盘证据唯一。**  
   step 是否可完成，只能由 `.claude/scripts/verify_gate.py` 对 `plan.md` 规则和 `executor.md` 证据作出裁决。  
   依据：`.claude/scripts/verify_gate.py:5-20,80-106,109-152,160-202`。

2. **INV-B2：文档不能自行宣称 VERIFIED。**  
   `VERIFIED` 是裁决输出，不是 skill、hook、模型或人工可直接写入的状态。

3. **INV-B3：缺少裁决器等同验证失败。**  
   不得把 “script missing”“ImportError”“timeout” 转译成手动 PASS、WARN 放行或默认 ACCEPT。

4. **INV-B4：不可逆裁决只属于人。**  
   人工可批准不可逆动作，但批准事实必须由现有证据链消费；不能通过创建一个 24 小时 bypass 文件绕过所有后续动作。

5. **INV-B5：不保留双副本。**  
   `.omc/scripts/oracle_gate.py` 和 `.claude/scripts/oracle_gate.py` 不得继续以复制文件、软链接或 wrapper 形式存在。

6. **INV-B6：R6 只约束脚本类型和可验证性，不偏好编程语言。**  
   `.py` 必须通过 `py_compile`；`.sh` 必须通过 `bash -n`；其余扩展名拒绝。

7. **INV-B7：Pipeline 所有权唯一。**  
   只有 `/lx-oma split --pipeline <pipeline>` 接收 `--pipeline`；`lx-rpe` 只接收 OMA 提供的 `BASE_DIR`。

8. **INV-B8：高优先级自动否决。**  
   若本方案任何文档便利性与验证、零信任或守护冲突，以前者作废。

---

## ② 文件清单：路径 → 操作 → 精确 diff 或完整新内容

### 2.1 `.claude/scripts/oracle_gate.py` → `delete`

**理由**：该文件不是生产 hook 注册项；其职责已被统一 `pretool-gate.py` 覆盖，而且它允许基于文件 mtime 的 24 小时全局 bypass。  
证据：

- 未注册：`.claude/settings.json:20-85`
- 生产实现：`.claude/hooks/pretool-gate.py:574-607`
- bypass：`.claude/scripts/oracle_gate.py:46-58,79-82`
- 所谓硬阻断：`.claude/scripts/oracle_gate.py:91-95`

精确操作：

```bash
git rm -- .claude/scripts/oracle_gate.py
```

---

### 2.2 `.omc/scripts/oracle_gate.py` → `delete`

**理由**：它与 `.claude/scripts/oracle_gate.py` 是逐字重复的第二真相源。材料包已给出两份完整内容相同；保留软链接也会继续暴露废弃命令入口。

精确操作：

```bash
git rm -- .omc/scripts/oracle_gate.py
```

> 不得把该路径改成软链接，不得保留兼容 wrapper。现有生产 hook 从未依赖该命令，因此删除不构成接口迁移。

---

### 2.3 `.claude/skills/lx-validate-skill/SKILL.md` → `edit`

**哲学映射**：验证、文档、增益、少。  
**证据**：现有 R6 位于 `.claude/skills/lx-validate-skill/SKILL.md:66`，与仓库正式 `.sh` 入口冲突。

精确 diff：

```diff
diff --git a/.claude/skills/lx-validate-skill/SKILL.md b/.claude/skills/lx-validate-skill/SKILL.md
--- a/.claude/skills/lx-validate-skill/SKILL.md
+++ b/.claude/skills/lx-validate-skill/SKILL.md
@@ -63,7 +63,7 @@
 | R3 | SKILL.md 内联完整（无 body_ref） | 无 body_ref: 行 |
 | R4 | 无私有 nodes/ 目录 | `ls skills/lx-*/nodes/` |
 | R5 | 无私有 schemas/ 目录 | `ls skills/lx-*/schemas/` |
-| R6 | scripts/ 仅 .py（无 .sh 超出模板文件） | glob 检查 |
+| R6 | scripts/ 仅允许 `.py` 与 `.sh`；`.py` 必须通过 `python3 -m py_compile`，`.sh` 必须通过 `bash -n`；其他扩展名一律失败 | 扩展名白名单 + 逐文件语法检查 |
 | R7 | frontmatter 有 description | yaml 校验 |
 | R8 | 至少引用 1 个 `../../nodes/` | grep SKILL.md |
 | R9 | 至少引用 1 个 `../../schemas/` | grep SKILL.md |
```

---

### 2.4 `.claude/skills/lx-validate-skill/references/report-templates.md` → `edit`

**哲学映射**：验证、文档。  
**证据**：该文件第 41 行仍把 R6 描述为“缺少状态机声明”，与主规则 `.claude/skills/lx-validate-skill/SKILL.md:66` 完全不同，形成同一规则号的双重语义。

精确 diff：

```diff
diff --git a/.claude/skills/lx-validate-skill/references/report-templates.md b/.claude/skills/lx-validate-skill/references/report-templates.md
--- a/.claude/skills/lx-validate-skill/references/report-templates.md
+++ b/.claude/skills/lx-validate-skill/references/report-templates.md
@@ -38,7 +38,7 @@
 | R3 | SKILL.md 使用 body_ref | 删除 body_ref 并内联正文 |
 | R4 | 存在私有 nodes/ | 改为引用共享 nodes |
 | R5 | 存在私有 schemas/ | 改为引用共享 schemas |
-| R6 | 缺少状态机声明 | 添加 ### 状态机 声明 |
+| R6 | scripts/ 含非 `.py`/`.sh` 文件，或脚本语法检查失败 | 删除非白名单脚本；对 `.py` 修复至 `python3 -m py_compile` 通过，对 `.sh` 修复至 `bash -n` 通过 |
```

---

### 2.5 `.claude/skills/lx-validate-skill/scripts/validate_skill.py` → `edit`

**哲学映射**：验证、零信任。  
**目的**：让 R6 的执行器与唯一文档定义一致，不只改说明。

施工者执行以下**确定性 AST 级替换命令**；命令在找不到旧 R6 实现、找到多个实现或生成后不含唯一新实现时以 exit 2 失败，不得猜测位置。

```bash
python3 - <<'PY'
from pathlib import Path
import re
import sys

path = Path(".claude/skills/lx-validate-skill/scripts/validate_skill.py")
text = path.read_text(encoding="utf-8")

pattern = re.compile(
    r'(?ms)^def check_r6\([^)]*\).*?(?=^def check_r7\()'
)

replacement = '''def check_r6(skill_dir):
    """R6: scripts/ only permits .py and .sh, and every script must parse."""
    import subprocess

    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return True, "scripts/ absent"

    files = sorted(path for path in scripts_dir.rglob("*") if path.is_file())
    invalid = [
        str(path.relative_to(skill_dir))
        for path in files
        if path.suffix not in {".py", ".sh"}
    ]
    if invalid:
        return False, "unsupported script types: " + ", ".join(invalid)

    failures = []
    for script in files:
        if script.suffix == ".py":
            command = [sys.executable, "-m", "py_compile", str(script)]
        else:
            command = ["bash", "-n", str(script)]
        result = subprocess.run(
            command,
            cwd=str(skill_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().replace("\\n", " ")
            failures.append(f"{script.relative_to(skill_dir)}: {detail[:240]}")

    if failures:
        return False, "script syntax failed: " + "; ".join(failures)
    return True, f"{len(files)} scripts passed extension and syntax checks"


'''

matches = list(pattern.finditer(text))
if len(matches) != 1:
    print(
        f"ERROR: expected exactly one check_r6 block before check_r7; found {len(matches)}",
        file=sys.stderr,
    )
    raise SystemExit(2)

updated = pattern.sub(replacement, text, count=1)
if updated.count("def check_r6(") != 1:
    print("ERROR: resulting check_r6 count is not 1", file=sys.stderr)
    raise SystemExit(2)
if 'path.suffix not in {".py", ".sh"}' not in updated:
    print("ERROR: R6 extension whitelist missing", file=sys.stderr)
    raise SystemExit(2)
if '["bash", "-n", str(script)]' not in updated:
    print("ERROR: R6 bash syntax check missing", file=sys.stderr)
    raise SystemExit(2)
if '[sys.executable, "-m", "py_compile", str(script)]' not in updated:
    print("ERROR: R6 Python syntax check missing", file=sys.stderr)
    raise SystemExit(2)

path.write_text(updated, encoding="utf-8")
PY
```

> 此项采用确定性函数整体替换而不是模糊手改。替换的完整新函数内容已经在命令中给出，没有设计空间。

---

### 2.6 `.claude/skills/lx-oma/SKILL.md` → `edit`

#### 2.6.1 修正校验器缺失时的 fail-open 降级

**哲学映射**：验证、零信任。  
**证据**：`.claude/skills/lx-oma/SKILL.md:180-186` 将“校验脚本不存在”降级为手动校验，与机械证据门冲突。

精确 diff：

```diff
diff --git a/.claude/skills/lx-oma/SKILL.md b/.claude/skills/lx-oma/SKILL.md
--- a/.claude/skills/lx-oma/SKILL.md
+++ b/.claude/skills/lx-oma/SKILL.md
@@ -180,10 +180,10 @@
 ### 降级策略
 
 | 场景 | 主路径 | 降级 |
 |------|--------|------|
 | Sub PRD <200 字 | 按已有内容拆解 | 告知内容不足 |
-| 校验脚本不存在 | 自动化校验 | 降级手动校验 |
+| 校验脚本不存在 | 自动化校验 | BLOCKED：不得生成通过结论；恢复校验脚本后重跑 |
 | hier 不可用 | 委托调用 | 手动 `/lx-oma hier` |
```

#### 2.6.2 修正另一处 MECE 校验器缺失的 fail-open 降级

**证据**：`.claude/skills/lx-oma/SKILL.md:112-126` 把 `verify_oma_mece.py` 的 exit code 定义为质量证据，却又允许脚本缺失时手动自检。

精确 diff：

```diff
diff --git a/.claude/skills/lx-oma/SKILL.md b/.claude/skills/lx-oma/SKILL.md
--- a/.claude/skills/lx-oma/SKILL.md
+++ b/.claude/skills/lx-oma/SKILL.md
@@ -121,9 +121,9 @@
 ### 降级策略
 
 | 场景 | 降级路径 |
 |------|---------|
-| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |
+| verify_oma_mece.py 不可用 | BLOCKED：不得生成 MECE 通过结论；恢复脚本后重跑 |
 | Sub PRD 输出失败 | 保留中间产物，标注缺失项 |
 | MECE 校验 3 轮未通过 | 标记需人工介入 |
```

#### 2.6.3 固化 Pipeline 所有权

在 `.claude/skills/lx-oma/SKILL.md` 第 168 行所在 `split` pipeline 段之后插入以下完整内容：

```markdown
### Pipeline 参数所有权

- `--pipeline <path>` 只允许由 `/lx-oma split` 消费。
- `<path>` 必须指向已存在的 pipeline 状态文件；路径缺失、文件缺失或解析失败均为 `BLOCKED`。
- `lx-rpe` 不接收 `--pipeline`，不读取或写入 `pipeline.yaml`；OMA 只向 RPE 传递已解析的 `BASE_DIR`。
- 未经 OMA 状态机落盘的自然语言“pipeline 已完成”不构成阶段证据。
```

确定性插入命令：

```bash
python3 - <<'PY'
from pathlib import Path
import sys

path = Path(".claude/skills/lx-oma/SKILL.md")
text = path.read_text(encoding="utf-8")

anchor = "入口 `--pipeline <pipeline>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。"
block = """入口 `--pipeline <pipeline>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。

### Pipeline 参数所有权

- `--pipeline <path>` 只允许由 `/lx-oma split` 消费。
- `<path>` 必须指向已存在的 pipeline 状态文件；路径缺失、文件缺失或解析失败均为 `BLOCKED`。
- `lx-rpe` 不接收 `--pipeline`，不读取或写入 `pipeline.yaml`；OMA 只向 RPE 传递已解析的 `BASE_DIR`。
- 未经 OMA 状态机落盘的自然语言“pipeline 已完成”不构成阶段证据。
"""

if text.count(anchor) != 1:
    print(f"ERROR: expected one pipeline anchor, found {text.count(anchor)}", file=sys.stderr)
    raise SystemExit(2)
if "### Pipeline 参数所有权" in text:
    print("ERROR: pipeline ownership block already exists", file=sys.stderr)
    raise SystemExit(2)

path.write_text(text.replace(anchor, block, 1), encoding="utf-8")
PY
```

---

### 2.7 `.claude/skills/lx-rpe/SKILL.md` → `edit`

**哲学映射**：验证、文档、少。  
**证据**：`.claude/skills/lx-rpe/SKILL.md:94-96` 已经声明 RPE 不读写 pipeline，但未机械说明拒绝 `--pipeline`。

精确 diff：

```diff
diff --git a/.claude/skills/lx-rpe/SKILL.md b/.claude/skills/lx-rpe/SKILL.md
--- a/.claude/skills/lx-rpe/SKILL.md
+++ b/.claude/skills/lx-rpe/SKILL.md
@@ -92,7 +92,9 @@
 
 ## Pipeline 集成
 
-编排由 `lx-oma-orch` 统一管理。lx-rpe 不做 pipeline.yaml 读写，仅接收 BASE_DIR。
+编排由 `lx-oma-orch` 统一管理。`lx-rpe` 不做 `pipeline.yaml` 读写，仅接收 `BASE_DIR`。
+
+`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误；调用方必须先由 `/lx-oma split --pipeline <path>` 解析状态，再只传递 `BASE_DIR`。
```

---

### 2.8 `.claude/skills/references/oma/skill-chaining.md` → `edit`

**哲学映射**：验证、文档。  
**证据**：该文件 `:27-29` 当前连续展示 `hier --pipeline`、`split --pipeline`、`rpe --pipeline`，与唯一所有权冲突。

精确 diff：

```diff
diff --git a/.claude/skills/references/oma/skill-chaining.md b/.claude/skills/references/oma/skill-chaining.md
--- a/.claude/skills/references/oma/skill-chaining.md
+++ b/.claude/skills/references/oma/skill-chaining.md
@@ -24,8 +24,8 @@
 
-1. /lx-oma-hier docs/master-prd.md --pipeline <pipeline>
-2. /lx-oma-split sub-prds/domain-auth.md --pipeline <pipeline>
-3. /lx-rpe prd/auth/feat-login --pipeline <pipeline>
+1. /lx-oma hier docs/master-prd.md
+2. /lx-oma split sub-prds/domain-auth.md --pipeline <pipeline>
+3. /lx-rpe <BASE_DIR>
```

在该列表后追加：

```markdown
`--pipeline` 仅属于 `/lx-oma split`；`lx-rpe` 不消费 pipeline 文件。`BASE_DIR` 必须来自 OMA 对 pipeline 磁盘状态的解析结果。
```

确定性追加命令：

```bash
python3 - <<'PY'
from pathlib import Path
import sys

path = Path(".claude/skills/references/oma/skill-chaining.md")
text = path.read_text(encoding="utf-8")
anchor = "3. /lx-rpe <BASE_DIR>"
sentence = (
    "\n\n`--pipeline` 仅属于 `/lx-oma split`；`lx-rpe` 不消费 pipeline 文件。"
    "`BASE_DIR` 必须来自 OMA 对 pipeline 磁盘状态的解析结果。"
)

if text.count(anchor) != 1:
    print(f"ERROR: expected one chaining anchor, found {text.count(anchor)}", file=sys.stderr)
    raise SystemExit(2)
if sentence.strip() in text:
    print("ERROR: ownership sentence already exists", file=sys.stderr)
    raise SystemExit(2)

path.write_text(text.replace(anchor, anchor + sentence, 1), encoding="utf-8")
PY
```

---

### 2.9 `.claude/skills/references/oma/pipeline-contract.md` → `edit`

将当前第 14 行的泛化描述：

```markdown
收到 `--pipeline <path>` 时：
```

精确替换为：

```markdown
仅 `/lx-oma split` 可接收 `--pipeline <path>`。收到该参数时：
```

并在其后插入以下硬约束：

```markdown
1. `<path>` 不存在、不可读或解析失败：返回 `BLOCKED`，不得降级为内存状态或人工声明。
2. `lx-rpe` 不得接收该参数；RPE 只接收 OMA 从磁盘状态解析出的 `BASE_DIR`。
3. pipeline 阶段推进必须先原子落盘，再向下游发出动作。
```

确定性命令：

```bash
python3 - <<'PY'
from pathlib import Path
import sys

path = Path(".claude/skills/references/oma/pipeline-contract.md")
text = path.read_text(encoding="utf-8")
old = "收到 `--pipeline <path>` 时："
new = """仅 `/lx-oma split` 可接收 `--pipeline <path>`。收到该参数时：

1. `<path>` 不存在、不可读或解析失败：返回 `BLOCKED`，不得降级为内存状态或人工声明。
2. `lx-rpe` 不得接收该参数；RPE 只接收 OMA 从磁盘状态解析出的 `BASE_DIR`。
3. pipeline 阶段推进必须先原子落盘，再向下游发出动作。"""

if text.count(old) != 1:
    print(f"ERROR: expected one pipeline contract anchor, found {text.count(old)}", file=sys.stderr)
    raise SystemExit(2)

path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
```

---

### 2.10 六处重复验证的处置表

这里不新增第七个聚合器；逐项决定“接线、保留为测试、删除”。

| 当前实现或入口 | 处置 | 机械边界 | 证据 |
|---|---|---|---|
| `.claude/scripts/verify_gate.py` | **保留为唯一裁决源** | 只有它可以输出 step 的 `VERIFIED/BLOCKED/REJECTED` | `verify_gate.py:5-20,42-50` |
| `.claude/scripts/carros_base.py::cmd_verify` | **由 PKG-A 接线** | 必须调用唯一裁决源；PKG-B 不改该文件 | `carros_base.py:788-864` |
| `.claude/hooks/pretool-gate.py::_check_verified` | **由 PKG-A 改成证据消费者** | 不得自行推导规则；PKG-B 不改该文件 | `pretool-gate.py:254-278,543-572` |
| `.claude/scripts/runtime_verify.py` | **保留为系统回归测试运行器** | 不得写 step VERIFIED，不得替代 VerifyGate | `runtime_verify.py:3-6,20-73` |
| `.claude/scripts/verify_tests.py` | **保留为测试 harness** | 测试结果不能直接推进任务状态 | `verify_tests.py:3-10,46-65` |
| `.claude/scripts/feature_verify.py` | **保留为特性测试执行器** | 产物只能成为 executor evidence，不能直接勾选 plan |
| `.claude/scripts/oracle_engine.py` | **保留为 L2 复核评分器** | Oracle 结果不能替代基础验证证据 | `oracle_engine.py:22-38,40-70,201-235` |
| 两份 `oracle_gate.py` | **删除** | 删除后引用数必须为零 | `oracle_gate.py:46-58,71-102` |

> `runtime_verify.py`、`verify_tests.py`、`feature_verify.py` 和 `oracle_engine.py` 不是另一个 step 验证裁决器；它们分别是证据生产者、测试 harness 或复核器。方案通过文档和 grep 验收禁止它们写 `VERIFIED`，而不是再造统一 wrapper。

---

## ③ 精确命令序列

施工者必须在仓库根目录按顺序执行。任何一步非零立即停止。

### 3.1 前置保护

```bash
set -euo pipefail

EXPECTED_HEAD='91954a0b01f9c53edf94965238308fcb080818eb'
ACTUAL_HEAD="$(git rev-parse HEAD)"
test "$ACTUAL_HEAD" = "$EXPECTED_HEAD"

mkdir -p .omc/state/pkg-b-backup
git diff --binary -- \
  .claude/scripts/oracle_gate.py \
  .omc/scripts/oracle_gate.py \
  .claude/skills/lx-validate-skill/SKILL.md \
  .claude/skills/lx-validate-skill/references/report-templates.md \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py \
  .claude/skills/lx-oma/SKILL.md \
  .claude/skills/lx-rpe/SKILL.md \
  .claude/skills/references/oma/skill-chaining.md \
  .claude/skills/references/oma/pipeline-contract.md \
  > .omc/state/pkg-b-backup/pre-pkg-b.patch

git status --porcelain=v1 > .omc/state/pkg-b-backup/pre-pkg-b.status
```

### 3.2 创建并预检静态补丁

```bash
cat > /tmp/pkg-b-static.patch <<'PATCH'
diff --git a/.claude/skills/lx-validate-skill/SKILL.md b/.claude/skills/lx-validate-skill/SKILL.md
--- a/.claude/skills/lx-validate-skill/SKILL.md
+++ b/.claude/skills/lx-validate-skill/SKILL.md
@@ -63,7 +63,7 @@
 | R3 | SKILL.md 内联完整（无 body_ref） | 无 body_ref: 行 |
 | R4 | 无私有 nodes/ 目录 | `ls skills/lx-*/nodes/` |
 | R5 | 无私有 schemas/ 目录 | `ls skills/lx-*/schemas/` |
-| R6 | scripts/ 仅 .py（无 .sh 超出模板文件） | glob 检查 |
+| R6 | scripts/ 仅允许 `.py` 与 `.sh`；`.py` 必须通过 `python3 -m py_compile`，`.sh` 必须通过 `bash -n`；其他扩展名一律失败 | 扩展名白名单 + 逐文件语法检查 |
 | R7 | frontmatter 有 description | yaml 校验 |
 | R8 | 至少引用 1 个 `../../nodes/` | grep SKILL.md |
 | R9 | 至少引用 1 个 `../../schemas/` | grep SKILL.md |
diff --git a/.claude/skills/lx-validate-skill/references/report-templates.md b/.claude/skills/lx-validate-skill/references/report-templates.md
--- a/.claude/skills/lx-validate-skill/references/report-templates.md
+++ b/.claude/skills/lx-validate-skill/references/report-templates.md
@@ -38,7 +38,7 @@
 | R3 | SKILL.md 使用 body_ref | 删除 body_ref 并内联正文 |
 | R4 | 存在私有 nodes/ | 改为引用共享 nodes |
 | R5 | 存在私有 schemas/ | 改为引用共享 schemas |
-| R6 | 缺少状态机声明 | 添加 ### 状态机 声明 |
+| R6 | scripts/ 含非 `.py`/`.sh` 文件，或脚本语法检查失败 | 删除非白名单脚本；对 `.py` 修复至 `python3 -m py_compile` 通过，对 `.sh` 修复至 `bash -n` 通过 |
diff --git a/.claude/skills/lx-oma/SKILL.md b/.claude/skills/lx-oma/SKILL.md
--- a/.claude/skills/lx-oma/SKILL.md
+++ b/.claude/skills/lx-oma/SKILL.md
@@ -121,9 +121,9 @@
 ### 降级策略
 
 | 场景 | 降级路径 |
 |------|---------|
-| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |
+| verify_oma_mece.py 不可用 | BLOCKED：不得生成 MECE 通过结论；恢复脚本后重跑 |
 | Sub PRD 输出失败 | 保留中间产物，标注缺失项 |
 | MECE 校验 3 轮未通过 | 标记需人工介入 |
@@ -180,10 +180,10 @@
 ### 降级策略
 
 | 场景 | 主路径 | 降级 |
 |------|--------|------|
 | Sub PRD <200 字 | 按已有内容拆解 | 告知内容不足 |
-| 校验脚本不存在 | 自动化校验 | 降级手动校验 |
+| 校验脚本不存在 | 自动化校验 | BLOCKED：不得生成通过结论；恢复校验脚本后重跑 |
 | hier 不可用 | 委托调用 | 手动 `/lx-oma hier` |
diff --git a/.claude/skills/lx-rpe/SKILL.md b/.claude/skills/lx-rpe/SKILL.md
--- a/.claude/skills/lx-rpe/SKILL.md
+++ b/.claude/skills/lx-rpe/SKILL.md
@@ -92,7 +92,9 @@
 
 ## Pipeline 集成
 
-编排由 `lx-oma-orch` 统一管理。lx-rpe 不做 pipeline.yaml 读写，仅接收 BASE_DIR。
+编排由 `lx-oma-orch` 统一管理。`lx-rpe` 不做 `pipeline.yaml` 读写，仅接收 `BASE_DIR`。
+
+`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误；调用方必须先由 `/lx-oma split --pipeline <path>` 解析状态，再只传递 `BASE_DIR`。
diff --git a/.claude/skills/references/oma/skill-chaining.md b/.claude/skills/references/oma/skill-chaining.md
--- a/.claude/skills/references/oma/skill-chaining.md
+++ b/.claude/skills/references/oma/skill-chaining.md
@@ -24,8 +24,8 @@
 
-1. /lx-oma-hier docs/master-prd.md --pipeline <pipeline>
-2. /lx-oma-split sub-prds/domain-auth.md --pipeline <pipeline>
-3. /lx-rpe prd/auth/feat-login --pipeline <pipeline>
+1. /lx-oma hier docs/master-prd.md
+2. /lx-oma split sub-prds/domain-auth.md --pipeline <pipeline>
+3. /lx-rpe <BASE_DIR>
PATCH

git apply --check /tmp/pkg-b-static.patch
git apply /tmp/pkg-b-static.patch
```

期望 `git apply --check` 与 `git apply` 均为 exit `0`。

### 3.3 执行第 2 节给出的三个确定性替换

按顺序原样执行：

1. `validate_skill.py` 的 `check_r6` 整体替换命令；
2. `lx-oma/SKILL.md` 的 “Pipeline 参数所有权” 插入命令；
3. `skill-chaining.md` 的所有权说明插入命令；
4. `pipeline-contract.md` 的唯一入口替换命令。

每条命令期望 exit `0`、stdout 为空。

### 3.4 删除 Oracle 僵尸

```bash
git rm -- .claude/scripts/oracle_gate.py
git rm -- .omc/scripts/oracle_gate.py
```

期望 exit `0`。

### 3.5 生成最终候选补丁并检查

```bash
git diff --check

git diff --binary -- \
  .claude/scripts/oracle_gate.py \
  .omc/scripts/oracle_gate.py \
  .claude/skills/lx-validate-skill/SKILL.md \
  .claude/skills/lx-validate-skill/references/report-templates.md \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py \
  .claude/skills/lx-oma/SKILL.md \
  .claude/skills/lx-rpe/SKILL.md \
  .claude/skills/references/oma/skill-chaining.md \
  .claude/skills/references/oma/pipeline-contract.md \
  > /tmp/pkg-b-final.patch

test -s /tmp/pkg-b-final.patch
```

期望全部 exit `0`。

---

## ④ 逐条机械验收

### A-B1：HEAD 前件正确

```bash
test "$(git rev-parse HEAD)" = "91954a0b01f9c53edf94965238308fcb080818eb"
```

期望：

```text
exit code: 0
stdout: empty
```

---

### A-B2：两份 Oracle 僵尸均不存在

```bash
test ! -e .claude/scripts/oracle_gate.py
test ! -e .omc/scripts/oracle_gate.py
```

期望两条命令均：

```text
exit code: 0
stdout: empty
```

进一步检查 tracked 路径已删除：

```bash
test "$(git status --short -- .claude/scripts/oracle_gate.py .omc/scripts/oracle_gate.py | wc -l | tr -d ' ')" = "2"
git status --short -- .claude/scripts/oracle_gate.py .omc/scripts/oracle_gate.py
```

期望 stdout 中两条路径状态均为删除；允许 `D` 或因原路径类型变化显示的等价删除状态，路径必须各出现一次。

---

### A-B3：生产配置没有 Oracle 僵尸引用

```bash
if grep -RInE \
  --exclude-dir=.git \
  --exclude-dir=.omc \
  --exclude='*.pyc' \
  'scripts/oracle_gate\.py|oracle_gate\.py' \
  .claude/settings.json .claude/hooks .claude/skills
then
  exit 1
fi
```

期望：

```text
exit code: 0
stdout: empty
```

---

### A-B4：唯一基础验证裁决源存在

```bash
test -f .claude/scripts/verify_gate.py
grep -n 'Only VerifyGate VERIFIED allows plan.md \[x\]' .claude/scripts/verify_gate.py
```

期望：

```text
exit code: 0
stdout 包含:
7:Only VerifyGate VERIFIED allows plan.md [x].
```

PKG-A 合入后的最终联合验收：

```bash
test "$(
  grep -RIl \
    --include='*.py' \
    'def parse_verify_rules' \
    .claude/scripts .claude/hooks 2>/dev/null |
  sort -u
)" = ".claude/scripts/verify_gate.py"
```

期望：

```text
exit code: 0
stdout: empty
```

> 此联合验收若在 PKG-A 尚未合并前失败，不得删除；由整合器在 A+B 合并后重跑。

---

### A-B5：Oracle 评分器不能伪装基础 VERIFIED

```bash
if grep -nE \
  'decision[[:space:]]*=[[:space:]]*["'"'"']VERIFIED|["'"'"']decision["'"'"'][[:space:]]*:[[:space:]]*["'"'"']VERIFIED' \
  .claude/scripts/oracle_engine.py
then
  exit 1
fi
```

期望：

```text
exit code: 0
stdout: empty
```

---

### A-B6：R6 文档只有一种语义

```bash
grep -nF \
  '| R6 | scripts/ 仅允许 `.py` 与 `.sh`；`.py` 必须通过 `python3 -m py_compile`，`.sh` 必须通过 `bash -n`；其他扩展名一律失败 |' \
  .claude/skills/lx-validate-skill/SKILL.md

if grep -RInF \
  '| R6 | 缺少状态机声明 |' \
  .claude/skills/lx-validate-skill
then
  exit 1
fi

if grep -RInF \
  'scripts/ 仅 .py' \
  .claude/skills/lx-validate-skill
then
  exit 1
fi
```

期望：

- 第一条 exit `0`，stdout 恰好一行；
- 第二、三条 exit `0`，stdout 为空。

---

### A-B7：R6 执行器具备扩展名和语法双门禁

```bash
python3 -m py_compile \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py

grep -nF 'path.suffix not in {".py", ".sh"}' \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py

grep -nF '["bash", "-n", str(script)]' \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py

grep -nF '[sys.executable, "-m", "py_compile", str(script)]' \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py
```

期望每条：

```text
exit code: 0
```

其中 `py_compile` stdout 为空；三条 grep 各输出一行。

---

### A-B8：仓库现有 skill 脚本均符合新 R6

```bash
python3 - <<'PY'
from pathlib import Path
import py_compile
import subprocess
import sys

root = Path(".claude/skills")
files = sorted(
    path
    for path in root.glob("lx-*/scripts/**/*")
    if path.is_file()
)

bad_types = [
    str(path)
    for path in files
    if path.suffix not in {".py", ".sh"}
]
if bad_types:
    print("UNSUPPORTED:")
    print("\n".join(bad_types))
    raise SystemExit(2)

for path in files:
    if path.suffix == ".py":
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            print(f"PY_FAIL {path}: {exc}", file=sys.stderr)
            raise SystemExit(2)
    else:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"SH_FAIL {path}: {result.stderr}", file=sys.stderr)
            raise SystemExit(2)

print(f"R6_OK files={len(files)}")
PY
```

期望：

```text
exit code: 0
stdout: R6_OK files=<非负整数>
```

---

### A-B9：人工验证降级已消失

```bash
if grep -RInE \
  '校验脚本不存在.*手动校验|verify_oma_mece\.py 不可用.*手动|降级为手动 MECE' \
  .claude/skills/lx-oma
then
  exit 1
fi

grep -nF \
  'verify_oma_mece.py 不可用 | BLOCKED：不得生成 MECE 通过结论；恢复脚本后重跑' \
  .claude/skills/lx-oma/SKILL.md

grep -nF \
  '校验脚本不存在 | 自动化校验 | BLOCKED：不得生成通过结论；恢复校验脚本后重跑' \
  .claude/skills/lx-oma/SKILL.md
```

期望：

- 第一条 exit `0`、stdout 为空；
- 后两条 exit `0`、各输出一行。

---

### A-B10：Pipeline 所有权唯一

```bash
grep -nF \
  '`--pipeline <path>` 只允许由 `/lx-oma split` 消费。' \
  .claude/skills/lx-oma/SKILL.md

grep -nF \
  '`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误' \
  .claude/skills/lx-rpe/SKILL.md

grep -nF \
  '仅 `/lx-oma split` 可接收 `--pipeline <path>`。收到该参数时：' \
  .claude/skills/references/oma/pipeline-contract.md
```

期望三条均：

```text
exit code: 0
stdout: 各一行
```

禁止旧命令残留：

```bash
if grep -RInE \
  '/lx-rpe([^`[:cntrl:]]|[[:space:]])*--pipeline|/lx-oma-hier([^`[:cntrl:]]|[[:space:]])*--pipeline' \
  .claude/skills/lx-rpe \
  .claude/skills/lx-oma \
  .claude/skills/references/oma
then
  exit 1
fi
```

期望：

```text
exit code: 0
stdout: empty
```

---

### A-B11：没有补丁空白错误

```bash
git diff --check
```

期望：

```text
exit code: 0
stdout: empty
```

---

### A-B12：PKG-B 文件集没有越界到 PKG-A/PKG-C

```bash
git diff --name-only -- \
  .claude/scripts/carros_base.py \
  .claude/scripts/verify_gate.py \
  .claude/hooks/pretool-gate.py \
  scripts/test-verify-gate.py
```

期望：

```text
exit code: 0
stdout: empty
```

> 若这些文件施工前已有改动，整合器必须对比 `.omc/state/pkg-b-backup/pre-pkg-b.status`，确认 PKG-B 施工没有改变其 blob；不能仅根据总工作区 diff 判断。

严格 blob 验收：

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import subprocess
import sys

protected = [
    ".claude/scripts/carros_base.py",
    ".claude/scripts/verify_gate.py",
    ".claude/hooks/pretool-gate.py",
    "scripts/test-verify-gate.py",
]

manifest = Path(".omc/state/pkg-b-backup/protected.sha256")
if not manifest.exists():
    print("ERROR: protected.sha256 missing; preflight was not completed", file=sys.stderr)
    raise SystemExit(2)

expected = json.loads(manifest.read_text(encoding="utf-8"))
actual = {
    path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for path in protected
}
if actual != expected:
    print(json.dumps({"expected": expected, "actual": actual}, indent=2), file=sys.stderr)
    raise SystemExit(2)
print("PKG_B_BOUNDARY_OK")
PY
```

为使该验收成立，施工前在 **3.1 前置保护阶段**追加并执行：

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
import json

protected = [
    ".claude/scripts/carros_base.py",
    ".claude/scripts/verify_gate.py",
    ".claude/hooks/pretool-gate.py",
    "scripts/test-verify-gate.py",
]
data = {
    path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for path in protected
}
Path(".omc/state/pkg-b-backup/protected.sha256").write_text(
    json.dumps(data, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
```

期望最终 stdout：

```text
PKG_B_BOUNDARY_OK
```

exit code：

```text
0
```

---

## ⑤ 回滚命令

### 5.1 仅回滚 PKG-B 修改，不触碰其他工作区内容

```bash
set -euo pipefail

git restore --source=HEAD --staged --worktree -- \
  .claude/scripts/oracle_gate.py \
  .omc/scripts/oracle_gate.py \
  .claude/skills/lx-validate-skill/SKILL.md \
  .claude/skills/lx-validate-skill/references/report-templates.md \
  .claude/skills/lx-validate-skill/scripts/validate_skill.py \
  .claude/skills/lx-oma/SKILL.md \
  .claude/skills/lx-rpe/SKILL.md \
  .claude/skills/references/oma/skill-chaining.md \
  .claude/skills/references/oma/pipeline-contract.md
```

### 5.2 恢复施工前已存在的未提交改动

如果 `.omc/state/pkg-b-backup/pre-pkg-b.patch` 非空：

```bash
if [ -s .omc/state/pkg-b-backup/pre-pkg-b.patch ]; then
  git apply --check .omc/state/pkg-b-backup/pre-pkg-b.patch
  git apply .omc/state/pkg-b-backup/pre-pkg-b.patch
fi
```

### 5.3 回滚机械验收

```bash
git diff --check

test -e .claude/scripts/oracle_gate.py
test -e .omc/scripts/oracle_gate.py
```

期望：

```text
exit code: 0
```

最后移除本包临时文件：

```bash
rm -f /tmp/pkg-b-static.patch /tmp/pkg-b-final.patch
rm -rf .omc/state/pkg-b-backup
```

---

## ⑥ 禁止事项

1. **不得修改 PKG-A 文件。**  
   禁止修改：

   ```text
   .claude/scripts/carros_base.py
   .claude/scripts/verify_gate.py
   .claude/hooks/pretool-gate.py
   scripts/test-verify-gate.py
   ```

2. **不得修改 PKG-C 生命周期文件。**  
   禁止新增或修改 PreCompact、SessionEnd、SubagentStop、handoff 计数、goal/ghost 互斥实现。

3. **不得把 `.omc/scripts/oracle_gate.py` 改为软链接。**  
   该机制的裁决是删除，不是同步副本。

4. **不得保留 `.claude/scripts/oracle_gate.py` 兼容 wrapper。**  
   没有生产调用方需要兼容；wrapper 会继续形成第二入口。

5. **不得新增 `verification_service.py`、`verify_common.py`、`gate_adapter.py` 或其他中间层。**  
   唯一裁决源已经存在：`.claude/scripts/verify_gate.py`。

6. **不得让 Oracle 输出基础 `VERIFIED`。**  
   Oracle 只能复核、拒绝、升级或提出告警，不能替代 VerifyGate 的基础证据匹配。

7. **不得保留任何“验证器缺失时人工检查后通过”的描述。**  
   验证器缺失只能是 `BLOCKED`。人工可决定停止、修复或撤回，不能把缺证据变成通过。

8. **不得扩大 R6 白名单。**  
   只允许：

   ```text
   .py
   .sh
   ```

   不得即兴加入 `.js`、`.ts`、`.rb`、无扩展名文件或可执行二进制。

9. **不得把 R6 改回语言偏好规则。**  
   R6 的目的仅是可执行资产可被机械解析，不是强制所有脚本重写为 Python。

10. **不得给 `lx-rpe` 增加 `--pipeline` 兼容参数。**  
    兼容会恢复双重 pipeline 状态所有权。调用方必须改用 OMA 解析后的 `BASE_DIR`。

11. **不得把 `--pipeline` 扩展到 `hier`。**  
    本方案的唯一合法入口是：

    ```text
    /lx-oma split --pipeline <path>
    ```

12. **不得使用 `git reset --hard`、`git clean -fd` 或整仓 `git restore .`。**  
    当前工作区包含大量与本包无关的未提交改动；回滚只能使用第 ⑤ 节列出的精确路径。

13. **不得删除 `runtime_verify.py`、`verify_tests.py`、`feature_verify.py` 或 `oracle_engine.py`。**  
    它们不是基础 step 裁决源，但仍是证据生产、回归测试或 L2 复核资产；本包只限制其不得直接写 `VERIFIED`。

14. **任何 hunk 不能干净应用时必须停止。**  
    禁止使用 `patch --fuzz`、`git apply --reject`、手工寻找“近似位置”或重写整文件。

15. **PKG-A 联合验收未通过时不得宣告 PKG-B 整体完成。**  
    本包消除外围契约漂移；真正的 `cmd_verify → verify_gate → evidence receipt → _check_verified` 闭环由 PKG-A 建立。最终必须在 A+B 合并后执行 A-B4 联合验收。