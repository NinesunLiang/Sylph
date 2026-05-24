#!/usr/bin/env python3
"""Meta-Oracle review entry point — cross-platform replacement for meta-oracle-review.sh.

Called by AI after Meta-Oracle trigger notification, or by pipeline scripts
(lx-oma-orch, lx-oma-hier, package-release.sh).

Usage:
  python3 .claude/scripts/meta-oracle-review.py [G1|G2|G3|G4]

Outputs:
  1. Meta-Oracle review methodology (prompt for AI/critic agent)
  2. Runs C/E/G/UX scoring via meta-oracle-scorer
  3. Writes verdict entry to .omc/state/meta-oracle-verdicts.md
"""

import json
import os
import sys
from datetime import datetime, timezone


IS_WINDOWS = os.name == "nt"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")

# Platform-adaptive Python command
PY_CMD = "py -3" if IS_WINDOWS else "python3"

TRIGGER_TYPE = sys.argv[1] if len(sys.argv) > 1 else "G3"


# ── Methodology (mirrors meta-oracle-review.sh METHODOLOGY heredoc) ─

def print_methodology():
    print(r"""# Meta-Oracle 最后守门员 — 最高级审查方法论

你是 Meta-Oracle — Carror OS 的最高审查权威（最后守门员），独立于 Oracle。
你的审查权威高于 Oracle，使用完全不同的方法论（运行时验证 > 静态检查，对抗性审查 > 合规检查）。

## 通用审查原则（所有触发点适用）

1. **运行时验证 > 静态检查** — Oracle 的 auto-score.sh 基于文件存在性+正则匹配，容易系统性虚高。
   你应优先检查: 烟雾测试日志中的实际通过率、hook 生产验证的实际输出、error-dna.jsonl 中的真实频率。

2. **烟雾日志 > 文件存在性** — 文件注册了 ≠ 机制生效了。检查:
   - harness-smoke-test 的实际 pass/fail 计数
   - hook-production-verify 的实际阻断场景
   - error-dna.jsonl 中是否有真实的高频错误模式

3. **设计级盲区检查** — Oracle 的静态检查看不到的东西:
   - fail-open vs fail-closed 设计缺陷
   - ghost/goal 模式下的门禁降级
   - 正则表达式的匹配覆盖率（测试多种输入格式）

## 按触发点的专项审查
""")

    if TRIGGER_TYPE == "G1":
        print(r"""### G1: 架构决策终审
触发条件: 涉及 >=2 子系统 + 不可逆的架构变更
审查重点:
1. 跨子系统影响分析是否完整（所有下游子系统是否已识别）
2. 不可逆性评估（变更后能否回滚？回滚成本？）
3. 接口契约变更是否已同步到所有相关 feature
4. 是否与现有哲学/铁律冲突
5. source mirror 同步计划是否已就绪
""")
    elif TRIGGER_TYPE == "G2":
        print(r"""### G2: PRD/方案最后一步
触发条件: PRD 完整生命周期的最终阶段（Oracle 已 ACCEPT）
审查重点:
1. PRD 方案的 MECE 完整性（是否所有功能域已覆盖）
2. Oracle 的 ACCEPT 是否存在虚高（交叉验证 Oracle 评分依据）
3. 方案中的 NFR 数字是否有来源（避免 DG-02 类问题）
4. 下游 feature 的接口契约是否完整归属
5. 方案的可执行性（子任务拆分是否合理、依赖是否清晰）
""")
    elif TRIGGER_TYPE == "G3":
        print(r"""### G3: Oracle ACCEPT + 高分
触发条件: Oracle 给出 ACCEPT 且评分 >=8.5
审查重点:
1. 读取 Oracle 的评分输出，提取所有 >=8.5 分的维度
2. 对每个高分维度，寻找相反证据:
   - 烟雾测试中有无该维度的 FAIL？
   - error-dna 中有无该机制被绕过的记录？
   - 该机制的 regex/阈值 是否在边界场景下失效？
3. 产出 Meta-Oracle 纠正报告
""")
    elif TRIGGER_TYPE == "G4":
        print(r"""### G4: Release 门禁
触发条件: package-release.sh 执行前
审查重点:
1. source mirror 一致性检查（audit-hooks.sh --check-source-mirror）
2. 是否有未同步的治理文件变更
3. harness-smoke-test 全绿验证
4. 版本号一致性（VERSION.json <-> feature-registry.yaml <-> harness.yaml）
5. 是否有 PENDING_SYNC 标记的未发布变更
""")

    print(r"""
## 审查步骤

1. 确认触发类型（G1/G2/G3/G4），加载对应的专项审查清单
2. 收集证据: 运行烟雾测试、检查 error-dna、搜索设计文档
3. 交叉验证 Oracle 结论（如 Oracle 已给出裁决）
4. 寻找相反证据 — 刻意假设 Oracle 错误，尝试证伪
5. 产出 Meta-Oracle 裁决报告

## 输出格式

```
# Meta-Oracle 裁决报告 [{TRIGGER_TYPE}]

## 裁决
[Meta-Oracle: ACCEPT] / [Meta-Oracle: ADVISORY] / [Meta-Oracle: REJECT]

## Oracle 评分 vs Meta-Oracle 评估（如 Oracle 已评分）
| 维度 | Oracle 得分 | Meta-Oracle 评估 | 偏差 | 原因 |
|------|-----------|----------------|------|------|

## 关键发现
- [Finding 1]
- [Finding 2]

## 漏报发现（Oracle 未发现的问题）

## 虚高/虚低分析（如适用）

## 建议修正项
- [Action 1]
- [Action 2]

## 覆写理由（仅 REJECT 被覆写时需要）
[AI 如决定覆写 Meta-Oracle 的 REJECT 裁决，必须在此填写明确书面理由]
```

## 软门禁协议

1. ACCEPT -> 继续流程，记录到 .omc/state/meta-oracle-verdicts.md
2. ADVISORY -> 建议修正但不阻断，AI 自行判断
3. REJECT -> 强烈建议阻断，AI 必须有明确书面理由才能覆写
4. 连续 2 次 REJECT -> 升级为事实阻断，需人工介入
""")


# ── Scoring ─────────────────────────────────────────────────────────

def run_scoring():
    """Run the Python scorer (primary path) or fall back to bash scripts."""
    # Primary path: Python scorer
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from importlib import import_module
        scorer = import_module("meta-oracle-scorer")
        result = scorer.score_all(calibrated=True, meta_oracle=True)
        return result, True  # Python scoring used
    except ImportError as e:
        print(f"[警告] Python scorer import 失败: {e}", file=sys.stderr)

    # Fallback: bash scripts (macOS/Linux only)
    if IS_WINDOWS:
        print("[警告] bash fallback 不可用 (Windows)，跳过评分", file=sys.stderr)
        return None, False

    auto_score = os.path.join(SCRIPT_DIR, "auto-score.sh")
    score_ux = os.path.join(SCRIPT_DIR, "score-ux.sh")

    if not os.path.isfile(auto_score):
        print("[警告] auto-score.sh 不存在，跳过评分", file=sys.stderr)
        return None, False

    import subprocess
    try:
        output = subprocess.run(
            ["bash", auto_score, "--meta-oracle", "--calibrated"],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT,
        )
        print(output.stdout)
        if output.stderr:
            print(output.stderr, file=sys.stderr)

        # Extract gate verdict and score from bash output
        gate_match = None
        score_match = None
        for line in output.stdout.splitlines():
            if "[Meta-Oracle:" in line:
                gate_match = line.strip()
            if "C/E/G 加权总分" in line:
                import re
                m = re.search(r"(\d+\.\d+)", line)
                if m:
                    score_match = m.group(1)

        # UX score (bash)
        ux_score = "N/A"
        ux_max = "10"
        if os.path.isfile(score_ux):
            ux_output = subprocess.run(
                ["bash", score_ux], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT
            )
            try:
                ux_data = json.loads(ux_output.stdout.splitlines()[-1])
                ux_score = ux_data["total"]["score"]
                ux_max = ux_data["total"]["max"]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        return {
            "aggregate": {
                "weighted_score_10": float(score_match) if score_match else 0,
                "gate_verdict": gate_match or "N/A",
            },
            "ux_score": ux_score,
            "ux_max": ux_max,
        }, False

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"[警告] bash scoring 失败: {e}", file=sys.stderr)
        return None, False


# ── Verdict Writing ─────────────────────────────────────────────────

def write_verdict(gate_verdict, weighted_score, ux_score, ux_max):
    """Write verdict entry to meta-oracle-verdicts.md (cross-platform)."""
    os.makedirs(STATE_DIR, exist_ok=True)
    verdicts_path = os.path.join(STATE_DIR, "meta-oracle-verdicts.md")
    verdict_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ux_str = f"{ux_score}/{ux_max}" if ux_score is not None else "N/A"
    entry = (
        f"[{verdict_date}] [{TRIGGER_TYPE}] [{gate_verdict}] "
        f"— C/E/G 加权: {weighted_score}/10 | UX 独立: {ux_str}\n"
    )

    if os.path.isfile(verdicts_path):
        with open(verdicts_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Insert after header (line 0) + blank line (line 1) -> position 2
        lines.insert(2, entry)
        with open(verdicts_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        with open(verdicts_path, "a", encoding="utf-8") as f:
            f.write(entry)

    print(f"\n--- 裁决已留痕: {verdicts_path} ---")
    print(f"四维打分体系已就绪 | 权威等级: 高于 Oracle | 门禁: 软门禁")
    print(f"  方法论: 运行时验证 > 静态检查 | 对抗性审查 > 合规检查")
    print(f"  UX 维度: 独立评分, 不参与 C/E/G 的 8.6/10 门禁判定")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print(f"=== Meta-Oracle 最后守门员 [{TRIGGER_TYPE}] ===")
    print(f"审查状态文件: {os.path.join(STATE_DIR, 'meta-oracle-verdicts.md')}")
    print(f"触发类型: {TRIGGER_TYPE}\n")

    # Output methodology
    print_methodology()

    # Run scoring
    print("\n--- 运行四维打分 (C/E/G 加权聚合 + UX 独立) ---")
    result, used_python = run_scoring()

    if result is None:
        print("\n[警告] 评分不可用，仅输出方法论")
        print(f"  评分脚本: {PY_CMD} .claude/scripts/meta-oracle-scorer.py --calibrated --meta-oracle")
        return

    agg = result.get("aggregate", {})
    weighted_score = agg.get("weighted_score_10", 0)
    gate_verdict = agg.get("gate_verdict", "N/A")

    ux_score = result.get("ux_score") if not used_python else None
    ux_max = result.get("ux_max") if not used_python else None

    # For Python scoring, UX is embedded in result
    if used_python and "dimensions" in result:
        ux = result["dimensions"].get("UX", {})
        ux_score = ux.get("score", "N/A")
        ux_max = ux.get("max", 10)

    print(f"\n--- Meta-Oracle 门禁裁决 ---")
    print(f"C/E/G 加权总分: {weighted_score}/10")
    print(f"8.6 门禁判定:   {gate_verdict}")

    if ux_score is not None:
        print(f"\n--- UX 独立评分 ---")
        print(f"UX 得分: {ux_score}/{ux_max} (独立, 不参与 8.6 门禁)")

    # Write verdict
    write_verdict(gate_verdict, weighted_score, ux_score, ux_max)


if __name__ == "__main__":
    main()
