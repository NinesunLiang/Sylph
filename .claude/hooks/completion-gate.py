#!/usr/bin/env python3
"""completion-gate.py — PostToolUse:TaskUpdate — 强制 TaskUpdate 前提供结构化证据文件
Role: 强制 TaskUpdate 前提供结构化证据文件

等效移植自 completion-gate.sh (438行):
- 提取 status 字段，非 completed → 放行
- 自主/无人值守模式降级（检查 + warn，不阻断）
- 证据文件存在性/新鲜度检查
- 原子消费（mv 防并发）
- 证据内容验证：长度 ≥ min_evidence_chars
- 要求证据含 VERIFIED 关键字
- R27 结构化验证标记（file:line / test markers）
- E3 软完成语检测
- E2 双源证据要求（≥2/3 验证类别）
- 证据质量评分（4维度，阈值可配）
- RCA/根因分析: 强制根因分析要求，防止症状混搭
- E5 根因分析门禁
- B5 模板化 RCA 检测
- C3 L3 复杂度检测 + Oracle 终审记录检查
- Pipeline step 自动推进
- A→B→A 交叉验证触发
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, hc_emit_hook_json, flywheel_event, output_continue

# ─── 路径常量 ───

PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"

# ─── C8 可维护性: 模块级常量（单点维护，消除散落魔数） ───
_DEFAULT_SOFT_COMPLETION_WORDS = (
    "应该没问题了|基本完成|大部分完成|差不多了.*完成|理论上可行|"
    "看起来正常|之前验证过|should be fine|basically done|mostly complete|"
    "seems to work|probably works|theoretically|should work|looks good"
)
_DEFAULT_QUALITY_THRESHOLD = "75"
_DEFAULT_MIN_EVIDENCE_CHARS = "20"
_DEFAULT_FRESHNESS_SEC = "300"
_DEFAULT_REQUIRED_KEYWORD = "VERIFIED"
_DEFAULT_EVIDENCE_DIR = ".omc/state"
_FALLBACK_LEVELS_MAP = {2: "降级模式", 3: "紧急模式"}

# ─── Fallback level 机制 ───
# Level 1（默认）：完整路径，不变
# Level 2（降级）：finish-length-detected 标记存在时，走简化 3 步链
# Level 3（紧急）：连续 2 次 Level 2 降级后，退化为 warning-only 模式

def _get_fallback_level():
    """从 harness.yaml 读取 completion_gate.fallback_level，不存在返回 1。"""
    raw = hc_get("completion_gate.fallback_level", "1")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 1

def _check_finish_length_detected():
    """检查 finish-length-detected 标记文件是否存在。"""
    return (STATE_DIR / "finish-length-detected").exists()

def _manage_finish_length_streak():
    """管理连续降级计数。返回当前 streak 值。"""
    streak_file = STATE_DIR / "finish-length-streak"
    streak = 0
    try:
        if streak_file.exists():
            raw = streak_file.read_text(encoding="utf-8", errors="replace").strip()
            if raw:
                streak = int(raw)
    except (OSError, ValueError):
        streak = 0
    streak += 1
    if streak >= 2:
        # streak ≥ 2 自动清理（触发 Level 3 后用一次即清理）
        try:
            streak_file.unlink()
        except OSError:
            pass
        # 同时清理标记文件
        try:
            (STATE_DIR / "finish-length-detected").unlink()
        except OSError:
            pass
        return streak
    try:
        streak_file.parent.mkdir(parents=True, exist_ok=True)
        streak_file.write_text(str(streak), encoding="utf-8")
    except OSError:
        pass
    return streak


# ─── 自主模式检测 ───

def _is_autonomous():
    """检测是否处于自主/无人值守模式。"""
    tokens_dir = STATE_DIR / "tokens"
    checks = [
        tokens_dir / "autonomous.active",
        STATE_DIR / "ghost-mode.active",
        tokens_dir / "lx-ghost.json",
        tokens_dir / "lx-goal.json",
    ]
    for f in checks:
        if f.exists():
            return True
    return False


# ─── 软阻断（自主模式降级） ───

def _auto_soft_block(message, autonomous):
    """软阻断：自主模式写日志 + continue，否则 exit 2。"""
    # issue-triage 集成
    triage_script = _HOOKS_DIR.parent / "scripts" / "issue-triage.sh"
    triage_msg = ""
    if triage_script.exists():
        try:
            result = subprocess.run(
                ["bash", str(triage_script), "triage_for_hook", "completion-gate", message, "", "{}"],
                capture_output=True, text=True, timeout=10
            )
            triage_msg = result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass

    if autonomous:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_line = f"[{ts}] [自主模式] {message}"
        log_path = STATE_DIR / "completion-gate-autonomous.log"
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(str(log_path), "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
                if triage_msg:
                    f.write(f"[{ts}] {triage_msg}\n")
        except OSError:
            pass
        print(json.dumps({"continue": True}))
        sys.exit(0)
    else:
        if triage_msg:
            print(triage_msg, file=sys.stderr, flush=True)
        flywheel_event("completion_gate", "blocked", "P2")
        sys.exit(2)


# ─── 证据质量评分 ───

def _evidence_quality_score(content):
    """评估证据质量评分（5维度），返回 (score, details_list, stats_dict)。

    C4 增强: 结构化证据块校验——executor evidence block 必须含 action/file/command/output/status 六字段。
    stats_dict 供 BLOCKED 输出路径复用，避免重复计算（C8 可维护性）。
    """
    fl_count = len(re.findall(r"[\w./-]+\.[a-z]+:\d+", content))
    fl_score = min(fl_count / 3.0, 1.0) * 35

    cmd_patterns = ["exit.code", r"\bPASS\b", r"\bFAIL\b", "✅", "❌", "test", "build", r"\d+ passed", r"\d+ failed", "VERIFIED"]
    cmd_hits = sum(1 for p in cmd_patterns if re.search(p, content, re.IGNORECASE))
    cmd_score = min(cmd_hits / 4.0, 1.0) * 25

    multi_patterns = [r"\d+%", r"\d+ms", r"\d+ req", "coverage", "all tests", "zero errors", "edge.case", "regression"]
    multi_hits = sum(1 for p in multi_patterns if re.search(p, content, re.IGNORECASE))
    multi_score = min(multi_hits / 3.0, 1.0) * 20

    quant_patterns = [r"\d+/\d+", r"\d+\.\d+", r"PASS.*FAIL", r"N/A"]
    quant_hits = sum(1 for p in quant_patterns if re.search(p, content))
    quant_score = min(quant_hits / 2.0, 1.0) * 10

    # C4: 结构化证据块字段校验——6字段全必填（防AI省略字段后的伪验证）
    struct_fields = 0
    struct_bits = {}  # C8: 记录每字段命中/未命中供输出
    _STRUCT_FIELD_PATTERNS = [
        (r"\*\*证据块|证据块：|evidence.block|##+\s*EV-|###\s*EV-", "证据块标题"),
        (r"(?m)^\s*[-*+]\s*`?action`?\s*:", "action"),
        (r"(?m)^\s*[-*+]\s*`?file`?\s*:", "file"),
        (r"(?m)^\s*[-*+]\s*`?command`?\s*:", "command"),
        (r"(?m)^\s*[-*+]\s*`?output`?\s*:", "output"),
        (r"(?m)^\s*[-*+]\s*`?status`?\s*:", "status"),
    ]
    for pat, name in _STRUCT_FIELD_PATTERNS:
        hit = bool(re.search(pat, content))
        struct_bits[name] = hit
        if hit:
            struct_fields += 1
    struct_score = 0
    if struct_fields >= 6:
        struct_score = 10  # 六字段全齐（C4 硬化：必须6/6）
    elif struct_fields >= 4:
        struct_score = 5   # 缺关键字段

    # C4: VERIFIED 模板格式检测——证据应为 `VERIFIED: <action> → <result>` 格式
    # 防AI写"看起来没问题" 等软完成语假冒验证
    _VERIFIED_TEMPLATE_RE = re.compile(
        r"VERIFIED:\s*`?[^`\n]+`?\s*(?:→|->|=>)\s*`?[^`\n]+`?",
        re.IGNORECASE,
    )
    if not _VERIFIED_TEMPLATE_RE.search(content):
        struct_score = max(struct_score - 3, 0)  # 格式不合格扣3分

    total = fl_score + cmd_score + multi_score + quant_score + struct_score
    stats = {
        "fl_count": fl_count, "fl_score": fl_score,
        "cmd_hits": cmd_hits, "cmd_score": cmd_score,
        "multi_hits": multi_hits, "multi_score": multi_score,
        "quant_hits": quant_hits, "quant_score": quant_score,
        "struct_fields": struct_fields, "struct_score": struct_score,
        "struct_bits": struct_bits,
    }
    details = [
        f"file:line refs ({fl_count}处): {fl_score:.0f}/35",
        f"test/cmd markers ({cmd_hits}处): {cmd_score:.0f}/25",
        f"multi-aspect ({multi_hits}处): {multi_score:.0f}/20",
        f"quantification ({quant_hits}处): {quant_score:.0f}/10",
        f"structured evidence ({struct_fields}/6字段): {struct_score:.0f}/10",
    ]
    return int(round(total)), details, stats


# ─── 双源证据检测 ───

def _dual_source_count(content):
    """返回证据来源类别数（0-3）。"""
    sources = 0
    # A: file:line
    if re.search(r"[\w./-]+\.[a-zA-Z]+:\d+", content):
        sources += 1
    # B: test/compile markers
    if re.search(r"(exit\.code|PASS|FAIL|✅|❌|build|test|\d+ passed|\d+ failed)", content, re.IGNORECASE):
        sources += 1
    # C: quantification
    if re.search(r"(\d+/\d+|\d+\.\d+%|edge\.case|coverage|regression|\d+ms)", content, re.IGNORECASE):
        sources += 1
    return sources


# ─── 主函数 ───

def main():
    if not hc_enabled("completion_gate"):
        output_continue()
        return

    # 从 stdin 读取输入
    input_str = sys.stdin.read()

    # 提取 status 字段
    status = ""
    try:
        data = json.loads(input_str)
        status = data.get("tool_input", {}).get("status", "")
    except (json.JSONDecodeError, Exception):
        pass

    # 非 completed 状态 → 放行
    if status != "completed":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 自主/无人值守模式检测
    autonomous = _is_autonomous()

    # ── Fallback Level 检测 ──
    fallback_level = _get_fallback_level()
    finish_length_detected = _check_finish_length_detected()

    # 如果标记文件存在，动态切换到降级路径
    if finish_length_detected and fallback_level < 2:
        fallback_level = 2

    # 获取配置（默认值引用模块级常量，C8: 单点维护）
    evidence_dir_str = hc_get("completion_gate.evidence_dir", _DEFAULT_EVIDENCE_DIR)
    evidence_dir = PROJECT_ROOT / evidence_dir_str

    # ── 优先检查 Harness 捕获的证据 ──
    # harness 从真实命令执行中捕获的输出，比 AI 手写证据更可信
    # 如果存在最近的 harness 证据，直接跳过 AI 证据文件检查
    _HARNESS_EVIDENCE_DIR = PROJECT_ROOT / ".omc" / "state" / ".harness-evidence"
    _harness_ok = False
    try:
        if _HARNESS_EVIDENCE_DIR.exists():
            now_ts = time.time()
            # 查找最近 10 分钟内的 harness 证据
            for f in sorted(_HARNESS_EVIDENCE_DIR.iterdir(), reverse=True):
                if f.suffix == ".json" and now_ts - f.stat().st_mtime < 600:
                    _harness_ok = True
                    break
    except Exception:
        pass
    freshness_sec = int(hc_get("completion_gate.evidence_freshness_sec", _DEFAULT_FRESHNESS_SEC))
    min_chars = int(hc_get("completion_gate.min_evidence_chars", _DEFAULT_MIN_EVIDENCE_CHARS))
    req_keyword = hc_get("completion_gate.required_keyword", _DEFAULT_REQUIRED_KEYWORD)
    quality_threshold = int(hc_get("completion_gate.quality_threshold", _DEFAULT_QUALITY_THRESHOLD))
    soft_words_raw = hc_get("completion_gate.soft_completion_words", _DEFAULT_SOFT_COMPLETION_WORDS)

    # ── Fallback Level 2: 简化 3 步链 ──
    if fallback_level >= 2:
        level_label = _FALLBACK_LEVELS_MAP.get(fallback_level, "降级模式")

        # Level 3（紧急）：warning-only 模式，记录但不阻断
        if fallback_level >= 3:
            print(f"[Completion Gate] 紧急模式（fallback_level=3）: finish-length 连续降级，跳过阻断。",
                  file=sys.stderr, flush=True)
            flywheel_event("completion_gate", "fallback_level_3_skip", "P2")
            print(json.dumps({"continue": True}))
            sys.exit(0)

        # Level 2（降级）：简化 3 步链
        flywheel_event("completion_gate", "fallback_level_2", "P2")

        # 管理连续降级计数
        streak = _manage_finish_length_streak()
        if streak >= 2:
            print(f"[Completion Gate] 连续 {streak} 次降级，升级至 Level 3（紧急模式: warning-only）",
                  file=sys.stderr, flush=True)
            print(json.dumps({"continue": True}))
            sys.exit(0)

        print(f"[Completion Gate] {level_label}: 执行简化验证链", file=sys.stderr, flush=True)

        # 证据文件路径（当前分钟）
        evidence_file = evidence_dir / f".completion-evidence-{datetime.now().strftime('%Y%m%d-%H%M')}"

        # 简化步骤 1: 证据存在性检查
        if not evidence_file.exists() and not _harness_ok:
            print(f"[Completion Gate] 证据文件缺失 (simplified check)", file=sys.stderr, flush=True)
            _auto_soft_block("无证据文件（降级模式）", autonomous)

        # 简化步骤 2: 原子消费 + 读取 + 基础长度校验
        consumed = evidence_file.parent / f"{evidence_file.name}.consumed.{os.getpid()}"
        try:
            os.rename(str(evidence_file), str(consumed))
        except OSError:
            print("⛔ COMPLETION BLOCKED: 证据已被其他进程消费", file=sys.stderr, flush=True)
            _auto_soft_block("证据已被其他进程消费（降级模式）", autonomous)

        try:
            content = consumed.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        content_len = len(content)

        # 基础长度校验
        if content_len < min_chars:
            print(f"⛔ COMPLETION BLOCKED: 证据内容过短（{content_len} 字符 < {min_chars} 字符最低要求）。", file=sys.stderr, flush=True)
            try:
                consumed.unlink()
            except OSError:
                pass
            _auto_soft_block(f"证据内容过短（{content_len}字符，降级模式）", autonomous)

        # 简化步骤 3: VERIFIED 关键词检查
        if req_keyword not in content:
            print(f"⛔ COMPLETION BLOCKED: 证据文件中未找到 '{req_keyword}' 关键字。", file=sys.stderr, flush=True)
            try:
                consumed.unlink()
            except OSError:
                pass
            _auto_soft_block("证据文件缺少关键字（降级模式）", autonomous)

        # 降级模式验证通过
        print(f"[Completion Gate] {level_label} 验证通过", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        # 清理 finish-length 标记
        try:
            (STATE_DIR / "finish-length-detected").unlink()
        except OSError:
            pass
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Fallback Level 1（默认）：完整路径不变 ──
    # 证据文件路径（当前分钟）
    evidence_file = evidence_dir / f".completion-evidence-{datetime.now().strftime('%Y%m%d-%H%M')}"

    if not evidence_file.exists() and not _harness_ok:
        # 从 feature-registry.yaml 读取预期证据级别
        evidence_level_label = "L3"
        registry_path = _HOOKS_DIR.parent / "feature-registry.yaml"
        if registry_path.exists():
            try:
                content = registry_path.read_text(encoding="utf-8", errors="replace")
                # 查找 completion-gate 的 evidence_level
                in_completion_gate = False
                for line in content.splitlines():
                    if "name: completion-gate" in line:
                        in_completion_gate = True
                    elif in_completion_gate and "evidence_level:" in line:
                        m = re.search(r"evidence_level:\s*(.+)", line)
                        if m:
                            evidence_level_label = m.group(1).strip()
                            break
                    elif in_completion_gate and line.strip().startswith("- ") and "name:" not in line:
                        # End of this entry's properties
                        pass
                    elif in_completion_gate and "name:" in line and "completion-gate" not in line:
                        break
            except OSError:
                pass

        print(f"[Completion Gate] evidence missing: expected {evidence_level_label} at {evidence_file}", file=sys.stderr, flush=True)
        _auto_soft_block("无证据文件", autonomous)

    # 证据文件存在，检查新鲜度
    try:
        age = time.time() - evidence_file.stat().st_mtime
        fresh = age < freshness_sec
    except OSError:
        fresh = False

    if not fresh:
        print(f"[Completion Gate] evidence expired: age={age:.0f}s > {freshness_sec}s", file=sys.stderr, flush=True)
        _auto_soft_block("证据文件已过期", autonomous)

    # 原子消费：mv 到 consumed 文件
    consumed = evidence_file.parent / f"{evidence_file.name}.consumed.{os.getpid()}"
    try:
        os.rename(str(evidence_file), str(consumed))
    except OSError:
        print("⛔ COMPLETION BLOCKED: 证据已被其他进程消费", file=sys.stderr, flush=True)
        _auto_soft_block("证据已被其他进程消费", autonomous)

    # 读取证据内容
    try:
        content = consumed.read_text(encoding="utf-8", errors="replace")
    except OSError:
        content = ""
    content_len = len(content)

    # 证据内容长度检查
    if content_len < min_chars:
        print(f"⛔ COMPLETION BLOCKED: 证据内容过短（{content_len} 字符 < {min_chars} 字符最低要求）。", file=sys.stderr, flush=True)
        print(f"证据必须包含至少 {min_chars} 字符的实际验证描述，不能只有 '{req_keyword}' 等占位符。", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block(f"证据内容过短（{content_len}字符）", autonomous)

    # VERIFIED 关键字检查
    if req_keyword not in content:
        print(f"⛔ COMPLETION BLOCKED: 证据文件中未找到 '{req_keyword}' 关键字。", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block("证据文件缺少关键字", autonomous)

    # R27: 结构化验证标记
    if not re.search(r"(\[已验证:|\[已测试:|✅|exit 0|PASS|is_danger.*false|status.*completed)", content):
        print("⛔ COMPLETION BLOCKED: 证据格式过于模糊，缺少结构化验证标记。", file=sys.stderr, flush=True)
        print("证据必须包含以下结构化格式之一：", file=sys.stderr, flush=True)
        print("  - [已验证: file:line] 格式的代码引用", file=sys.stderr, flush=True)
        print("  - [已测试: 命令+输出] 格式的运行验证", file=sys.stderr, flush=True)
        print("  - 明确的通过标记（exit 0, PASS, ✅ 等）", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block("证据格式模糊", autonomous)

    # E3: 软完成语检测
    try:
        if re.search(soft_words_raw, content, re.IGNORECASE):
            print("⛔ COMPLETION BLOCKED: 证据含软完成语（违禁词），请用具体验证结果替换。", file=sys.stderr, flush=True)
            print("违禁词: 应该没问题了、基本完成、大部分完成、差不多了、理论上可行、看起来正常", file=sys.stderr, flush=True)
            print("正确格式示例: 'VERIFIED: go build ./... → exit 0, all tests PASS'", file=sys.stderr, flush=True)
            try:
                consumed.unlink()
            except OSError:
                pass
            _auto_soft_block("证据含软完成语", autonomous)
    except re.error:
        pass

    # E2: 双源证据要求
    dual_count = _dual_source_count(content)
    if dual_count < 2:
        print(f"⛔ COMPLETION BLOCKED: 证据仅来自 {dual_count}/3 个验证类别，需要 ≥2 类独立证据。", file=sys.stderr, flush=True)
        print("证据类别:", file=sys.stderr, flush=True)
        print("  (A) file:line 代码引用", file=sys.stderr, flush=True)
        print("  (B) 测试/编译通过标记", file=sys.stderr, flush=True)
        print("  (C) 量化/边界数据", file=sys.stderr, flush=True)
        print("示例: 'VERIFIED: go build → exit 0, handler.go:42 配置加载 ✅'", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block(f"证据仅来自 {dual_count}/3 类别", autonomous)

    # E3 增强: 证据质量评分
    quality_score, quality_details, quality_stats = _evidence_quality_score(content)
    thresh = quality_threshold

    if quality_score < thresh:
        print(f"⛔ COMPLETION BLOCKED: 证据质量评分 {quality_score}% < {thresh}% 最低要求。", file=sys.stderr, flush=True)
        print("质量分解与改进方向:", file=sys.stderr, flush=True)

        # 统计各维度（复用 _evidence_quality_score 的返回值，避免重复计算）
        fl = quality_stats["fl_count"]
        cmd = quality_stats["cmd_hits"]
        multi = quality_stats["multi_hits"]
        quant = quality_stats["quant_hits"]
        struct = quality_stats["struct_fields"]
        fl_s = quality_stats["fl_score"]
        cmd_s = quality_stats["cmd_score"]
        multi_s = quality_stats["multi_score"]
        quant_s = quality_stats["quant_score"]
        struct_s = quality_stats["struct_score"]
        total = fl_s + cmd_s + multi_s + quant_s + struct_s
        print(f"  总分分解: {total:.0f}/100 = file:line({fl_s:.0f}/35) + test/cmd({cmd_s:.0f}/25) + multi({multi_s:.0f}/20) + quant({quant_s:.0f}/10) + struct({struct_s:.0f}/10)", file=sys.stderr, flush=True)
        print(f"  具体统计: file:line={fl}处(需≥3)  test/cmd={cmd}处(需≥2)  multi={multi}处(需≥2)  quant={quant}处(需≥1)  struct={struct}字段(需≥4)", file=sys.stderr, flush=True)

        # Find weakest area
        candidates = [
            (40 - fl_s, "添加更多 file:line 引用", fl < 3),
            (30 - cmd_s, "补充命令输出/PASS/FAIL 等测试标记", cmd < 2),
            (20 - multi_s, "增加多方面验证（覆盖率/百分比/边界值）", multi < 2),
            (10 - quant_s, "添加量化数据（计数/比率/具体数值）", quant < 1),
        ]
        weakest = max(candidates, key=lambda x: x[0])
        if weakest[2]:
            print(f"  >>> 优先改进: {weakest[1]}", file=sys.stderr, flush=True)
        print("  通用改进: 引用 file:line 源码 + 使用 VERIFIED: 格式 + 附原始命令输出", file=sys.stderr, flush=True)

        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block(f"证据质量评分过低（{quality_score}%）", autonomous)

    # E5 根因分析门禁 + 错误去重（防AI伪装RCA + 防同一症状重复出现）
    # ── 改进：不只检查字段存在性，还检查内容质量 ──
    rca_content_lines = content
    rca_structured = 0
    rca_has_repro = 0
    rca_repro_evidence = 0
    rca_templated = 0
    rca_has_reference = 0
    rca_has_quant = 0        # E5增强: RCA含量化数据
    rca_has_file_line = 0    # E5增强: RCA含具体代码位置
    rca_depth_score = 0      # E5增强: 综合深度评分

    # 检测: 结构化字段存在性
    if re.search(r"root\.cause[:=].{5,}", content, re.IGNORECASE):
        rca_structured += 1
    if re.search(r"(repro|复现|触发条件).{5,}", content, re.IGNORECASE):
        rca_structured += 1
        rca_has_repro = 1
    if re.search(r"(underlying|底层原因|why.*fail).{5,}", content, re.IGNORECASE):
        rca_structured += 1
    if re.search(r"(fix\.approach|修复方式|solution).{5,}", content, re.IGNORECASE):
        rca_structured += 1
    if re.search(r"(根因|原因分析|cause_analysis|根本原因)", content):
        rca_structured += 1

    # E5深度检测1: RCA内容含具体代码位置(file:line)
    if re.search(r"[a-zA-Z0-9_./-]+\.[a-z]+:\d+", content):
        rca_has_file_line = 1
        rca_has_reference = 1
        rca_depth_score += 2

    # E5深度检测2: RCA内容含量化数据(计数/比率/具体数值)
    if re.search(r"\d+/\d+|\d+\.\d+%|\d+ passed|\d+ failed|\d+ errors?", content):
        rca_has_quant = 1
        rca_depth_score += 2

    # E5深度检测3: RCA内容含验证性命令/操作(不是空头分析)
    if re.search(r"(verified|测试|tested|confirmed|验证).{5,}(exit|通过|PASS|\d+)", content, re.IGNORECASE):
        rca_depth_score += 1

    # Karpathy test-first: 复现证据
    if rca_has_repro == 1:
        if re.search(r"(FAIL|exit.*[1-9]|Traceback|Error:|assertion.*fail|失败输出|复现命令)", content, re.IGNORECASE):
            rca_repro_evidence = 1
            rca_depth_score += 1

    # B5: 模板化 RCA 检测
    if re.search(r"(占位符|placeholder|待补充|TODO|待确定|TBD|具体.*根据.*情况)", content, re.IGNORECASE):
        rca_templated += 1
    if re.search(r"(需要查看|需确认|需进一步|请根据|请参考|参见.*文档)", content, re.IGNORECASE):
        rca_templated += 1
    if re.search(r"(typical\.common|generic|general.*error|standard.*root)", content, re.IGNORECASE):
        rca_templated += 1

    # E5跨步错误去重检测: 检查error-dna是否已有相同错误签名在不同步骤重复出现
    _error_dna_dedup_found = False
    _error_dna_dedup_steps = []
    _error_dna_path = STATE_DIR / "error-dna.jsonl"
    if _error_dna_path.exists():
        try:
            error_records = []
            for line in _error_dna_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        error_records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            # 按错误类型聚类（使用error字段前40字符作为近似签名）
            from collections import defaultdict
            error_clusters = defaultdict(list)
            for rec in error_records:
                err_sig = rec.get("error", "")[:40]
                step = rec.get("step", "unknown")
                if err_sig.strip():
                    error_clusters[err_sig].append(step)
            # 检测: 同错误签名出现在≥3个不同步骤 → 症状反复
            for sig, steps in error_clusters.items():
                unique_steps = list(dict.fromkeys(steps))
                if len(unique_steps) >= 3:
                    _error_dna_dedup_found = True
                    _error_dna_dedup_steps = unique_steps
                    break
        except Exception:
            pass

    if _error_dna_dedup_found:
        print(f"⛔ COMPLETION BLOCKED [E5-dedup]: 检测到同一错误签名在 {len(_error_dna_dedup_steps)} 个不同步骤重复出现", file=sys.stderr, flush=True)
        print(f"  重复步骤: {', '.join(_error_dna_dedup_steps)}", file=sys.stderr, flush=True)
        print(f"  症状反复 = AI 在治标不治本（仅处理症状，未消除根因）", file=sys.stderr, flush=True)
        print(f"  请提供全局根因分析，确认修复项覆盖所有出现该错误的步骤", file=sys.stderr, flush=True)
        try:
            consumed.unlink()
        except OSError:
            pass
        _auto_soft_block("E5-dedup 硬阻断: 同错误签名跨步重复", autonomous)

    # E5裁决: 综合深度评分 ≥4 才通过（字段存在性 rca_structured≥2 是旧要求）
    _rca_passes_depth = rca_depth_score >= 4

    if rca_structured < 2:
        if quality_score >= thresh:
            if rca_templated >= 1:
                print(f"⛔ COMPLETION BLOCKED [E5+B5]: 检测到模板化 RCA（占位符/泛泛而谈），请提供具体根因分析。", file=sys.stderr, flush=True)
                print(f"  RCA 中含模板化表述({rca_templated}处)，缺少具体 file:line 引用。", file=sys.stderr, flush=True)
                if rca_has_reference == 0:
                    print("  建议: RCA 中引用具体代码位置 file:line", file=sys.stderr, flush=True)
                try:
                    consumed.unlink()
                except OSError:
                    pass
                _auto_soft_block("E5+B5 硬阻断: RCA 模板化（含占位符）", autonomous)
            else:
                print(f"⛔ COMPLETION BLOCKED [E5]: 证据质量评分 {quality_score}% 已达阈值 {thresh}%，但缺少根因分析。", file=sys.stderr, flush=True)
                print("  高质量证据表明 AI 有能力完成验证，但未诊断问题根因 — 这是症状混淆风险（E5）。", file=sys.stderr, flush=True)
                print(f"  深度评分: {rca_depth_score}/4 (需≥4)", file=sys.stderr, flush=True)
                print("  请补充结构化根因分析后重试（需≥2/5字段，含file:line引用和验证性命令）。格式示例:", file=sys.stderr, flush=True)
                print("    root_cause: <错误签名> / repro: <复现条件> / underlying: <底层原因> / fix_approach: <修复方式>", file=sys.stderr, flush=True)
                if rca_has_repro == 1 and rca_repro_evidence == 0:
                    print("  ⚠️ [test-first] 复现字段存在但缺少实际失败输出（FAIL/exit非零/Traceback），请补充复现命令+输出。", file=sys.stderr, flush=True)
                try:
                    consumed.unlink()
                except OSError:
                    pass
                _auto_soft_block("E5 硬阻断: 质量评分≥阈值但 RCA 缺失", autonomous)
        else:
            print("  ⚠️ [E5] RCA 根因分析未检测到。建议在证据中包含根因分析（root cause analysis）以证明修复触及底层原因，而非仅表面修复。", file=sys.stderr, flush=True)
            print("    格式示例: 'root_cause: <错误签名> / <复现条件> / <底层原因> / <修复方式>'", file=sys.stderr, flush=True)
    else:
        if not _rca_passes_depth:
            print(f"  ⚠️ [E5] RCA结构字段已存在({rca_structured}/5)，但深度评分不足({rca_depth_score}/4)", file=sys.stderr, flush=True)
            print(f"    改进: 补充 file:line 代码引用({'+2' if not rca_has_file_line else '✓'})", file=sys.stderr, flush=True)
            print(f"          补充量化验证数据({'+2' if not rca_has_quant else '✓'})", file=sys.stderr, flush=True)
            print(f"          补充验证性命令输出({'+1' if rca_depth_score < 4 else '✓'})", file=sys.stderr, flush=True)
        else:
            print(f"  ✓ RCA 根因分析已通过深度检测（结构{rca_structured}/5 + 深度{rca_depth_score}/5）", file=sys.stderr, flush=True)

    # P3.4: 质量评分透明输出
    if autonomous:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_line = f"[{ts}] [自主模式] 证据通过 — 质量评分: {quality_score}/100 (阈值 {thresh})"
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(str(STATE_DIR / "completion-gate-autonomous.log"), "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except OSError:
            pass
    else:
        # agentic_status success 等效
        print(f"\n✅ [证据通过]\n{'═' * 55}\n质量评分: {quality_score}/100 (阈值 {thresh})\n", file=sys.stderr, flush=True)
        fl = len(re.findall(r"[\w./-]+\.[a-z]+:\d+", content))
        cmd = sum(1 for p in ["exit.code", r"PASS", r"FAIL", "✅", "❌", "test", "build"] if re.search(p, content, re.IGNORECASE))
        multi = sum(1 for p in [r"\d+%", r"\d+ms", "coverage", "all tests", "edge.case"] if re.search(p, content, re.IGNORECASE))
        quant = sum(1 for p in [r"\d+/\d+", r"\d+\.\d+"] if re.search(p, content))
        print(f"  file:line={fl}  test/cmd={cmd}  multi-aspect={multi}  quant={quant}", file=sys.stderr, flush=True)

    # C3: L3 复杂度检测 — Oracle 终审记录检查
    if re.search(r"(L[34]|三重门|architecture|arch decision|方案选型|跨模块|interface change|multi.*file|设计决策|架构变更|design decision)", content, re.IGNORECASE):
        if "## Oracle 终审记录" not in content:
            print("⚠️ [C3] L3 任务检测到：证据内容含架构决策/多文件变更等 L3 复杂度关键词，但未找到 Oracle 终审记录块。", file=sys.stderr, flush=True)
            print("   L3 任务应包含 Oracle 终审记录以完成 C3 流程验证。格式参考：", file=sys.stderr, flush=True)
            print("   ## Oracle 终审记录", file=sys.stderr, flush=True)
            print("   审核时间: {timestamp}", file=sys.stderr, flush=True)
            print("   审核者: Oracle", file=sys.stderr, flush=True)
            print("   结论: APPROVED | NEEDS_REVISION", file=sys.stderr, flush=True)
            print("   备注: {note}", file=sys.stderr, flush=True)
        else:
            print("  ✓ C3: Oracle 终审记录已找到", file=sys.stderr, flush=True)

    # 验证通过，清理消费文件
    try:
        consumed.unlink()
    except OSError:
        pass

    # 自动推进 Pipeline Step
    pipeline_script = PROJECT_ROOT / ".claude" / "scripts" / "pipeline-step.sh"
    if pipeline_script.exists():
        try:
            subprocess.run(
                ["bash", str(pipeline_script), "advance"],
                capture_output=True, timeout=10
            )
        except (subprocess.SubprocessError, OSError):
            pass

    # A→B→A 交叉验证触发
    trigger = False

    # 通道1: 复杂度门控
    if re.search(r"(L[34]|三重门|architecture|arch decision|方案选型|跨模块|interface change|multi.*file|设计决策|架构变更|design decision)", content, re.IGNORECASE):
        trigger = True

    # 通道2: 关键词匹配
    if not trigger:
        if re.search(r"(验收|benchmark|scorecard|通过率|口径|mapping|合规)", content, re.IGNORECASE):
            trigger = True
        else:
            matched = set(re.findall(r"(报告|方案|评估|design|proposal|review|analysis|评审|分析)", content, re.IGNORECASE))
            if len(matched) >= 2:
                trigger = True

    if trigger:
        handoff_file = STATE_DIR / "cross-verify-handoff.md"
        # 扫描近期修改的方案/报告文件
        recent_docs = []
        try:
            for search_dir in [PROJECT_ROOT / "docs", PROJECT_ROOT / "rpe", PROJECT_ROOT / ".omc" / "plans"]:
                if search_dir.is_dir():
                    for mdfile in search_dir.rglob("*.md"):
                        try:
                            if time.time() - mdfile.stat().st_mtime < 600:  # 10 min
                                recent_docs.append(str(mdfile))
                                if len(recent_docs) >= 5:
                                    break
                        except OSError:
                            pass
                if len(recent_docs) >= 5:
                    break
        except OSError:
            pass

        evidence_preview = "\n".join(content.split("\n")[:5])
        handoff_content = f"""# 🚦 三重门交叉验证 — A→B→A

## Phase 1: A 填写可证伪预测（发给 B 前填写）
> 注意：以下预测由 A 终端填写，B 终端**不得查看** Phase 1 内容

**subject**: 任务验证

predictions:
{chr(10).join(f"  {l}" for l in evidence_preview.split(chr(10)) if l.strip())}
- [ ] 预测1: [A 填写具体可证伪断言]
- [ ] 预测2: [A 填写具体可证伪断言]
- [ ] 预测3: [A 填写具体可证伪断言]

**evidence_requirements**:
  - build: [产物/exit_code/构建日志]
  - test: [通过数/失败数/覆盖率]
  - behavior: [路径/内容/副作用]

---

## Phase 2: B 盲执行（剥离预测后发给 B）

> 以下内容复制到 B 终端（B **不知道** A 的预测，消除确认偏差）

B 终端，你是执行方。执行以下验证任务，**只陈述事实**，不下结论：

**任务描述**:
{content}

**近期修改的相关文件（10分钟内）**:
{chr(10).join(f"  - {d}" for d in recent_docs)}

**B 报告格式**（请逐项填写原始输出，不做分析）:
```
executed_steps:
  - step_id: "S1"
    command: "[实际执行的命令]"
    exit_code: 0|1|null
    actual_output: "[原始输出]"
    observed: "[客观描述]"
anomalies: []
```

---

## Phase 3: A 自证（收到 B 报告后填写）

comparisons:
  - prediction_id: "P1"
    expected: "[A 的预测内容]"
    observed: "[B 的观测结果]"
    match: true|false
    explanation: "[不匹配时解释原因]"
self_verdict: "PASS|FAIL|INCONCLUSIVE"
reasoning: "[综合判断]"

***** 全部内容结束 *****
"""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        handoff_file.write_text(handoff_content, encoding="utf-8")
        print(handoff_content, file=sys.stderr, flush=True)
        print("", file=sys.stderr, flush=True)
        print("📁 手off文件已写入: .omc/state/cross-verify-handoff.md", file=sys.stderr, flush=True)
        print("   B 终端启动后直接执行: cat .omc/state/cross-verify-handoff.md", file=sys.stderr, flush=True)
        print("", file=sys.stderr, flush=True)
        print("同模型交叉验证效果有限（盲区重叠），必须不同模型才能真正发现断言造假。", file=sys.stderr, flush=True)
        print("比对一致 → 验收通过 | 不一致 → 返回 A 重新生成方案，重复此流程", file=sys.stderr, flush=True)
        print("══════════════════════════", file=sys.stderr, flush=True)

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
