#!/usr/bin/env python3
"""
stop-flywheel.py — CarrorOS Stop hook（飞轮自动触发 + 升华检查）

会话停止时：
  1. run_flywheel：error-dna → 模式提取 → anti-patterns.md + claude-next.md
  2. 升华检查：claude-next 条目 hits≥5 → 升华至 anti-patterns.md（kernel 候选），
     记录 sublimation-log.jsonl（铁律 6：不直接改 kernel.md/AGENTS.md，升华候选由人类裁决晋升）

设计：快速（<2s）、永不阻断（exit 0）、失败静默。
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

KNOWLEDGE = ROOT / ".omc" / "knowledge"
CLAUDE_NEXT = KNOWLEDGE / "claude-next.md"
SUBLIMATION_LOG = KNOWLEDGE / "sublimation-log.jsonl"
ANTI_PATTERNS = ROOT / ".claude" / "references" / "anti-patterns.md"
ANTI_PATTERN_REDIRECTS = ROOT / ".omc" / "state" / "anti-pattern-redirects.jsonl"
ERROR_DNA = ROOT / ".omc" / "state" / "error-dna.jsonl"
KERNEL_CANDIDATES = KNOWLEDGE / "kernel-candidates.md"

SUBLIMATION_HITS = 5


# ── ADR-0012: 反模式→REDIRECT 规则转译 ──
# 升华时自动产生一条机器可读的 redirect rule，供 pretool-gate oracle 消费。
# 规则 = pattern 的 escaped 版本 → 匹配 bash 命令/Edit 路径。
# hits≥SUBLIMATION_HITS→写入 anti-pattern-redirects.jsonl。
_ANTI_PATTERN_GUIDANCE_MAP: dict[str, str] = {
    "E1": "做完了必须回去验证,smoke-test + audit-hooks 全绿才提交",
    "E2": "犯错后立即写 claude-next 条目,DG-xxx 格式记录失败",
    "E3": "同一失败反复出现时启用升华管道,不要盲目重试",
    "E4": "编译不过先读错误信息定位问题,不要在错误方向上反复重试",
    "F1": "用 Read 工具读文件,不要用 cat/grep/shell 命令读文件",
    "F2": "使用 PROJECT_ROOT 环境变量或相对路径,不写死绝对路径",
    "G1": "每次会话开头加载 AGENTS.md,阅读治理文档后再执行",
    "G2": "新会话先读 session-handoff.md 继承上下文",
    "H1": "密钥走环境变量引用,不敲明文 token/密码到命令中",
    "H2": "删除/发布前需 permission-gate + 三次确认",
}


def _to_redirect_rule(pattern_name: str, guidance: str, source: str = "sublimation",
                       hits: int = 0) -> dict:
    """将反模式名转译为 pretool-gate 可消费的 REDIRECT 规则."""
    # pattern_name 可能是中文（如 "不回查"）或英文 slug，转译为匹配 key
    key = pattern_name.lower().replace(" ", "_")[:40]
    return {
        "pattern_key": key,
        "guidance": guidance,
        "source": source,
        "hits": hits,
        "created": _now_iso(),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_flywheel() -> dict:
    try:
        from lib.flywheel import run_flywheel
        return run_flywheel(ROOT)
    except Exception as exc:
        return {"error": str(exc)}


def _sublimation_check() -> list[str]:
    """claude-next + error-dna 中 hits≥5 的模式 → anti-patterns.md + 升华日志。返回升华的模式。"""
    patterns: dict[str, int] = {}  # pattern -> hit count

    # ── 数据源1: claude-next.md ──
    if CLAUDE_NEXT.exists():
        try:
            lines = CLAUDE_NEXT.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if "已升华" in line or "升华到" in line:
                    continue
                m = re.search(r"Pattern '([^']+)'", line)
                if m:
                    patterns[m.group(1)] = patterns.get(m.group(1), 0) + 1
        except Exception:
            pass

    # ── 数据源2: error-dna.jsonl 中的高频 error_type 簇 ──
    _error_type_counts: dict[str, int] = {}
    if ERROR_DNA.exists():
        try:
            with ERROR_DNA.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    et = entry.get("error_type")
                    msg = entry.get("message", "")
                    # 跳过旧 harvester 格式（无 error_type）
                    if not et or et == "?" or entry.get("_source") == "harvester":
                        continue
                    _error_type_counts[et] = _error_type_counts.get(et, 0) + 1
        except Exception:
            pass
    for et, cnt in _error_type_counts.items():
        if cnt >= SUBLIMATION_HITS and et not in patterns:
            patterns[et] = cnt

    candidates = [p for p, c in patterns.items() if c >= SUBLIMATION_HITS]
    if not candidates:
        return []

    # 已存在于 anti-patterns.md 的模式跳过
    existing = ""
    if ANTI_PATTERNS.exists():
        try:
            existing = ANTI_PATTERNS.read_text(encoding="utf-8")
        except Exception:
            existing = ""

    sublimated: list[str] = []
    _now_dt = datetime.now(timezone.utc)
    for pattern in candidates:
        if f"`{pattern}`" in existing or pattern in existing:
            continue
        hits = patterns[pattern]
        entry = (
            f"\n### {pattern}（飞轮升华 {_now_dt.strftime('%Y-%m-%d')}）\n"
            f"- 来源：自动升华，hits={hits}（阈值≥{SUBLIMATION_HITS}）\n"
            f"- 触发条件：反复出现的 `{pattern}` 失败模式\n"
            f"- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决\n"
        )
        try:
            with ANTI_PATTERNS.open("a", encoding="utf-8") as f:
                f.write(entry)
            with SUBLIMATION_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": _now_iso(), "pattern": pattern, "hits": hits,
                    "target": "anti-patterns.md", "kernel_promotion": "pending_human_review",
                }, ensure_ascii=False) + "\n")
            # ── ADR-0012: 同时写入 redirect rule（幂等：跳过已存在的 pattern） ──
            _key = pattern.lower().replace(" ", "_")[:40]
            _already_redirect = False
            if ANTI_PATTERN_REDIRECTS.exists():
                try:
                    with ANTI_PATTERN_REDIRECTS.open("r", encoding="utf-8") as f:
                        _existing_redirects = [json.loads(l) for l in f if l.strip()]
                    if any(r.get("pattern_key") == _key for r in _existing_redirects):
                        _already_redirect = True
                except Exception:
                    pass
            if not _already_redirect:
                _rule = _to_redirect_rule(pattern, f"error-dna 中反复出现 {pattern} 失败,见 claude-next 条目;路径正确做法见对应条目",
                                           source="sublimation", hits=hits)
                ANTI_PATTERN_REDIRECTS.parent.mkdir(parents=True, exist_ok=True)
                with ANTI_PATTERN_REDIRECTS.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(_rule, ensure_ascii=False) + "\n")
            # ── 写入 kernel-candidates.md（升华候选暂存区，不碰冻结的 kernel.md） ──
            KERNEL_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
            kc_entry = (
                f"\n## {pattern}\n"
                f"- 升华时间: {_now_iso()}\n"
                f"- hits: {hits}（阈值≥{SUBLIMATION_HITS}）\n"
                f"- 状态: pending_human_review\n"
                f"- 来源: error-dna 自动升华\n"
                f"- 描述: 反复出现的 `{pattern}` 失败模式\n"
                f"- 晋升 kernel: 需人类审查后将此节迁移至 kernel.md\n"
            )
            with KERNEL_CANDIDATES.open("a", encoding="utf-8") as f:
                f.write(kc_entry)
            sublimated.append(pattern)
        except Exception:
            pass
    return sublimated


def main() -> None:
    # 读 stdin（Stop payload），但不依赖其内容
    try:
        sys.stdin.read()
    except Exception:
        pass

    result = _run_flywheel()
    sublimated = _sublimation_check()

    if result.get("patterns_found") or sublimated:
        print(
            f"🛞 [flywheel] patterns={result.get('patterns_found', 0)} "
            f"anti_patterns={result.get('anti_patterns_written', False)} "
            f"sublimated={sublimated or 'none'}",
            file=sys.stderr, flush=True,
        )

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
