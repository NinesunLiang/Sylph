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
