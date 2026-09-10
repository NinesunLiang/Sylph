"""index48 S2：read-tracker 与 claim-audit 零触发路径移除回归。

移除依据（12 天真实遥测）：
- `IRRELEVANT_CLAIM`（file:line 引用未在 read-tracker 中）：审计中 **0 次**
- `COLD_START`（read-tracker 冷启动警告）：审计中 **0 次**
- `read-tracker` 钩子：1204 次运行，其**唯一消费者**即上述两条零触发路径

**保留并修复**（人类 BACKLOG 2026-09-09 明确裁决「保留 K2 EDIT_REPEAT 防抖」）：
- E6 / K2 的 edit-churn-log 机制保留；其 `_autofix_log_edit_repeat` 的
  `STATE_DIR` 未定义 bug（调用必抛 NameError 被吞）本轮修好。
- soft-completion 检测（228 次真实告警）保留。
- gate-bypassed 观测（拦截≠阻止留痕）保留。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
HOOK = HOOKS / "posttool-claim-audit.py"


def _src() -> str:
    return HOOK.read_text(encoding="utf-8")


def _code_lines() -> list[str]:
    return [l.split("#", 1)[0] for l in _src().splitlines() if l.split("#", 1)[0].strip()]


def test_read_tracker_removed():
    assert not (HOOKS / "read-tracker.py").exists(), "read-tracker 钩子仍在"
    assert "read-tracker.py" not in json.dumps(json.loads(SETTINGS.read_text()), ensure_ascii=False)


def test_read_tracker_dependent_paths_removed():
    """只查代码行——注释里说明「已移除」是允许的。"""
    code = "\n".join(_code_lines())
    for token in ("IRRELEVANT_CLAIM", "COLD_START"):
        assert token not in code, f"依赖 read-tracker 的零触发路径残留: {token}"


def test_k2_and_e6_kept():
    """人类裁决保留 K2（EDIT_REPEAT 防抖）——不得误删。"""
    src = _src()
    assert "edit-churn-log" in src, "K2/E6 的 churn-log 机制被误删"
    assert "E6_VIOLATIONS" in src, "E6 自我矛盾检测被误删"


def test_valuable_paths_kept():
    src = _src()
    assert "soft" in src.lower(), "soft-completion 检测被误删"
    assert "_detect_gate_bypassed" in src, "gate-bypassed 观测被误删"


def test_k2_state_dir_bug_fixed():
    """历史 bug：_autofix_log_edit_repeat 引用未定义的 STATE_DIR → NameError 被吞。

    修复后：模块级必须有 STATE_DIR 常量，且该函数在 main 之外也可见它。
    """
    assert "_autofix_log_edit_repeat" in _src(), "K2 autofix 被误删"
    head = _src().split("def main(")[0]
    assert re.search(r"^STATE_DIR\s*=", head, re.M), "模块级 STATE_DIR 未定义（K2 仍会 NameError）"


def test_hook_runs_clean_on_benign_payload():
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": "/tmp/x.md", "content": "hello"}})
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                          capture_output=True, text=True, timeout=30, cwd=str(ROOT))
    assert proc.returncode == 0, f"钩子退出码非 0: {proc.stderr[:300]}"
    assert "Traceback" not in proc.stderr, f"钩子抛异常: {proc.stderr[:300]}"
    assert json.loads(proc.stdout.strip().splitlines()[-1]).get("continue") is True
