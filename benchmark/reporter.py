"""CarrorOS Benchmark — 报告生成器

聚合 experiment runs，生成统计分析报告。
"""

from __future__ import annotations
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from schemas import ExperimentRun, Budget, Routing, Context, Recovery, Verification, FailureClass, AggregateMetrics


def _bootstrap_ci(values: list[float], n_iter: int = 10000, ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap confidence interval for the mean."""
    if len(values) < 2:
        return (float("nan"), float("nan"))
    means = []
    n = len(values)
    for _ in range(n_iter):
        sample = [random.choice(values) for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    alpha = (1.0 - ci) / 2.0
    lower = means[int(alpha * n_iter)]
    upper = means[int((1.0 - alpha) * n_iter)]
    return (lower, upper)


def _mcnemar_test(
    pair_counts: tuple[int, int, int, int]
) -> float:
    """McNemar's test for paired binary outcomes.

    Args: (both_pass, full_only, bare_only, both_fail)
    Returns p-value.
    """
    _, b, c, _ = pair_counts
    n = b + c
    if n == 0:
        return 1.0
    # Continuity corrected McNemar
    chi2 = (abs(b - c) - 1) ** 2 / n
    # 1 degree of freedom
    # Approximation using chi2 distribution
    from scipy.stats import chi2
    try:
        return 1.0 - chi2.cdf(chi2, 1)
    except ImportError:
        # No scipy? Simple approximation
        return chi2 / (chi2 + 4.0) * 2.0  # rough


class Reporter:
    """Aggregates experiment runs and generates reports."""

    def __init__(self, runs_dir: Path):
        self.runs_dir = runs_dir
        self.runs: list[ExperimentRun] = []
        self._load_runs()

    def _load_runs(self) -> None:
        """Load all experiment runs from the runs directory."""
        for run_file in sorted(self.runs_dir.glob("**/*.json")):
            try:
                data = json.loads(run_file.read_text(encoding="utf-8"))
                run = self._dict_to_run(data)
                self.runs.append(run)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  ⚠  Skipping {run_file}: {e}")

    def _dict_to_run(self, d: dict) -> ExperimentRun:
        identity = d.get("identity", {})
        budget = d.get("budget", {})
        routing = d.get("routing", {})
        ctx = d.get("context", {})
        recovery = d.get("recovery", {})
        verification = d.get("verification", {})
        result = d.get("result", {})

        return ExperimentRun(
            run_id=identity.get("run_id", ""),
            task_id=identity.get("task_id", ""),
            timestamp=identity.get("timestamp", ""),
            stack=identity.get("stack", "claude-code"),
            model=identity.get("model", ""),
            model_revision=identity.get("model_revision", ""),
            provider=identity.get("provider", ""),
            group=identity.get("group", "A_bare"),
            seed=identity.get("seed", 0),
            repository_commit=identity.get("repository_commit", ""),
            budget=Budget(
                input_tokens=budget.get("input_tokens", 0),
                output_tokens=budget.get("output_tokens", 0),
                cached_tokens=budget.get("cached_tokens", 0),
                max_tool_calls=budget.get("max_tool_calls", 0),
                actual_tool_calls=budget.get("actual_tool_calls", 0),
                wall_time_seconds=budget.get("wall_time_seconds", 0),
                cost_usd=budget.get("cost_usd", 0.0),
            ),
            routing=Routing(
                expected_workflow=routing.get("expected_workflow", ""),
                selected_workflow=routing.get("selected_workflow", ""),
                first_path_correct=routing.get("first_path_correct", False),
                route_switches=routing.get("route_switches", 0),
                irrelevant_docs_loaded=routing.get("irrelevant_docs_loaded", 0),
                time_to_first_correct_hypothesis_s=routing.get("time_to_first_correct_hypothesis_s", 0.0),
                tool_calls_before_first_evidence=routing.get("tool_calls_before_first_evidence", 0),
            ),
            context=Context(
                context_peak_ratio=ctx.get("context_peak_ratio", 0.0),
                checkpoints=ctx.get("checkpoints", 0),
                lossless_compactions=ctx.get("lossless_compactions", 0),
                l5_lossy_compactions=ctx.get("l5_lossy_compactions", 0),
                stable_prefix=ctx.get("stable_prefix", False),
                cache_hit_rate=ctx.get("cache_hit_rate"),
                artifacts_written=ctx.get("artifacts_written", 0),
                artifacts_missing=ctx.get("artifacts_missing", 0),
                preview_stability=ctx.get("preview_stability", 1.0),
            ),
            recovery=Recovery(
                forced_interruptions=recovery.get("forced_interruptions", 0),
                successful_resumes=recovery.get("successful_resumes", 0),
                duplicate_actions_after_resume=recovery.get("duplicate_actions_after_resume", 0),
                stale_state_events=recovery.get("stale_state_events", 0),
                fault_injections=recovery.get("fault_injections", 0),
                faults_recovered=recovery.get("faults_recovered", 0),
            ),
            verification=Verification(
                agent_claimed_complete=verification.get("agent_claimed_complete", False),
                visible_tests_pass=verification.get("visible_tests_pass", False),
                hidden_tests_pass=verification.get("hidden_tests_pass", False),
                regression_pass=verification.get("regression_pass", False),
                evidence_complete=verification.get("evidence_complete", False),
                verify_override_attempted=verification.get("verify_override_attempted", False),
                verify_override_escaped=verification.get("verify_override_escaped", False),
                governance_violation=verification.get("governance_violation", False),
                constraints_pass=verification.get("constraints_pass", False),
            ),
            verified_success=result.get("verified_success", False),
            silent_false_success=result.get("silent_false_success", False),
            human_interventions=result.get("human_interventions", 0),
            failure_class=result.get("failure_class", "none"),
            failure_detail=result.get("failure_detail", ""),
            session_transcript_path=result.get("session_transcript_path", ""),
        )

    def compute_metrics(self) -> AggregateMetrics:
        """Compute aggregate metrics across all runs."""
        metrics = AggregateMetrics()
        metrics.total_runs = len(self.runs)

        if not self.runs:
            return metrics

        # By group
        by_group: dict[str, list[ExperimentRun]] = {}
        by_difficulty: dict[str, list[ExperimentRun]] = {}

        for run in self.runs:
            g = run.group.value if hasattr(run.group, 'value') else str(run.group)
            by_group.setdefault(g, []).append(run)

        # Compute overall rates
        successes = [r for r in self.runs if r.verified_success]
        hard_tasks = [r for r in self.runs if getattr(r, '_difficulty', '') == 'hard']
        silent_false = [r for r in self.runs if r.silent_false_success]
        regressions = [r for r in self.runs if not r.verification.regression_pass]
        first_correct = [r for r in self.runs if r.routing.first_path_correct]

        metrics.verified_success_rate = len(successes) / len(self.runs) if self.runs else 0.0
        metrics.hard_task_success_rate = (
            len([r for r in hard_tasks if r.verified_success]) / len(hard_tasks)
            if hard_tasks else 0.0
        )
        metrics.first_path_correct_rate = len(first_correct) / len(self.runs) if self.runs else 0.0
        metrics.silent_false_success_rate = len(silent_false) / len(self.runs) if self.runs else 0.0
        metrics.regression_escape_rate = len(regressions) / len(self.runs) if self.runs else 0.0

        # Cost per success
        total_cost = sum(r.budget.cost_usd for r in self.runs)
        metrics.dollar_per_verified_success = (
            total_cost / len(successes) if successes else float("inf")
        )

        # Per-group metrics
        for group_name, group_runs in sorted(by_group.items()):
            g_successes = [r for r in group_runs if r.verified_success]
            g_cost = sum(r.budget.cost_usd for r in group_runs)
            metrics.groups[group_name] = {
                "count": len(group_runs),
                "verified_success": len(g_successes),
                "verified_success_rate": len(g_successes) / len(group_runs) if group_runs else 0.0,
                "total_cost": g_cost,
                "avg_cost": g_cost / len(group_runs) if group_runs else 0.0,
                "cost_per_success": g_cost / len(g_successes) if g_successes else float("inf"),
                "avg_tool_calls": sum(r.budget.actual_tool_calls for r in group_runs) / len(group_runs) if group_runs else 0.0,
            }

        return metrics

    def generate_capability_report(self, output_path: Path | None = None) -> str:
        """Generate capability amplification report."""
        metrics = self.compute_metrics()

        lines = [
            "# CarrorOS 能力放大测试报告",
            "",
            f"> 生成时间: {datetime.now(timezone.utc).isoformat()}",
            f"> 总运行次数: {metrics.total_runs}",
            "",
            "---",
            "",
            "## 总体指标",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| Verified Success Rate | {metrics.verified_success_rate:.1%} |",
            f"| Hard Task Success Rate | {metrics.hard_task_success_rate:.1%} |",
            f"| First Path Correct Rate | {metrics.first_path_correct_rate:.1%} |",
            f"| Silent False Success Rate | {metrics.silent_false_success_rate:.1%} |",
            f"| Regression Escape Rate | {metrics.regression_escape_rate:.1%} |",
            f"| Cost / Verified Success | ${metrics.dollar_per_verified_success:.2f} |",
            "",
            "## 分组对比",
            "",
            "| 组 | N | Success Rate | Avg Cost | Cost/Success | Avg Tool Calls |",
            "|----|---|-------------|----------|--------------|----------------|",
        ]

        for g, data in sorted(metrics.groups.items()):
            lines.append(
                f"| {g} | {data['count']} | "
                f"{data['verified_success_rate']:.1%} | "
                f"${data['avg_cost']:.2f} | "
                f"${data['cost_per_success']:.2f} | "
                f"{data['avg_tool_calls']:.1f} |"
            )

        # Amplification
        if "A_bare" in metrics.groups and "E_full" in metrics.groups:
            bare_rate = metrics.groups["A_bare"]["verified_success_rate"]
            full_rate = metrics.groups["E_full"]["verified_success_rate"]
            amplification = full_rate / bare_rate if bare_rate > 0 else float("inf")
            absolute_gain = full_rate - bare_rate
            lines += [
                "",
                "## 能力放大",
                "",
                f"| 指标 | 裸模型 (A) | 完整系统 (E) | 放大倍数 |",
                f"|------|-----------|-------------|---------|",
                f"| Verified Success Rate | {bare_rate:.1%} | {full_rate:.1%} | {amplification:.2f}× |",
                f"| 绝对提升 | — | — | {absolute_gain:.1%} |",
            ]

        # Ablation progression
        lines += [
            "",
            "## 组件消融梯度",
            "",
            "| 过渡 | 新增组件 | 回答的问题 |",
            "|------|----------|-----------|",
        ]
        transitions = [
            ("A → B", "AGENTS + CLAUDE.md", "入口文档是否提升协议遵守率？"),
            ("B → C", "INDEX + kernel", "路由和约束是否提升路径正确率？"),
            ("C → D", "Context Engine", "上下文管理是否提升持续执行能力？"),
            ("D → E", "Harness + Hooks", "软约束转为硬执行是否提升完成率？"),
        ]
        for trans, comp, question in transitions:
            lines.append(f"| {trans} | {comp} | {question} |")

        # Failure taxonomy
        failure_counts: dict[str, int] = {}
        for run in self.runs:
            fc = run.failure_class.value if hasattr(run.failure_class, 'value') else str(run.failure_class)
            failure_counts[fc] = failure_counts.get(fc, 0) + 1

        lines += [
            "",
            "## 失败分类",
            "",
            "| 失败类型 | 次数 | 占比 |",
            "|----------|------|------|",
        ]
        for fc, count in sorted(failure_counts.items()):
            lines.append(f"| {fc} | {count} | {count/len(self.runs):.1%} |")

        report = "\n".join(lines)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report + "\n", encoding="utf-8")

        return report

    def generate_long_running_report(self, output_path: Path | None = None) -> str:
        """Generate long-running stability report."""
        lines = [
            "# CarrorOS 长任务稳定测试报告",
            "",
            f"> 生成时间: {datetime.now(timezone.utc).isoformat()}",
            f"> 总运行次数: {len(self.runs)}",
            "",
            "---",
            "",
            "## 会话轮次分布",
            "",
            "| 档位 | Turn 范围 | 样本数 |",
            "|------|-----------|--------|",
        ]

        # Sort by turn count
        by_turns = {"S30": 0, "S60": 0, "S100": 0, "S_resume": 0}
        for run in self.runs:
            tc = run.budget.actual_tool_calls
            if tc >= 80:
                by_turns["S100"] += 1
            elif tc >= 50:
                by_turns["S60"] += 1
            elif tc >= 30:
                by_turns["S30"] += 1

        for tier in ["S30", "S60", "S100"]:
            lines.append(f"| {tier} | — | {by_turns[tier]} |")
        lines.append(f"| S_resume | 跨会话恢复 | {sum(1 for r in self.runs if r.recovery.successful_resumes > 0)} |")

        # Recovery metrics
        total_interruptions = sum(r.recovery.forced_interruptions for r in self.runs)
        total_resumes = sum(r.recovery.successful_resumes for r in self.runs)
        total_duplicates = sum(r.recovery.duplicate_actions_after_resume for r in self.runs)
        total_faults = sum(r.recovery.fault_injections for r in self.runs)
        total_recovered = sum(r.recovery.faults_recovered for r in self.runs)
        total_compactions = sum(r.context.lossless_compactions + r.context.l5_lossy_compactions for r in self.runs)
        total_l5 = sum(r.context.l5_lossy_compactions for r in self.runs)

        lines += [
            "",
            "## 恢复与故障",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 强制中断次数 | {total_interruptions} |",
            f"| 成功恢复次数 | {total_resumes} |",
            f"| 恢复后重复操作 | {total_duplicates} |",
            f"| 故障注入 | {total_faults} |",
            f"| 故障恢复 | {total_recovered} |",
            f"| 恢复成功率 | {total_recovered/total_faults:.1%} |" if total_faults else "| 恢复成功率 | N/A |",
        ]

        lines += [
            "",
            "## 上下文健康",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 压缩次数 | {total_compactions} |",
            f"| L5 有损压缩占比 | {total_l5/total_compactions:.1%} |" if total_compactions else "| L5 有损压缩占比 | 0 |",
        ]

        report = "\n".join(lines)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report + "\n", encoding="utf-8")

        return report
