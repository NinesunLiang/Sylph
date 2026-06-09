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

    # Generate new cache content
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        f"<!-- CONTEXT-COMPRESSOR: {now_str} 自动生成 -->",
        "<!-- 源文件: AGENTS.md + anti-patterns.md + claude-next.md + kernel.md -->",
        "<!-- 渐进式披露: 注入精简版，完整版请 Read 源文件 -->",
        "",
    ]

    all_ok = True
    for src_file in src_files:
        if src_file.exists():
            try:
                content = src_file.read_text(encoding="utf-8")
                src_lines = content.splitlines()[:80]
                lines.extend(src_lines)
                lines.append("")
                lines.append("---")
                lines.append("")
            except Exception:
                print(f"[context-compressor] ⚠️ 读取失败: {src_file}", file=sys.stderr)
                all_ok = False
        else:
            print(f"[context-compressor] ⚠️ 源文件缺失: {src_file}", file=sys.stderr)
            all_ok = False

    try:
        cache_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

    cache_size = cache_file.stat().st_size if cache_file.exists() else 0
    if all_ok:
        print(f"[context-compressor] ✅ 缓存已更新: {cache_file} ({cache_size} bytes)", file=sys.stderr)
    else:
        print("[context-compressor] ⚠️ 部分源文件缺失，缓存不完整", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
