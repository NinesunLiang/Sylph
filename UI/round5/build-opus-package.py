#!/usr/bin/env python3
"""build-opus-package.py — 组装 Opus 4.8 §17a 审计源码包（从磁盘逐字读取，幂等可重跑）

产出：UI/round5/opus-source-package.md
结构：Opus 要求的三批文件 + 附录A（carros_base.py 关键命令实现）+ 附录B（证据日志）
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "opus-source-package.md"

# (标题, 相对路径, fence语言, 行区间或None=全文)
BATCH1 = [
    ("1.1 夜跑 hook v3（夜间 Bash 无条件默认拒绝 + 精确白名单；Sol P0-SOL-1 修复）", ".claude/hooks/carroros-night-deny.py", "python", None),
    ("1.2 gate-result 信封库 + reducer", "scripts/carroros-gates/lib/gate_result.py", "python", None),
    ("1.3 finalize-page.sh（C8a：权威链收口 + producer 校验 + contract_trust）", "scripts/carroros-gates/finalize-page.sh", "bash", None),
    ("1.4 assertion-catalog.yaml v1.0（O3 封闭词表）", "scripts/carroros-gates/assertion-catalog.yaml", "yaml", None),
    ("1.5 preflight.sh（起飞前 12 项检查，含 4b helper 绑定 / 7b S1 签署硬拦）", "scripts/carroros-gates/preflight.sh", "bash", None),
]
BATCH2 = [
    ("2.1 lib/common.sh（参数解析 / digest / gates_write_result 唯一信封写入助手）", "scripts/carroros-gates/lib/common.sh", "bash", None),
    ("2.2 lib/run-gate.sh（C2/C4/C5/C6 包装器 + argv_digest）", "scripts/carroros-gates/lib/run-gate.sh", "bash", None),
    ("2.3 scope-check.sh（C1：files_allowed 前缀门禁）", "scripts/carroros-gates/scope-check.sh", "bash", None),
    ("2.4 evidence-check.sh（C7：证据新鲜度 + AC 覆盖 qualified 判定）", "scripts/carroros-gates/evidence-check.sh", "bash", None),
    ("2.5 smoke/run-all.sh（73 例八类：正负 / 崩溃恢复 / fail-open / 篡改 / hook 攻击 / 子目录前缀 / Sol 动态路径语义绕过集）", "scripts/carroros-gates/smoke/run-all.sh", "bash", None),
]
BATCH3 = [
    ("3.1 night-loop.md（夜循环 13 步 + 禁止列表 + 夜熔规则）", ".claude/workflows/frontend-overnight/night-loop.md", "markdown", None),
    ("3.2 intake.md（输入成熟度矩阵 + reconcile + BLOCKED_INPUT）", ".claude/workflows/frontend-overnight/intake.md", "markdown", None),
    ("3.3 night-manifest.signoff.template.yaml（Owner 签署件模板）", "scripts/carroros-gates/templates/night-manifest.signoff.template.yaml", "yaml", None),
    ("3.4 night-manifest.template.yaml（v3.1 全字段模板：trust_boundary/first_night_selection/pages schema）", "scripts/carroros-gates/templates/night-manifest.template.yaml", "yaml", None),
]
# 附录A：carros_base.py 摘录（Opus 点名：manifest-json 路径规范化 / token CAS / gate-results-init）
APPENDIX_A = [
    ("A.1 _load_token / CASConflict / _save_token（token CAS：flock + expected_revision + tmp+rename 原子写）",
     ".omc/scripts/carros_base.py", "python", (178, 230)),
    ("A.2 cmd_manifest_json（manifest 规范化 JSON 出口：--get 点路径 / --pages / --page-id，缺失即 exit 2 fail-closed）",
     ".omc/scripts/carros_base.py", "python", (2110, 2183)),
    ("A.3 cmd_token_write（token.json 唯一合法写入入口；--set path=value，CAS 冲突 exit 3）",
     ".omc/scripts/carros_base.py", "python", (2186, 2239)),
    ("A.4 cmd_gate_results_init（页级 gate-results 权威链事实目录创建，幂等）",
     ".omc/scripts/carros_base.py", "python", (2242, 2266)),
]
APPENDIX_B = [
    ("B.1 smoke 独立复跑日志（rsync→/tmp→SMOKE_RUNNER=independent，73/73 绿，post-Sol 新 digest 入袋）",
     "UI/round5/logs/smoke-independent-rerun-20260718-post-sol.log", "text", None),
    ("B.2 preflight NO-GO 复跑日志（裸 repo 12 项全拦，fail-closed 证据）",
     "UI/round5/logs/preflight-nogo-rerun-20260718.log", "text", None),
    ("B.3 Sol P0-SOL-1 fresh payload 验证（18 攻击全 BLOCK + 20 合法全 ALLOW + 6 坏 payload fail-closed + cwd 漂移）",
     "UI/round5/logs/sol-p0-verify-20260718.log", "text", None),
]

HEADER = """# §17a 审计源码包（post-Grok + post-Opus + post-Sol 三轮修复后的当前磁盘状态）

> 生成：build-opus-package.py 从磁盘逐字拼装（幂等）。本包即当前工作区真实源码，非转述。
> 文件名沿用首任审计方 Opus 的名字；内容已含 Grok 轮 + Opus 轮 + Sol 轮全部修复，供 GPT-5.6 Sol 复审及后续审计方使用。
> 背景：三家高阶审计进度——
> - Grok-4.5：3 P0（Bash 旁路/自证当证据/合法假 PASS）全修，Conditional GO 清单 4/5 机器绿
>   （audit-receipt / audit-response / audit-rereview / audit-closure-grok-4.5.md 四份同袋）
> - Opus 4.8：3 新 P1（O3/O5 为误报已闭环、P1-10 真洞已修 9b 硬拦）复审确认闭环
>   （opus-4.8.md / audit-response-opus-4.8.md / opus-4.8_response.md / audit-closure-opus-4.8.md 四份同袋）
> - GPT-5.6 Sol：1 阻断性 P0（动态路径删 marker → hook 熄灯，实证修复前 7/8 穿防）已修：
>   hook v3 夜间 Bash 无条件默认拒绝 + marker __file__/env 锚定 + 坏 payload fail-closed；
>   fresh payload 18 攻击全 BLOCK / 20 合法全 ALLOW / R-SOL-A..I 全绿
>   （gpt-5.6Sol.md / audit-response-gpt-5.6Sol.md / sol-p0-verify 日志同袋）
>
> 三批文件逐字未删节（附录A 按函数区间摘录 carros_base.py——全文 2284 行，
> 仅摘录审计点名的 cmd_manifest_json / cmd_token_write / cmd_gate_results_init / _save_token CAS，
> 其余为无关命令实现，如需全本可另发）。
> 证据日志在附录B；Grok-A/B、Opus P1、Sol P0 的 fresh payload 驱动与日志在 UI/round5/ 同目录。
>
> 特别回应审计疑点：
> - 「C1 prefix 逻辑（manifest-json 如何规范化路径）」→ 2.3 scope-check.sh + 附录 A.2
> - 「run-gate 临时文件 + fsync + 原子 rename」→ 2.2 run-gate.sh + 附录 A.1 _save_token（tmp+rename 模式同构）
> - 「token-write CAS 冲突返回非零」→ 附录 A.1 CASConflict + A.3 cmd_token_write（exit 3）
> - 「空 gate-results / 全 SUPERSEDED」→ 2.5 smoke 类 4（0 文件不得称 PASS）+ 类 5h（SUPERSEDED 滤空→BLOCKED）
> - 「动态路径旁路（删 marker 关灯）」→ 1.1 hook v3（无条件默认拒绝）+ 2.5 smoke 类 8（29 例 Sol 集）+ 附录 B.3

---

# 第一批
"""

def emit(title: str, rel: str, lang: str, span) -> str:
    p = ROOT / rel
    text = p.read_text(encoding="utf-8")
    if span is not None:
        a, b = span
        lines = text.splitlines()
        text = "\n".join(lines[a - 1 : b]) + "\n"
        rel = f"{rel}#L{a}-L{b}"
    # 外层用四个反引号，避免文件内三反引号截断
    return f"\n## {title}\n\n`{rel}`\n\n````{lang}\n{text}````\n"

parts = [HEADER]
for t, r, l, s in BATCH1:
    parts.append(emit(t, r, l, s))
parts.append("\n---\n\n# 第二批\n")
for t, r, l, s in BATCH2:
    parts.append(emit(t, r, l, s))
parts.append("\n---\n\n# 第三批\n")
for t, r, l, s in BATCH3:
    parts.append(emit(t, r, l, s))
parts.append("\n---\n\n# 附录A：carros_base.py 关键命令实现（按函数区间摘录，行号真实）\n")
for t, r, l, s in APPENDIX_A:
    parts.append(emit(t, r, l, s))
parts.append("\n---\n\n# 附录B：证据日志\n")
for t, r, l, s in APPENDIX_B:
    parts.append(emit(t, r, l, s))

OUT.write_text("".join(parts), encoding="utf-8")
size = OUT.stat().st_size
lines = OUT.read_text(encoding="utf-8").count("\n") + 1
print(f"OK: {OUT}  {size} bytes, {lines} lines")
