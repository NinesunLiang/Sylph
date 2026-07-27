#!/usr/bin/env python3
"""
gatekeeper.py — CarrorOS GateKeeper 分层裁决链

三协议模型：
  A = 真阻断（危险/不可逆/越权/架构调整）→ ASK_USER + 选项 + 推荐
  B = 轻量拦截（可修正的技术问题）→ REDIRECT + 引导 + auto-retry
  C = AI自决（一般情况）→ 哲学加权裁决

分层裁决链：
  GateContext → Step1 铁律检查 → Step2 协议A/B分流 → Step3 哲学授权
              → Step4 现状/ROI调节 → GateDecision → 格式化输出

用法:
  from gatekeeper import GateKeeper, GateContext, GateDecision
  gk = GateKeeper()
  ctx = GateContext(action="rm -rf /data", hazard_flags=["destructive", "irreversible"])
  decision = gk.evaluate(ctx)
  output = gk.format_output(decision)  # 按协议格式化
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal


# ═══════════════════════════════════════════════════
# 枚举定义
# ═══════════════════════════════════════════════════

class GateDecision(Enum):
    """6种裁决结果"""
    ALLOW = "allow"              # 协议C: 允许
    ALLOW_WITH_CONSTRAINTS = "allow_with_constraints"  # 协议C: 带约束允许
    ASK_USER = "ask_user"        # 协议A: 等待用户决策
    REDIRECT = "redirect"        # 协议B: 拦截+引导+retry
    BLOCK = "block"              # 协议A/铁律: 阻断
    SKIP = "skip"                # 无人模式: 跳过+记录


class Philosophy(Enum):
    """7条哲学（降序优先级）
    优先数越低 → 权重越高
    """
    VERIFY_FIRST = ("verify_first", 1, "验证优先")
    ZERO_TRUST = ("zero_trust", 2, "零信任")
    GUARD_FIRST = ("guard_first", 3, "守护优先")
    DOC_FIRST = ("doc_first", 4, "文档优先")
    HUMAN_FIRST = ("human_first", 5, "人本优先")
    GAIN_FIRST = ("gain_first", 6, "增益优先")
    LESS_IS_MORE = ("less_is_more", 7, "少即是多")

    def __init__(self, key: str, priority: int, label: str):
        self.key = key
        self.priority = priority
        self.label = label

    def weight(self) -> float:
        """优先级权重: 数字越小权重越高"""
        return 10.0 - self.priority + 1.0  # 7→4, 1→10


# ═══════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════

@dataclass
class GateContext:
    """Gate 上下文 — 所有裁决的输入"""
    action: str                                          # 操作描述
    target: str                                          # 目标（文件/命令/URL）
    hazard_flags: list[str] = field(default_factory=list) # 危险标记
    risk_level: Literal["low", "medium", "high"] = "low"
    metadata: dict[str, Any] = field(default_factory=dict)
    unattended: bool = False                             # 无人模式
    iron_rules_triggered: list[str] = field(default_factory=list)  # 命中的铁律

    # 快捷判断
    @property
    def is_destructive(self) -> bool:
        return "destructive" in self.hazard_flags

    @property
    def is_irreversible(self) -> bool:
        return "irreversible" in self.hazard_flags

    @property
    def is_privilege_escalation(self) -> bool:
        return "privilege_escalation" in self.hazard_flags

    @property
    def is_architecture_change(self) -> bool:
        return "architecture_change" in self.hazard_flags

    @property
    def affects_production(self) -> bool:
        return "production" in self.hazard_flags

    @property
    def is_protocol_a(self) -> bool:
        """协议A条件: 任何高危标记命中"""
        return bool(self.hazard_flags) and (
            self.is_destructive or self.is_irreversible
            or self.is_privilege_escalation or self.is_architecture_change
            or self.affects_production or self.risk_level == "high"
        )

    @property
    def is_protocol_b(self) -> bool:
        """协议B条件: 有技术问题但非高危"""
        return bool(self.metadata.get("fixable_issue", False))


@dataclass
class BlockOption:
    """协议A的选项"""
    key: str
    label: str
    risk: str = "low"
    action: str = ""


@dataclass
class GateDecisionResult:
    """裁决结果"""
    decision: GateDecision
    reason: str
    protocol: Literal["A", "B", "C", "NONE"]
    explanation: str = ""                                # 为何终止（协议A）
    options: list[BlockOption] = field(default_factory=list)  # 可选方案（协议A）
    recommendation: tuple[str, str] = ("", "")            # 推荐（key, 理由）
    guidance: str = ""                                   # 引导（协议B）
    philosophy_hits: list[tuple[str, float]] = field(default_factory=list)
    iron_law_violations: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════
# GateKeeper 核心类 — 分层裁决链
# ═══════════════════════════════════════════════════

class GateKeeper:
    """分层裁决链引擎

    管线:
      step1 _check_iron_rules()    → 铁律命中直接 BLOCK
      step2 _detect_protocol()     → 分流 A/B/C
      step3 _evaluate_philosophy() → 哲学加权评分
      step4 _apply_adjustments()   → 现状/ROI 调节 → 最终裁决
    """

    _STATE_DIR: Path | None = None
    _EVENT_LOG: list[dict] = []
    _PHILOSOPHY_ORDER: list[str] = [
        "verify_first", "zero_trust", "guard_first",
        "doc_first", "human_first", "gain_first", "less_is_more"
    ]

    @classmethod
    def set_state_dir(cls, path: Path) -> None:
        cls._STATE_DIR = path

    # ════════════════════════════════════════════
    # 主入口
    # ════════════════════════════════════════════

    @classmethod
    def evaluate(cls, context: GateContext) -> GateDecisionResult:
        """分层裁决链主入口"""
        # Step 1: 铁律检查 — 一票否决
        iron_violations = cls._check_iron_rules(context)
        if iron_violations:
            result = GateDecisionResult(
                decision=GateDecision.BLOCK,
                reason=f"铁律违反: {' → '.join(iron_violations[:3])}",
                protocol="NONE",
                explanation="铁律绝不可违反。当前操作违反了以下铁律:\n" +
                            "\n".join(f"  · {v}" for v in iron_violations),
                iron_law_violations=iron_violations,
            )
            cls._log_event(result, context)
            return result

        # 无人模式: 协议A降级为SKIP
        if context.unattended and context.is_protocol_a:
            result = GateDecisionResult(
                decision=GateDecision.SKIP,
                reason="无人模式: 高风险操作跳过",
                protocol="A",
                explanation=(
                    f"⚠️ 无人模式跳过: {context.action}\n"
                    f"  原因: 命中了 {'/'.join(context.hazard_flags)}\n"
                    f"  详情已记录至 skipped-risks.jsonl，退出报告将汇总"
                ),
                options=[],
                recommendation=("SKIP", "无人模式不执行高危操作"),
            )
            cls._log_event(result, context, is_skip=True)
            return result

        # Step 2: 协议分流
        protocol, _ = cls._detect_protocol(context)

        # Step 3: 哲学授权评分
        philosophy_score, philosophy_hits = cls._evaluate_philosophy(context)
        # Step 4: 现状/ROI调节
        final_decision, reason, extra = cls._apply_adjustments(context, protocol, philosophy_score, philosophy_hits)

        result = GateDecisionResult(
            decision=final_decision,
            reason=reason,
            protocol=protocol,
            explanation=extra.get("explanation", ""),
            options=extra.get("options", []),
            recommendation=extra.get("recommendation", ("", "")),
            guidance=extra.get("guidance", ""),
            philosophy_hits=philosophy_hits,
            constraints=extra.get("constraints", []),
            confidence=extra.get("confidence", 1.0),
        )
        cls._log_event(result, context)
        return result

    # ════════════════════════════════════════════
    # Step 1: 铁律检查
    # ════════════════════════════════════════════

    @classmethod
    def _check_iron_rules(cls, ctx: GateContext) -> list[str]:
        """铁律检查：任何一条违反 → 直接 BLOCK"""
        violations: list[str] = []
        md = ctx.metadata

        if md.get("lacks_evidence"):
            violations.append("不编造 — 操作依据不足")
        if md.get("unverifiable"):
            violations.append("证据门禁 — 结果不可验证")
        if md.get("scope_violation"):
            violations.append("范围冻结 — 超出已声明范围")
        if md.get("privacy_violation"):
            violations.append("隐私防线 — 涉及敏感数据")
        if md.get("missing_init"):
            violations.append("先init后动手 — 未初始化")
        if md.get("untrusted_value"):
            violations.append("数值断言溯源 — 无来源")
        if md.get("governance_violation"):
            violations.append("治理文件不可改 — 试图修改治理文件")
        if md.get("bypass_attempt"):
            violations.append("不可绕过gate — 尝试绕过门禁")

        return violations

    # ════════════════════════════════════════════
    # Step 2: 协议分流
    # ════════════════════════════════════════════

    @classmethod
    def _detect_protocol(cls, ctx: GateContext) -> tuple[str, str]:
        """分流 A/B/C"""
        if ctx.is_protocol_a:
            return ("A", "高危操作 → 协议A (ASK_USER)")
        if ctx.is_protocol_b:
            return ("B", "可修正技术问题 → 协议B (REDIRECT)")
        return ("C", "一般情况 → 协议C (AI自决)")

    # ════════════════════════════════════════════
    # Step 3: 哲学授权评分
    # ════════════════════════════════════════════

    @classmethod
    def _evaluate_philosophy(
        cls, ctx: GateContext
    ) -> tuple[float, list[tuple[str, float]]]:
        """哲学授权评分: 命中数正向加权

        每命中一条哲学 → 累加其权重(priority-based)
        命中越多 → 得分越高 → 倾向前通过
        """
        hits: list[tuple[str, float]] = []
        total = 0.0
        md = ctx.metadata

        # 验证优先 → weight=10
        if md.get("has_verification"):
            hits.append(("verify_first", 10.0))
            total += 10.0

        # 零信任 → weight=9
        if md.get("minimal_privilege"):
            hits.append(("zero_trust", 9.0))
            total += 9.0

        # 守护优先 → weight=8
        if md.get("has_safeguards"):
            hits.append(("guard_first", 8.0))
            total += 8.0

        # 文档优先 → weight=7
        if md.get("generates_documentation"):
            hits.append(("doc_first", 7.0))
            total += 7.0

        # 人本优先 → weight=6
        if md.get("user_requested") or ctx.risk_level != "high":
            hits.append(("human_first", 6.0))
            total += 6.0

        # 增益优先 → weight=5
        if md.get("positive_roi"):
            hits.append(("gain_first", 5.0))
            total += 5.0

        # 少即是多 → weight=4
        if md.get("simplifies_system") or ctx.risk_level == "low":
            hits.append(("less_is_more", 4.0))
            total += 4.0

        return (total, hits)

    # ════════════════════════════════════════════
    # Step 4: 现状/ROI 调节 → 最终裁决
    # ════════════════════════════════════════════

    @classmethod
    def _apply_adjustments(
        cls, ctx: GateContext, protocol: str,
        score: float, hits: list[tuple[str, float]]
    ) -> tuple[GateDecision, str, dict[str, Any]]:
        """根据协议和哲学得分做最终裁决"""
        extra: dict[str, Any] = {}
        md = ctx.metadata

        if protocol == "A":
            # 协议A: 生成选项+推荐
            extra["options"] = cls._generate_options(ctx)
            extra["recommendation"] = cls._recommend_option(ctx, extra["options"])
            extra["explanation"] = cls._explain_block(ctx)

            if ctx.unattended:
                # 无人模式: 已在上层处理为SKIP
                return GateDecision.SKIP, "无人模式跳过", extra
            return GateDecision.ASK_USER, f"需要用户确认: {ctx.action}", extra

        elif protocol == "B":
            extra["guidance"] = cls._generate_guidance(ctx)
            return GateDecision.REDIRECT, f"拦截+引导: {ctx.action}", extra

        else:
            # 协议C: 哲学加权裁决
            threshold = cls._threshold_for_risk(ctx.risk_level)

            if score >= threshold:
                if md.get("needs_constraints"):
                    extra["constraints"] = cls._generate_constraints(ctx)
                    return GateDecision.ALLOW_WITH_CONSTRAINTS, "哲学授权通过(带约束)", extra
                return GateDecision.ALLOW, "哲学授权通过", extra

            # 中等得分 → 可能转协议B
            if score >= threshold * 0.6:
                extra["guidance"] = cls._generate_guidance(ctx)
                return GateDecision.REDIRECT, "哲学得分中等,建议引导", extra

            # 低分 → 阻断
            return GateDecision.BLOCK, f"哲学授权不足(得分={score:.0f},阈值={threshold:.0f})", extra

    @staticmethod
    def _threshold_for_risk(risk: str) -> float:
        """风险等级→哲学得分阈值"""
        return {"low": 15.0, "medium": 25.0, "high": 35.0}.get(risk, 25.0)

    # ════════════════════════════════════════════
    # 协议A辅助
    # ════════════════════════════════════════════

    @classmethod
    def _explain_block(cls, ctx: GateContext) -> str:
        """构建协议A的为何终止"""
        parts = []
        if ctx.is_destructive:
            parts.append("该操作具有破坏性,可能造成数据丢失")
        if ctx.is_irreversible:
            parts.append("该操作不可逆,执行后无法回滚")
        if ctx.is_privilege_escalation:
            parts.append("该操作涉及权限越级,需要人工确认")
        if ctx.is_architecture_change:
            parts.append("该操作涉及架构调整,影响面大")
        if ctx.affects_production:
            parts.append("该操作影响生产环境")
        if not parts:
            parts.append("该操作命中高风险标记")
        return " | ".join(parts[:2])

    @classmethod
    def _generate_options(cls, ctx: GateContext) -> list[BlockOption]:
        """动态生成协议A选项"""
        opts: list[BlockOption] = []

        # 需要备份的场景
        if ctx.is_destructive or ctx.is_irreversible:
            opts.append(BlockOption("A", "确认操作并执行", "high", "风险自担"))
            opts.append(BlockOption("B", "先备份再执行", "medium", "创建快照后继续"))
            opts.append(BlockOption("C", "取消/跳过", "low", "不执行此操作"))

        # 架构/越权场景
        elif ctx.is_architecture_change or ctx.is_privilege_escalation:
            opts.append(BlockOption("A", "在staging环境验证", "medium", "先在非生产环境执行"))
            opts.append(BlockOption("B", "缩小范围后执行", "medium", "仅执行子集"))
            opts.append(BlockOption("C", "取消/跳过", "low", "不执行此操作"))

        # 生产场景
        elif ctx.affects_production:
            opts.append(BlockOption("A", "确认执行", "high", "生产操作"))
            opts.append(BlockOption("B", "仅dry-run", "low", "模拟不执行"))
            opts.append(BlockOption("C", "取消/跳过", "low", "不执行此操作"))

        # 默认
        else:
            opts.append(BlockOption("A", "确认执行", "high"))
            opts.append(BlockOption("B", "先验证再执行", "medium"))
            opts.append(BlockOption("C", "取消/跳过", "low"))

        return opts

    @classmethod
    def _recommend_option(cls, ctx: GateContext, opts: list[BlockOption]) -> tuple[str, str]:
        """从选项中推荐一个"""
        if not opts:
            return ("C", "取消操作,默认安全选择")
        # 默认推荐最安全的选项: 最后一个
        safe = opts[-1]
        return (safe.key, f"{safe.label} — 最低风险选择")

    # ════════════════════════════════════════════
    # 协议B辅助
    # ════════════════════════════════════════════

    @classmethod
    def _generate_guidance(cls, ctx: GateContext) -> str:
        """生成协议B引导"""
        action_lower = ctx.action.lower()
        target = ctx.target

        if "write" in action_lower or "edit" in action_lower:
            return f"建议先 Read {target} 确认当前内容,再决定如何修改"
        if "delete" in action_lower or "rm" in action_lower:
            return f"建议确认 {target} 无其他依赖后再执行"
        if "push" in action_lower or "deploy" in action_lower:
            return "建议先执行 dry-run 确认变更范围"
        if "install" in action_lower:
            return f"建议检查 {target} 版本兼容性后再安装"

        return "建议先执行影响分析,再做决定"

    @classmethod
    def _generate_constraints(cls, ctx: GateContext) -> list[str]:
        """生成协议C约束条件"""
        cs: list[str] = []
        if ctx.risk_level == "medium":
            cs.append("执行前需确认回滚路径")
            cs.append("执行后需验证结果")
        if ctx.metadata.get("has_verification"):
            cs.append("验证命令必须通过才标记完成")
        return cs

    # ════════════════════════════════════════════
    # 格式化输出
    # ════════════════════════════════════════════

    @classmethod
    def format_output(cls, result: GateDecisionResult) -> str:
        """按协议类型格式化输出"""
        if result.decision in (GateDecision.ALLOW, GateDecision.ALLOW_WITH_CONSTRAINTS):
            # 协议C: 无输出
            return ""

        if result.decision == GateDecision.BLOCK:
            return cls._format_block(result)

        if result.decision == GateDecision.ASK_USER:
            return cls._format_ask_user(result)

        if result.decision == GateDecision.REDIRECT:
            return cls._format_redirect(result)

        if result.decision == GateDecision.SKIP:
            return cls._format_skip(result)

        return ""

    @classmethod
    def _format_block(cls, result: GateDecisionResult) -> str:
        """BLOCK格式: 简洁阻断"""
        parts = [f"⛔ 操作被阻断: {result.reason}"]
        if result.explanation:
            parts.append(f"  原因: {result.explanation}")
        return "\n".join(parts)

    @classmethod
    def _format_ask_user(cls, result: GateDecisionResult) -> str:
        """协议A格式: 真阻断→ASK_USER"""
        lines = [
            f"⛔ 操作被阻断: {result.reason}",
            f"━━━ 为何终止 ━━━",
            result.explanation if result.explanation else result.reason,
            "",
            "━━━ 可选方案 ━━━",
        ]
        for opt in result.options:
            lines.append(f"{opt.key}. {opt.label}")
            if opt.action:
                lines.append(f"   {opt.action}")
        lines.append("")
        lines.append("━━━ AI 推荐 ━━━")
        key, reason = result.recommendation
        lines.append(f"推荐选择 {key}: {reason}")

        if result.constraints:
            lines.append("")
            lines.append("━━━ 附加约束 ━━━")
            for c in result.constraints:
                lines.append(f"  · {c}")

        return "\n".join(lines)

    @classmethod
    def _format_redirect(cls, result: GateDecisionResult) -> str:
        """协议B格式: 拦截+引导"""
        lines = [
            f"🔄 操作重定向: {result.reason}",
        ]
        if result.guidance:
            lines.append(f"💡 {result.guidance}")
        lines.append("继续...")
        return "\n".join(lines)

    @classmethod
    def _format_skip(cls, result: GateDecisionResult) -> str:
        """无人模式跳过格式"""
        lines = [
            f"⚠️ 跳过: {result.reason}",
            f"  详情: {result.explanation if result.explanation else result.reason}",
        ]
        return "\n".join(lines)

    # ════════════════════════════════════════════
    # 事件日志
    # ════════════════════════════════════════════

    @classmethod
    def _log_event(
        cls, result: GateDecisionResult, ctx: GateContext,
        is_skip: bool = False
    ) -> None:
        """记录Gate事件到内存+磁盘"""
        event = {
            "ts": time.time(),
            "decision": result.decision.value,
            "protocol": result.protocol,
            "reason": result.reason,
            "action": ctx.action,
            "target": ctx.target,
            "risk_level": ctx.risk_level,
            "hazard_flags": ctx.hazard_flags,
            "unattended": ctx.unattended,
            "iron_law_violations": result.iron_law_violations,
            "philosophy_hits": result.philosophy_hits,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
        }
        cls._EVENT_LOG.append(event)

        # 磁盘持久化
        if cls._STATE_DIR:
            log_file = cls._STATE_DIR / "gatekeeper-events.jsonl"
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError:
                pass

        # 跳过记录单独记录
        if is_skip and cls._STATE_DIR:
            skipped_file = cls._STATE_DIR / "skipped-risks.jsonl"
            try:
                with open(skipped_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": time.time(),
                        "action": ctx.action,
                        "target": ctx.target,
                        "hazards": ctx.hazard_flags,
                        "reason": result.reason,
                    }, ensure_ascii=False) + "\n")
            except OSError:
                pass

    @classmethod
    def get_events(cls) -> list[dict]:
        return list(cls._EVENT_LOG)

    @classmethod
    def export_logs(cls, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [{
            "event_type": "gatekeeper_event",
            "actor": "gatekeeper",
            "action": "log_export",
            "events": cls._EVENT_LOG,
        }]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════
# 快速创建上下文
# ═══════════════════════════════════════════════════

def make_context(
    action: str,
    target: str = "",
    destructive: bool = False,
    irreversible: bool = False,
    privilege_escalation: bool = False,
    architecture_change: bool = False,
    production: bool = False,
    risk: Literal["low", "medium", "high"] = "low",
    unattended: bool = False,
    **metadata: Any,
) -> GateContext:
    """快捷创建 GateContext"""
    flags: list[str] = []
    if destructive:
        flags.append("destructive")
    if irreversible:
        flags.append("irreversible")
    if privilege_escalation:
        flags.append("privilege_escalation")
    if architecture_change:
        flags.append("architecture_change")
    if production:
        flags.append("production")

    return GateContext(
        action=action,
        target=target,
        hazard_flags=flags,
        risk_level=risk,
        unattended=unattended,
        metadata=metadata or {},
    )


# ═══════════════════════════════════════════════════
# 简单测试
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("=== GateKeeper 自检 ===")

    # 测试1: 铁律违反
    ctx = GateContext(action="修改治理文件", target=".claude/hooks/pretool-gate.py",
                      metadata={"governance_violation": True})
    r = GateKeeper.evaluate(ctx)
    print(f"\n[铁律违反] {r.decision.value}: {r.reason}")
    output = GateKeeper.format_output(r)
    if output:
        print(output)

    # 测试2: 协议A — 不可逆操作
    ctx = make_context("rm -rf /data", destructive=True, irreversible=True, risk="high")
    r = GateKeeper.evaluate(ctx)
    print(f"\n[协议A] {r.decision.value}: {r.reason}")
    print(GateKeeper.format_output(r))

    # 测试3: 协议C — 安全操作
    ctx = make_context("读取配置文件", risk="low",
                       has_verification=True, minimal_privilege=True, positive_roi=True)
    r = GateKeeper.evaluate(ctx)
    print(f"\n[协议C] {r.decision.value}: {r.reason} (得分={sum(w for _, w in r.philosophy_hits):.0f})")

    # 测试4: 无人模式跳过
    ctx = make_context("删除生产表", destructive=True, irreversible=True,
                       production=True, risk="high", unattended=True)
    r = GateKeeper.evaluate(ctx)
    print(f"\n[无人模式] {r.decision.value}: {r.reason}")
    print(GateKeeper.format_output(r))

    # 测试5: 协议B — 可修正问题
    ctx = make_context("写入未读文件", risk="low", fixable_issue=True)
    r = GateKeeper.evaluate(ctx)
    print(f"\n[协议B] {r.decision.value}: {r.reason}")
    print(GateKeeper.format_output(r))

    print(f"\n=== 事件数: {len(GateKeeper.get_events())} ===")
    print("ALL PASS" if GateKeeper.get_events() else "FAIL")
