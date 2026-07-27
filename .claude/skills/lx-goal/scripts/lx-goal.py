#!/usr/bin/env python3
"""
lx-goal.py — 目标模式（目标驱动自主执行）
跨平台（macOS/Linux/Windows）

用法: lx-goal <目标描述> [小时]  或  lx-goal 子命令 [参数]

与 lx-ghost 的区别: goal = 目标驱动（具体任务），ghost = 方向驱动（开放探索）
"""

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# 路径定位 — 跨平台 PROJECT_ROOT 计算
# ============================================================
# 脚本所在目录深度决定向上层数：
#   .claude/skills/lx-goal/scripts/lx-goal.py → ../../../../.. = 5 layers up
#   packages/carroros-gov/src/scripts/lx-goal.py → ../../.. = 3 layers up
#   template/skills/lx-goal/scripts/lx-goal.py → ../../../../.. = 5 layers up
# 通过检测目标目录文件名自适应
SCRIPT_DIR = Path(__file__).resolve().parent

# 从脚本目录向上查找，找到包含 AGENTS.md 或 .claude/ 的目录
def _find_project_root(start: Path) -> Path:
    """向上查找 CarrorOS 项目根目录（含非空 AGENTS.md 或 .claude/ 的目录）"""
    d = start
    for _ in range(10):  # 最多向上 10 层
        agents_md = d / "AGENTS.md"
        has_valid_agents = agents_md.exists() and agents_md.stat().st_size > 0
        has_dot_claude = (d / ".claude").is_dir()
        if has_valid_agents or has_dot_claude:
            return d
        parent = d.parent
        if parent == d:
            break
        d = parent
    raise RuntimeError(f"Cannot find project root from {start}")

PROJECT_ROOT = _find_project_root(SCRIPT_DIR)
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TASKS_DIR = PROJECT_ROOT / ".omc" / "tasks"   # 文档系统 — "房间"
TOKENS_DIR = PROJECT_ROOT / ".omc" / "tokens"  # 令牌系统 — "钥匙" (独立于 tasks，compact 恢复入口)
PLANS_DIR = TASKS_DIR                           # 向后兼容: plan/research/executor 写入 tasks
MODE_FILE = STATE_DIR / "tokens" / "lx-goal.json"
AUTONOMOUS_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
get_now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Round7 PKG-6: 生命周期互斥 SSOT(set_mode 唯一写口;导入失败 = fail-closed 禁入 goal)
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "hooks" / "lib"))
try:
    from lifecycle_ssot import set_mode as _lc_set_mode
except Exception:
    _lc_set_mode = None


# ============================================================
# 工具函数
# ============================================================
def _sanitize(text: str) -> str:
    """清除控制字符和代理对"""
    result = []
    for c in text:
        if 0xD800 <= ord(c) <= 0xDFFF:
            continue
        if ord(c) < 0x20 and c not in ("\n", "\t", "\r"):
            continue
        result.append(c)
    return "".join(result)


def _read_mode_file() -> dict:
    """读取 lx-goal.json，不存在时报错退出"""
    path = str(MODE_FILE)
    if not MODE_FILE.exists():
        # 尝试旧格式兼容
        old = STATE_DIR / "unattended-mode.json"
        if old.exists():
            path = str(old)
        else:
            print("❌ 目标模式未开启")
            sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def _write_mode_file(data: dict, path: str):
    """原子写入 mode file"""
    tmp = path + ".tmp." + str(os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.rename(tmp, path)


def is_mode_active() -> bool:
    """goal 模式是否激活：mode file 存在 + active + 未过期 + autonomous 信号存在。

    供 hook/脚本调用（此前仅文档声明，无实现）：
      python3 lx-goal.py is-active  → exit 0=激活 1=未激活
    """
    if not AUTONOMOUS_SIGNAL.exists():
        return False
    path = MODE_FILE if MODE_FILE.exists() else STATE_DIR / "unattended-mode.json"
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    if not data.get("active"):
        return False
    expires = data.get("expires_at")
    if expires:
        try:
            if datetime.now(timezone.utc) >= datetime.fromisoformat(expires):
                return False
        except Exception:
            pass
    return True


def cmd_is_active():
    """is-active 子命令：供 hook/脚本探测 goal 模式（exit 0=激活）。"""
    if is_mode_active():
        print("✅ goal 模式激活中")
        return 0
    print("⭕ goal 模式未激活")
    return 1


def _get_plan_dir(mode_data: dict):
    """从 mode file 中提取计划目录路径"""
    p = mode_data.get("rpe_plan_dir", "")
    return Path(p) if p and Path(p).exists() else None


def cmd_assert_plan_dir():
    """assert-plan-dir 子命令: 输出 plan_dir 路径给 AI 捕获, 验证目录存在。

    goal 模式激活后,AI 必须调用此命令获取唯一计划目录路径,不得自行创建或猜测。

    成功 → 输出 plan_dir 绝对路径到 stdout, exit 0
    失败(未激活/目录不存在) → exit 2
    """
    if not is_mode_active():
        print("❌ 目标模式未激活,无法获取 plan_dir", file=sys.stderr)
        sys.exit(2)
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir or not plan_dir.exists():
        print("❌ plan_dir 不存在或已被删除, 请重新激活目标模式", file=sys.stderr)
        sys.exit(2)
    # 输出 plan_dir 绝对路径（AI 在 Phase 1 捕获此输出作为 I/O 锚定）
    print(str(plan_dir.resolve()))
    sys.exit(0)


def _update_lock_counter(plan_dir: Path, field: str, inc: int = 1):
    """更新物理锁内的计数器字段"""
    from_plan = str(plan_dir)
    slug = Path(from_plan).name
    date_dir = Path(from_plan).parent.name
    lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
    if not lock_file.exists():
        return  # 锁不存在时静默跳过
    with open(lock_file, encoding="utf-8") as f:
        lock = json.load(f)
    lock[field] = lock.get(field, 0) + inc
    lock["updated_at"] = get_now()
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)


# ============================================================
# 子命令
# ============================================================

def cmd_on(goal: str, expiry_hours: int = 6):
    """激活目标模式 — 创建 mode file + 计划目录 + 物理锁"""
    goal = goal or "目标任务未指定"
    expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
    now = get_now()

    # Round7 PKG-6: 生命周期互斥(fail-closed)——ghost 激活中拒绝进入 goal,先于任何落盘
    date_str = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "", goal.replace(" ", "-")[:50])
    # 纯中文/纯符号名(all non-ASCII)→slug被掏空只剩"-",回退到时间戳
    slug = slug.strip("-_") or f"goal-{datetime.now().strftime('%H%M%S')}"
    if _lc_set_mode is None:
        print("❌ lifecycle SSOT 不可用(lifecycle_ssot 导入失败),拒绝进入 goal 模式", file=sys.stderr)
        sys.exit(2)
    try:
        _lc_set_mode("goal", goal_id=slug)
    except ValueError as exc:
        print(f"❌ 生命周期互斥拒绝: {exc}", file=sys.stderr)
        sys.exit(2)

    # 写 mode file
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    mode_data = {
        "active": True,
        "mode": "goal",
        "goal": goal,
        "expires_at": expires,
        "activated_at": now,
        "retry_count": 0,
        "skipped_risks": [],
        "completed_tasks": [],
        "hard_boundary_hits": [],
        "blocked_human": [],
    }
    _write_mode_file(mode_data, str(MODE_FILE))

    # 清理旧格式
    for old in [STATE_DIR / "unattended-mode.json", STATE_DIR / ".unattended-mode"]:
        if old.exists():
            old.unlink()

    # 创建 autonomous.active 信号
    AUTONOMOUS_SIGNAL.touch()

    # ── 委托 carros_base.py 创建任务目录 + 结构化模板 ──
    # 不再自建 research/plan/executor 骨架模板
    carros_base = PROJECT_ROOT / ".claude" / "scripts" / "carros_base.py"
    user_request = f"goal: {goal}"
    plan_dir = None
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, str(carros_base), "init",
             "--task-id", slug,
             "--level", "L2",
             "--user-request", user_request,
             "--task-mode", "goal"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            print(f"❌ carros_base.py init 失败 (exit={result.returncode})", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(2)

        # 解析最后一行 CARROROS_TASK_DIR=xxx
        task_dir_line = ""
        for line in reversed(result.stdout.splitlines()):
            if line.startswith("CARROROS_TASK_DIR="):
                task_dir_line = line
                break
        if not task_dir_line:
            print("❌ 未找到 CARROROS_TASK_DIR= 输出", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            sys.exit(2)
        plan_dir_str = task_dir_line.split("=", 1)[1].strip()
        plan_dir = Path(plan_dir_str)
        if not plan_dir.exists():
            print(f"❌ carros_base 创建的 task dir 不存在: {plan_dir}", file=sys.stderr)
            sys.exit(2)

        # 输出 carros_base 的 stdout（过滤掉 CARROROS_TASK_DIR 行）
        for line in result.stdout.splitlines():
            if not line.startswith("CARROROS_TASK_DIR="):
                print(line)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except FileNotFoundError:
        print(f"❌ carros_base.py 脚本不存在: {carros_base}", file=sys.stderr)
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print("❌ carros_base.py init 超时 (15s)", file=sys.stderr)
        sys.exit(2)

    # ── 创建 goal 模式专用物理锁（覆盖基础 token，补充 goal 字段）──
    lock_file = TOKENS_DIR / date_str / f"{slug}.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_data = {
        "task": slug,
        "slug": slug,
        "goal": goal[:200],
        "mode": "goal",
        "phase": "draft",
        "created_at": now,
        "updated_at": now,
        "expires_at": expires,
        "completed_tasks": 0,
        "skipped_risks": 0,
        "hard_boundary_hits": 0,
        "blocked_human": 0,
        "plan_dir": str(plan_dir),
    }
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2, ensure_ascii=False)

    # 保存 plan_dir 到 mode file
    mode_data["rpe_plan_dir"] = str(plan_dir)
    _write_mode_file(mode_data, str(MODE_FILE))

    print(f"🔒 物理锁: {lock_file}")
    print(f"✅ 目标模式已开启 — 目标: {goal}, {expiry_hours}h 过期")
    print("   autonomous.active 信号已创建: hook 软门降级 warn-only;危险操作门(BLOCK/ASK_USER)保持 fail-closed 拦截")
    print("   被拦项勿等待人类——用 blocked-human/skip-risk 记录后继续其他任务,退出报告自动汇总")
    print('   任务逐项标记: lx-goal.py task-done "完成项描述"')
    print("   完成后输出报告: lx-goal.py report")
    # 无人模式轮询指引（跨会话/compact 恢复硬化）
    print("   ── 无人模式硬化 ──")
    print("   状态探测: lx-goal.py is-active  (exit 0=激活)")
    print("   轮询注册: CronCreate '*/10 * * * *' → lx-goal.py status && lx-goal.py poll")
    print("   会话内:   ScheduleWakeup delaySeconds=1200（长任务心跳）")
    print("   跨会话恢复: 新会话读 .omc/state/tokens/lx-goal.json → plan_dir 续跑")

    # Scope-from-Goal
    auto_scope = PROJECT_ROOT / ".claude" / "scripts" / "auto-scope.sh"
    if auto_scope.exists():
        os.system(f"bash {auto_scope} 2>/dev/null")

    # 决策链注入（skill 自带 references，原 .claude/reference/ 路径不存在为死代码）
    decision_chain = SCRIPT_DIR.parent / "references" / "autonomous-execution.md"
    if decision_chain.exists():
        print(f"\n[{decision_chain.relative_to(PROJECT_ROOT)}]")
        print(decision_chain.read_text(encoding="utf-8"))


def cmd_off():
    """关闭目标模式 — 生成退出报告 + 更新锁 phase=off + 清理运行态"""
    if MODE_FILE.exists():
        mode_data, _ = _read_mode_file()
        plan_dir = _get_plan_dir(mode_data)
        if plan_dir:
            # 更新物理锁 phase → off
            slug = plan_dir.name
            date_dir = plan_dir.parent.name
            lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
            if lock_file.exists():
                with open(lock_file, encoding="utf-8") as f:
                    lock = json.load(f)
                lock["phase"] = "off"
                lock["updated_at"] = get_now()
                with open(lock_file, "w", encoding="utf-8") as f:
                    json.dump(lock, f, indent=2, ensure_ascii=False)
                print(f"🔒 锁 phase 已更新为 off: {lock_file}")

            done = len(mode_data.get("completed_tasks", []))
            skip = len(mode_data.get("skipped_risks", []))
            hard = len(mode_data.get("hard_boundary_hits", []))
            blocked = len(mode_data.get("blocked_human", []))
            checklist = plan_dir / "state" / "checklist.md"
            checklist.parent.mkdir(parents=True, exist_ok=True)
            checklist.write_text(
                f"# Checklist\n\n## 验收清单\n"
                f"- [x] 目标模式已关闭\n"
                f"- [x] 完成任务: {done} 项\n"
                f"- [x] 跳过风险: {skip} 项\n"
                f"- [x] 硬边界拦截: {hard} 项\n"
                f"- [x] 推迟决策: {blocked} 项\n"
                f"\n> 自动生成 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                encoding="utf-8",
            )
            # 更新 token.json phase=completed
            if lock_file.exists():
                lock = json.loads(lock_file.read_text(encoding="utf-8"))
                lock["phase"] = "completed"
                lock["updated_at"] = get_now()
                lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
                # 将已完成 token 移入 archive/tokens/ 作为墓碑，避免 .omc/tokens/ 堆积
                archive_tokens_dir = PROJECT_ROOT / ".omc" / "archive" / "tokens"
                archive_tokens_dir.mkdir(parents=True, exist_ok=True)
                tombstone = archive_tokens_dir / f"{lock_file.parent.name}_{lock_file.name}.tombstone"
                try:
                    shutil.copy2(str(lock_file), str(tombstone))
                    print(f"📦 Token 归档: {tombstone}")
                except Exception as e:
                    print(f"⚠️ Token 归档失败(不阻断 off): {e}", file=sys.stderr)
            print(f"RPE退出报告: {checklist}")

        # 关闭前自动生成完整退出报告（确保需人类介入项必反馈，不被遗漏）
        cmd_report()

        MODE_FILE.unlink(missing_ok=True)

    # 清理旧格式和信号
    for old in [STATE_DIR / "unattended-mode.json", STATE_DIR / ".unattended-mode"]:
        old.unlink(missing_ok=True)
    AUTONOMOUS_SIGNAL.unlink(missing_ok=True)

    # Round7 PKG-6: 生命周期回 idle(off 永不阻断,失败仅警告)
    if _lc_set_mode is not None:
        try:
            _lc_set_mode("idle")
        except Exception as exc:
            print(f"⚠️ lifecycle 回 idle 失败(不阻断 off): {exc}", file=sys.stderr)

    print("✅ 目标模式已关闭，所有 hook 恢复正常阻断")


def cmd_status():
    """查看目标模式状态（含物理锁信息）"""
    if MODE_FILE.exists():
        mode_data, _ = _read_mode_file()
        goal = mode_data.get("goal", "?")
        exp = mode_data.get("expires_at", "无")
        done = len(mode_data.get("completed_tasks", []))
        skip = len(mode_data.get("skipped_risks", []))
        hard = len(mode_data.get("hard_boundary_hits", []))
        blocked = len(mode_data.get("blocked_human", []))
        retry = mode_data.get("retry_count", 0)
        print(f"📋 目标模式 (lx-goal): 🟢 开启中")
        print(f"   目标: {_sanitize(goal)}")
        print(f"   过期: {exp}")
        print(f"   已完成: {done}  跳过风险: {skip}  硬边界: {hard}  推迟决策: {blocked}  重试: {retry}")

        # 显示物理锁信息
        plan_dir = _get_plan_dir(mode_data)
        if plan_dir:
            slug = plan_dir.name
            date_dir = plan_dir.parent.name
            lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
            if lock_file.exists():
                with open(lock_file, encoding="utf-8") as f:
                    lock = json.load(f)
                print(f"   物理锁: 🔒 {lock_file}")
                print(f"   锁 phase: {lock.get('phase', '?')}")
                print(f"   锁统计: completed={lock.get('completed_tasks', 0)} "
                      f"skipped={lock.get('skipped_risks', 0)} "
                      f"hard={lock.get('hard_boundary_hits', 0)} "
                      f"blocked={lock.get('blocked_human', 0)}")
            else:
                print(f"   物理锁: ⚠️ 不存在 ({lock_file})")
    elif (STATE_DIR / "unattended-mode.json").exists():
        print("📋 目标模式 (旧格式 unattended-mode.json): 🟡 兼容中")
        print('   建议执行 lx-goal.py off && lx-goal.py on "目标" 迁移到新格式')
    elif (STATE_DIR / ".unattended-mode").exists():
        print("📋 目标模式 (旧格式 .unattended-mode): 🟡 兼容中")
    else:
        print("📋 目标模式 (lx-goal): ⚪ 已关闭")


def cmd_set(key: str, value_str: str):
    """修改 mode file 中任意字段"""
    mode_data, path = _read_mode_file()
    try:
        value = json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        value = value_str
    mode_data[key] = value
    _write_mode_file(mode_data, path)
    print(f"✅ 目标模式 {key} 已更新为 {value}")


def cmd_phase0_done():
    """Phase 0 → 1 硬过渡: 验证 research.md 有内容 → 设置 phase=executing"""
    mode_data, path = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在，请重新激活目标模式")
        sys.exit(1)

    research_md = plan_dir / "research.md"
    if research_md.exists():
        lines = len(research_md.read_text(encoding="utf-8").split("\n"))
    else:
        lines = 0
    if lines <= 4:
        print(f"❌ Phase 0 未完成: research.md 内容不足 ({lines} 行)")
        print("   AI 必须写入: 子任务列表、验收标准、风险点")
        sys.exit(1)

    # 写 phase0_passed_at 到 mode file
    mode_data["phase0_passed_at"] = get_now()
    _write_mode_file(mode_data, path)

    # 同步更新 token.json phase
    slug = plan_dir.name
    date_dir = plan_dir.parent.name
    lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
    if lock_file.exists():
        lock = json.loads(lock_file.read_text(encoding="utf-8"))
        lock["phase"] = "executing"
        lock["updated_at"] = get_now()
        lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")

    # 追加到 plan.md
    plan_md = plan_dir / "plan.md"
    with open(plan_md, "a", encoding="utf-8") as f:
        f.write(f"\n## Phase 0 完成 — 进入自主执行\n")
        f.write(f"- research.md: {lines} 行\n")
        f.write(f"- 激活时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 状态: executing\n")

    print("✅ Phase 0 完成 → Phase 1 自主执行已解锁")
    print("   Plan Gate 现已放行 Edit/Write/Bash")
    print("   完成后运行: lx-goal.py done")


def cmd_report():
    """生成结构化执行报告"""
    mode_data, path = _read_mode_file()
    report_file = STATE_DIR / "goal-report.md"

    goal = mode_data.get("goal", "?")
    done = len(mode_data.get("completed_tasks", []))
    skip = len(mode_data.get("skipped_risks", []))
    hard = len(mode_data.get("hard_boundary_hits", []))
    blocked = len(mode_data.get("blocked_human", []))
    retry = mode_data.get("retry_count", 0)
    activated = mode_data.get("activated_at", "?")
    expires = mode_data.get("expires_at", "?")

    # build lists
    def _skip_line(r):
        if isinstance(r, dict):
            lvl = r.get("risk_level", "low")
            line = f"- [{lvl}] {r.get('description', '?')}"
            if r.get("reason"):
                line += f" — 理由: {r['reason']}"
            if r.get("impact"):
                line += f" / 影响: {r['impact']}"
            return line
        return f"- {r}"

    skip_list = "\n".join(_skip_line(r) for r in mode_data.get("skipped_risks", [])) or "无"
    hard_list = ""
    for h in mode_data.get("hard_boundary_hits", []):
        hard_list += f"- **操作**: {h.get('description', '?')}\n  **原因**: {h.get('reason', '?')}\n  **需人类执行**: {h.get('human_action', '?')}\n\n"
    hard_list = hard_list or "无"
    blocked_list = ""
    for b in mode_data.get("blocked_human", []):
        blocked_list += f"- **决策**: {b.get('description', '?')}\n  **AI 推荐**: {b.get('ai_recommendation', '?')}\n  **依据**: {b.get('rationale', '?')}\n\n"
    blocked_list = blocked_list or "无"
    task_list = "\n".join(
        f"- [x] {t.get('description', t) if isinstance(t, dict) else t}  ({t.get('timestamp', '') if isinstance(t, dict) else ''})"
        for t in mode_data.get("completed_tasks", [])
    ) or "无"

    # 人为决策汇总表
    decision_rows = []
    idx = 0
    for h in mode_data.get("hard_boundary_hits", []):
        idx += 1
        decision_rows.append(f"| {idx} | 硬边界 | {h.get('description', '?')} | {h.get('human_action', '?')} | {h.get('reason', '?')} |")
    for b in mode_data.get("blocked_human", []):
        idx += 1
        decision_rows.append(f"| {idx} | 推迟决策 | {b.get('description', '?')} | {b.get('ai_recommendation', '?')} | {b.get('rationale', '?')} |")
    # 中高风险跳过项 — 只跳过不执行，必须反馈人类干预（goal 模式核心安全阀）
    for r in mode_data.get("skipped_risks", []):
        if isinstance(r, dict) and r.get("risk_level") in ("medium", "high", "critical"):
            idx += 1
            basis = r.get("reason") or "风险规避"
            if r.get("impact"):
                basis += f" / 影响: {r['impact']}"
            decision_rows.append(
                f"| {idx} | 中高风险跳过[{r['risk_level']}] | {r.get('description', '?')} "
                f"| 建议人类评估后手动执行或明确放弃 | {basis} |"
            )
    if not decision_rows:
        decision_rows.append("| - | - | 无需人类介入的项 | - | - |")

    # GateKeeper 事件摘要（从 gatekeeper_digest 消费）
    _gk_digest = ""
    try:
        _gk_result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "gatekeeper_digest.py"), "--alert"],
            capture_output=True, text=True, timeout=10,
        )
        _gk_digest = _gk_result.stdout.strip()
    except Exception:
        pass
    _gk_section = f"\n## GateKeeper 事件摘要\n\n```\n{_gk_digest}\n```\n\n" if _gk_digest else ""

    report_content = f"""# 目标模式执行报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目标

{_sanitize(goal)}

## 基本信息

- 激活时间: {activated}
- 过期时间: {expires}

## 执行摘要

- 已完成任务数: {done}
- 跳过风险数: {skip}
- 硬边界拦截数: {hard}
- 推迟决策数: {blocked}
- 重试次数: {retry}

## 已完成任务

{task_list}

## 跳过的风险

{skip_list}

## ⚠️ 需人为决策汇总

| # | 类型 | 描述 | AI 推荐 | 依据 |
|---|------|------|---------|------|
{chr(10).join(decision_rows)}

## ⚠️ 需人类介入项（硬边界）

{hard_list}

## 推迟决策项（裁决链 Level 3 — 需人类裁决）

{blocked_list}

{_gk_section}## 验证状态

VERIFIED: 报告生成完毕（{done} 项完成，{skip} 项风险跳过，{hard} 项硬边界拦截，{blocked} 项推迟决策，{retry} 次重试）
"""
    report_file.write_text(report_content, encoding="utf-8")
    print(f"✅ 报告已生成: {report_file}")
    print(report_content)


def cmd_poll():
    """轮询入口 — 由 loop skill / ralph-loop 调用"""
    if not MODE_FILE.exists():
        if (STATE_DIR / "unattended-mode.json").exists():
            poll_path = str(STATE_DIR / "unattended-mode.json")
        else:
            print("❌ 目标模式未激活，停止轮询")
            sys.exit(1)
    else:
        poll_path = str(MODE_FILE)

    with open(poll_path, encoding="utf-8") as f:
        data = json.load(f)

    # 检查过期
    expires_str = data.get("expires_at", "")
    if expires_str:
        try:
            exp = datetime.fromisoformat(expires_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                print(f"⏰ 目标模式已过期（{expires_str}），自动关闭")
                if MODE_FILE.exists():
                    print("   生成过期报告...")
                    cmd_report()
                MODE_FILE.unlink(missing_ok=True)
                AUTONOMOUS_SIGNAL.unlink(missing_ok=True)
                return
        except ValueError:
            pass

    goal = data.get("goal", "?")
    done = len(data.get("completed_tasks", []))
    skip = len(data.get("skipped_risks", []))
    hard = len(data.get("hard_boundary_hits", []))
    retry = data.get("retry_count", 0)
    print(f"🔄 目标轮询 {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"   目标: {_sanitize(goal)}")
    print(f"   已完成: {done}  已跳过风险: {skip}  硬边界: {hard}  重试次数: {retry}")
    print("   请继续执行目标，完成后用 lx-goal.py task-done 或 lx-goal.py report 输出报告")


def cmd_task_done(description: str = "未知任务"):
    """标记一项任务为已完成"""
    mode_data, path = _read_mode_file()
    ts = datetime.now().isoformat()
    mode_data.setdefault("completed_tasks", []).append({"description": description, "timestamp": ts})
    _write_mode_file(mode_data, path)

    # Append to plan.md
    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [x] {description}  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
        # 更新物理锁计数器
        _update_lock_counter(plan_dir, "completed_tasks")

    print(f"✅ 已标记任务完成: {_sanitize(description)}")


def cmd_skip_risk(description: str = "未知风险", risk_level: str = "low", reason: str = "", impact: str = ""):
    """记录跳过的风险。

    risk_level: low/medium/high/critical。
    中高风险（medium+）只跳过不执行，会自动进入退出报告的「需人为决策汇总」表，
    反馈给人类干预 — 这是 goal 模式的核心安全阀。
    """
    risk_level = (risk_level or "low").lower()
    if risk_level not in ("low", "medium", "high", "critical"):
        risk_level = "low"
    mode_data, path = _read_mode_file()
    mode_data.setdefault("skipped_risks", []).append({
        "description": description,
        "risk_level": risk_level,
        "reason": reason,
        "impact": impact,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [skip-risk/{risk_level}] {description} — {reason or '未填理由'}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "skipped_risks")

    marker = "⚠️" if risk_level in ("medium", "high", "critical") else "📝"
    print(f"{marker} 已记录跳过的风险[{risk_level}]: {_sanitize(description)}")
    if risk_level in ("medium", "high", "critical"):
        print("   中高风险项：仅跳过不执行，将出现在退出报告「需人为决策汇总」")


def cmd_hard_boundary_hit(description: str = "未知硬边界", reason: str = "未知原因", human_action: str = "请人工审阅并决定是否执行"):
    """记录硬边界拦截项"""
    mode_data, path = _read_mode_file()
    mode_data.setdefault("hard_boundary_hits", []).append({
        "description": description,
        "reason": reason,
        "human_action": human_action,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [hard-boundary] {description} — {reason}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "hard_boundary_hits")

    print(f"🛑 硬边界拦截已记录: {_sanitize(description)} (原因: {_sanitize(reason)})")


def cmd_blocked_human(description: str = "未知决策", ai_recommendation: str = "AI 推荐方案未提供", rationale: str = "决策依据未提供"):
    """记录推迟到退出报告的人类决策项"""
    mode_data, path = _read_mode_file()
    mode_data.setdefault("blocked_human", []).append({
        "description": description,
        "ai_recommendation": ai_recommendation,
        "rationale": rationale,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [blocked-human] {description} → {ai_recommendation}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "blocked_human")

    print(f"🤔 推迟决策已记录: {_sanitize(description)} → 推荐: {_sanitize(ai_recommendation)}")


def cmd_retry():
    """重试计数 +1"""
    mode_data, path = _read_mode_file()
    mode_data["retry_count"] = mode_data.get("retry_count", 0) + 1
    _write_mode_file(mode_data, path)
    print("📝 重试计数 +1")


def cmd_subagent_log(action: str, agent_name: str = "", subtask: str = "", detail: str = ""):
    """记录 subagent 分配/回收/结果"""
    if not MODE_FILE.exists():
        print("❌ 目标模式未开启")
        sys.exit(1)
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在")
        sys.exit(1)

    # subagent 日志写入 executor.md
    executor_md = plan_dir / "executor.md"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(executor_md, "a", encoding="utf-8") as f:
        if action == "assign":
            f.write(f"\n### {ts} — 分配: {agent_name} → {subtask}\n")
        elif action == "complete":
            f.write(f"\n### {ts} — 完成: {agent_name} → {subtask}\n  - 结果: {detail}\n")
        elif action == "fail":
            f.write(f"\n### {ts} — 失败: {agent_name} → {subtask}\n  - 原因: {detail}\n")
        elif action == "summary":
            f.write(f"\n---\n### SubAgent 执行摘要 @ {ts}\n")
            # 简单的统计
            content = executor_md.read_text(encoding="utf-8")
            f.write(f"- 分配: {content.count('分配:')}\n")
            f.write(f"- 完成: {content.count('完成:')}\n")
            f.write(f"- 失败: {content.count('失败:')}\n")
        else:
            print("用法: lx-goal.py subagent-log assign|complete|fail|summary <agent> <subtask> [detail]")
            sys.exit(1)

    print(f"📝 subagent 日志已更新: {executor_md}")


def cmd_checklist_verify():
    """检测 executor.md 的 Checklist 是否全部 [x]。未达标 → exit=1"""
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        return 0  # 无计划目录时不阻断（向后兼容）
    executor_md = plan_dir / "executor.md"
    if not executor_md.exists():
        return 0

    text = executor_md.read_text(encoding="utf-8")
    import re
    checked = len(re.findall(r'- \[x\]', text, re.IGNORECASE))
    unchecked = len(re.findall(r'- \[ \]', text))
    if unchecked > 0:
        print(f"❌ Checklist 未达标: {checked}/{checked + unchecked} 项通过，还有 {unchecked} 项未完成", file=sys.stderr)
        for line in text.splitlines():
            l = line.strip()
            if l.startswith("- [ ]"):
                print(f"   ⬜ {l[5:].strip()}", file=sys.stderr)
        print(f"\n   完成所有 [ ] 项后重试: lx-goal.py done", file=sys.stderr)
        sys.exit(1)
    return 0


def cmd_done():
    """验收通过后删除物理锁（先检查 checklist）"""
    if not MODE_FILE.exists():
        print("❌ 目标模式未开启")
        sys.exit(1)
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在，无法完成验收")
        sys.exit(1)

    # 门禁：先跑 checklist-verify
    try:
        cmd_checklist_verify()
    except SystemExit as e:
        if e.code != 0:
            print("❌ checklist 未全部通过，不得关闭任务", file=sys.stderr)
            sys.exit(1)

    slug = plan_dir.name
    date_dir = plan_dir.parent.name
    lock_file = TOKENS_DIR / date_dir / f"{slug}.json"

    if lock_file.exists():
        lock_file.unlink()
        print(f"🔓 物理锁已删除: {lock_file}")
        print("✅ 任务验收完成，锁已移除")
    else:
        print("⚠️ 锁文件不存在，可能已被删除")

    # 更新 plan.md
    plan_md = plan_dir / "plan.md"
    with open(plan_md, "a", encoding="utf-8") as f:
        f.write(f"\n---\n✅ **任务验收完成** @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def cmd_update_lock(plan_dir_str: str = "", field: str = "", inc: int = 1):
    """更新物理锁计数器 — 内部子命令"""
    if not plan_dir_str:
        return
    plan_dir = Path(plan_dir_str)
    if not plan_dir.exists():
        return
    _update_lock_counter(plan_dir, field, inc)


# ============================================================
# 主入口
# ============================================================
KNOWN_SUBCOMMANDS = {
    "on": cmd_on,
    "off": cmd_off,
    "status": cmd_status,
    "set": cmd_set,
    "phase0-done": cmd_phase0_done,
    "checklist-verify": cmd_checklist_verify,
    "assert-plan-dir": cmd_assert_plan_dir,
    "report": cmd_report,
    "poll": cmd_poll,
    "is-active": cmd_is_active,
    "task-done": cmd_task_done,
    "skip-risk": cmd_skip_risk,
    "hard-boundary-hit": cmd_hard_boundary_hit,
    "blocked-human": cmd_blocked_human,
    "retry": cmd_retry,
    "subagent-log": cmd_subagent_log,
    "done": cmd_done,
    "_update-lock": cmd_update_lock,
}


def _usage() -> str:
    cmds = "、".join(sorted(k for k in KNOWN_SUBCOMMANDS if k != "_update-lock"))
    return (
        "用法: lx-goal.py <子命令> [参数]  或  lx-goal.py on \"<目标描述>\" [小时]\n"
        f"子命令: {cmds}\n"
        "说明: 无参数=status; 非子命令文本=当作目标激活(等价 on); 以 - 开头的未知参数报错不激活"
    )


def main():
    if len(sys.argv) < 2:
        cmd_status()
        return

    # 参数守卫: help 与未知 dash 参数 → usage,绝不激活(F7 修复: --help 曾被当 goal 建锁)
    if sys.argv[1] in ("-h", "--help", "help"):
        print(_usage())
        sys.exit(0)
    if sys.argv[1].startswith("-") and sys.argv[1] not in KNOWN_SUBCOMMANDS:
        print(f"ERROR: 未知参数 {sys.argv[1]!r}(若以 - 开头请用 on \"目标\" 显式激活)", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        sys.exit(2)

    if sys.argv[1] not in KNOWN_SUBCOMMANDS:
        # 非子命令文本 → 当作目标描述自动激活
        raw = sys.argv[1:]
        goal = " ".join(raw)
        expiry = 6
        if raw and raw[-1].isdigit():
            expiry = int(raw[-1])
            goal = " ".join(raw[:-1])
        cmd_on(goal, expiry)
        return

    cmd_name = sys.argv[1]
    args = sys.argv[2:]

    if cmd_name == "on":
        goal = args[0] if args else "目标任务未指定"
        expiry = int(args[1]) if len(args) > 1 else 6
        cmd_on(goal, expiry)
    elif cmd_name == "set":
        if len(args) < 2:
            print("用法: lx-goal.py set <key> <value>")
            sys.exit(1)
        cmd_set(args[0], args[1])
    elif cmd_name == "subagent-log":
        if not args:
            print("用法: lx-goal.py subagent-log assign|complete|fail|summary <agent> <subtask> [detail]")
            sys.exit(1)
        cmd_subagent_log(*args[:4])
    elif cmd_name == "_update-lock":
        # kwargs parsing: key=value
        kwargs = {}
        for arg in args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kwargs[k] = v
        cmd_update_lock(**kwargs)
    elif cmd_name == "skip-risk":
        # skip-risk "描述" [risk_level] [reason] [impact]
        cmd_skip_risk(*(args[:4]))
    elif cmd_name in ("task-done", "hard-boundary-hit", "blocked-human"):
        handlers = {
            "task-done": cmd_task_done,
            "hard-boundary-hit": cmd_hard_boundary_hit,
            "blocked-human": cmd_blocked_human,
        }
        handlers[cmd_name](*(args[:3]))
    else:
        # off, status, phase0-done, report, poll, retry, done — 无参数
        rc = KNOWN_SUBCOMMANDS[cmd_name]()
        if isinstance(rc, int):
            sys.exit(rc)


if __name__ == "__main__":
    main()
