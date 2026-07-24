#!/usr/bin/env python3
"""test-lx-stepwise.py — lx-stepwise 卡片推进器状态机测试(第 11 套件)

正向:
  P1 on 建任务 → current_card=C00 status=active
  P2 全链 happy path: C00..C14 逐卡 pass(confirm/output 从模板动态生成) → off → status=done
  P3 status 单卡视图含 目标/exit_criteria/下一张
对抗(机械门禁,全部期望 exit 2):
  A1 跳卡: current=C00 时 pass C01
  A2 exit_criteria 缺项: 只 confirm 第 1 项
  A3 outputs.required 缺项: 少交一个 --output
  A4 C07 门: 伪造 current=C08 且 C07 未过 → pass C08 拒绝
  A5 C09 门: 伪造 current=C13 且 C09 未过 → pass C13 拒绝
  A6 C14 门: C14 未过 → off 拒绝
  A7 fail-card route 不在当前卡 failure_routes
  A8 无 pending_route 时 ask
  A9 waiting_user 中 pass/fail 拒绝;resolve 回来源卡
  A10 resolve --goto 白名单: X04→C08 放行且回退 passed;Q01→C08 拒绝
  A11 已有 active 任务时第二个 on 拒绝

副作用声明: 整目录备份/恢复 .claude/references/templates/stepwise_cards/.state/
  (测试在其中建删任务状态文件,结束原样还原,不吞生产状态)

Usage: python3 scripts/test-lx-stepwise.py
Exit: 0 = PASS, 1 = FAIL
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / ".claude" / "skills" / "lx-stepwise" / "scripts" / "lx-stepwise.py"
CARDS_DIR = ROOT / ".claude" / "references" / "templates" / "stepwise_cards"
STATE_DIR = CARDS_DIR / ".state"
MAIN = [f"C{i:02d}" for i in range(15)]
PASS = 0
FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def run(*argv):
    return subprocess.run(
        [sys.executable, str(CLI), *argv],
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )


def load_card(cid):
    data = yaml.safe_load((CARDS_DIR / f"{cid}.yaml").read_text(encoding="utf-8"))
    return data["card"]


def pass_args(cid):
    """从模板动态生成全量 --confirm 与 --output(禁硬编码卡面)。"""
    card = load_card(cid)
    n = len(card.get("exit_criteria") or [])
    outs = (card.get("outputs") or {}).get("required") or []
    argv = ["pass-card", "--card", cid, "--confirm", *[str(i) for i in range(1, n + 1)],
            "--evidence", f"test evidence for {cid}"]
    for o in outs:
        argv += ["--output", f"{o}=test-{cid}-{o}"]
    return argv


def active_state():
    for p in STATE_DIR.glob("*.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        if s.get("status") in ("active", "waiting_user"):
            return p.stem, s
    return None, None


def clear_states():
    """清场(单任务前提): 删除 .state 下所有状态文件。"""
    for p in STATE_DIR.glob("*.json"):
        p.unlink()


def craft_state(**over):
    """直接伪造状态文件(测 C07/C09/C14 门的越级场景)。"""
    base = {
        "task_id": "crafted-test", "summary": "crafted", "current_card": "C00",
        "passed": [], "status": "active", "pending_route": None, "return_card": None,
        "outputs": {}, "allowed_files": [], "protected_files": [],
        "user_decisions": [], "unresolved_risks": [], "validation_results": [],
    }
    base.update(over)
    (STATE_DIR / "crafted-test.json").write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    return base


# ── 备份 .state 整目录(finally 原样恢复) ──
STATE_BAK = ROOT / ".claude" / "references" / "templates" / "stepwise_cards" / ".state.bak.test"
if STATE_BAK.exists():
    shutil.rmtree(STATE_BAK)
if STATE_DIR.exists():
    shutil.copytree(STATE_DIR, STATE_BAK)
else:
    STATE_BAK.mkdir(parents=True)

try:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for p in STATE_DIR.glob("*.json"):  # 清场,保证单任务前提
        p.unlink()

    print("=" * 64)
    print("P1: on 建任务")
    print("=" * 64)
    r = run("on", "测试任务: 给登录页加加载态")
    tid, st = active_state()
    ok("P1 on 成功 + C00/active", r.returncode == 0 and st and st["current_card"] == "C00"
       and st["status"] == "active", f"rc={r.returncode} out={r.stdout[:150]}")

    print("=" * 64)
    print("P3: status 单卡视图")
    print("=" * 64)
    r = run("status")
    ok("P3 视图含 目标/exit_criteria/下一张",
       r.returncode == 0 and "当前卡片: C00" in r.stdout
       and "exit_criteria" in r.stdout and "下一张" in r.stdout, r.stdout[:200])

    print("=" * 64)
    print("A1/A2/A3/A7/A8/A11: 门禁对抗(当前 C00)")
    print("=" * 64)
    r = run("pass-card", "--card", "C01", "--confirm", "1", "--evidence", "x")
    ok("A1 跳卡 pass C01 → exit 2", r.returncode == 2 and "禁跳卡" in r.stdout, r.stdout[:150])
    r = run("pass-card", "--card", "C00", "--confirm", "1", "--evidence", "x",
            "--output", "task.summary=s", "--output", "task.repository=r",
            "--output", "task.target_area=t", "--output", "task.user_constraints=u",
            "--output", "task.initial_risks=i")
    ok("A2 exit_criteria 缺项 → exit 2", r.returncode == 2 and "exit_criteria 未全确认" in r.stdout,
       r.stdout[:150])
    r = run("pass-card", "--card", "C00", "--confirm", "1", "2", "3", "--evidence", "x",
            "--output", "task.summary=s")
    ok("A3 outputs 缺项 → exit 2", r.returncode == 2 and "outputs.required 未全落值" in r.stdout,
       r.stdout[:150])
    r = run("fail-card", "--card", "C00", "--route", "X04")
    ok("A7 route 不在 failure_routes → exit 2", r.returncode == 2, f"rc={r.returncode} {r.stdout[:150]}")
    r = run("ask", "--question", "问什么?")
    ok("A8 无 pending_route 时 ask → exit 2", r.returncode == 2, f"rc={r.returncode} {r.stdout[:150]}")
    r = run("on", "第二个任务")
    ok("A11 已有 active 时 on → exit 1 拒绝", r.returncode == 1 and "已有未闭环任务" in r.stdout,
       r.stdout[:150])

    print("=" * 64)
    print("A9: waiting_user 锁 + resolve 回来源卡")
    print("=" * 64)
    r = run("fail-card", "--card", "C00", "--route", "Q01", "--reason", "需求歧义")
    ok("A9 fail→Q01 成功", r.returncode == 0 and "Q01" in r.stdout, r.stdout[:150])
    r = run("ask", "--question", "保存后关闭弹窗?", "--options", "A 关闭|B 保持")
    ok("A9 ask → waiting_user", r.returncode == 0 and "waiting_user" in r.stdout, r.stdout[:150])
    r = run("pass-card", "--card", "Q01", "--confirm", "1", "--evidence", "x")
    ok("A9 waiting 中 pass → exit 2", r.returncode == 2 and "waiting_user" in r.stdout,
       r.stdout[:150])
    r = run("fail-card", "--card", "Q01", "--route", "X01")
    ok("A9 waiting 中 fail → exit 2", r.returncode == 2, f"rc={r.returncode}")
    r = run("resolve", "--answer", "A 关闭")
    tid, st = active_state()
    ok("A9 resolve → 回来源卡 C00 + 决定落账",
       r.returncode == 0 and st is not None and st["current_card"] == "C00"
       and st["status"] == "active" and len(st["user_decisions"]) == 1,
       f"{r.stdout[:150]} state={st and st['current_card']}")

    print("=" * 64)
    print("A10: resolve --goto 白名单")
    print("=" * 64)
    r = run("fail-card", "--card", "C00", "--route", "Q01", "--reason", "再问一次")
    r = run("ask", "--question", "q")
    r = run("resolve", "--answer", "a", "--goto", "C08")
    ok("A10 Q01 --goto C08 → exit 2(白名单为空)", r.returncode == 2 and "白名单" in r.stdout,
       r.stdout[:150])
    r = run("resolve", "--answer", "a")  # 闭环 Q01,回到 C00
    clear_states()  # P1 任务清场——crafted 场景要求全场仅一个 live 任务
    craft_state(current_card="C09", passed=["C00", "C01", "C02", "C03", "C04", "C05",
                                            "C06", "C07", "C08"], status="active",
                pending_route="X04", return_card="C09")
    # 先手工 ask 状态置 waiting(craft 只到 pending_route)
    st = json.loads((STATE_DIR / "crafted-test.json").read_text(encoding="utf-8"))
    st["status"] = "waiting_user"
    st["pending_question"] = {"card": "X04", "question": "修复路线?", "options": "", "at": "t"}
    (STATE_DIR / "crafted-test.json").write_text(json.dumps(st, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")
    r = run("resolve", "--answer", "A 契约内修复", "--goto", "C08")
    st = json.loads((STATE_DIR / "crafted-test.json").read_text(encoding="utf-8"))
    ok("A10 X04 --goto C08 → 回跳且 C08 起退回重做",
       r.returncode == 0 and st["current_card"] == "C08"
       and st["passed"] == ["C00", "C01", "C02", "C03", "C04", "C05", "C06", "C07"],
       f"rc={r.returncode} {r.stdout[:150]} passed={st['passed']}")

    print("=" * 64)
    print("A4/A5/A6: 三道硬门禁(伪造越级状态)")
    print("=" * 64)
    clear_states()
    craft_state(current_card="C08", passed=["C00", "C01", "C02", "C03", "C04", "C05", "C06"])
    r = run(*pass_args("C08"))
    ok("A4 C07 未过 → pass C08 exit 2", r.returncode == 2 and "C07" in r.stdout, r.stdout[:150])
    craft_state(current_card="C13", passed=[c for c in MAIN if c != "C09" and c != "C13"])
    r = run(*pass_args("C13"))
    ok("A5 C09 未过 → pass C13 exit 2", r.returncode == 2 and "C09" in r.stdout, r.stdout[:150])
    craft_state(current_card="C14", passed=[c for c in MAIN if c != "C14"])
    r = run("off")
    ok("A6 C14 未过 → off exit 2", r.returncode == 2 and "C14" in r.stdout, r.stdout[:150])

    print("=" * 64)
    print("P2: 全链 happy path C00..C14 → off")
    print("=" * 64)
    for p in STATE_DIR.glob("*.json"):
        p.unlink()
    r = run("on", "测试任务: 全链过卡")
    chain_ok = r.returncode == 0
    for cid in MAIN:
        r = run(*pass_args(cid))
        if r.returncode != 0:
            chain_ok = False
            print(f"    断在 {cid}: {r.stdout[:200]}")
            break
    r = run("off")
    final = json.loads(next(STATE_DIR.glob("*.json")).read_text(encoding="utf-8"))
    ok("P2 15 卡全过 + off → done",
       chain_ok and r.returncode == 0 and final["status"] == "done",
       f"off rc={r.returncode} {r.stdout[:200]}")
    ok("P2 C07 冻结落账 allowed/protected_files",
       bool(final.get("allowed_files")) and bool(final.get("protected_files")),
       f"allowed={final.get('allowed_files')}")

    print("=" * 64)
    print("S1/S2: 抗 compact — SessionStart 注入恢复入口")
    print("=" * 64)
    SESSION_START = ROOT / ".claude" / "hooks" / "session-start.py"

    def run_session_start():
        return subprocess.run(
            [sys.executable, str(SESSION_START)],
            input=json.dumps({"session_id": "tt-sw", "source": "compact",
                              "transcript_path": "/tmp/tt-sw-nonexistent.jsonl"}),
            capture_output=True, text=True, cwd=str(ROOT), timeout=30,
        )

    clear_states()
    r = run_session_start()
    ok("S1 无 live 任务 → 不注入 Active Stepwise",
       r.returncode == 0 and "Active Stepwise" not in r.stdout, r.stdout[:200])
    clear_states()
    r = run("on", "测试任务: 抗 compact 恢复")
    r = run_session_start()
    ok("S2 compact 后注入 [Active Stepwise] 恢复入口(含卡号+status 对齐提示)",
       r.returncode == 0 and "[Active Stepwise]" in r.stdout
       and "card=C00" in r.stdout and "lx-stepwise status" in r.stdout,
       f"rc={r.returncode} {r.stdout[:300]}")

finally:
    if STATE_DIR.exists():
        shutil.rmtree(STATE_DIR)
    STATE_BAK.rename(STATE_DIR)

print("=" * 64)
print(f"结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
if FAIL:
    print("❌ LX-STEPWISE 存在失败项")
    sys.exit(1)
print("✅ ALL PASS — 卡片推进器机械门禁全成立")
