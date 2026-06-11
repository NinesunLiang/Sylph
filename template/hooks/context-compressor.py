#!/usr/bin/env python3
"""
context-compressor.py — SessionStart — 渐进式披露：源文件精简版注入缓存
检测源文件 mtime → 拼接精简内容 → 缓存到 .omc/state/context-cache.md
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event


def safe_stat_mtime(path):
    """Get file modification time (epoch), returns 0 on error."""
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0


def main():
    if not hc_enabled("context_compressor"):
        sys.exit(0)

    project_root = (_HOOKS_DIR / "../..").resolve()
    claude_dir = project_root / ".claude"
    state_dir = project_root / ".omc" / "state"
    cache_file = state_dir / "context-cache.md"

    state_dir.mkdir(parents=True, exist_ok=True)

    force_regen = False

    if not cache_file.exists():
        bootstrap = (
            "<!-- CONTEXT-COMPRESSOR: bootstrap 自动生成 -->\n"
            "铁律:\n"
            "1.禁止编造:断言必有file:line/命令输出,找不到→BLOCKED\n"
            "2.用户裁定:验收/选型/冲突由Boss决定,AI不可自判\n"
            "3.证据门禁:无VERIFIED证据禁止说\"已完成/已验证\"\n"
            "4.Git门禁:编译→功能→报告→Boss批准→提交,跳步=回滚\n"
            "5.范围冻结:一次一个Step,非核心只写TODO,越界撤销\n"
            "6.隐私防线:禁读.env/私钥,禁Bash敲明文Token\n"
            "7.断言真实:百分比/评分须有来源URL/file:line,无来源标注[内部自检]\n"
            "8.哲学先行:问人前先过哲学7条,哲学能裁决→[哲学先行:#N→action]直接执行\n"
            "#8细则:过程性问题直接执行/抉择性问题哲学裁决\n"
            "禁止问:\"跑X?\"→[#4→执行] \"A还是B?\"→[#2→选A]\n"
            "哲学优先级:#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)\n"
            "软完成语禁令→必须VERIFIED:\n"
            "应该没问题/基本完成/理论上/看起来正常/差不多了/之前验证过\n"
            "should be fine/basically done/mostly complete/seems to work\n"
            "操作约束:\n"
            "-编辑:Read-before-Edit|current-scope越界→BLOCKED\n"
            "-Bash:git commit/push|rm -rf|sudo→BLOCKED\n"
            "-完成:VERIFIED|evidence≥60|fresh≤300s\n"
            "-隐私:.env|Token|密钥→BLOCKED\n"
            "权威:Boss指令>项目宪法>PRD>Skill>设计文档>代码\n"
            "---\n"
        )
        try:
            cache_file.write_text(bootstrap, encoding="utf-8")
        except Exception:
            pass
        print("[context-compressor] bootstrap: 最小脱水上下文已生成", file=sys.stderr)
        force_regen = True

    src_files = [
        project_root / "AGENTS.md",
        claude_dir / "anti-patterns.md",
        claude_dir / "claude-next.md",
        claude_dir / "kernel.md",
    ]

    need_regen = False
    if not cache_file.exists():
        need_regen = True
    else:
        cache_mtime = safe_stat_mtime(str(cache_file))
        for src_file in src_files:
            if not src_file.exists():
                continue
            src_mtime = safe_stat_mtime(str(src_file))
            if src_mtime > cache_mtime:
                need_regen = True
                break

    if not need_regen and not force_regen:
        flywheel_event("context_compressor", "cache_hit", "L0")
        sys.exit(0)

    flywheel_event("context_compressor", "regenerating", "L1")

    # Generate new cache content — AI-optimized compression (same format as bootstrap)
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        f"<!-- CONTEXT-COMPRESSOR: {now_str} 自动生成 -- 渐进式披露：仅注入精简路由 + 哲学铁律 -->",
        "<!-- 源文件已变: AGENTS.md + anti-patterns.md + claude-next.md + kernel.md -->",
        "<!-- 渐进式披露: 精简版在此，完整版请 Read 对应源文件 -->",
        "",
    ]

    # === 1. 读取 AGENTS.md 精华（前 40 行=哲学+铁律+难度分级完整）===
    agents_file = project_root / "AGENTS.md"
    agents_summary = ""
    if agents_file.exists():
        try:
            al = agents_file.read_text(encoding="utf-8").splitlines()
            # Strip leading @.claude lines, find content start
            start_i = 0
            for i, l in enumerate(al):
                if l.strip() and not l.strip().startswith("@"):
                    start_i = i
                    break
            agents_summary = "\n".join(al[start_i:start_i + 40]).strip()
        except Exception:
            agents_summary = "(AGENTS.md read error)"
    if not agents_summary:
        agents_summary = "(AGENTS.md empty or not found)"
    lines.append("--- AGENTS.md 精华 ---")
    lines.append(agents_summary)

    # === 2. 读取 kernel.md — 摘取核心编码规则和难度分级 ===
    kernel_file = project_root / ".claude" / "kernel.md"
    if kernel_file.exists():
        try:
            kc = kernel_file.read_text(encoding="utf-8")
            # Grab first 15 non-empty lines
            klines = [l for l in kc.splitlines() if l.strip()][:15]
            lines.append("--- kernel.md 精华 ---")
            lines.extend(klines[:15])
        except Exception:
            lines.append("--- kernel.md: (read error) ---")
    else:
        lines.append("--- kernel.md: (missing) ---")

    # === 3. 读取 claude-next.md — 最近 3 条 lessons ===
    cn_file = project_root / ".claude" / "claude-next.md"
    if cn_file.exists():
        try:
            import re
            cn_text = cn_file.read_text(encoding="utf-8")
            cn_hits = re.findall(r'^###\s+(.+)$', cn_text, re.MULTILINE)[:3]
            lines.append("--- claude-next.md lessons ---")
            for h in cn_hits:
                lines.append(f"  - {h.strip()[:100]}")
        except Exception:
            lines.append("--- claude-next.md: (parse error) ---")

    # === 4. 读取 anti-patterns.md — 3 个最新反模式标题 ===
    ap_file = project_root / ".claude" / "anti-patterns.md"
    if ap_file.exists():
        try:
            import re
            ap_text = ap_file.read_text(encoding="utf-8")
            ap_hits = re.findall(r'^##\s+(.+)$', ap_text, re.MULTILINE)[:3]
            if ap_hits:
                lines.append("--- anti-patterns.md ---")
                for h in ap_hits:
                    lines.append(f"  - {h.strip()[:100]}")
        except Exception:
            pass

    lines.append("")
    lines.append("<!-- 完整源文件路径: AGENTS.md / .claude/anti-patterns.md / .claude/claude-next.md / .claude/kernel.md -->")

    try:
        cache_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cache_size = cache_file.stat().st_size
        print(f"[context-compressor] ✅ 缓存已压缩更新: {cache_file} ({cache_size} bytes)", file=sys.stderr)
    except Exception as e:
        print(f"[context-compressor] ❌ 写入失败: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
