#!/usr/bin/env python3
"""
oracle-meta-handoff.py — Oracle → Meta-Oracle 交接文档生成器
Python 移植版，完全等价 oracle-meta-handoff.sh v1.0

Role: Oracle ACCEPT 后生成交接文档，中断执行，让人参与选择

非无人模式流程:
  1. Oracle ACCEPT → 生成交接文档 .omc/state/oracle-handoff-*.md
  2. 中断执行，展示交接文档给用户
  3. 用户选择: 本终端继续 / 其他终端不同模型 / 跳过

无人模式(goal/ghost): 不中断，自动记录后继续

用法: python3 oracle-meta-handoff.py <generate|show> [args...]
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Try harness_lib
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
    from harness_lib import flywheel_event, is_mode_active
except ImportError:
    def flywheel_event(*args, **kwargs):
        pass

    def is_mode_active(state_dir=None):
        """Simple check fallback."""
        if state_dir is None:
            return "normal"
        sd = Path(state_dir)
        for tok in [sd / "tokens" / "lx-ghost.json"]:
            if tok.exists():
                return "ghost"
        for tok in [sd / "tokens" / "lx-goal.json"]:
            if tok.exists():
                return "goal"
        return "normal"


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
PLANS_DIR = PROJECT_ROOT / ".omc" / "plans"

MODE = is_mode_active(str(STATE_DIR))
TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now().strftime("%Y%m%d-%H%M%S")
PYTHON_BIN = os.environ.get("PYTHON_BIN", "python3")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── 生成交接文档 ───
def generate_handoff(oracle_verdict: str, review_target: str, review_type: str):
    # Generate topic dir name
    topic = re.sub(r'[\/:.*"<>|]', '', review_type)[:40]
    if not topic:
        topic = "oracle-meta-handoff"

    topic_dir = PLANS_DIR / TODAY / topic
    topic_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect version
    version = 1
    for f in topic_dir.glob("v*.md"):
        m = re.search(r'v(\d+)\.md$', f.name)
        if m:
            v = int(m.group(1))
            if v >= version:
                version = v + 1

    handoff_file = topic_dir / f"v{version}.md"

    # Read latest Oracle verdict details
    oracle_detail = ""
    oracle_file = STATE_DIR / "oracle-verdicts.md"
    if oracle_file.exists():
        lines = oracle_file.read_text(encoding="utf-8").splitlines()
        oracle_detail = "\n".join(lines[-20:])

    # Read target summary
    target_summary = ""
    target_path = Path(review_target)
    if target_path.exists():
        lines = target_path.read_text(encoding="utf-8").splitlines()
        target_summary = "\n".join(lines[:30])

    content = f"""# Oracle → Meta-Oracle 交接文档

> 生成时间: {now_utc()}
> 审核类型: {review_type}
> 审核目标: {review_target}

---

## 一、Oracle 裁决结果

```
{oracle_verdict}
```

### Oracle 审核详情

{oracle_detail}

---

## 二、审核目标摘要

```
{target_summary}
```

---

## 三、Meta-Oracle 审查要求

Meta-Oracle 是 Carror OS 的最高审查权威，独立于 Oracle。
使用完全不同的审查方法（运行时验证 > 静态检查，对抗性审查 > 合规检查）。

**审查重点**:
1. 运行时验证 > 静态检查 — 检查 smoke test 实际通过率、error-dna 真实频率
2. 设计级盲区检查 — fail-open/fail-closed 设计缺陷、门禁降级、正则覆盖率
3. 对抗性审查 — 刻意假设 Oracle 错误，尝试证伪

---

## 四、请选择执行路径

> 请在下方选择 Meta-Oracle 审查的执行方式：

### [选项 A] 本终端继续
在当前终端使用当前模型执行 Meta-Oracle 审查。
命令:
```bash
python3 {SCRIPT_DIR}/meta-oracle-agent-spawn.py prepare
# 然后 AI 使用 Agent(subagent_type="critic") 拉起独立审查
```

### [选项 B] 其他终端 — 不同模型
将本交接文档复制到其他终端，用不同模型执行 Meta-Oracle 审查。
在其他终端中:
```bash
# 1. 读取本交接文档了解上下文
cat {handoff_file}

# 2. 运行 Meta-Oracle 审查脚本
python3 {SCRIPT_DIR}/meta-oracle-agent-spawn.py prepare

# 3. 审查完成后记录裁决
python3 {SCRIPT_DIR}/meta-oracle-agent-spawn.py record --verdict "<审查结果>"
```

### [选项 C] 跳过 Meta-Oracle
信任 Oracle 裁决，跳过 Meta-Oracle 二审。直接继续执行。

---

> 选择后请告知 AI，AI 将根据您的选择执行对应操作。
"""

    handoff_file.write_text(content, encoding="utf-8")
    print(str(handoff_file))


# ─── 展示交接文档 ───
def show_handoff(handoff_path: str):
    handoff_file = Path(handoff_path)
    if not handoff_file.exists():
        print(f"[oracle-meta-handoff] ERROR: handoff file not found: {handoff_file}", file=sys.stderr)
        sys.exit(1)

    # Autonomous mode: skip human interruption
    if MODE != "normal":
        print("[oracle-meta-handoff] 自主模式: 跳过人为交接，记录到退出报告", file=sys.stderr)
        flywheel_event("oracle_meta_handoff", "autonomous_skip", "P2", f"mode={MODE}")
        print('{"continue": true}')
        sys.exit(0)

    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🔄 Oracle → Meta-Oracle 交接                              ║")
    print("║  Oracle 已给出 ACCEPT 裁决，需要 Meta-Oracle 独立二审     ║")
    print("║                                                           ║")
    print(f"║  交接文档已生成: {handoff_file}  ║".format(handoff_file=handoff_file))
    print("╚══════════════════════════════════════════════════════════════╝")
    print("")
    print("请选择 Meta-Oracle 审查的执行路径:")
    print("")
    print("  [A] 本终端继续 — 当前模型执行 Meta-Oracle 审查")
    print("  [B] 其他终端 — 用不同模型执行 Meta-Oracle 审查")
    print("  [C] 跳过 — 信任 Oracle 裁决，跳过 Meta-Oracle")
    print("")
    print("输入 A/B/C 后告知 AI:")
    print("")

    flywheel_event("oracle_meta_handoff", "handoff_created", "P2", f"file={handoff_file}")


def print_usage():
    print("Usage: oracle-meta-handoff.py <generate|show>", file=sys.stderr)
    print("  generate <verdict> <target> <type>   生成交接文档", file=sys.stderr)
    print("  show <handoff_file>                  展示交接文档并中断", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "generate":
        args = sys.argv[2:]
        if len(args) < 3:
            print("generate requires: <verdict> <target> <type>", file=sys.stderr)
            sys.exit(1)
        generate_handoff(args[0], args[1], args[2])
    elif cmd == "show":
        args = sys.argv[2:]
        if len(args) < 1:
            print("show requires: <handoff_file>", file=sys.stderr)
            sys.exit(1)
        show_handoff(args[0])
    elif cmd in ("help", "--help", "-h"):
        print_usage()
        sys.exit(0)
    else:
        print(f"[oracle-meta-handoff] Usage: {sys.argv[0]} <generate|show>", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
