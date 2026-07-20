#!/usr/bin/env python3
"""lx-stepwise.py — 卡片推进器状态机(front-stepwise 可执行化)

核心原则(origin.md): 一次只抽一张卡;能检查就不问,不能决定才问;当前卡未闭环,绝不进入下一张。

子命令:
  on "<任务描述>"                          建任务(同时只允许一个 active/waiting_user 任务)
  status                                   展示当前卡(单卡视图)+进度+exit_criteria 勾选态
  pass-card --card C0X --confirm 1,2,3 --evidence "..." [--output k=v ...]
                                           机械门禁全过 → 推进到下一张
  fail-card --card C0X --route Q01|X01..X05 --reason "..."
                                           进入异常卡(route 必须在当前卡 failure_routes 中)
  ask --question "..." [--options "A..|B.."]  仅 pending_route 在挂时可用;唯一能置 waiting_user 的入口
  resolve --answer "..." [--goto C06|C07|C08] 用户回答后闭环异常卡,回来源卡(或合法回跳)
  off                                      C14 已 pass 才允许,置 done 并打印交付摘要

机械门禁(违反即 exit 2 拒绝并打印原因):
  - pass-card 的 --card 必须等于 current_card(禁跳卡)
  - exit_criteria 必须全部被 --confirm 覆盖(禁缺项放行)
  - outputs.required 必须全部经 --output 落值(禁空骨架)
  - C08+ 任何卡 pass 前 C07 必须已 passed(变更契约未冻结不动代码)
  - C13 pass 前 C09 必须已 passed(机械验证未过不宣称完成)
  - off 前 C14 必须已 passed(交付记录未闭环不收官)
  - fail-card --route 必须命中当前卡 failure_routes
  - waiting_user 状态下一切 pass/fail 拒绝(先 resolve)

退出码: 0=成功, 1=用法/状态错误, 2=门禁拒绝
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

import yaml

ROOT = Path(__file__).resolve().parents[4]  # .claude/skills/lx-stepwise/scripts/ → 仓库根
CARDS_DIR = ROOT / ".claude" / "references" / "templates" / "stepwise_cards"
STATE_DIR = CARDS_DIR / ".state"

MAIN_ORDER = [f"C{i:02d}" for i in range(15)]
EXCEPTION_IDS = ["Q01"] + [f"X{i:02d}" for i in range(1, 6)]
# resolve --goto 合法回跳白名单(X04 选 A→C08 / 选 C→C06;X01/X03 批准→重过 C07)
GOTO_WHITELIST = {"X01": ["C07"], "X03": ["C07"], "X04": ["C06", "C08"],
                  "Q01": [], "X02": [], "X05": []}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _die(msg: str, code: int = 1) -> NoReturn:
    print(f"❌ {msg}")
    sys.exit(code)


def _gate(msg: str) -> NoReturn:
    _die(f"门禁拒绝: {msg}", 2)


def _load_card(card_id: str) -> dict:
    path = CARDS_DIR / f"{card_id}.yaml"
    if not path.exists():
        _die(f"卡片模板不存在: {card_id}({path})")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    card = data.get("card") if isinstance(data, dict) else None
    if not isinstance(card, dict):
        _die(f"卡片模板缺 card 根键: {card_id}")
    return card


def _state_path(task_id: str) -> Path:
    return STATE_DIR / f"{task_id}.json"


def _all_states() -> list[tuple[str, dict]]:
    out = []
    if STATE_DIR.exists():
        for p in sorted(STATE_DIR.glob("*.json")):
            try:
                out.append((p.stem, json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
    return out


def _active() -> tuple[str, dict]:
    """返回唯一未闭环任务;无则 die。"""
    live = [(tid, s) for tid, s in _all_states()
            if s.get("status") in ("active", "waiting_user")]
    if not live:
        _die("没有进行中的 lx-stepwise 任务(先 on 建任务)")
    if len(live) > 1:
        _die(f"发现 {len(live)} 个未闭环任务({[t for t, _ in live]}),状态损坏,需人工清理 .state/")
    return live[0]


def _save(task_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _state_path(task_id).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_state_path(task_id))


def _slug(text: str) -> str:
    s = re.sub(r"[^\w一-鿿]+", "-", text.strip()).strip("-").lower()
    return (s[:24].strip("-") or "task")


# ── on ──
def cmd_on(args) -> None:
    summary = args.summary.strip()
    if not summary:
        _die("on 需要一句话任务描述")
    live = [tid for tid, s in _all_states() if s.get("status") in ("active", "waiting_user")]
    if live:
        _die(f"已有未闭环任务 {live}(先 off 或 resolve 闭环);同时只允许一个")
    task_id = f"{_slug(summary)}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    state = {
        "task_id": task_id,
        "summary": summary,
        "current_card": "C00",
        "passed": [],
        "status": "active",
        "pending_route": None,
        "return_card": None,
        "outputs": {},
        "allowed_files": [],
        "protected_files": [],
        "user_decisions": [],
        "unresolved_risks": [],
        "validation_results": [],
        "created_at": _now(),
    }
    _save(task_id, state)
    print(f"✅ 任务已建: {task_id}")
    print(f"当前卡: C00 启动卡——按 status 查看单卡视图,逐卡推进")
    _show_card(state, _load_card("C00"))


# ── status ──
def _show_card(state: dict, card: dict) -> None:
    cid = card["id"]
    confirmed = state.get("confirmed", {}).get(cid, [])
    print(f"\n## 当前卡片: {cid} {card.get('title', '')}")
    print(f"### 目标\n{card.get('objective', '')}")
    checks = card.get("auto_checks") or []
    if isinstance(checks, dict):  # C08 pre/post 形态
        for k, v in checks.items():
            print(f"### {k}")
            for c in v or []:
                print(f"  - {c}")
    elif checks:
        print("### 自动检查(能自查就不问人)")
        for c in checks:
            print(f"  - {c}")
    uq = (card.get("user_questions") or {}).get("questions") or []
    if uq:
        print("### 仅在以下情况问用户")
        for q in uq:
            print(f"  - {q}")
    else:
        print("### 需要用户回答\n当前不需要,先自行检查。")
    print("### 退出条件(exit_criteria)")
    for i, c in enumerate(card.get("exit_criteria") or [], 1):
        mark = "x" if i in confirmed else " "
        print(f"  [{mark}] {i}. {c}")
    outs = (card.get("outputs") or {}).get("required") or []
    if outs:
        have = (state.get("outputs") or {}).get(cid, {})
        print("### 必交产出(outputs.required)")
        for o in outs:
            mark = "x" if o in have else " "
            print(f"  [{mark}] {o}")
    fr = card.get("failure_routes") or {}
    if fr:
        print("### 异常路由")
        for k, v in fr.items():
            print(f"  - {k} → {v}")
    print(f"### 下一张\n{card.get('next_card') or '(异常卡/终点——resolve 回来源卡或 pass 后 off)'}")
    print(f"\n进度: passed={state.get('passed', [])} status={state.get('status')}"
          + (f" pending_route={state.get('pending_route')}" if state.get("pending_route") else ""))


def cmd_status(_args) -> None:
    _, state = _active()
    _show_card(state, _load_card(state["current_card"]))


# ── pass-card ──
def cmd_pass(args) -> None:
    _, state = _active()
    cid = state["current_card"]
    if state.get("status") == "waiting_user":
        _gate("waiting_user 状态——先 resolve 用户答复,再推进")
    if args.card != cid:
        _gate(f"禁跳卡: 当前卡是 {cid},不能 pass {args.card}")
    card = _load_card(cid)
    # 门禁 1: exit_criteria 全覆盖
    criteria = card.get("exit_criteria") or []
    confirmed = sorted(set(args.confirm or []))
    missing = [i for i in range(1, len(criteria) + 1) if i not in confirmed]
    if missing:
        _gate(f"exit_criteria 未全确认,缺第 {missing} 项:\n"
              + "\n".join(f"  {i}. {criteria[i-1]}" for i in missing))
    # 门禁 2: outputs.required 全落值
    required = (card.get("outputs") or {}).get("required") or []
    outs = dict((state.get("outputs") or {}).get(cid, {}))
    for kv in args.output or []:
        if "=" not in kv:
            _die(f"--output 须为 k=v 形态: {kv!r}")
        k, v = kv.split("=", 1)
        outs[k.strip()] = v.strip()
    miss_out = [k for k in required if k not in outs]
    if miss_out:
        _gate(f"outputs.required 未全落值,缺: {miss_out}(用 --output k=v 逐项交)")
    # 门禁 3: C07 硬门禁
    passed = state.get("passed", [])
    if cid in MAIN_ORDER and MAIN_ORDER.index(cid) > MAIN_ORDER.index("C07") \
            and "C07" not in passed:
        _gate("C07 变更契约未 passed——冻结前不动代码")
    # 门禁 4: C09 硬门禁(C13)
    if cid == "C13" and "C09" not in passed:
        _gate("C09 机械验证未 passed——不宣称完成")
    if not (args.evidence or "").strip():
        _gate("--evidence 不能为空(本卡证据: 文件/符号/命令结果/用户决定)")
    # 通过: 落账
    state.setdefault("outputs", {})[cid] = outs
    state.setdefault("confirmed", {})[cid] = confirmed
    state.setdefault("evidence", {})[cid] = args.evidence.strip()
    if cid == "C07":  # 契约冻结 → 写状态,供 C08 pre-check
        state["allowed_files"] = [v for k, v in outs.items() if "allowed_files" in k]
        state["protected_files"] = [v for k, v in outs.items() if "protected_files" in k]
    if cid == "C09" and "validation_table" in outs:
        state["validation_results"].append({"card": cid, "table": outs["validation_table"], "at": _now()})
    if cid not in passed:
        passed.append(cid)
    state["passed"] = passed
    nxt = card.get("next_card")
    if nxt:
        state["current_card"] = nxt
    task_id = state["task_id"]
    _save(task_id, state)
    print(f"✅ {cid} {card.get('title', '')} PASSED(evidence 已落账)")
    if nxt:
        print(f"→ 下一张: {nxt}")
        _show_card(state, _load_card(nxt))
    else:
        print("本卡无 next_card——若交付记录已闭环,执行 off 收官")


# ── fail-card ──
def cmd_fail(args) -> None:
    _, state = _active()
    if state.get("status") == "waiting_user":
        _gate("waiting_user 状态——先 resolve 当前问询")
    cid = state["current_card"]
    if args.card != cid:
        _gate(f"禁跳卡: 当前卡是 {cid},不能 fail {args.card}")
    card = _load_card(cid)
    routes = card.get("failure_routes") or {}
    if args.route not in routes.values():
        _gate(f"route {args.route} 不在 {cid} 的 failure_routes {sorted(routes.values())} 中")
    if args.route not in EXCEPTION_IDS:
        _gate(f"未知异常卡: {args.route}")
    state["pending_route"] = args.route
    state["return_card"] = cid
    state["current_card"] = args.route
    state.setdefault("unresolved_risks", []).append(
        {"card": cid, "route": args.route, "reason": (args.reason or "").strip(), "at": _now()})
    _save(state["task_id"], state)
    print(f"⚠️ {cid} 触发异常 → {args.route}({_load_card(args.route).get('title', '')})")
    print("下一步: ask 向用户提该异常卡的决策问题(或 resolve 直接给答复闭环)")
    _show_card(state, _load_card(args.route))


# ── ask ──
def cmd_ask(args) -> None:
    _, state = _active()
    if not state.get("pending_route"):
        _gate("无挂起异常卡——ask 仅用于 fail-card 之后(唯一能置 waiting_user 的入口)")
    if state.get("status") == "waiting_user":
        _gate("已处于 waiting_user——先 resolve 当前问题")
    q = (args.question or "").strip()
    if not q:
        _die("ask 需要 --question")
    state["status"] = "waiting_user"
    state["pending_question"] = {"card": state["pending_route"], "question": q,
                                 "options": (args.options or "").strip(), "at": _now()}
    _save(state["task_id"], state)
    print(f"🔒 已进入 waiting_user({state['pending_route']})")
    print(f"问题: {q}")
    if args.options:
        print(f"选项: {args.options}")
    print("等用户答复后: resolve --answer \"...\"")


# ── resolve ──
def cmd_resolve(args) -> None:
    _, state = _active()
    if state.get("status") != "waiting_user":
        _gate("非 waiting_user 状态——resolve 仅用于闭环用户问询")
    route = state.get("pending_route")
    if not isinstance(route, str) or not route:
        _die("状态损坏: waiting_user 但无 pending_route")
    answer = (args.answer or "").strip()
    if not answer:
        _die("resolve 需要 --answer")
    pq = state.get("pending_question") or {}
    state.setdefault("user_decisions", []).append({
        "card": route, "question": pq.get("question", ""), "answer": answer, "at": _now()})
    state["pending_question"] = None
    state["pending_route"] = None
    state["status"] = "active"
    target = state.get("return_card") or "C00"
    if args.goto:
        allowed = GOTO_WHITELIST.get(route, [])
        if args.goto not in allowed:
            _gate(f"{route} 不允许回跳 {args.goto}(白名单: {allowed or '无——只能回来源卡'})")
        target = args.goto
        # 回跳: 目标卡及之后的主卡全部退回未过(重做)
        ti = MAIN_ORDER.index(target)
        state["passed"] = [c for c in state.get("passed", [])
                           if c in MAIN_ORDER and MAIN_ORDER.index(c) < ti]
    state["current_card"] = target
    state["return_card"] = None
    _save(state["task_id"], state)
    print(f"✅ {route} 闭环: 决定已落账 → 回到 {target}")
    _show_card(state, _load_card(target))


# ── off ──
def cmd_off(_args) -> None:
    task_id, state = _active()
    if state.get("status") == "waiting_user":
        _gate("waiting_user 状态——先 resolve 再收官")
    if "C14" not in state.get("passed", []):
        _gate("C14 交付闭环卡未 passed——交付记录未写完不收官")
    state["status"] = "done"
    state["done_at"] = _now()
    _save(task_id, state)
    d = (state.get("outputs") or {}).get("C14", {})
    print(f"✅ 任务 {task_id} 干净闭环(status=done)")
    print(f"final_status: {d.get('delivery.final_status', '?')}")
    for k in ("delivery.changed_files", "delivery.user_acceptance", "delivery.known_limitations"):
        if k in d:
            print(f"  {k}: {d[k]}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="lx-stepwise", description="卡片推进器状态机")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("on", help="建任务(一句话描述)")
    p.add_argument("summary")
    p.set_defaults(fn=cmd_on)

    p = sub.add_parser("status", help="当前卡单卡视图")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("pass-card", help="过当前卡(机械门禁)")
    p.add_argument("--card", required=True)
    p.add_argument("--confirm", type=int, nargs="+", default=[],
                   help="exit_criteria 序号(必须全覆盖)")
    p.add_argument("--output", action="append", default=[],
                   help="outputs.required 落值,k=v 形态,可多次")
    p.add_argument("--evidence", required=True, help="本卡证据")
    p.set_defaults(fn=cmd_pass)

    p = sub.add_parser("fail-card", help="当前卡触发异常路由")
    p.add_argument("--card", required=True)
    p.add_argument("--route", required=True, choices=EXCEPTION_IDS)
    p.add_argument("--reason", default="")
    p.set_defaults(fn=cmd_fail)

    p = sub.add_parser("ask", help="向用户提异常卡决策问题(唯一 waiting_user 入口)")
    p.add_argument("--question", required=True)
    p.add_argument("--options", default="")
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("resolve", help="闭环用户问询,回来源卡或合法回跳")
    p.add_argument("--answer", required=True)
    p.add_argument("--goto", default=None, choices=MAIN_ORDER)
    p.set_defaults(fn=cmd_resolve)

    p = sub.add_parser("off", help="收官(C14 已 pass 才允许)")
    p.set_defaults(fn=cmd_off)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
