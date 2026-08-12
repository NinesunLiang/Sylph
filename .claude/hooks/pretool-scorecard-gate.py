#!/usr/bin/env python3
"""
pretool-scorecard-gate.py — PreToolUse:Edit|Write 自评审计门禁（ADR-0013）

门禁规则（组合型: 证据溯源 + Oracle 交叉校验）:
  1. scorecard.md 中每项分数提升,必须在本行或紧邻行附带可验证的 file:line 引用
  2. 不满足证据溯源 → REDIRECT（拦截+指明缺失项+引导补全后重试）
  3. Oracle 交叉校验由后续独立流程触发（本钩专攻证据溯源）

设计原则:
  - 不阻断非 scorecard 的任何操作
  - 只检查提分项，不提分的不审查
  - 审计事件写入 audit 供 Oracle 交叉校验消费
  - exit 0 放行,exit 2 阻断 + 具体缺失列表明晰

Usage:注册在 settings.json PreToolUse:Edit|Write
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── 审计: 阻断时记 flywheel ──
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import flywheel_event  # noqa: E402

# U3 (index18 人类裁决)：agentic-ui 标准化输出；库缺失时回退，不阻断
try:
    from lib.agentic_ui import banner as _au_banner
except Exception:
    def _au_banner(level, title, message):
        print(f"\n⚠️ [{title}] {message}\n", file=sys.stderr)

_HOOK_DIR = Path(__file__).resolve().parent
ROOT = _HOOK_DIR.parents[1]

OMC = ROOT / ".omc"
AUDIT = OMC / "audit"
SCORECARD_PATH = ROOT / ".claude" / "references" / "scorecard.md"

# ── scorecard 提分行匹配 ──
# 格式示例:
#   | C6 | 知识密度 | 10 | 7 | 7→**9** | **6** | **-3** | ...
#   | C6 | 知识密度 | 10 | 4 | **6** | **6** | 0 | ...
# 提分 = column 5（自评/当前） > column 6（外评）
_SCORE_LINE_RE = re.compile(
    r"^\|\s*(C\d+|E\d+|[^\|]+)\s*\|\s*[^\|]+\|\s*\d+\s*\|\s*(\d+)\s*\|\s*"
    r"(?:\d+→)?\*{0,2}(\d+)\*{0,2}\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|"
)

# ── 证据引用模式（同行或紧邻行）──
_EVIDENCE_RE = re.compile(
    r"(?:\[已验证|\[已测试|VERIFIED|source[:：]|来源[:：]|ref[:：]|"
    r"https?://|file:line|commit\s+[a-f0-9]{7,}|[a-zA-Z0-9_./-]+\.[a-z]+:\d+|"
    r"实测|实测数据)"
)


def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _extract_tool(payload: dict) -> str:
    return str(payload.get("tool_name") or payload.get("tool") or payload.get("name") or "")


def _extract_input(payload: dict) -> dict[str, Any]:
    for key in ("tool_input", "input", "arguments", "args"):
        val = payload.get(key)
        if isinstance(val, dict):
            return val
    return payload


def _extract_path(payload: dict) -> str:
    data = _extract_input(payload)
    return str(data.get("file_path") or data.get("filePath") or data.get("path") or data.get("filename") or "")


def _extract_content(payload: dict) -> str:
    """提取将要写入的内容（Edit 的 new_string / Write 的 content）。"""
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content:
        # MultiEdit: 可能有多个 task
        tasks = ti.get("tasks", []) or ti.get("edits", []) or []
        for t in tasks:
            if isinstance(t, dict):
                content += str(t.get("new_string", "") or t.get("content", "") or "")
    return content


def check_path_scope(path, task_dir=None) -> str | None:
    """前置路径预检（v2 升级，index15 降噪·强前置引导）。

    读取活跃任务的 working-set.yaml 的 allowed_paths/denied_paths（schema 声明的
    路径契约），判断写路径是否越界：
      - allowed_paths 内 → None（放行）
      - denied_paths → REDIRECT（引导）
      - 未声明 → REDIRECT（引导补声明）
      - 无活跃任务 / 无 working-set / 非写路径 → None（不阻断）
    返回 REDIRECT 消息或 None。
    """
    try:
        path_str = str(path).replace("\\", "/")
        # 豁免治理运行时区（任务文档/治理文件非产物，不适用产物路径契约）
        if ("/.omc/" in path_str or path_str.startswith(".omc/")
                or "/.claude/" in path_str or path_str.startswith(".claude/")
                or "scorecard.md" in path_str):
            return None
        # 定位活跃任务的 working-set.yaml
        if not task_dir:
            task_dir = _active_task_dir()
        if not task_dir:
            return None
        ws = Path(task_dir) / "working-set.yaml"
        if not ws.exists():
            return None
        import yaml
        data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
        allowed = [str(p).rstrip("/") for p in data.get("allowed_paths", []) or []]
        denied = [str(p).rstrip("/") for p in data.get("denied_paths", []) or []]

        # denied 优先：命中即 REDIRECT（前缀匹配相对/绝对路径）
        for d in denied:
            if _path_matches(path_str, d):
                return (f"REDIRECT 路径越界（denied_paths）: {path_str}\n"
                        f"  schema 声明禁止此路径。请在 working-set.yaml 声明范围内操作。")
        # allowed：命中即放行
        for a in allowed:
            if _path_matches(path_str, a):
                return None
        # 未声明 → REDIRECT 引导补声明
        if allowed:
            return (f"REDIRECT 路径未声明: {path_str}\n"
                    f"  working-set.yaml allowed_paths 未包含此路径。请补声明或移回声明范围。")
        return None
    except Exception:
        return None


def _path_matches(path_str: str, declared: str) -> bool:
    """判断写路径是否命中 working-set 声明的路径（相对声明匹配任意绝对/相对写路径）。

    声明 `src/` 匹配：
      - 绝对路径含 `/src/x.py`
      - 相对路径 `src/x.py`
    声明带尾部斜杠 / 不带均归一。
    """
    d = declared.rstrip("/")
    p = path_str.rstrip("/")
    # 相对声明：匹配路径后缀段（如 src/ 命中任何 /.../src/...）
    if not d.startswith("/"):
        if p == d or p.startswith(d + "/"):
            return True
        if f"/{d}/" in p or p.endswith("/" + d):
            return True
        return False
    # 绝对声明：前缀匹配
    return p == d or p.startswith(d + "/")


def _active_task_dir():
    """定位活跃任务目录（token.task_dir 或 active-resume 指针）。"""
    try:
        state_root = ROOT / ".omc" / "state"
        ptr = state_root / "active-resume.json"
        if ptr.exists():
            data = json.loads(ptr.read_text(encoding="utf-8"))
            td = data.get("task_dir") or data.get("plan_dir")
            if td and Path(td).exists():
                return td
    except Exception:
        pass
    return None


def _append_audit(event: dict) -> None:
    try:
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event.setdefault("timestamp", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _score_text(dimension: str, old: str, new: str, violations: list[str]) -> str:
    """生成缺失证据条目的人类可读描述"""
    lines = [f"  · {dimension}: {old}→{new}"]
    for v in violations[:3]:
        lines.append(f"    — {v}")
    return "\n".join(lines)


def main() -> int:
    payload = _read_stdin()
    tool_name = _extract_tool(payload).lower()
    if tool_name not in ("edit", "write", "multiedit"):
        print(json.dumps({"continue": True}))
        return 0

    path = _extract_path(payload)
    # v2 前置路径预检：写路径须在 working-set.yaml schema 声明范围内
    # 豁免（治理运行时区，非任务产物）：scorecard.md / .claude 治理目录 / .omc 任务目录
    normalized_path = path.replace("\\", "/") if path else ""
    is_governance_file = (
        "scorecard.md" in normalized_path
        or "/.claude/" in normalized_path
        or normalized_path.startswith(".claude/")
        or "/.omc/" in normalized_path
        or normalized_path.startswith(".omc/")
    )
    scope_result = None if is_governance_file else (check_path_scope(path) if path else None)
    if scope_result:
        _au_banner("redirect", "scorecard-gate", scope_result)
        print(json.dumps({"continue": False, "reason": scope_result, "message": scope_result}))
        return 2

    if not path or "scorecard.md" not in path.replace("\\", "/"):
        print(json.dumps({"continue": True}))
        return 0

    content = _extract_content(payload)
    if not content:
        print(json.dumps({"continue": True}))
        return 0

    # 解析提分项
    violations: list[dict] = []
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = _SCORE_LINE_RE.match(line.strip())
        if not m:
            continue
        dimension = m.group(1).strip()  # e.g. "C6"
        baseline = int(m.group(2))     # column 4: 基线/前次
        self_rating = int(m.group(3))  # column 5: 自评（当前分数）
        ext_rating = int(m.group(4))   # column 6: 外评分数
        # 提分判定: 自评 > 基线（分数提升了）或 自评 > 外评（虚高风险）
        if self_rating <= baseline and self_rating <= ext_rating:
            continue  # 未提分且未虚高,不审查

        # 检查本行和紧邻上下行是否有证据引用
        found_evidence = bool(_EVIDENCE_RE.search(line))
        if not found_evidence:
            # 检查上一行（如果是本编辑的一部分）
            if i > 0 and _EVIDENCE_RE.search(lines[i - 1]):
                found_evidence = True
        if not found_evidence:
            # 检查下一行
            if i + 1 < len(lines) and _EVIDENCE_RE.search(lines[i + 1]):
                found_evidence = True

        if not found_evidence:
            violations.append({
                "dimension": dimension,
                "old": baseline,
                "new": self_rating,
                "ext": ext_rating,
                "line": line.strip()[:120],
            })

    if not violations:
        # 无违规 → 放行
        print(json.dumps({"continue": True}))
        return 0

    # 写 audit
    for v in violations:
        _append_audit({
            "event_type": "scorecard_evidence_missing",
            "actor": "hook:pretool-scorecard-gate",
            "decision": "REDIRECT",
            "dimension": v["dimension"],
            "old_score": v["old"],
            "new_score": v["new"],
            "ext_score": v["ext"],
            "line_snippet": v["line"],
        })

    # 组合阻断消息
    detail_parts = []
    for v in violations:
        detail_parts.append(_score_text(v["dimension"], str(v["old"]), str(v["new"]), [v["line"]]))
    detail = "\n".join(detail_parts)

    guidance = (
        f"⛔ scorecard 自评审计门禁: {len(violations)} 项提分缺证据引用(ADR-0013)\n"
        f"\n"
        f"缺失项:\n"
        f"{detail}\n"
        f"\n"
        f"原因: scorecard 提分必须附带可验证 file:line 引用或测试证据（自评 vs 外评 Δ=-0.98 的根因）\n"
        f"\n"
        f"可选方案:\n"
        f"  1. 在每个提分项所在行或紧邻行添加证据引用,如:\n"
        f"     `| C6 | 知识密度 | 10 | 4 | **6** | file:line`\n"
        f"     `测试证据: error-dna.py:123`\n"
        f"  2. 如果提分仅依赖 Oracle 外评,标注 `[内部自检,非行业标准]`\n"
        f"  3. 如果提分未做任何验证,score 不应提高\n"
        f"\n"
        f"预期结果: 补充证据后重试;不补充则回退到外评分数"
    )

    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"scorecard: {len(violations)} 项提分缺证据引用",
            "additionalContext": guidance,
        },
    }, ensure_ascii=False))
    sys.stderr.write(f"pretool-scorecard-gate: DENIED - {len(violations)} 项缺证据\n")
    flywheel_event("pretool_scorecard_gate", "redirected", "P1",
                   f"scorecard:{len(violations)}_violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
