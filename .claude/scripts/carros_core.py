"""carros_core — CarrorOS 核心纯函数库（design-doc 15 / M0）。

从 carros_base.py 迁出的无全局依赖 helper（时间/路径/解析/文本）。
约定：
  - 本模块不 import carros_base（避免循环依赖）。
  - 平铺于 .claude/scripts/ 根（不走 lib/ 包：lib 为无 __init__ 的命名空间包，
    与 .claude/hooks/lib 同名，会被 test_compact_session_isolation 删 sys.modules['lib']
    后重建指向 hooks/lib，导致 carros_core 找不到 —— 见 research.md 关键发现 1）。
  - carros_base 调用方须用「函数级懒 import」：在被调用函数体内
    `from carros_core import xxx`，不做模块顶层 import
    （顶层 import 会引发跨测试 import 顺序污染，见 5786429 教训）。
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from token_lifecycle import TERMINAL_STATUSES


_ORACLE_SEVERITY: dict[str, int] = {
    "REJECT": 4,
    "ESCALATE": 3,
    "ADVISORY": 2,
    "ACCEPT": 1,
    "UNAVAILABLE": 0,
}


def aggregate_verdicts(v1: str, v2: str, severity: dict[str, int] | None = None) -> str:
    """Return the stricter verdict using an optional caller-owned severity map."""
    levels = _ORACLE_SEVERITY if severity is None else severity
    return v1 if levels.get(v1, 0) >= levels.get(v2, 0) else v2


def _research_md_is_placeholder(research_path) -> bool:
    """M2 门禁：research.md 是否仍为占位模板。

    判定：文件存在但所有 section 内容为空或仅为占位标记（无实质正文）。
    用于普通任务归档前检测，防「占位模板绕过归档」。
    """
    try:
        text = Path(research_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True
    # 提取 section 内容：跳过标题行与 HTML 注释
    lines = [l.strip() for l in text.splitlines()
             if l.strip() and not l.strip().startswith("#")
             and not l.strip().startswith("<!--")
             and not l.strip().endswith("-->")]
    if not lines:
        return True
    # 占位特征：全为短标注/括号/引号框
    substantive = [l for l in lines if len(l) > 4 and not l.startswith(">")]
    return len(substantive) < 2


def _ev_field(block: str, name: str) -> str:
    """提取 EV 块中 `- name: value` 字段值（去空白）。"""
    m = re.search(rf"- {name}:\s*(.*)$", block, re.M)
    return m.group(1).strip() if m else ""


def _build_backcard_guidance(reasons: list[str]) -> list[str]:
    """从 REJECT reasons 生成可执行的修复指引(打回单)。"""
    if not reasons:
        return ["Oracle 未给出具体原因，请人工检查 oracle 输出后修复"]
    return [f"按原因修复: {r}" for r in reasons[:3]]


def _result_template() -> dict:
    """result.json 模板 — subagent 完成工作后写"""
    return {
        "status": "running",
        "summary": "",
        "evidence": [],
        "files_changed": [],
        "failure": None,
        "completed_at": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def _print_path_contract(task_dir):
    """前置引导：打印 working-set.yaml 的路径契约（allowed/denied），
    让 AI 在任务激活时就知道允许写什么、禁止碰什么，主动规划在 schema 内。"""
    try:
        ws = Path(task_dir) / "working-set.yaml"
        if not ws.exists():
            return
        import yaml
        data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
        allowed = data.get("allowed_paths") or []
        denied = data.get("denied_paths") or []
        print("   ── 路径契约（working-set.yaml）──")
        print(f"   允许: {', '.join(str(a) for a in allowed) if allowed else '(无)'}")
        print(f"   禁止: {', '.join(str(d) for d in denied) if denied else '(无)'}")
        print("   提示: 任务若涉及仓库外输入/输出（如桌面路径），research 阶段"
              "把路径加入 allowed_paths（支持绝对路径声明，见 SKILL Phase 0 step 11b）")
        print("   ── 格式契约 ──")
        print("   提示: goal plan.md 模板已内置 PlanGate 格式骨架（Phase/step/字段/verify 前缀），"
              "PLANNING 阶段照骨架填不返工；executor 的 EV 断言须逐字覆盖 verify 规则关键短语")
    except Exception:
        pass  # 契约打印失败不阻断 init


def _is_terminal_token(token) -> bool:
    """M1 终结器判定：token 顶层 status 或 task.status 处于终态。

    terminal 语义：任务不可再推进（completed/archived/failed/expired/cancelled）。
    命中时 _save_token 写盘后同步销毁 sidecar lock，保持物理锁「锁存在=进行中」。
    """
    try:
        top = token.get("status", "")
        task_status = (token.get("task") or {}).get("status", "")
    except AttributeError:
        return False
    return top in TERMINAL_STATUSES or task_status in TERMINAL_STATUSES
