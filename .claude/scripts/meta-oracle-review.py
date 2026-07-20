#!/usr/bin/env python3
"""
meta-oracle-review.py — 双审判官手动 CLI（AGENTS.md 引用入口）

用法：
  python3 .claude/scripts/meta-oracle-review.py G1 [--task-id ID]  # 执行方案审核（静态，实施前）
  python3 .claude/scripts/meta-oracle-review.py G3 [--task-id ID]  # 校验结果审核（静态+运行时+meta聚合）

G1 = 五步法方案审核门：static_oracle 审 plan.md
G3 = 五步法校验审核门：static + runtime + meta_oracle 聚合（同 cmd_verify L2 自动链路）

退出码：0=ACCEPT 1=ADVISORY 2=REJECT 3=ESCALATE 4=UNAVAILABLE
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]

STATIC_AGENT = SCRIPT_DIR / "static_oracle_agent.py"
RUNTIME_AGENT = SCRIPT_DIR / "runtime_oracle_agent.py"
META = SCRIPT_DIR / "meta_oracle.py"
TOKENS_DIR = ROOT / ".omc" / "tokens"

# Round7 PKG-2: token 读取委托 SSOT(单一真相源,禁第二实现)
# 直插 lib 目录按顶层模块导入——hooks/lib 正规包会遮蔽 lib.* 包路径
sys.path.insert(0, str(SCRIPT_DIR / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
except Exception:  # SSOT 不可用 → 无默认 task-id(调用方已处理 None)
    _ssot_latest_active_token = None


def _latest_task_id() -> str | None:
    """委托 task_ssot:终态(archived/done/completed)与非任务 token 永不复活。

    根因(2026-07-20 幻影 token 事件):旧实现按 mtime 取前 5,archived token
    经水位回写刷新 mtime → 审核归属到已终态的旧任务。
    """
    if _ssot_latest_active_token is None:
        return None
    path = _ssot_latest_active_token(TOKENS_DIR)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data.get("session", {}).get("id") or path.stem


def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return r.returncode, r.stdout, r.stderr
    except Exception as exc:
        return 4, "", str(exc)


def g1_review(task_id: str) -> int:
    """方案审核：static oracle 审 plan（实施前）。"""
    print(f"⚖️  G1 执行方案审核 — static oracle, task={task_id}")
    rc, out, err = _run([sys.executable, str(STATIC_AGENT), "review", "--task-id", task_id])
    print(out.strip())
    if err.strip():
        print(err[:300], file=sys.stderr)
    verdict = _verdict_from_file(task_id, "static")
    print(f"⚖️  G1 裁决: {verdict}")
    return _verdict_rc(verdict)


def g3_review(task_id: str) -> int:
    """校验结果审核：static + runtime + meta 聚合（实施后）。"""
    print(f"⚖️  G3 校验结果审核 — 双审判官, task={task_id}")
    for name, agent in (("static", STATIC_AGENT), ("runtime", RUNTIME_AGENT)):
        rc, out, err = _run([sys.executable, str(agent), "review", "--task-id", task_id])
        if rc not in (0, 1):
            print(f"⚠  {name} oracle exit={rc}: {err[:200]}", file=sys.stderr)
    rc, out, err = _run([sys.executable, str(META), "aggregate", "--task-id", task_id], timeout=30)
    print(out.strip())
    verdict = _verdict_from_file(task_id, "meta")
    print(f"⚖️  G3 裁决: {verdict}")
    return _verdict_rc(verdict)


def _extract_verdict(text: str) -> str:
    try:
        start = text.find("{")
        if start >= 0:
            return json.loads(text[start:]).get("verdict", "UNAVAILABLE")
    except Exception:
        pass
    for v in ("ACCEPT", "REJECT", "ESCALATE", "ADVISORY"):
        if v in text:
            return v
    return "UNAVAILABLE"


def _verdict_from_file(task_id: str, kind: str = "meta") -> str:
    """从裁决落盘文件读取（oracle 脚本 stdout 只输出路径，裁决在 latest.json）。"""
    root = ROOT / ".omc" / "state" / f"{kind}-oracle-verdicts" / task_id / "latest.json"
    try:
        return json.loads(root.read_text(encoding="utf-8")).get("verdict", "UNAVAILABLE")
    except Exception:
        return "UNAVAILABLE"


def _verdict_rc(verdict: str) -> int:
    return {"ACCEPT": 0, "ADVISORY": 1, "REJECT": 2, "ESCALATE": 3}.get(verdict, 4)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if not args or args[0] not in ("G1", "G3"):
        print(__doc__)
        return 64
    gate = args[0]
    task_id = None
    if "--task-id" in args:
        i = args.index("--task-id")
        if i + 1 < len(args):
            task_id = args[i + 1]
    if not task_id:
        task_id = _latest_task_id()
    if not task_id:
        print("❌ 无 task-id 且无活跃 token", file=sys.stderr)
        return 2

    if gate == "G1":
        return g1_review(task_id)
    return g3_review(task_id)


if __name__ == "__main__":
    raise SystemExit(main())
