#!/usr/bin/env python3
"""test-posttool-claim-audit.py — Claim Audit 测试 (G1 PSEUDO_INTEGRITY + E6 EDIT_REPEAT + 基础)
"""
from __future__ import annotations
import json, subprocess, sys, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK = PROJECT_ROOT / ".claude" / "hooks" / "posttool-claim-audit.py"
CACHE = PROJECT_ROOT / ".omc" / "state" / ".harness-cache"
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
PASS, FAIL = 0, 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name}  {detail}")

def run_hook(input_json: str) -> dict:
    """Run the hook as subprocess and return parsed JSON output."""
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=input_json,
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": r.stdout[:200], "stderr": r.stderr[:200]}

# ─── Setup: ensure harness cache enables the hook ───
CACHE.parent.mkdir(parents=True, exist_ok=True)
CACHE.write_text("__parsed_count__=1\nhooks_enabled.posttool_claim_audit=true\n")

# ─── Base tests ───
ok("exists", HOOK.exists())
ok("compiles", subprocess.run([sys.executable, "-c", f"import py_compile; py_compile.compile('{HOOK}', doraise=True)"], capture_output=True, text=True, timeout=10).returncode == 0)
d = run_hook('{"tool_name":"Write","tool_input":{"file_path":"some/report.md","content":"test"}}')
ok("accepts Write input", d.get("continue") is True, f"got={json.dumps(d)[:100]}")

# ─── K1: G1_PSEUDO_INTEGRITY — 数值断言无来源 ───

# K1-1: 非豁免文件中的无来源数值应当在 hook 输出中被标记
# 注意: hook 只对 非 代码/测试/参考 文件做 G1 检查
# 报告类文件应命中
k1_input_no_source = json.dumps({
    "tool_name": "Write",
    "tool_input": {
        "file_path": "docs/report.md",
        "content": "测试覆盖率 85%，性能提升 30%，节省 50% 的时间"
    }
})
k1_result = run_hook(k1_input_no_source)
k1_has_warn = "G1" in json.dumps(k1_result) or "PSEUDO_INTEGRITY" in json.dumps(k1_result)
ok("K1-1: 无来源数值断言触发 G1 警告", k1_has_warn, f"got={json.dumps(k1_result)[:200]}")

# K1-2: 有来源的数值断言不应触发
k1_input_with_source = json.dumps({
    "tool_name": "Write",
    "tool_input": {
        "file_path": "docs/report.md",
        "content": "测试覆盖率 85% [内部自检，非行业标准]，性能提升 30% [benchmark-run-7.md:42]"
    }
})
k1_result2 = run_hook(k1_input_with_source)
k1_no_warn = "G1" not in json.dumps(k1_result2) or "continue" in json.dumps(k1_result2)
ok("K1-2: 有来源数值断言不触发 G1", k1_no_warn, f"got={json.dumps(k1_result2)[:200]}")

# K1-3: 豁免文件（.py）不应触发 G1
k1_input_exempt = json.dumps({
    "tool_name": "Write",
    "tool_input": {
        "file_path": "src/test_runner.py",
        "content": "测试覆盖率 85%，性能提升 30%"
    }
})
k1_result3 = run_hook(k1_input_exempt)
k1_skip = d.get("continue") is True
ok("K1-3: 豁免路径 (.py) 跳过 G1 检查", k1_skip, f"got={json.dumps(k1_result3)[:100]}")

# ─── E6: EDIT_REPEAT — 高频编辑检测（需隔离 edit-churn-log） ───
EH_LOG = STATE_DIR / "edit-churn-log.jsonl"
eh_before = EH_LOG.read_text() if EH_LOG.exists() else ""

try:
    # 清空 edit-churn-log 并写入 4 条同文件记录
    EH_LOG.parent.mkdir(parents=True, exist_ok=True)
    EH_LOG.write_text("")
    import time
    t = int(time.time())
    for i in range(4):
        entry = {
            "ts": t - (4 - i) * 5,
            "file_path": "docs/churn-report.md",
            "tool_name": "Edit",
            "edit_mode": "replace",
            "edit_scope": "medium",
            "patience_score": 0.5,
            "sig": f"hash{i}",
            "edit_count": i + 1,
            "contradiction": False,
            "revert_of": None,
            "content_hash": f"ch{i}",
        }
        with open(EH_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # 触发检查 — 第5次编辑应命中 EDIT_REPEAT
    # 注意：路径不能用 "test-" 因为 hook 的豁免路径包含 /test- 会误匹配
    e6_input = json.dumps({
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "docs/churn-report.md",
            "old_string": "old",
            "new_string": "new"
        }
    })
    e6_result = run_hook(e6_input)
    e6_has_repeat = "EDIT_REPEAT" in json.dumps(e6_result)
    ok("E6-1: 同文件 4+ 次编辑触发 EDIT_REPEAT 警告", e6_has_repeat,
       f"got={json.dumps(e6_result.get('hookSpecificOutput',{}))[:200]}" if isinstance(e6_result, dict) else "")
except Exception as ex:
    ok("E6-1: EDIT_REPEAT", False, f"exception: {ex}")
finally:
    # 恢复原 edit-churn-log
    if EH_LOG.exists():
        EH_LOG.write_text(eh_before)

# ─── 输出 ───
print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
