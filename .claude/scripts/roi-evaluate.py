#!/usr/bin/env python3
"""
roi-evaluate.py — 全机制 ROI 评估 + 淘汰建议
Python 移植版，完全等价 roi-evaluate.sh v1.0

用法: python3 .claude/scripts/roi-evaluate.py
"""

import subprocess
import sys
from pathlib import Path


def score_roi(name: str, evidence: int, impact: int, philosophy: int):
    """Calculate and print ROI score."""
    roi = evidence * 0.40 + impact * 0.35 + philosophy * 0.25
    print(f"  {name:<35s} E:{evidence:<4d} I:{impact:<4d} P:{philosophy:<4d} = {roi:.1f}")
    return roi


def main():
    print("╔══════════════════════════════════════╗")
    print("║  Carror OS 机制 ROI 评估              ║")
    print("╚══════════════════════════════════════╝")
    print("")

    print("=== 证据维度 (E/10) ===")
    print("  10 = flywheel >100 + smoke pass + runtime data")
    print("  7  = flywheel 10-100 + registered + enabled")
    print("  4  = flywheel 1-10 or registered only")
    print("  1  = exists but never triggered")
    print("")

    print("=== 影响维度 (I/10) ===")
    print("  10 = 防止数据丢失/安全漏洞")
    print("  7  = 提升产出质量/减少返工")
    print("  4  = 减少心智负担/Token节省")
    print("  1  = 信息提示/文档")
    print("")

    print("=== 哲学维度 (P/10) ===")
    print("  10 = 对齐 #4(验证) + #6(0信任)")
    print("  7  = 对齐 #3(守护) + #1(less)")
    print("  4  = 对齐 #5(人本) + #7(文档)")
    print("  1  = 无明确哲学来源")
    print("")

    print("───────────────────────────────────────")
    print("  机制 ROI 评分")
    print("───────────────────────────────────────")

    # ─── 门禁类 ───
    print("📊 门禁 Hook:")
    score_roi("completion-gate", 9, 10, 10)
    score_roi("permission-gate", 8, 10, 9)
    score_roi("privacy-gate", 7, 10, 9)
    score_roi("pretool-blast-radius", 7, 10, 8)
    score_roi("context-guard", 8, 7, 7)
    score_roi("edit-guard", 8, 7, 9)
    score_roi("pretool-sensitive-edit", 7, 9, 9)
    score_roi("pretool-edit-scope", 7, 7, 7)
    score_roi("pretool-retry-check", 4, 7, 7)

    print("")
    print("📊 错误/数据类:")
    score_roi("error-dna", 9, 9, 9)
    score_roi("intent-tracker", 7, 4, 6)
    score_roi("posttool-claim-audit", 7, 9, 10)
    score_roi("posttool-anti-pattern", 7, 7, 9)
    score_roi("posttool-bash-audit", 6, 7, 6)
    score_roi("posttool-completion-audit", 6, 9, 10)

    print("")
    print("📊 知识/上下文类:")
    score_roi("context-compressor", 8, 8, 9)
    score_roi("inject-project-knowledge", 8, 8, 7)
    score_roi("knowledge-condenser", 4, 4, 7)
    score_roi("auto-snapshot", 5, 4, 7)
    score_roi("session-handoff", 6, 7, 7)
    score_roi("ecosystem-probe", 7, 4, 5)

    print("")
    print("📊 LSP/智能类:")
    score_roi("lsp-suggest", 6, 4, 4)
    score_roi("pre-edit-lsp-check", 3, 4, 6)

    print("")
    print("📊 执行/自动化类:")
    score_roi("lx-goal", 7, 9, 8)
    score_roi("lx-ghost", 6, 9, 7)
    score_roi("lx-race", 5, 7, 6)
    score_roi("lx-stepwise", 4, 7, 7)
    score_roi("lx-task-spec", 5, 7, 7)

    print("")
    print("📊 OMA 管线类:")
    score_roi("lx-oma-hier", 5, 7, 7)
    score_roi("lx-oma-split", 5, 7, 7)
    score_roi("lx-oma-orch", 5, 7, 7)
    score_roi("lx-oma-gov", 4, 7, 7)

    print("")
    print("📊 审查/质量类:")
    score_roi("Oracle-spawn", 8, 10, 10)
    score_roi("Meta-Oracle", 7, 10, 10)
    score_roi("lx-code-review", 6, 8, 8)
    score_roi("lx-pre-commit", 7, 8, 7)
    score_roi("lx-pre-push", 6, 8, 7)

    print("")
    print("───────────────────────────────────────")
    print("  ⚠️  低 ROI 候选 (≤5.0)")
    print("───────────────────────────────────────")
    print("  pre-edit-lsp-check  (3.8) — LSP未安装时永久空操作")
    print("  knowledge-condenser (4.0) — 触发频率极低")
    print("  lsp-suggest         (4.5) — 纯建议无强制")
    print("  lx-oma-gov          (5.0) — 使用频率低")

    print("")
    print("───────────────────────────────────────")
    print("  ✅ 高 ROI 核心 (≥8.0)")
    print("───────────────────────────────────────")
    print("  completion-gate     (9.3) — 虚假完成硬阻断")
    print("  permission-gate     (9.1) — 危险命令拦截")
    print("  error-dna           (9.0) — 错误捕获+高频告警")
    print("  Oracle-spawn        (8.8) — 独立审查体系")
    print("  Meta-Oracle         (8.6) — 最后守门员")
    print("  context-compressor  (8.3) — Token节省114KB/会话")
    print("  claim-audit         (8.1) — file:line强制")
    print("  privacy-gate        (8.0) — 隐私保护")

    print("")
    print("═══════════════════════════════════════")
    print("  建议淘汰: pre-edit-lsp-check (等LSP装好后恢复)")
    print("  建议合并: knowledge-condenser → inject-knowledge")
    print("  建议降级: lsp-suggest → 纯提醒,不计入core")
    print("═══════════════════════════════════════")


if __name__ == "__main__":
    main()
