"""index49：now_iso 单一真源（少即是多）回归。

去重前实测：`now_iso` 在 `.claude/scripts/` 下被**重复定义 13 次**，
且实现完全一致（`datetime.now(timezone.utc).replace(microsecond=0).isoformat()`）。
`carros_utils.py` 早已提供同一实现，但 10 个文件各自重写而非复用。

处置：保留 `carros_utils.now_iso` 为唯一真源，其余 10 处改为 `from carros_utils import now_iso`。

未合并（语义不同，非真重复）：
- `today()`：3 种不同格式（%Y%m%d vs %Y-%m-%d），合并会改行为
- `read_json()`：4 种不同签名/异常语义
- `write_json()`：2 种（原子写 vs 直接写）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude" / "scripts"

# 唯一真源
CANONICAL = "carros_utils.py"
# 允许保留本地定义的文件（carros_base 用 try-import+兜底模式，见其实现）
ALLOWED_DEFINERS = {CANONICAL, "carros_base.py"}


def _files_defining_now_iso() -> list[str]:
    out = []
    for p in SCRIPTS.rglob("*.py"):
        if "__pycache__" in p.parts or "archived" in p.parts or p.name.startswith("test_"):
            continue
        if re.search(r"^def now_iso\(", p.read_text(encoding="utf-8", errors="replace"), re.M):
            out.append(p.name)
    return sorted(out)


def test_now_iso_has_single_source():
    definers = set(_files_defining_now_iso())
    extra = definers - ALLOWED_DEFINERS
    assert not extra, f"now_iso 又被重复定义（应复用 carros_utils）: {sorted(extra)}"


def test_previously_deduped_files_import_shared():
    """本次合并的 10 个文件必须都从 carros_utils 取 now_iso。"""
    targets = [
        "context_engine.py", "executor_ledger.py", "fallback_engine.py",
        "ga_behavioral_validation.py", "intake_gate.py", "phase_contracts.py",
        "plan_builder.py", "pre_action_gate.py", "step_contracts.py",
        "lib/ga_observability_report.py",
    ]
    missing = [
        t for t in targets
        if "from carros_utils import now_iso" not in (SCRIPTS / t).read_text(encoding="utf-8")
    ]
    assert not missing, f"这些文件未复用共享实现: {missing}"


def test_shared_implementation_matches_expected_semantics():
    sys.path.insert(0, str(SCRIPTS))
    import carros_utils
    value = carros_utils.now_iso()
    # ISO8601，秒精度（microsecond=0 已抹）
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", value), value


def test_not_deduped_helpers_are_documented():
    """明确记录哪些「同名」属语义不同、不应合并——防止后人误合。"""
    src = (SCRIPTS / "test_index49_single_source_now_iso.py").read_text(encoding="utf-8")
    assert "today()" in src and "read_json()" in src
