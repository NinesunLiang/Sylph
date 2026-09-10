"""index48 S1：error-dna 飞轮移除回归（人类 2026-09-10 裁决）。

移除依据（12 天真实遥测）：
- `.omc/state/error-dna.jsonl` 83 条记录 **100% `resolution: pending`**
- `.omc/knowledge/` 学习产出 **0**
- 76 条 `bash_path_not_found` 中 **67 条为测试自造命令 `ls /nonexistent`**
- `lib/error_dna.check_retry_gate` 无任何 live 调用方（仅安装脚本 apply-pkg-r4.sh 提及）
- 「重试阻断门禁」的立项依据（同一路径重试 67 次）即上述测试噪声

保留：`completion-gate`（防虚假完成，人类判定有效）需与 error-dna 解耦后继续工作。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"


def test_error_dna_hook_removed():
    assert not (HOOKS / "error-dna.py").exists(), "error-dna 钩子仍在"


def test_error_dna_lib_removed():
    assert not (ROOT / ".claude/scripts/lib/error_dna.py").exists(), "lib/error_dna.py 仍在"


def test_error_dna_tests_removed():
    assert not (HOOKS / "test_error_dna_failure_event.py").exists()
    assert not (ROOT / ".claude/scripts/test_error_dna_retry_gate.py").exists()


def test_settings_has_no_error_dna_registration():
    text = SETTINGS.read_text(encoding="utf-8")
    assert "error-dna.py" not in text, "settings.json 仍注册 error-dna"
    # 注册块本身不得残留
    data = json.loads(text)
    for event, groups in (data.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                assert "error-dna" not in h.get("command", ""), f"{event} 仍注册 error-dna"


def _code_lines(path: Path) -> list[str]:
    """只取代码行（剥掉 # 注释），注释里说明「已移除」不算引用。"""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        code = line.split("#", 1)[0]
        if code.strip():
            out.append(code)
    return out


def test_completion_gate_decoupled_from_error_dna():
    assert not any("error-dna.jsonl" in l for l in _code_lines(HOOKS / "completion-gate.py")), \
        "completion-gate 仍在代码中依赖 error-dna.jsonl"


def test_no_live_hook_writes_or_reads_error_dna():
    """除测试外，不得有存活钩子**在代码中**引用 error-dna 数据文件。"""
    offenders = [
        p.name for p in HOOKS.glob("*.py")
        if not p.name.startswith("test_")
        and any("error-dna.jsonl" in l for l in _code_lines(p))
    ]
    assert not offenders, f"存活钩子仍在代码中引用 error-dna.jsonl: {offenders}"
