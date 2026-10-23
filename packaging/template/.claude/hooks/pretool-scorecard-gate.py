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
  - 干预一律 ASK_USER（permissionDecision=ask），不 BLOCK（用户底线 2026-08-17）

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


def _scope_ask_payload(message: str) -> dict:
    """路径越界决策载荷：ASK_USER 而非 BLOCK（用户底线 2026-08-17）。

    返回 permissionDecision=ask，由 CC 弹授权确认，不再硬拦。
    """
    return {
        "continue": False,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": message,
            "additionalContext": f"{message}\n\n是否仍要写入该路径？确认则放行。",
        },
    }


def check_path_scope(path, task_dir=None) -> str | None:
    """前置路径预检（v2 升级，index15 降噪·强前置引导）。

    读取活跃任务的 working-set.yaml 的 allowed_paths/denied_paths（schema 声明的
    路径契约），判断写路径是否越界：
      - allowed_paths 内 → None（放行）
      - denied_paths → REDIRECT（引导）
      - 未声明 → REDIRECT（引导补声明）
      - 无活跃任务 / 无 working-set / 非写路径 → None（不阻断）
      - 仓库外绝对路径 → None（放行；任务产物契约不约束仓库外个人文件，
        2026-08-17 人类裁决）
    返回 REDIRECT 消息或 None。
    """
    try:
        path_str = str(path).replace("\\", "/")
        # F1 (2026-08-30) 修订：仅豁免 .omc/ 与 scorecard.md
        # .claude/ 治理内容文件走 working-set 检查（call 站点已区分基础设施 vs 内容）
        if ("/.omc/" in path_str or path_str.startswith(".omc/")
                or "scorecard.md" in path_str):
            return None
        # 仓库外绝对路径：不适用任务产物路径契约（桌面/daily_tasks 等个人文件放行）
        if path_str.startswith("/") and not path_str.startswith(str(ROOT) + "/"):
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

    index52：`./`、`.`、`*` 视为「**未收窄**」——匹配一切。
    理由：模板默认值原为 `src/ tests/ docs/`（与本仓实际结构不符）→ 一旦门禁上线就误拦
    `.claude/scripts/**` 等合法路径（实测误拦率 33%）。默认改为「不约束范围」，
    只由 `denied_paths` 兜底；需要严格管控的任务**自行收窄**，收窄后立即生效。
    """
    if declared.strip() in (".", "./", "*", "**"):
        return True
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
    """定位活跃任务目录。

    顺序（index52 修正）：
      1. `.omc/state/active-resume.json` 指针（lx-goal resume 写的）
      2. **最新带 `.json.lock` 的 token 的 `task_dir`** —— 原实现只认 1，
         而普通 `carros_base init` 建的任务不写 resume 指针 →
         路径契约门禁在绝大多数任务下**永不上线**（实测 `_active_task_dir()` 恒为 None）。
    """
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

    # 回退：**近期活跃**的 token（有 .json.lock = 任务进行中）
    #
    # 新鲜度判据（index52）：只看 lock 存在会把**陈旧未归档任务**当成活跃任务。
    # 实测仓内有 5 个 Aug-31 的遗留锁，其 working-set 仍是占位值 `src/ tests/ docs/`
    # → 会让门禁拿错数据去**误拦** `.claude/scripts/**`。
    # 故要求 token 的 `session.updated_at` 在 STALE_HOURS 内（tick 会刷新它，长任务不受影响）。
    STALE_HOURS = 24
    try:
        tokens_root = ROOT / ".omc" / "tokens"
        if not tokens_root.is_dir():
            return None
        from datetime import datetime as _dt, timezone as _tz
        now = _dt.now(_tz.utc)
        locks = sorted(tokens_root.glob("*/*.json.lock"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for lock in locks[:10]:
            token_path = lock.with_suffix("")  # 去掉 .lock
            if not token_path.exists():
                continue
            try:
                data = json.loads(token_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ts = str((data.get("session") or {}).get("updated_at")
                     or data.get("updated_at") or "")
            if not ts:
                continue
            try:
                age_h = (now - _dt.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
            except ValueError:
                continue
            if age_h > STALE_HOURS:
                continue  # 陈旧任务：不当活跃任务用
            td = data.get("task_dir") or data.get("plan_dir")
            if td and (ROOT / td).exists():
                return str(ROOT / td) if not Path(td).is_absolute() else td
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
    # F1 (2026-08-30) 修订：不再整目录豁免 .claude/，仅豁免治理基础设施
    # 治理内容文件（SKILLS.md / references/ 等）走 working-set 检查
    normalized_path = path.replace("\\", "/") if path else ""
    _GOVERNANCE_INFRA = (
        "/.omc/" in normalized_path
        or normalized_path.startswith(".omc/")
        or normalized_path.endswith("scorecard.md")
        or normalized_path.endswith(".claude/settings.json")
        or normalized_path.endswith(".claude/settings.local.json")
        or normalized_path.endswith(".claude/harness.yaml")
        or normalized_path.endswith(".claude/index.md")
        or normalized_path.endswith(".claude/kernel.md")
        or "/.claude/hooks/" in normalized_path
        or normalized_path.startswith(".claude/hooks/")
    )
    scope_result = None if _GOVERNANCE_INFRA else (check_path_scope(path) if path else None)
    if scope_result:
        _au_banner("redirect", "scorecard-gate", scope_result)
        # 用户底线（2026-08-17 裁决）：门禁只 ASK_USER 不 BLOCK
        print(json.dumps(_scope_ask_payload(scope_result), ensure_ascii=False))
        return 0

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
            "permissionDecision": "ask",
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
