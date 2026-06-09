#!/usr/bin/env python3
"""issue-triage.py — 统一问题分流脚本
Role: 发现问题 → 模式判定 → 分流决策 → 建议行动

用法:
  source issue-triage.py (被 source 时导入函数)
  python3 issue-triage.py "问题描述" "发现来源" "优先级提示" [上下文JSON]

输出: JSON to stdout
副作用: a-mode 写 auto-optimizations.jsonl, b-mode 写 pending-decisions.md

集成点（4 个发现 hook）:
  - error-dna.py: 捕获到新错误模式时
  - completion-gate.py: 证据评分低/RCA 缺失时
  - posttool-bash-audit.py: 检测到危险模式(E4/C1/E3)时
  - posttool-claim-audit.py: 检测到虚假断言时

Hook 不可失败原则：确保任何路径都 exit 0
"""
import sys
import json
import os
import re
import hashlib
import time
import tarfile
import io
from pathlib import Path
from datetime import datetime, timezone


# ─── 路径初始化（从脚本自身位置推导项目根）───
_IT_SCRIPT_DIR = Path(__file__).resolve().parent
_IT_PROJECT_ROOT = (_IT_SCRIPT_DIR / "../..").resolve()
# 验证 project_root 合理性：应含 .claude/ 目录
if not (_IT_PROJECT_ROOT / ".claude").is_dir():
    # 回退: 从当前目录向上搜索含 .claude/ 的目录
    cur = Path.cwd()
    while cur != Path("/"):
        if (cur / ".claude").is_dir():
            _IT_PROJECT_ROOT = cur
            break
        cur = cur.parent

_IT_STATE_DIR = _IT_PROJECT_ROOT / ".omc/state"
_IT_STATE_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════
# 模式判定
# ══════════════════════════════════════════════════════════════════

def is_autonomous_mode():
    """判定当前是否为自主模式（a-mode）"""
    # 1) ghost/goal mode（通过 is_mode_active）
    mode = _is_mode_active()
    if mode in ("ghost", "goal"):
        return True

    # 2) score mode 检测: 最近 2 分钟内有 auto-score-*.json 写入
    if _IT_STATE_DIR.is_dir():
        for f in _IT_STATE_DIR.glob("auto-score-*.json"):
            if f.stat().st_mtime > time.time() - 120:
                return True

    # 3) Oracle review mode 检测: 最近 5 分钟内有 oracle 相关活动
    if _IT_STATE_DIR.is_dir():
        for pattern in ("oracle-verdict*.json", "meta-oracle-verdicts.md", "cross-verify-handoff.md"):
            for f in _IT_STATE_DIR.glob(pattern):
                if f.stat().st_mtime > time.time() - 300:
                    return True

    return False


def _is_mode_active():
    """简易 is_mode_active 实现"""
    mode_file = _IT_STATE_DIR / "mode"
    if mode_file.is_file():
        return mode_file.read_text(encoding="utf-8").strip()
    return "normal"


def get_mode_label():
    """返回当前模式的可读标签"""
    if is_autonomous_mode():
        mode = _is_mode_active()
        if mode in ("ghost", "goal"):
            return mode
        # 检查是否为 score/oracle 子模式
        if _IT_STATE_DIR.is_dir():
            for f in _IT_STATE_DIR.glob("auto-score-*.json"):
                if f.stat().st_mtime > time.time() - 120:
                    return "score"
        return "oracle-review"
    else:
        return "normal"


# ══════════════════════════════════════════════════════════════════
# P0-P3 问题分类
# ══════════════════════════════════════════════════════════════════

def classify_priority(desc, source, hint=""):
    """分类优先级 P0 | P1 | P2 | P3"""
    # 如果调用方已明确提示优先级，优先采纳
    if hint in ("P0", "P1", "P2", "P3"):
        if hint == "P0":
            if re.search(r'(security|安全|漏洞|injection|注入|隐私|privacy|secret|token|password|credential|auth|绕过|bypass|escape)', desc, re.IGNORECASE):
                return "P0"
            return "P1"
        return hint

    # 自动分类
    # P0: 安全问题
    if re.search(r'(security|安全|漏洞|injection|注入|隐私泄露|privacy|secret|token|password|credential|auth.*bypass|绕过.*门禁|escape.*detect)', desc, re.IGNORECASE):
        return "P0"

    # P1: 功能缺陷 / 机制失效
    if re.search(r'(bug|缺陷|失效|broken|not.working|regression|退化|block|阻断|误杀|false.positive|exit.*code|fail|crash|崩溃|机制.*失效|hook.*fail|门禁.*无效)', desc, re.IGNORECASE):
        return "P1"

    # P3: 风格/命名
    if re.search(r'(style|风格|命名|naming|rename|重命名|format.*style|indent|缩进|lint.*warn|whitespace|trailing|空白)', desc, re.IGNORECASE):
        return "P3"

    # P2: 设计改进 / 可优化（默认）
    return "P2"


# ══════════════════════════════════════════════════════════════════
# 分流决策矩阵
# ══════════════════════════════════════════════════════════════════

def dispatch_action(mode_label, priority):
    """决策矩阵"""
    if mode_label == "autonomous" or is_autonomous_mode():
        if priority == "P0":
            return "auto_fix"
        elif priority == "P1":
            return "auto_fix"
        elif priority == "P2":
            return "auto_optimize"
        elif priority == "P3":
            return "skip"
        else:
            return "auto_optimize"
    else:
        if priority == "P0":
            return "block_and_report"
        elif priority == "P1":
            return "record_and_submit"
        elif priority == "P2":
            return "record_and_submit"
        elif priority == "P3":
            return "record_todo"
        else:
            return "record_and_submit"


# ══════════════════════════════════════════════════════════════════
# 核心分流函数
# ══════════════════════════════════════════════════════════════════

def auto_optimizations_archive(opt_file, archive_dir):
    """当 auto-optimizations.jsonl 超过 500KB 时归档"""
    if not opt_file.is_file():
        return
    size = opt_file.stat().st_size
    if size > 512000:  # 500KB
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"auto-optimizations-{timestamp}.tar.gz"
        archive_path = archive_dir / archive_name

        # Create tar.gz
        with tarfile.open(str(archive_path), "w:gz") as tar:
            tar.add(str(opt_file), arcname="auto-optimizations.jsonl")

        # Truncate original
        opt_file.write_text("", encoding="utf-8")
        print(f"[issue-triage] 📦 auto-optimizations.jsonl 已归档 ({size} bytes → {archive_path})", file=sys.stderr)


def triage_issue(desc, source="unknown", hint="", context="{}"):
    """发现问题 → 模式判定 → 分流决策 → 建议行动"""
    if not desc:
        print(json.dumps({"error": "empty description"}, ensure_ascii=False))
        return 1

    mode_label = get_mode_label()
    autonomous = is_autonomous_mode()
    priority = classify_priority(desc, source, hint)

    if autonomous:
        mode_label = mode_label or "autonomous"
        action = dispatch_action("autonomous", priority)
    else:
        mode_label = "normal"
        action = dispatch_action("normal", priority)

    now_ts = int(time.time())
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 生成建议文本 ──
    suggestion = ""
    if action == "auto_fix":
        suggestion = f"[a-mode/{priority}] 自主修复: {desc}（max 3 轮 → Oracle 验证 → 记录）"
    elif action == "auto_optimize":
        suggestion = f"[a-mode/{priority}] 评估后自主优化: {desc}"
    elif action == "skip":
        suggestion = f"[a-mode/{priority}] 范围冻结 — 跳过: {desc}"
    elif action == "block_and_report":
        suggestion = f"[b-mode/{priority}] 立即阻断 + 报告用户: {desc}"
    elif action == "record_and_submit":
        suggestion = f"[b-mode/{priority}] 结构化记录 → 提交用户决策: {desc}"
    elif action == "record_todo":
        suggestion = f"[b-mode/{priority}] 记录 TODO，不主动提示: {desc}"
    else:
        suggestion = f"[分流] {desc}"

    # ── 副作用: a-mode 写入 auto-optimizations.jsonl ──
    if autonomous:
        opt_file = _IT_STATE_DIR / "auto-optimizations.jsonl"
        auto_optimizations_archive(opt_file, _IT_PROJECT_ROOT / ".omc/archive")

        try:
            ctx = json.loads(context) if context else {}
        except Exception:
            ctx = {}

        record = {
            "ts": now_ts,
            "ts_iso": now_iso,
            "mode": mode_label,
            "priority": priority,
            "action": action,
            "source": source,
            "desc": desc,
            "context": ctx
        }
        with opt_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ── 副作用: b-mode 写入 pending-triage.md ──
    if not autonomous and action != "skip":
        pending_file = _IT_STATE_DIR / "pending-triage.md"
        if not pending_file.is_file():
            pending_file.write_text(
                "# 待分流决策清单（issue-triage）\n\n"
                "> 自动生成于 AI 发现但非自主模式下的问题。\n"
                "> SessionStart 时由 inject-project-knowledge.py 注入提醒。\n"
                "> 用户决策后删除对应条目，或整个文件 `rm -f .omc/state/pending-triage.md` 清除全部。\n"
                "> 注意: 此文件与 lx-oma-gov 的 pending-decisions.md 独立，不会冲突。\n\n"
                "<!-- issue-triage: pending decisions marker -->\n\n",
                encoding="utf-8"
            )

        # Dedup
        sig_text = desc[:100]
        dedup_key = hashlib.md5((source + "::" + sig_text).encode()).hexdigest()
        content = pending_file.read_text(encoding="utf-8")

        existing = re.findall(r'### \[([^\]]+)\].*?来源: (\S+).*?dedup_key: ([a-f0-9]+)', content, re.DOTALL)
        should_skip = False
        for ts_str, src, key in existing:
            if key == dedup_key:
                try:
                    entry_ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                    if now_ts - entry_ts < 86400:  # 24h
                        should_skip = True
                        break
                except Exception:
                    pass

        if not should_skip:
            entry_text = (
                f"### [{now_iso}] [{priority}] 来源: {source}\n"
                f"- **问题**: {desc}\n"
                f"- **建议行动**: {suggestion}\n"
                f"- **上下文**: {context}\n"
                f"- **dedup_key**: {dedup_key}\n\n"
            )
            marker = "<!-- issue-triage: pending decisions marker -->"
            if marker in content:
                content = content.replace(marker, marker + "\n\n" + entry_text)
                pending_file.write_text(content, encoding="utf-8")

    # ── 输出 JSON 结果 ──
    result = {
        "mode": mode_label,
        "priority": priority,
        "action": action,
        "suggestion": suggestion,
        "source": source,
        "ts": now_ts
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


# ══════════════════════════════════════════════════════════════════
# Hook 集成辅助函数
# ══════════════════════════════════════════════════════════════════

def triage_for_hook(hook_name, desc, hint="", context="{}"):
    """对 hook 友好的封装: 输出 additionalContext 格式的文本"""
    import io as _io
    old_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    try:
        result = triage_issue(desc, hook_name, hint, context)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    try:
        result_dict = json.loads(output.strip())
        action = result_dict.get("action", "")
        suggestion = result_dict.get("suggestion", "")
        priority = result_dict.get("priority", "")
    except Exception:
        action = ""
        suggestion = ""
        priority = ""

    if action in ("auto_fix", "auto_optimize"):
        print(f"[issue-triage] a-mode/{priority} → {action}: {suggestion}")
    elif action == "block_and_report":
        print(f"[issue-triage] ⚠️ b-mode/{priority} → {action}: {suggestion} | [Hook-Skill桥] 安全问题需用户立即处理 → 检查 pending-decisions.md")
    elif action == "skip":
        print(f"[issue-triage] a-mode/{priority} → skipped (范围冻结)")
    else:
        print(f"[issue-triage] b-mode/{priority} → {action}: {suggestion}")


# ══════════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("=== issue-triage.py self-test ===")
        print()
        print(f"Mode: {get_mode_label()}")
        print(f"Autonomous: {'YES' if is_autonomous_mode() else 'NO'}")
        print()
        print("--- Test 1: P0 security issue ---")
        triage_issue("security vulnerability in permission-gate: command injection via cache", "test", "P0")
        print()
        print("--- Test 2: P1 functional bug ---")
        triage_issue("completion-gate quality scoring returns wrong values for edge cases", "test", "P1")
        print()
        print("--- Test 3: P2 design improvement ---")
        triage_issue("posttool-bash-audit E4 detection could use regex optimization", "test", "P2")
        print()
        print("--- Test 4: P3 style issue ---")
        triage_issue("variable naming inconsistency in harness_config.sh", "test", "P3")
        print()
        print("=== self-test complete ===")
        sys.exit(0)

    if len(sys.argv) >= 2:
        desc = sys.argv[1]
        source = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        hint = sys.argv[3] if len(sys.argv) > 3 else ""
        context = sys.argv[4] if len(sys.argv) > 4 else "{}"
        triage_issue(desc, source, hint, context)
