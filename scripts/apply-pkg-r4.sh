#!/usr/bin/env bash
# apply-pkg-r4.sh — R4 补缺冲刺施工脚本(整合器基于真实代码)
# 项目: E1/E7/H9半/K1/S1/S2/K3/H8/H10/K4(S7 经核实 gov/ 已不存在,无需施工)
# 幂等: 已应用 SKIP(marker 判据);备份已存在不覆盖
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail() { echo "ERROR: $1" >&2; exit 1; }

# ---------- 1. 前置保护 ----------
BK=.omc/state/pkg-r4-backup
mkdir -p "$BK"
if [ ! -f "$BK/pre-pkg-r4.sha256" ]; then
  python3 - << 'PY'
from pathlib import Path
import hashlib, json
files = [
    ".claude/hooks/pretool-gate.py",
    ".claude/scripts/lib/error_dna.py",
    ".claude/scripts/verify_gate.py",
    ".claude/skills/lx-goal/SKILL.md",
    ".claude/skills/lx-oma/SKILL.md",
    ".claude/skills/references/oma/skill-chaining.md",
    ".claude/skills/skill-dependencies.yaml",
    ".claude/skills/lx-varlock/SKILL.md",
    ".claude/references/feature-registry.yaml",
    "VERSION",
    "CHANGELOG.md",
    ".omc/scripts/carros_base.py",
    "scripts/test-verify-gate.py",
]
data = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files if Path(p).exists()}
Path(".omc/state/pkg-r4-backup/pre-pkg-r4.sha256").write_text(
    json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("pre-pkg-r4.sha256 written")
PY
else
  echo "backup exists, skip"
fi

# ---------- 2. 替换批次 ----------
python3 - << 'PY'
from pathlib import Path
import sys

def replace(path, old, new, label, marker=None, required=True):
    p = Path(path)
    if not p.exists():
        if required:
            print(f"ERROR {label}: {path} missing", file=sys.stderr); raise SystemExit(2)
        print(f"SKIP {label} (file gone)"); return
    text = p.read_text(encoding="utf-8")
    mark = marker if marker is not None else new.strip()[:60]
    if mark in text:
        print(f"SKIP {label} (already applied)"); return
    old_n = text.count(old)
    if old_n == 0:
        if not required:
            print(f"SKIP {label} (anchor absent, optional)"); return
        print(f"ERROR {label}: anchor not found in {path}", file=sys.stderr); raise SystemExit(2)
    if old_n != 1:
        print(f"ERROR {label}: anchor not unique ({old_n}) in {path}", file=sys.stderr); raise SystemExit(2)
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"OK   {label}")

PG = ".claude/hooks/pretool-gate.py"
ED = ".claude/scripts/lib/error_dna.py"
VG = ".claude/scripts/verify_gate.py"

# ── E7: oracle FORCE 关键词截断修复(aut→auth) ──
replace(PG,
    'ORACLE_FORCE_KW = ["aut", "payment", "migration", "permission"]',
    'ORACLE_FORCE_KW = ["auth", "payment", "migration", "permission"]',
    "E7 oracle FORCE kw aut→auth")

# ── E1: Gate5 docstring 与行为对齐 ──
replace(PG,
    '"""Gate 5: 越界不阻断，记录 audit（方案二：柔性约束）"""',
    '"""Gate 5: 越界阻断（E1 防线；CARROROS_EDIT_SCOPE=warn 恢复方案二柔性约束）"""',
    "E1 gate5 docstring")

# ── E1a: token scope 越界 WARN→BLOCK ──
replace(PG,
    '''        # 越界 → audit 不阻断
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "token_scope_violation",
            "path": path,
            "scope": token_scope[:10],
        })
        return None  # 放行''',
    '''        # 越界 → BLOCK（E1 目标漂移防线；CARROROS_EDIT_SCOPE=warn 恢复柔性）
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "token_scope_violation",
            "path": path,
            "scope": token_scope[:10],
        })
        if os.environ.get("CARROROS_EDIT_SCOPE", "block").lower() == "warn":
            return None
        return (f"BLOCK edit_out_of_scope path={path}|"
                f"该路径不在当前任务 token scope 内。修复: 加入 token scope 或 plan.md ## Scope 段；"
                f"临时放行: CARROROS_EDIT_SCOPE=warn 或临时 bypass")''',
    "E1a token scope BLOCK")

# ── E1b: plan scope 越界 WARN→BLOCK ──
replace(PG,
    '''    if not _in_scope(path, scope):
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "plan_scope_violation",
            "path": path,
            "scope": scope[:10],
        })
        return None  # 放行
    return None''',
    '''    if not _in_scope(path, scope):
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "plan_scope_violation",
            "path": path,
            "scope": scope[:10],
        })
        if os.environ.get("CARROROS_EDIT_SCOPE", "block").lower() == "warn":
            return None
        return (f"BLOCK edit_out_of_scope path={path}|"
                f"该路径不在 plan.md ## Scope 声明内。修复: 将其加入 Scope 段；"
                f"临时放行: CARROROS_EDIT_SCOPE=warn 或临时 bypass")
    return None''',
    "E1b plan scope BLOCK",
    marker='不在 plan.md ## Scope 声明内')

# ── H9半: secret-scan 门(防明文密钥再染;轮换本身=人工) ──
replace(PG,
    "# ── Gate registry ──",
    '''SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")
SECRET_SCAN_MAX_BYTES = 1_000_000

def _git_secret_candidates(command: str) -> list[str]:
    """从 git add/commit 命令提取待扫描文件(相对仓库根)。"""
    import subprocess
    parts = command.split()
    if len(parts) < 2 or parts[0] != "git":
        return []
    sub = parts[1]
    if sub == "commit":
        try:
            r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                               capture_output=True, text=True, timeout=10)
            return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
        except Exception:
            return []
    if sub == "add":
        flags = [a for a in parts[2:] if a.startswith("-")]
        args = [a for a in parts[2:] if not a.startswith("-")]
        if "." in args or "-A" in flags or "--all" in flags:
            try:
                r = subprocess.run(["git", "ls-files", "--modified", "--others", "--exclude-standard"],
                                   capture_output=True, text=True, timeout=10)
                return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            except Exception:
                return []
        return args
    return []

def _check_secret_scan(payload: dict) -> str | None:
    """Gate: 阻断把明文密钥(sk-...)引入暂存区 — H9 防再染(轮换仍需人工)。"""
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload) or ""
    if not re.match(r"^\\s*git\\s+(add|commit)\\b", command):
        return None
    hits = []
    for rel in _git_secret_candidates(command):
        p = ROOT / rel
        try:
            if not p.is_file() or p.stat().st_size > SECRET_SCAN_MAX_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if SECRET_RE.search(text):
            hits.append(rel)
    if hits:
        _append_audit({
            "event_type": "secret_scan_block",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "plaintext_secret_in_staging",
            "files": hits[:10],
        })
        return ("BLOCK plaintext_secret_in_staging files=" + ",".join(hits[:5]) + "|"
                "检测到明文密钥(sk-...)。修复: 改为环境变量引用后再提交;"
                "确认误报或确需提交: 申请临时 bypass")
    return None


# ── Gate registry ──''',
    "H9 secret-scan gate")

replace(PG,
    '''    ("action", _check_action_gate),''',
    '''    ("action", _check_action_gate),
    ("secret-scan", _check_secret_scan),''',
    "H9 GATES entry")

# ── K1: error_dna 噪声过滤(<8 字符不入库) ──
replace(ED,
    '''    """记录失败为 Error DNA。返回 DNA 记录。"""
    dna = {''',
    '''    """记录失败为 Error DNA。返回 DNA 记录。

    K1 噪声过滤: error 文本 < 8 字符(如 "t"/"err" 测试噪声)不入库,
    返回带 quarantined 标记的记录 — 防再染(存量隔离见 .omc/error-dna.quarantine.jsonl)。
    """
    if len((error_text or "").strip()) < 8:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step_id,
            "error": (error_text or "")[:500],
            "artifact": artifact_path or "",
            "retry_count": retry_count,
            "suggested_action": "quarantined: noise below MIN_ERROR_LEN(8)",
            "quarantined": True,
        }
    dna = {''',
    "K1 error_dna noise filter")

# ── H10: verify_gate 审计日期格式统一 %Y%m%d ──
replace(VG,
    '''def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")''',
    '''def today() -> str:
    # H10: 与 carros_base/carros_utils 审计文件名格式统一(%Y%m%d)
    return datetime.now(timezone.utc).strftime("%Y%m%d")''',
    "H10 audit date format")

# ── S1a: lx-goal 幽灵路由(lx-race 已归档/lx-stepwise 已移除) ──
replace(".claude/skills/lx-goal/SKILL.md",
    '''| ≥3 同构独立子任务 | **lx-race**（并行蜂群） |
| 有依赖链/异构/跨模块/根因不明 | **lx-stepwise**（串行） |''',
    '''| ≥3 同构独立子任务 | **原生并行 Task 调用**（一条消息内多个 Agent 并行；lx-race 已归档，勿路由） |
| 有依赖链/异构/跨模块/根因不明 | **串行 direct**（按依赖顺序执行+证据；lx-stepwise 已移除，勿路由） |''',
    "S1a lx-goal ghost routes")

# ── S1b: lx-oma race 模式措辞 ──
replace(".claude/skills/lx-oma/SKILL.md",
    '> **注意：** `execution_mode: stepwise` 为根级声明。split 子命令内部使用 `race` 模式 — AI 自主拆解 + 脚手架构建后交还人工审核门禁。',
    '> **注意：** `execution_mode: stepwise` 为根级声明。split 子命令内部并行执行 — AI 自主拆解 + 脚手架构建后交还人工审核门禁（lx-race 已归档，此处仅为模式描述，非 skill 调用）。',
    "S1b lx-oma race wording")

# ── S1c1: skill-chaining 主链图去 lx-test-gen ──
replace(".claude/skills/references/oma/skill-chaining.md",
    '''lx-oma-hier ──→ lx-oma-split ──→ lx-rpe ──→ lx-code-review ──→ lx-test-gen
 (主PRD→Sub)    (Sub→Feature)    (开发)      (审查)            (测试)''',
    '''lx-oma-hier ──→ lx-oma-split ──→ lx-rpe ──→ lx-code-review
 (主PRD→Sub)    (Sub→Feature)    (开发)      (审查)''',
    "S1c1 chaining diagram ghost")

# ── S1c2: skill-chaining 链式调用去 lx-test-gen + 注记 ──
replace(".claude/skills/references/oma/skill-chaining.md",
    '''  4. /lx-code-review
  5. /lx-test-gen
```

> `--pipeline` 仅属于 `/lx-oma-split`（即 `/lx-oma split`）；`lx-rpe` 不消费 pipeline 文件。`BASE_DIR` 必须来自 OMA 对 pipeline 磁盘状态的解析结果。''',
    '''  4. /lx-code-review
```

> `--pipeline` 仅属于 `/lx-oma-split`（即 `/lx-oma split`）；`lx-rpe` 不消费 pipeline 文件。`BASE_DIR` 必须来自 OMA 对 pipeline 磁盘状态的解析结果。
> lx-test-gen 未实现，已从主链移除（S1 幽灵路由清理）。''',
    "S1c2 chaining list ghost")

# ── S1c3: skill-chaining 并发链 lx-race 归档注记 ──
replace(".claude/skills/references/oma/skill-chaining.md",
    '''## 并发链：Race 模式

```
lx-race
  ├── Task A: lx-rpe feat-A        (并行)
  ├── Task B: lx-rpe feat-B        (并行)
  └── Task C: lx-rpe feat-C        (并行)
       ↓
  聚合报告 → lx-oma-orch 更新 pipeline
```''',
    '''## 并发链：并行执行模式

> lx-race 已归档（.claude/skills/archived/lx-race）。并行通过原生 Task/Agent 并发调用实现。

```
并行执行（原生 Task 并发）
  ├── Task A: lx-rpe feat-A        (并行)
  ├── Task B: lx-rpe feat-B        (并行)
  └── Task C: lx-rpe feat-C        (并行)
       ↓
  聚合报告 → lx-oma-orch 更新 pipeline
```''',
    "S1c3 chaining race section")

# ── S1d: skill-dependencies lx-race 标记归档 ──
replace(".claude/skills/skill-dependencies.yaml",
    '''  - id: lx-race
    version: v1.0.0
    type: coordination''',
    '''  - id: lx-race
    version: v1.0.0
    status: archived  # 已归档(S1): .claude/skills/archived/lx-race,并行请用原生 Task 并发
    type: coordination''',
    "S1d skill-deps lx-race archived")

# ── S2: lx-varlock markdown 修复(表 + 铁律编号 + 4 个代码块) ──
VL = ".claude/skills/lx-varlock/SKILL.md"

# S2a: 表(行级定位——损坏行连字符数不稳定,内容锚不可靠)
_p = Path(VL)
_text = _p.read_text(encoding="utf-8")
if '| 脚本 | 用途 | 调用时机 |\n|------|------|----------|' in _text:
    print("SKIP S2a varlock table (already applied)")
else:
    _lines = _text.split("\n")
    _hits = [i for i, ln in enumerate(_lines) if ln.startswith("### scripts/") and "| 脚本 | 用途 |" in ln]
    if len(_hits) != 1:
        print(f"ERROR S2a: corrupted table line hits={len(_hits)}", file=sys.stderr)
        raise SystemExit(2)
    _lines[_hits[0]] = ('### scripts/（确定性执行层）\n\n'
                        '| 脚本 | 用途 | 调用时机 |\n'
                        '|------|------|----------|\n'
                        '| `scripts/varlock.py` | 敏感信息的双向脱敏：代理执行与读写恢复 | 敏感文件或命令交互 |')
    _p.write_text("\n".join(_lines), encoding="utf-8")
    print("OK   S2a varlock table")

replace(VL,
    '1. **绝对禁止使用原生 `Read` 读取 `.env`、`secrets.yml` 等凭据文件**。如果需要读取，必须使用 `python3 .claude/skills/lx-varlock/scripts/varlock.py read <file>`。返回的内容会将真实的密钥如 `222222` 替换为 `[MASKED_KEY_NAME]`。2. **绝对禁止使用原生 `Edit/Write` 写入敏感凭据**。如果需要修改 `.env`，必须输出包含占位符的文本，并调用 `python3 varlock.py write .env "<内容>"`，脚本会在落盘时自动将占位符恢复为明文。3. **禁止在 Bash 工具中组装明文 Token**（如 `curl -H "Auth: sk-ant..."`）。必须使用占位符调用代理：`python3 varlock.py run "curl -H \'Auth: [MASKED_TOKEN]\' ..."`。',
    '''1. **绝对禁止使用原生 `Read` 读取 `.env`、`secrets.yml` 等凭据文件**。如果需要读取，必须使用 `python3 .claude/skills/lx-varlock/scripts/varlock.py read <file>`。返回的内容会将真实的密钥如 `222222` 替换为 `[MASKED_KEY_NAME]`。
2. **绝对禁止使用原生 `Edit/Write` 写入敏感凭据**。如果需要修改 `.env`，必须输出包含占位符的文本，并调用 `python3 varlock.py write .env "<内容>"`，脚本会在落盘时自动将占位符恢复为明文。
3. **禁止在 Bash 工具中组装明文 Token**（如 `curl -H "Auth: sk-ant..."`）。必须使用占位符调用代理：`python3 varlock.py run "curl -H 'Auth: [MASKED_TOKEN]' ..."`。''',
    "S2b varlock rules numbering",
    marker='`。\n2. **绝对禁止使用原生 `Edit/Write`')

replace(VL,
    '''```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py read .env# 返回脱敏结果：DB_PASS=[MASKED_DB_PASS]
bashpython3 .claude/skills/lx-varlock/scripts/varlock.py read .env# 返回脱敏结果：DB_PASS=[MASKED_DB_PASS]

```''',
    '''```bash
python3 .claude/skills/lx-varlock/scripts/varlock.py read .env
# 返回脱敏结果：DB_PASS=[MASKED_DB_PASS]
```''',
    "S2c varlock fence read")

replace(VL,
    '''```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py write .env "DB_HOST=127.0.0.1\\nDB_PASS=[MASKED_DB_PASS]"
bashpython3 .claude/skills/lx-varlock/scripts/varlock.py write .env "DB_HOST=127.0.0.1\\nDB_PASS=[MASKED_DB_PASS]"
```''',
    '''```bash
python3 .claude/skills/lx-varlock/scripts/varlock.py write .env "DB_HOST=127.0.0.1\\nDB_PASS=[MASKED_DB_PASS]"
```''',
    "S2d varlock fence write",
    marker='```bash\npython3 .claude/skills/lx-varlock/scripts/varlock.py write')

replace(VL,
    '''```bash
#
告诉用户：请打开本地普通终端，执行：python3 .claude/skills/lx-varlock/scripts/varlock.py set OPENAI_API_KEY "sk-xxxx..."
```待用户回复
后
，由 AI 代理执行测试：''',
    '''```bash
# 告诉用户：请打开本地普通终端，执行：
python3 .claude/skills/lx-varlock/scripts/varlock.py set OPENAI_API_KEY "sk-xxxx..."
```
待用户回复后，由 AI 代理执行测试：''',
    "S2e varlock fence set")

replace(VL,
    '''```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py run "curl -X POST <https://api.openai.com/v1/chat/completions> -H 'Authorization: Bearer [MASKED_OPENAI_API_KEY]' -d '{\\"model\\": \\"gpt-4o\\"}'"

```''',
    '''```bash
python3 .claude/skills/lx-varlock/scripts/varlock.py run "curl -X POST <https://api.openai.com/v1/chat/completions> -H 'Authorization: Bearer [MASKED_OPENAI_API_KEY]' -d '{\\"model\\": \\"gpt-4o\\"}'"
```''',
    "S2f varlock fence run",
    marker='```bash\npython3 .claude/skills/lx-varlock/scripts/varlock.py run')

# ── K3: VERSION 解冻 + CHANGELOG ──
replace("VERSION", "v7.1.0", "v7.2.0", "K3 VERSION bump")
replace("CHANGELOG.md",
    '# Changelog\n\n## v7.1.0 (2026-07-12)',
    '''# Changelog

## v7.2.0 (2026-07-20)

### Changed（R0-R4 评分冲刺：验证链 + 契约统一 + 补缺）
- R0：hook matcher 扩展 Read/Grep/Glob（H2）；hook-launcher fail-closed（H3）；oracle_gate 双源符号链接（H6-lite）；anti-patterns 测试污染回退
- R1（PKG-B）：oracle_gate 僵尸双删；R6 三方漂移统一为 .py/.sh 白名单 + py_compile/bash -n 语法门；--pipeline 所有权单点化（仅 /lx-oma split）；lx-oma 校验缺失改 BLOCKED fail-closed
- R2（PKG-A）：cmd_verify 接线 verify_gate（fail-closed，无证据不 [x]）；audit 自动绑 task_id（跨任务重放失效）；_check_verified step+task 双绑定、None 通配删除；L1 无规则降级留痕 verify_degraded
- R4：E1 edit-scope WARN→BLOCK（CARROROS_EDIT_SCOPE=warn 可恢复柔性）；oracle FORCE 关键词截断修复（aut→auth）；新增 secret-scan 门防明文密钥入库（H9 半，轮换需人工）；error-dna <8 字符噪声过滤 + 存量隔离；feature-registry 增加 runtime_reality 真相对齐（69 目录 vs 6 注册）；lx-race/lx-stepwise/lx-test-gen 幽灵路由清理（S1）；lx-varlock markdown 修复（S2）；verify_gate 审计日期格式统一 %Y%m%d（H10）

## v7.1.0 (2026-07-12)''',
    "K3 CHANGELOG entry")

# ── K4: feature-registry 真相对齐头 ──
replace(".claude/references/feature-registry.yaml",
    'version: 1\nhooks:',
    '''version: 2
# runtime_reality（2026-07-20 K4 真相对齐）：settings.json 实际注册 6 个 hook 入口——
#   PreToolUse: hook-launcher.sh → pretool-gate.py（统一 14 门） + carroros-night-deny.py
#   UserPromptSubmit: pretool-user-approve.py
#   PostToolUse: posttool-gate.py
#   SessionStart: session-start.py
#   Stop: stop-flywheel.py
# 本文件 69 条目为能力目录（含已合并/规划中），非运行时注册表；运行时以 settings.json 为唯一真相源。
hooks:''',
    "K4 registry reality header")
PY

# ---------- 3. K1 存量噪声隔离 ----------
python3 - << 'PY'
from pathlib import Path
import json
p = Path(".omc/error-dna.jsonl")
if p.exists():
    keep, junk = [], []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            keep.append(line)
            continue
        (junk if len(str(e.get("error", "")).strip()) < 8 else keep).append(line)
    if junk:
        q = Path(".omc/error-dna.quarantine.jsonl")
        existing = q.read_text(encoding="utf-8") if q.exists() else ""
        with q.open("a", encoding="utf-8") as f:
            for line in junk:
                if line not in existing:
                    f.write(line + "\n")
        p.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
        print(f"K1 quarantine: {len(junk)} noise entries moved")
    else:
        print("K1 quarantine: no noise found")
else:
    print("K1 quarantine: error-dna.jsonl absent")
PY

# ---------- 4. H8: 删除无引用 stale bak ----------
if [ -f .claude/settings.json.hooks-on.bak ]; then
  rm .claude/settings.json.hooks-on.bak
  echo "H8: settings.json.hooks-on.bak removed (untracked, zero references)"
fi

# ---------- 5. 机械验收 ----------
echo "== acceptance =="

# A-R4-1: 语法
python3 -m py_compile .claude/hooks/pretool-gate.py || fail "A-R4-1 pretool-gate"
python3 -m py_compile .claude/scripts/lib/error_dna.py || fail "A-R4-1 error_dna"
python3 -m py_compile .claude/scripts/verify_gate.py || fail "A-R4-1 verify_gate"
echo "A-R4-1 OK"

# A-R4-2: 锚点
grep -qF 'ORACLE_FORCE_KW = ["auth"' .claude/hooks/pretool-gate.py || fail "A-R4-2 auth kw"
grep -qF 'BLOCK edit_out_of_scope' .claude/hooks/pretool-gate.py || fail "A-R4-2 edit-scope block"
grep -qF '_check_secret_scan' .claude/hooks/pretool-gate.py || fail "A-R4-2 secret-scan"
grep -qF '("secret-scan", _check_secret_scan)' .claude/hooks/pretool-gate.py || fail "A-R4-2 GATES entry"
grep -qF 'quarantined: noise below MIN_ERROR_LEN(8)' .claude/scripts/lib/error_dna.py || fail "A-R4-2 K1 filter"
grep -qF 'runtime_reality' .claude/references/feature-registry.yaml || fail "A-R4-2 K4"
grep -qF 'v7.2.0' VERSION || fail "A-R4-2 VERSION"
grep -qF '%Y%m%d")' .claude/scripts/verify_gate.py || fail "A-R4-2 H10"
echo "A-R4-2 OK"

# A-R4-3: 行为单元(E1 BLOCK / secret-scan / K1 filter)
python3 - << 'PY'
import importlib.util, json, os, tempfile, sys
from pathlib import Path
ROOT = Path.cwd()

spec = importlib.util.spec_from_file_location("pg", ROOT / ".claude/hooks/pretool-gate.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)
os.chdir(ROOT)

fails = []

# E1: 越界 BLOCK / 界内放行 / warn 模式放行
with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    (tdir / "plan.md").write_text("# Plan\n\n## Scope\n\n- src/\n", encoding="utf-8")
    fake = {"task": {"current_step": "S1", "status": "active", "dir": str(tdir)},
            "session": {"id": "tt-r4"}, "task_dir": str(tdir)}
    pg._active_token = lambda: fake
    r = pg._check_edit_scope({"tool_name": "Edit", "tool_input": {"file_path": "etc/evil.md"}})
    if not (isinstance(r, str) and r.startswith("BLOCK edit_out_of_scope")):
        fails.append(f"edit-scope out not BLOCK: {r!r}")
    r = pg._check_edit_scope({"tool_name": "Edit", "tool_input": {"file_path": "src/main.py"}})
    if r is not None:
        fails.append(f"edit-scope in blocked: {r!r}")
    os.environ["CARROROS_EDIT_SCOPE"] = "warn"
    r = pg._check_edit_scope({"tool_name": "Edit", "tool_input": {"file_path": "etc/evil.md"}})
    if r is not None:
        fails.append(f"warn mode not soft: {r!r}")
    del os.environ["CARROROS_EDIT_SCOPE"]

# H9: secret-scan BLOCK / 清洁放行 / 非 git 放行
t = ROOT / ".omc/state/r4-test"
t.mkdir(parents=True, exist_ok=True)
try:
    (t / "secret.txt").write_text('token = "sk-' + "A" * 40 + '"\n', encoding="utf-8")
    (t / "clean.txt").write_text("hello\n", encoding="utf-8")
    r = pg._check_secret_scan({"tool_name": "Bash", "tool_input": {"command": "git add .omc/state/r4-test/secret.txt"}})
    if not (isinstance(r, str) and r.startswith("BLOCK plaintext_secret_in_staging")):
        fails.append(f"secret not BLOCK: {r!r}")
    r = pg._check_secret_scan({"tool_name": "Bash", "tool_input": {"command": "git add .omc/state/r4-test/clean.txt"}})
    if r is not None:
        fails.append(f"clean blocked: {r!r}")
    r = pg._check_secret_scan({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    if r is not None:
        fails.append(f"non-git blocked: {r!r}")
finally:
    import shutil
    shutil.rmtree(t, ignore_errors=True)

# K1: 噪声不入库 / 真实错误入库
spec2 = importlib.util.spec_from_file_location("ed", ROOT / ".claude/scripts/lib/error_dna.py")
ed = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(ed)
with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    d = ed.record_error(tdir, "S1", "t")
    if not d.get("quarantined"):
        fails.append("noise not quarantined")
    if (tdir / "error-dna.jsonl").exists():
        fails.append("noise written to dna log")
    d2 = ed.record_error(tdir, "S1", "real failure: syntax error on line 3")
    if d2.get("quarantined"):
        fails.append("real error quarantined")
    if not (tdir / "error-dna.jsonl").exists():
        fails.append("real error not written")

if fails:
    print("\n".join(fails), file=sys.stderr)
    raise SystemExit(2)
print("A-R4-3 behavior units OK")
PY

# A-R4-4: 存量隔离核验
python3 - << 'PY'
from pathlib import Path
import json, sys
p = Path(".omc/error-dna.jsonl")
if p.exists():
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if len(str(e.get("error", "")).strip()) < 8:
            print(f"noise remains at line {i}", file=sys.stderr)
            raise SystemExit(2)
print("A-R4-4 quarantine verified")
PY

# A-R4-5: R2 回归(verify 链不受影响)
python3 scripts/test-verify-gate.py > /tmp/r4-verify-regression.log 2>&1 || fail "A-R4-5 verify regression (see /tmp/r4-verify-regression.log)"
grep -q '20/20 PASS' /tmp/r4-verify-regression.log || fail "A-R4-5 not 20/20"
echo "A-R4-5 OK (20/20)"

# A-R4-6: launcher 回归
bash scripts/test-hook-launcher.sh > /tmp/r4-launcher.log 2>&1 || fail "A-R4-6 launcher regression"
echo "A-R4-6 OK"

# A-R4-7: 幽灵路由负向核验
if grep -nF '/lx-test-gen' .claude/skills/references/oma/skill-chaining.md | grep -v '未实现'; then
  fail "A-R4-7 lx-test-gen still routed"
fi
if grep -nE '\*\*lx-race\*\*（并行蜂群）|\*\*lx-stepwise\*\*' .claude/skills/lx-goal/SKILL.md; then
  fail "A-R4-7 lx-goal ghost route remains"
fi
if grep -nF '内部使用 `race` 模式' .claude/skills/lx-oma/SKILL.md; then
  fail "A-R4-7 lx-oma race wording remains"
fi
echo "A-R4-7 OK"

# A-R4-8: 空白检查(限本包文件)
git diff --check -- \
  .claude/hooks/pretool-gate.py \
  .claude/scripts/lib/error_dna.py \
  .claude/scripts/verify_gate.py \
  .claude/skills/lx-goal/SKILL.md \
  .claude/skills/lx-oma/SKILL.md \
  .claude/skills/references/oma/skill-chaining.md \
  .claude/skills/skill-dependencies.yaml \
  .claude/skills/lx-varlock/SKILL.md \
  .claude/references/feature-registry.yaml \
  VERSION CHANGELOG.md || fail "A-R4-8 git diff --check"
echo "A-R4-8 OK"

echo "== ALL R4 ACCEPTANCE PASSED =="
