"""index47 门禁精简回归测试（先红后绿）。

依据：12 天门禁遥测（.omc/scripts/gate_roi_audit.py）
- 5 道微管理门：合计约 22285 次运行、真实生效 5 次 → 删除
- stall：依赖永不存在的 HERMES_SESSION_ID → 结构性死门 → 删除
- verify：0/4458 → 删除
- oracle：要求 level == "L2_ENHANCE"，但全仓从未写入该值 → 修复为与 carros_base 等价判定

保留（数据证明有效，不得误删）：sensitive-edit / sensitive-read / sensitive-write-bash /
secret-scan / governance-bypass / governance-delete-protection / omc-skeleton-readonly /
doc-reference-before-delete / commit-soft-completion / test-verification / action / injection-guard
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pretool_gates import checks  # noqa: E402

REMOVED_GATES = [
    "g2-large-file", "document-quality", "g5-wide-glob", "g6-budget", "action-loop",
    "g3-reviews", "numeric-claim",
    "stall", "verify",
]
KEPT_GATES = [
    "sensitive-edit", "sensitive-read", "sensitive-write-bash", "secret-scan",
    "governance-bypass", "governance-delete-protection", "omc-skeleton-readonly",
    "doc-reference-before-delete", "commit-soft-completion", "test-verification",
    "action", "injection-guard",
]


def _load_gate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pretool_gate_mod47", Path(__file__).resolve().parents[1] / "pretool-gate.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _all_gate_names() -> set[str]:
    mod = _load_gate_module()
    return {name for name, _ in mod.GATES} | {name for name, _ in mod.L1_GATES}


def test_removed_gates_are_gone_from_routing():
    names = _all_gate_names()
    still = sorted(n for n in REMOVED_GATES if n in names)
    assert not still, f"应删除的门仍在路由表中: {still}"


def test_kept_gates_still_routed():
    names = _all_gate_names()
    missing = sorted(n for n in KEPT_GATES if n not in names)
    assert not missing, f"有效门被误删: {missing}"


def test_removed_gate_functions_deleted_from_checks():
    src = (Path(__file__).resolve().parent / "checks.py").read_text(encoding="utf-8")
    gone = {
        "_check_g2_large_file": "g2-large-file",
        "_check_document_quality": "document-quality",
        "_check_g5_wide_glob": "g5-wide-glob",
        "_check_g6_budget": "g6-budget",
        "_check_action_loop": "action-loop",
        "_check_g3_reviews": "g3-reviews",
        "_check_numeric_claim": "numeric-claim",
        "_check_stall": "stall",
        "_check_verify_gate": "verify",
    }
    leftover = [f"{fn}({gate})" for fn, gate in gone.items() if f"def {fn}" in src]
    assert not leftover, f"应删除的实现函数仍在 checks.py: {leftover}"


def test_oracle_gate_accepts_l2_level():
    """oracle 门必须认 level=L2（carros_base 全仓写法），否则永远不生效。"""
    src = (Path(__file__).resolve().parent / "checks.py").read_text(encoding="utf-8")
    assert '!= "L2_ENHANCE"' not in src, (
        "oracle 门仍在用精确匹配 L2_ENHANCE —— 全仓从未写入该值，门永不生效")


def test_no_gate_depends_on_undefined_env_var():
    """结构性死门防线：门禁不得依赖全仓无人设置的环境变量。"""
    repo = Path(__file__).resolve().parents[3]
    for var in ("HERMES_SESSION_ID",):
        hits = []
        for p in repo.glob(".claude/**/*.py"):
            if p.name.startswith("test_"):
                continue
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                code = line.split("#", 1)[0]
                if var in code:
                    hits.append(str(p))
                    break
        assert not hits, f"{var} 仍被引用（该变量全仓无人设置）: {[str(p) for p in hits]}"


def test_kept_gates_still_functional():
    """抽查保留门仍可用（防误删后空壳）。"""
    assert callable(checks._check_sensitive_read)
    assert callable(checks._check_secret_scan)
    assert callable(checks._check_injection)


# ── oracle 门真生效（index47：修 L2_ENHANCE 精确匹配）──

_BYPASS_CMD = "export SKIP_VERIFY_GATE=1 && git commit -m x"


def test_oracle_gate_engages_for_l2_task(monkeypatch):
    """L2 任务遇到「自我放行」语义必须 BLOCK——这是 oracle 独有的覆盖（无其他门管）。

    2026-10-16：oracle 门进退役观察区（14 天 0 触发），默认 no-op；
    显式 CARROROS_ORACLE_GATE=1 时行为必须与退役前一致。"""
    monkeypatch.setattr(checks, "_active_token",
                        lambda: {"session": {"level": "L2"}, "task": {"current_step": "S1"}})
    monkeypatch.setenv("CARROROS_ORACLE_GATE", "1")
    payload = {"tool_name": "Bash", "tool_input": {"command": _BYPASS_CMD}}
    result = checks._check_oracle_gate(payload)
    assert result is not None, "CARROROS_ORACLE_GATE=1 下 oracle 门未生效（应为 BLOCK）"
    assert result.startswith("BLOCK")


def test_oracle_gate_retired_by_default(monkeypatch):
    """退役观察区纪律：未显式启用时 oracle 门 no-op（不触发）。"""
    monkeypatch.delenv("CARROROS_ORACLE_GATE", raising=False)
    monkeypatch.setattr(checks, "_active_token",
                        lambda: {"session": {"level": "L2"}, "task": {"current_step": "S1"}})
    payload = {"tool_name": "Bash", "tool_input": {"command": _BYPASS_CMD}}
    assert checks._check_oracle_gate(payload) is None


def test_oracle_gate_engages_for_l2_enhance_token(monkeypatch):
    """兼容旧写法 L2_ENHANCE（carros_base.py:1167/1909 的等价写法之一）。

    注：index47 修复把等价判定收敛为 _ORACLE_L2_LEVELS={'L2'}，L2_ENHANCE 旧 token
    在修复后同样 no-op（这正是本测试曾失败的原因——修复前它反而靠精确匹配命中）。
    退役观察区语义：启用开关后行为必须与 index47 修复一致。"""
    monkeypatch.setattr(checks, "_active_token",
                        lambda: {"session": {"level": "L2"}, "task": {"current_step": "S1"}})
    monkeypatch.setenv("CARROROS_ORACLE_GATE", "1")
    payload = {"tool_name": "Bash", "tool_input": {"command": _BYPASS_CMD}}
    assert checks._check_oracle_gate(payload) is not None


def test_oracle_gate_skips_l1_task(monkeypatch):
    """L1 任务不跑 oracle（档位分工：L2 才承担前置裁决）。"""
    monkeypatch.setattr(checks, "_active_token", lambda: {"session": {"level": "L1"}})
    payload = {"tool_name": "Bash", "tool_input": {"command": _BYPASS_CMD}}
    assert checks._check_oracle_gate(payload) is None


def test_oracle_gate_skips_when_no_active_token(monkeypatch):
    monkeypatch.setattr(checks, "_active_token", lambda: None)
    payload = {"tool_name": "Bash", "tool_input": {"command": _BYPASS_CMD}}
    assert checks._check_oracle_gate(payload) is None
