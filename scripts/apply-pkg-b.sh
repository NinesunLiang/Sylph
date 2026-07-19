#!/usr/bin/env bash
# apply-pkg-b.sh — PKG-B(gpt-5.6Sol)验证契约统一施工脚本
# 来源: round2/gpt.md 方案 + 整合器对 3 处失配 hunk 的真实内容重做
# 整合器适配(全部记录,非静默):
#   A1 基线: gpt 前件 91954a0 → 实际 HEAD 50619b2(R0 已入库 H2/H3/H6-lite)
#   A2 lx-oma 插入锚: gpt 写 `--pipeline <pipeline>` → 真实为 `--pipeline <id>`(:168)
#   A3 pipeline-contract 锚: gpt 写 `--pipeline <path>` → 真实为 `--pipeline <id>`(:14)
#   A4 skill-chaining: 保留文件自有命令风格(/lx-oma-hier 连字符,:12 triggers 已注册双风格),
#      仅剥 hier/rpe 的 --pipeline;split 行补 <id> 占位
#   A5 validate_skill.py: gpt 假设 check_r6/check_r7 函数不存在;真实为 check()(:21)内联块(:51-57),
#      按 gpt 裁决语义(白名单+语法门)重写该块,sys.exit WARN 为未登记漂移随块移除
#   A6 oracle_gate 双删: .omc 侧已是符号链接(R0 已入库),git rm 适用
# 幂等: 替换已应用则 SKIP;备份已存在则不覆盖
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail() { echo "ERROR: $1" >&2; exit 1; }

# ---------- 1. 前置保护 ----------
BK=.omc/state/pkg-b-backup
mkdir -p "$BK"
if [ ! -f "$BK/pre-pkg-b.status" ]; then
  git status --porcelain=v1 > "$BK/pre-pkg-b.status"
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
    > "$BK/pre-pkg-b.patch"
  echo "backup written"
else
  echo "backup exists, skip"
fi

python3 - << 'PY'
from pathlib import Path
import hashlib, json
bk = Path(".omc/state/pkg-b-backup/protected.sha256")
if not bk.exists():
    protected = [
        ".claude/scripts/carros_base.py",
        ".claude/scripts/verify_gate.py",
        ".claude/hooks/pretool-gate.py",
        "scripts/test-verify-gate.py",
    ]
    data = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected}
    bk.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("protected.sha256 written")
else:
    print("protected.sha256 exists, skip")
PY

# ---------- 2. 文档与代码替换(锚点唯一校验 + 幂等) ----------
python3 - << 'PY'
from pathlib import Path
import sys

def replace(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    # 幂等: 先查"已应用"(new 是 old 的超集时,count(old) 永远为 1,必须先判)
    if new.strip()[:60] in text:
        print(f"SKIP {label} (already applied)")
        return
    old_n = text.count(old)
    if old_n == 0:
        print(f"ERROR {label}: anchor not found in {path}", file=sys.stderr)
        raise SystemExit(2)
    if old_n != 1:
        print(f"ERROR {label}: anchor not unique ({old_n}) in {path}", file=sys.stderr)
        raise SystemExit(2)
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"OK   {label}")

# E1: lx-validate-skill SKILL.md R6 行(gpt §2.3,行号:66 实证)
replace(
    ".claude/skills/lx-validate-skill/SKILL.md",
    "| R6 | scripts/ 仅 .py（无 .sh 超出模板文件） | glob 检查 |",
    "| R6 | scripts/ 仅允许 `.py` 与 `.sh`；`.py` 必须通过 `python3 -m py_compile`，`.sh` 必须通过 `bash -n`；其他扩展名一律失败 | 扩展名白名单 + 逐文件语法检查 |",
    "E1 SKILL.md R6",
)

# E2: report-templates.md R6 行(gpt §2.4,真实位于:41 警告列表)
replace(
    ".claude/skills/lx-validate-skill/references/report-templates.md",
    "| R6 | 缺少状态机声明 | 添加 ### 状态机 声明 |",
    "| R6 | scripts/ 含非 `.py`/`.sh` 文件，或脚本语法检查失败 | 删除非白名单脚本；对 `.py` 修复至 `python3 -m py_compile` 通过，对 `.sh` 修复至 `bash -n` 通过 |",
    "E2 report-templates R6",
)

# E3: lx-oma 降级表 A(gpt §2.6.2)
replace(
    ".claude/skills/lx-oma/SKILL.md",
    "| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |",
    "| verify_oma_mece.py 不可用 | BLOCKED：不得生成 MECE 通过结论；恢复脚本后重跑 |",
    "E3 lx-oma mece fail-closed",
)

# E4: lx-oma 降级表 B(gpt §2.6.1)
replace(
    ".claude/skills/lx-oma/SKILL.md",
    "| 校验脚本不存在 | 自动化校验 | 降级手动校验 |",
    "| 校验脚本不存在 | 自动化校验 | BLOCKED：不得生成通过结论；恢复校验脚本后重跑 |",
    "E4 lx-oma verify-script fail-closed",
)

# E5: lx-oma Pipeline 参数所有权(gpt §2.6.3,锚适配 <id>)
replace(
    ".claude/skills/lx-oma/SKILL.md",
    "入口 `--pipeline <id>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。",
    """入口 `--pipeline <id>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。

### Pipeline 参数所有权

- `--pipeline <id>` 只允许由 `/lx-oma split` 消费。
- `<id>` 必须指向已存在的 pipeline 状态文件；路径缺失、文件缺失或解析失败均为 `BLOCKED`。
- `lx-rpe` 不接收 `--pipeline`，不读取或写入 `pipeline.yaml`；OMA 只向 RPE 传递已解析的 `BASE_DIR`。
- 未经 OMA 状态机落盘的自然语言“pipeline 已完成”不构成阶段证据。""",
    "E5 lx-oma pipeline ownership",
)

# E6: lx-rpe Pipeline 集成段(gpt §2.7)
replace(
    ".claude/skills/lx-rpe/SKILL.md",
    "编排由 `lx-oma-orch` 统一管理。lx-rpe 不做 pipeline.yaml 读写，仅接收 BASE_DIR。",
    """编排由 `lx-oma-orch` 统一管理。`lx-rpe` 不做 `pipeline.yaml` 读写，仅接收 `BASE_DIR`。

`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误；调用方必须先由 `/lx-oma split --pipeline <id>` 解析状态，再只传递 `BASE_DIR`。""",
    "E6 lx-rpe pipeline rejection",
)

# E7: skill-chaining 主链调用块 + 所有权注记(gpt §2.8,保留连字符风格/缩进/5 行)
replace(
    ".claude/skills/references/oma/skill-chaining.md",
    """链式调用:
  1. /lx-oma-hier docs/master-prd.md --pipeline
  2. /lx-oma-split sub-prds/domain-auth.md --pipeline
  3. /lx-rpe prd/auth/feat-login --pipeline
  4. /lx-code-review
  5. /lx-test-gen
```""",
    """链式调用:
  1. /lx-oma-hier docs/master-prd.md
  2. /lx-oma-split sub-prds/domain-auth.md --pipeline <id>
  3. /lx-rpe prd/auth/feat-login
  4. /lx-code-review
  5. /lx-test-gen
```

> `--pipeline` 仅属于 `/lx-oma-split`（即 `/lx-oma split`）；`lx-rpe` 不消费 pipeline 文件。`BASE_DIR` 必须来自 OMA 对 pipeline 磁盘状态的解析结果。""",
    "E7 skill-chaining pipeline ownership",
)

# E8: pipeline-contract 唯一入口(gpt §2.9,锚适配 <id>,原 3 步保留为解析步骤)
replace(
    ".claude/skills/references/oma/pipeline-contract.md",
    "收到 `--pipeline <id>` 时：",
    """仅 `/lx-oma split` 可接收 `--pipeline <id>`。收到该参数时：

**硬约束**：
1. `<id>` 不存在、不可读或解析失败：返回 `BLOCKED`，不得降级为内存状态或人工声明。
2. `lx-rpe` 不得接收该参数；RPE 只接收 OMA 从磁盘状态解析出的 `BASE_DIR`。
3. pipeline 阶段推进必须先原子落盘，再向下游发出动作。

**解析步骤**：""",
    "E8 pipeline-contract single entry",
)

# E9: validate_skill.py import 增 subprocess
replace(
    ".claude/skills/lx-validate-skill/scripts/validate_skill.py",
    "import argparse, sys, json",
    "import argparse, sys, json, subprocess",
    "E9 validate_skill import",
)

# E10: validate_skill.py R6 块重写(gpt §2.5 语义,真实结构适配)
replace(
    ".claude/skills/lx-validate-skill/scripts/validate_skill.py",
    """    # 6. scripts/*.py 如存在，必须有 exit code 处理
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for py in scripts_dir.glob("*.py"):
            code = py.read_text(encoding="utf-8")
            if "sys.exit" not in code:
                warnings.append(f"scripts/{py.name} 缺少 sys.exit（建议加退出码）")""",
    """    # 6. R6: scripts/ 仅允许 .py/.sh，且逐文件语法检查（.py=py_compile, .sh=bash -n）
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        script_files = sorted(
            p for p in scripts_dir.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
        for script in script_files:
            rel = script.relative_to(skill_dir)
            if script.suffix not in {".py", ".sh"}:
                violations.append(f"R6: scripts/ 含非 .py/.sh 文件: {rel}")
                continue
            if script.suffix == ".py":
                proc = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(script)],
                    capture_output=True, text=True, timeout=30,
                )
            else:
                proc = subprocess.run(
                    ["bash", "-n", str(script)],
                    capture_output=True, text=True, timeout=30,
                )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout).strip().replace("\\n", " ")[:240]
                violations.append(f"R6: 脚本语法检查失败 {rel}: {detail}")""",
    "E10 validate_skill R6 rewrite",
)
PY

# ---------- 3. 删除 Oracle 僵尸(gpt §2.1/§2.2) ----------
if [ -L .omc/scripts/oracle_gate.py ]; then
  rm .omc/scripts/oracle_gate.py
  echo "symlink .omc/scripts/oracle_gate.py removed"
fi
if [ -e .claude/scripts/oracle_gate.py ]; then
  git rm -q .claude/scripts/oracle_gate.py
  echo "git rm .claude/scripts/oracle_gate.py"
fi
if [ -e .omc/scripts/oracle_gate.py ]; then
  git rm -q .omc/scripts/oracle_gate.py
  echo "git rm .omc/scripts/oracle_gate.py"
fi

# ---------- 4. 机械验收(适配版 A-B) ----------
echo "== acceptance =="

# A-B2: 双 Oracle 不存在
test ! -e .claude/scripts/oracle_gate.py || fail "A-B2: .claude oracle_gate still exists"
test ! -e .omc/scripts/oracle_gate.py || fail "A-B2: .omc oracle_gate still exists"
echo "A-B2 OK"

# A-B3: 生产配置无 Oracle 僵尸引用(排除 lib/oracle_gate_light——不同文件,保留)
if grep -RInE 'scripts/oracle_gate\.py' \
  .claude/settings.json .claude/hooks .claude/skills .claude/scripts \
  2>/dev/null | grep -v __pycache__ | grep -v 'oracle_gate_light'; then
  fail "A-B3: oracle_gate references remain"
fi
echo "A-B3 OK"

# A-B6: R6 文档单一语义
grep -qF 'scripts/ 仅允许 `.py` 与 `.sh`' .claude/skills/lx-validate-skill/SKILL.md || fail "A-B6: new R6 missing in SKILL.md"
if grep -RInF '| R6 | 缺少状态机声明 |' .claude/skills/lx-validate-skill 2>/dev/null; then
  fail "A-B6: old R6 semantics remain in report-templates"
fi
if grep -RInF 'scripts/ 仅 .py' .claude/skills/lx-validate-skill 2>/dev/null; then
  fail "A-B6: old R6 text remains"
fi
echo "A-B6 OK"

# A-B7: R6 执行器双门禁
python3 -m py_compile .claude/skills/lx-validate-skill/scripts/validate_skill.py || fail "A-B7: py_compile validate_skill.py"
grep -qF 'script.suffix not in {".py", ".sh"}' .claude/skills/lx-validate-skill/scripts/validate_skill.py || fail "A-B7: whitelist missing"
grep -qF '["bash", "-n", str(script)]' .claude/skills/lx-validate-skill/scripts/validate_skill.py || fail "A-B7: bash -n missing"
grep -qF '[sys.executable, "-m", "py_compile", str(script)]' .claude/skills/lx-validate-skill/scripts/validate_skill.py || fail "A-B7: py_compile call missing"
echo "A-B7 OK"

# A-B8: 全仓 skill 脚本过新 R6
python3 - << 'PY'
from pathlib import Path
import py_compile, subprocess, sys
root = Path(".claude/skills")
files = sorted(
    p for p in root.glob("lx-*/scripts/**/*")
    if p.is_file() and "__pycache__" not in p.parts
)
bad_types = [str(p) for p in files if p.suffix not in {".py", ".sh"}]
if bad_types:
    print("UNSUPPORTED:\n" + "\n".join(bad_types), file=sys.stderr)
    raise SystemExit(2)
for p in files:
    if p.suffix == ".py":
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as exc:
            print(f"PY_FAIL {p}: {exc}", file=sys.stderr)
            raise SystemExit(2)
    else:
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"SH_FAIL {p}: {r.stderr}", file=sys.stderr)
            raise SystemExit(2)
print(f"R6_OK files={len(files)}")
PY

# A-B9: 人工验证降级消失
if grep -RInE '校验脚本不存在.*手动校验|verify_oma_mece\.py 不可用.*手动|降级为手动 MECE' .claude/skills/lx-oma 2>/dev/null; then
  fail "A-B9: manual-fallback text remains"
fi
grep -qF 'verify_oma_mece.py 不可用 | BLOCKED：不得生成 MECE 通过结论；恢复脚本后重跑' .claude/skills/lx-oma/SKILL.md || fail "A-B9: mece BLOCKED line missing"
grep -qF '校验脚本不存在 | 自动化校验 | BLOCKED：不得生成通过结论；恢复校验脚本后重跑' .claude/skills/lx-oma/SKILL.md || fail "A-B9: script-missing BLOCKED line missing"
echo "A-B9 OK"

# A-B10: Pipeline 所有权唯一
grep -qF '`--pipeline <id>` 只允许由 `/lx-oma split` 消费。' .claude/skills/lx-oma/SKILL.md || fail "A-B10: lx-oma ownership missing"
grep -qF '`lx-rpe` 收到 `--pipeline` 时必须拒绝执行并返回参数错误' .claude/skills/lx-rpe/SKILL.md || fail "A-B10: lx-rpe rejection missing"
grep -qF '仅 `/lx-oma split` 可接收 `--pipeline <id>`。收到该参数时：' .claude/skills/references/oma/pipeline-contract.md || fail "A-B10: pipeline-contract entry missing"
if grep -RInE '/lx-rpe([^`]| )*--pipeline|/lx-oma-hier([^`]| )*--pipeline' \
  .claude/skills/lx-rpe .claude/skills/lx-oma .claude/skills/references/oma 2>/dev/null; then
  fail "A-B10: legacy --pipeline usage remains"
fi
echo "A-B10 OK"

# A-B11: 无空白错误
git diff --check || fail "A-B11: git diff --check"
echo "A-B11 OK"

# A-B12: PKG-A 文件未动
python3 - << 'PY'
from pathlib import Path
import hashlib, json, sys
protected = [
    ".claude/scripts/carros_base.py",
    ".claude/scripts/verify_gate.py",
    ".claude/hooks/pretool-gate.py",
    "scripts/test-verify-gate.py",
]
expected = json.loads(Path(".omc/state/pkg-b-backup/protected.sha256").read_text(encoding="utf-8"))
actual = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected}
if actual != expected:
    print(json.dumps({"expected": expected, "actual": actual}, indent=2), file=sys.stderr)
    raise SystemExit(2)
print("PKG_B_BOUNDARY_OK")
PY

echo "== ALL PKG-B ACCEPTANCE PASSED =="
