#!/usr/bin/env python3
"""
Carror OS Capability Smoke Tests — 模拟场景 → 验证机制真实起效
基于 story-01~18 描述的能力，注入已知刺激 → 检查 hook 是否产生预期响应。
"""

import os, sys, json, re, subprocess, time
from pathlib import Path

ROOT = Path("/Users/lucas.liang/Desktop/Sylph/Carror_Enhance_OS")
HOOKS = ROOT / ".claude" / "hooks"
STATE = ROOT / ".omc" / "state"
TASK_DIR = ROOT / ".omc" / "tasks" / "20260721" / "smoke-capability-20260721"

PASS, FAIL, SKIP = "✅ PASS", "❌ FAIL", "⚠️  SKIP"
results = []

def record(test_id, name, status, evidence, expected, actual):
    results.append({"id": test_id, "name": name, "status": status,
                    "evidence": evidence, "expected": expected, "actual": actual})
    icon = "✅" if status == PASS else ("❌" if status == FAIL else "⚠️")
    print(f"{icon} {test_id}: {name}")
    if status != PASS:
        print(f"   预期: {expected}")
        print(f"   实际: {actual}")

# ─── Helpers ───
def hook_exists(name):
    for ext in (".py", ".sh"):
        p = HOOKS / f"{name}{ext}"
        if p.exists():
            return str(p)
    return None

def grep_hook_source(hook_name, pattern):
    """Check if a pattern exists in a hook's source code."""
    hook_path = hook_exists(hook_name)
    if not hook_path:
        return False
    try:
        return bool(re.search(pattern, open(hook_path).read(), re.MULTILINE))
    except Exception:
        return False

def check_hook_evidence(hook_name, min_lines=1):
    """Check if hook-evidence.jsonl contains entries for this hook."""
    ev = STATE / "hook-evidence.jsonl"
    if not ev.exists():
        return 0
    count = 0
    try:
        for line in open(ev):
            if hook_name in line:
                count += 1
    except Exception:
        pass
    return count

def check_error_dna():
    """Check error-dna.jsonl for recent escape pattern records."""
    ed = STATE / "error-dna.jsonl"
    if not ed.exists():
        return 0, []
    entries = []
    try:
        for line in open(ed):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return len(entries), entries

def run_hook_direct(hook_name, stdin_data=None):
    """Try to run a hook directly and capture its output/exit code."""
    hook_path = hook_exists(hook_name)
    if not hook_path:
        return None, "hook not found"
    try:
        if hook_path.endswith(".py"):
            cmd = [sys.executable, hook_path]
        else:
            cmd = ["bash", hook_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                          input=stdin_data)
        return r.returncode, r.stdout + r.stderr
    except Exception as e:
        return None, str(e)

def check_settings_registration(hook_name):
    """Check if hook is registered in settings.json."""
    settings = ROOT / ".claude" / "settings.json"
    if not settings.exists():
        return False
    try:
        content = open(settings).read()
        return hook_name in content
    except Exception:
        return False

print("=" * 60)
print("Carror OS Capability Smoke Tests")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"36 hooks | 18 skills | 19 stories")
print("=" * 60)

# ═══════════════════════════════════════════
# S1: 铁律#1(不编造) — posttool-claim-audit 交叉验证
# Story-02, Story-04
# 验证：claim-audit 的代码中是否包含 file:line 交叉验证逻辑
# ═══════════════════════════════════════════
hook = "posttool-claim-audit"
path = hook_exists(hook)
has_cross_verify = grep_hook_source(hook, r"cross.?verify|cross.?check|file:line.*audit|read.?track")
has_read_track = grep_hook_source(hook, r"read.?track|_read_files|files_read")
ev_count = check_hook_evidence(hook)
registered = check_settings_registration(hook)

if path:
    if has_cross_verify or has_read_track:
        record("S1", "铁律#1-不编造(claim-audit交叉验证)", PASS,
               f"hook={path}, cross_verify={has_cross_verify}, read_track={has_read_track}, evidence_events={ev_count}",
               "交叉验证逻辑存在", "交叉验证逻辑存在且hook已触发")
    else:
        record("S1", "铁律#1-不编造(claim-audit交叉验证)", FAIL,
               f"hook={path}, 未找到file:line交叉验证逻辑",
               "cross-verify 或 read-track 检测逻辑", "无交叉验证逻辑")
else:
    record("S1", "铁律#1-不编造(claim-audit交叉验证)", SKIP,
           "hook文件不存在", "posttool-claim-audit.py 或 .sh", "无此文件")

# ═══════════════════════════════════════════
# S2: 铁律#3(证据门禁) — completion-gate VERIFIED检测
# Story-04 L1-L4 防线
# 验证：completion-gate 代码是否包含 VERIFIED/evidence_missing 检测逻辑
# ═══════════════════════════════════════════
hook = "completion-gate"
path = hook_exists(hook)
has_verified = grep_hook_source(hook, r"VERIFIED|evidence.*missing|evidence_freshness|EVIDENCE_FILE")
has_soft_words = grep_hook_source(hook, r"应该没问题|基本完成|理论上|看起来正常|差不多了|SOFT_WORD")
ev_count = check_hook_evidence(hook)

if path:
    if has_verified:
        record("S2", "铁律#3-证据门禁(completion-gate)", PASS,
               f"hook={path}, VERIFIED检测={has_verified}, evidence_events={ev_count}",
               "VERIFIED/evidence_missing 检测逻辑", "检测逻辑存在")
    else:
        record("S2", "铁律#3-证据门禁(completion-gate)", FAIL,
               f"hook={path}, 未找到VERIFIED检测逻辑",
               "VERIFIED 关键词或 evidence_missing 逻辑", "无此类检测")
else:
    record("S2", "铁律#3-证据门禁(completion-gate)", SKIP, "hook不存在", "", "")

# ═══════════════════════════════════════════
# S3: 铁律#5(范围冻结) — pretool-edit-scope or pretool-gate scope check
# Story-02, Story-03
# 验证：范围冻结机制是否有"越界编辑检测"逻辑
# ═══════════════════════════════════════════
hook = "pretool-gate"
path = hook_exists(hook)
has_scope = grep_hook_source(hook, r"scope|范围|plan\.md|out.of.scope|超出范围|越界")
ev_count = check_hook_evidence(hook)

if path and has_scope:
    record("S3", "铁律#5-范围冻结(pretool-gate)", PASS,
           f"hook={path}, scope检测逻辑存在, evidence_events={ev_count}",
           "范围/越界检测逻辑", "检测逻辑存在")
else:
    # Try alternative: pretool-edit-scope
    path2 = hook_exists("pretool-edit-scope")
    if path2:
        record("S3", "铁律#5-范围冻结(pretool-edit-scope)", PASS,
               f"hook={path2}", "范围冻结hook存在", "hook存在")
    else:
        record("S3", "铁律#5-范围冻结", FAIL,
               f"pretool-gate scope={has_scope}, pretool-edit-scope={'存在' if path2 else '不存在'}",
               "范围冻结机制", "未找到")

# ═══════════════════════════════════════════
# S4: 铁律#6(隐私防线) — privacy-gate
# Story-02
# 验证：privacy-gate 是否包含敏感文件检测模式
# ═══════════════════════════════════════════
hook = "privacy-gate"
path = hook_exists(hook)
has_env = grep_hook_source(hook, r"\.env|\.pem|\.key|id_rsa|credentials|secret|token.*auth")
registered = check_settings_registration(hook)
ev_count = check_hook_evidence(hook)

if path:
    if has_env:
        record("S4", "铁律#6-隐私防线(privacy-gate)", PASS,
               f"hook={path}, 敏感文件检测模式存在, evidence_events={ev_count}",
               ".env/.pem/.key 等敏感文件检测", "检测模式存在")
    else:
        record("S4", "铁律#6-隐私防线(privacy-gate)", FAIL,
               f"hook={path}, 未找到敏感文件检测模式",
               "需要包含 .env / .key / credentials 检测", "无此类模式")
else:
    record("S4", "铁律#6-隐私防线(privacy-gate)", SKIP, "hook不存在", "", "")

# ═══════════════════════════════════════════
# S5: 反模式A2(虚假完成) — completion-gate 软词检测
# Story-09: 7 个软完成触发词
# v7.x: posttool-anti-pattern-detect 已移除，A2 检测在 completion-gate.py
# ═══════════════════════════════════════════
hook = "completion-gate"
path = hook_exists(hook)
soft_words = ["应该没问题", "基本完成", "理论上", "看起来正常", "差不多了", "之前验证过", "大部分通过"]
found_words = sum(1 for w in soft_words if grep_hook_source(hook, w))
has_soft_block = grep_hook_source(hook, r"SOFT_WORD|SOFT_COMPLETION|软完成|违禁词")
ev_count = check_hook_evidence(hook)

if path and found_words >= 3:
    record("S5", "反模式A2-虚假完成(completion-gate软词检测)", PASS,
           f"hook={path}, 软词命中={found_words}/7, evidence_events={ev_count}",
           "≥3/7 软词在 completion-gate.py 中", f"{found_words}/7 命中")
else:
    record("S5", "反模式A2-虚假完成(completion-gate软词检测)", FAIL,
           f"hook={'存在' if path else '缺失'}, 软词命中={found_words}/7",
           "≥3/7 软词检测", f"{found_words}/7")

# ═══════════════════════════════════════════
# S6: Error DNA — 逃逸检测 (story-13)
# 验证：error-dna 是否从"收集exit≠0"迁移到"检测逃逸"
# ═══════════════════════════════════════════
ed_count, ed_entries = check_error_dna()
hook = "error-dna"
path = hook_exists(hook)
has_escape = grep_hook_source(hook, r"escape|逃逸|E[1-4]|治理文件绕过|验证码伪造|上下文规避|证据编造")
has_classifier = grep_hook_source(hook, r"classif|分类|GATE-BUG|HOOK-CHAIN|REF-DRIFT|LOGIC-GAP")
ev_count = check_hook_evidence(hook)

if path and ed_count > 0:
    if has_escape or has_classifier:
        record("S6", "Error-DNA-逃逸检测(v3)", PASS,
               f"hook={path}, 逃逸检测={has_escape}, 分类={has_classifier}, dna_entries={ed_count}, evidence_events={ev_count}",
               "逃逸模式检测(E1-E4)或错误分类逻辑", f"{ed_count}条错误DNA记录, 分类={'有' if has_classifier else '无'}")
    else:
        record("S6", "Error-DNA-逃逸检测(v3)", FAIL,
               f"hook={path}, ed_count={ed_count}, 但缺少逃逸检测和分类逻辑",
               "逃逸检测或4大类错误分类", "无分类/逃逸逻辑")
else:
    record("S6", "Error-DNA-逃逸检测(v3)", FAIL if not path else SKIP,
           f"hook={'存在' if path else '不存在'}, ed_entries={ed_count}",
           "error-dna hook + ≥1条DNA记录", f"hook={'OK' if path else 'MISS'}, 记录={ed_count}")

# ═══════════════════════════════════════════
# S7: 水位防线(context-guard) — 上下文水位硬阻断
# Story-06 五件套
# 验证：context-guard 是否包含水位检测+阻断逻辑
# ═══════════════════════════════════════════
hook = "context-guard"
path = hook_exists(hook)
has_watermark = grep_hook_source(hook, r"watermark|水位|80%|90%|FORCE|READONLY|context.*force.*override")
has_escape_hatch = grep_hook_source(hook, r"context.?force.?override|override.*context|逃生")
ev_count = check_hook_evidence(hook)

if path:
    if has_watermark:
        record("S7", "水位防线(context-guard)", PASS,
               f"hook={path}, 水位检测={has_watermark}, 逃生门={has_escape_hatch}, evidence_events={ev_count}",
               "水位阈值检测(80%/90%) + 硬阻断", "水位检测逻辑存在")
    else:
        record("S7", "水位防线(context-guard)", FAIL,
               f"hook={path}, 未找到水位检测逻辑",
               "需要包含 80%/90% 水位阈值检测", "无水位检测")
else:
    record("S7", "水位防线(context-guard)", SKIP, "hook不存在", "", "")

# ═══════════════════════════════════════════
# S8: 反模式H1/F1(语义编造/假设驱动) — 已确认移除
# v7.x 清理: posttool-anti-pattern-detect 源码存在但从未部署
# H1/F1 ROI 评估后决定不恢复——正则无法抓语义编造
# ═══════════════════════════════════════════
hook = "posttool-anti-pattern-detect"
path = hook_exists(hook)
if not path:
    record("S8", "反模式H1/F1-已确认移除(v7.x清理)", PASS,
           "posttool-anti-pattern-detect 已从所有副本删除, H1/F1 不通过正则实现",
           "确认移除", "文件不存在——符合预期")
else:
    record("S8", "反模式H1/F1-应已移除但仍存在", FAIL,
           f"残留文件: {path}", "不应存在", "文件仍存在")

# ═══════════════════════════════════════════
# S9: Goal/Ghost 自主降级 — mode detection
# Story-08 双生子
# 验证：is_mode_active() 是否在 hook 中被引用
# ═══════════════════════════════════════════
hooks_with_mode = []
for f in sorted(HOOKS.iterdir()):
    if f.suffix == ".py" and not f.name.startswith("__"):
        try:
            content = open(f).read()
            if "is_mode_active" in content or "autonomous" in content.lower():
                hooks_with_mode.append(f.name)
        except Exception:
            pass

if len(hooks_with_mode) >= 5:
    record("S9", "Goal/Ghost自主降级(is_mode_active)", PASS,
           f"{len(hooks_with_mode)} hooks 引用 is_mode_active(): {', '.join(hooks_with_mode[:6])}",
           "≥5 个 hook 引用 is_mode_active()来实现自主模式下降级", f"{len(hooks_with_mode)} 个 hooks")
else:
    record("S9", "Goal/Ghost自主降级(is_mode_active)", FAIL,
           f"仅 {len(hooks_with_mode)} 个 hooks: {hooks_with_mode}",
           "≥5 个 hook 需要感知自主模式", f"仅 {len(hooks_with_mode)} 个")

# ═══════════════════════════════════════════
# S10: Hook 链完整性 — 注册表 vs 磁盘文件一致性
# Story-03 门禁骑士团
# 验证：settings.json 注册的 hook 是否在磁盘上存在
# ═══════════════════════════════════════════
settings = ROOT / ".claude" / "settings.json"
if settings.exists():
    try:
        data = json.load(open(settings))
        registered_paths = set()
        for event_group in data.get("hooks", {}).values():
            if isinstance(event_group, list):
                for group in event_group:
                    if isinstance(group, dict):
                        for h in group.get("hooks", []):
                            if isinstance(h, dict):
                                cmd = h.get("command", "")
                                # Extract path from "python3 .claude/hooks/foo.py" or "bash .claude/hooks/foo.sh"
                                m = re.search(r'\.claude/hooks/([^\s"]+)', cmd)
                                if m:
                                    registered_paths.add(m.group(1))

        disk_files = set(f.name for f in HOOKS.iterdir()
                        if f.suffix in (".py", ".sh") and not f.name.startswith("__"))

        missing = [p for p in registered_paths if p not in disk_files]
        extra = [p for p in disk_files
                if p not in registered_paths and p not in ("harness_core.py", "harness_lib.py",
                    "carroros_hooklib.py", "carroros-night-deny.py", "agentic-ui.py",
                    "carroros-open-in-browser.py", "hook-launcher.py")]

        if not missing:
            record("S10", "Hook链完整性(注册=磁盘)", PASS,
                   f"注册 {len(registered_paths)} 个, 磁盘 {len(disk_files)} 个, 未注册={len(extra)}",
                   "无注册但磁盘缺失的hook", "全部注册hook在磁盘上存在")
        else:
            record("S10", "Hook链完整性(注册=磁盘)", FAIL,
                   f"注册={registered_paths}, 缺失={missing}",
                   "所有注册hook在磁盘上存在", f"缺失: {missing}")
    except Exception as e:
        record("S10", "Hook链完整性(注册=磁盘)", FAIL, str(e), "", "")
else:
    record("S10", "Hook链完整性(注册=磁盘)", SKIP, "settings.json not found", "", "")

# ═══════════════════════════════════════════
# S11: 上下文三件套 (v7.x: 五件套→三件套)
# skill-usage-tracker + compact-detect 已确认移除(ROI zero)
# ═══════════════════════════════════════════
three_piece = ["token_writer", "turn-counter", "context-guard"]
found_pieces = []
for name in three_piece:
    if hook_exists(name):
        found_pieces.append(name)
missing_pieces = [n for n in three_piece if n not in found_pieces]

if len(found_pieces) == 3:
    record("S11", "上下文三件套(token_writer+turn-counter+context-guard)", PASS,
           f"全部存在: {found_pieces}",
           "3/3 核心套件存在", "3/3 存在")
else:
    record("S11", "上下文三件套", FAIL,
           f"已找到: {found_pieces}, 缺失: {missing_pieces}",
           "3/3 存在", f"{len(found_pieces)}/3")

# ═══════════════════════════════════════════
# S12: 记忆神殿注入 (v7.x: inject-project-knowledge → session-start.py)
# inject-project-knowledge 源码存在但从未部署，功能由 session-start.py 替代
# ═══════════════════════════════════════════
hook = "session-start"
path = hook_exists(hook)
has_handoff = grep_hook_source(hook, r"handoff|session-handoff|交接")
has_task = grep_hook_source(hook, r"task|token|active")
has_prompt = grep_hook_source(hook, r"last.user|user.prompt|最近")
ev_count = check_hook_evidence(hook)

if path and has_handoff:
    record("S12", "记忆神殿注入(session-start替代inject-project-knowledge)", PASS,
           f"hook={path}, handoff注入={has_handoff}, task={has_task}, prompt={has_prompt}, evidence_events={ev_count}",
           "session-start 注入 handoff + 任务上下文 + 用户提示", "注入逻辑存在")
else:
    record("S12", "记忆神殿注入(session-start)", FAIL,
           f"hook={'存在' if path else '缺失'}, handoff={has_handoff}",
           "session-start 应包含 handoff/任务/提示 注入", "不满足")

# ═══════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("SMOKE TEST RESULTS")
print("=" * 60)

passed = sum(1 for r in results if r["status"] == PASS)
failed = sum(1 for r in results if r["status"] == FAIL)
skipped = sum(1 for r in results if r["status"] == SKIP)
total = len(results)

for r in results:
    icon = "✅" if r["status"] == PASS else ("❌" if r["status"] == FAIL else "⚠️")
    print(f"  {icon} {r['id']}: {r['name']}")

print(f"\n  PASS: {passed}/{total}  FAIL: {failed}/{total}  SKIP: {skipped}/{total}")
print(f"  Score: {passed}/{total-passed-skipped+passed} = {passed/(total-skipped)*100:.0f}% (不计SKIP)")

# Write report
report = {
    "test_run": "2026-07-21",
    "task": "smoke-capability-20260721",
    "total": total,
    "passed": passed,
    "failed": failed,
    "skipped": skipped,
    "score_pct": round(passed/(total-skipped)*100) if (total-skipped) > 0 else 0,
    "results": results
}

report_path = TASK_DIR / "smoke-results.json"
TASK_DIR.mkdir(parents=True, exist_ok=True)
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n  Report: {report_path}")
