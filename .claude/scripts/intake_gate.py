#!/usr/bin/env python3
"""
intake_gate.py — IntakeGate 任务入口分级裁决

CarrorOS 第三轮迭代 1.md 定义：
IntakeGate 是任务进入治理系统的唯一入口。
只做 5 件事：
1. 解析用户目标
2. 识别风险标签
3. 识别 scope 初始边界
4. 判定 L1 / L2 / ASK_USER / BLOCKED
5. 生成 token.json + plan.md 的最小初始态

IntakeGate 不做：
✗ 不执行代码修改
✗ 不运行危险命令
✗ 不读取敏感文件内容
✗ 不调用 Oracle
✗ 不写 executor.md 完成证据
✗ 不进入 VerifyGate
✗ 不根据模型档位决定任务等级

Usage:
    python3 intake_gate.py <user_request> [--enhance-available]

Exit codes:
    0 = L1/L2 (可执行)
    1 = ASK_USER/BLOCKED (需用户介入)
"""

import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─── 风险标签定义 ───

CRITICAL_ACTIONS = [
    "打印 .env", "打印密钥", "cat .env", "显示密钥",
    "打印 token", "泄露密钥", "打印密码",
    "不要记录", "不要审计", "跳过验证", "不要验证", "绕过安全",
]

SENSITIVE_PATHS = [
    "/etc/", "~/.ssh/", "~/.aws/", "~/.kube/",
    ".env", "credentials", "secrets", "token", "password",
    "生产", "production",
]

SENSITIVE_ACTIONS = [
    "delete", "drop", "truncate", "rm -rf",
    "shutdown", "reboot", "chmod 777",
    "生产发布", "数据迁移", "支付", "退款", "改密码", "提权",
]

HIGH_RISK_KEYWORDS = [
    "删除数据库", "全量删除", "批量修改", "运维操作",
    "生产环境", "正式上线", "对外发布", "数据迁移", "表结构变更",
]

MEDIUM_RISK_KEYWORDS = [
    "改配置", "修改权限", "跨模块", "重构", "迁移", "批量", "发布",
]

L1_LIMITS = {"max_files": 8, "max_steps": 5, "max_modules": 1}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─── 输出结构（1.md §4.2）───

@dataclass
class IntakeDecision:
    decision: str          # L1 | L2 | BLOCKED | ASK_USER
    task_type: str         # code | doc | config | infra | data | security | unknown
    risk_level: str        # low | medium | high | critical
    scope: list[str]
    required_confirmations: list[str]
    reasons: list[str]
    next_action: str       # create_plan | ask_user | block
    evidence: list[dict[str, Any]]


# ─── 解析 ───

def parse_user_request(request: str) -> dict:
    """解析用户目标的路径、动作、对象"""
    ext = None
    ext_match = re.search(r'\.(\w+)\b', request)
    if ext_match:
        ext = ext_match.group(1)

    file_count = 0
    file_matches = re.findall(r'(\d+)\s*个?\s*文件', request)
    if file_matches:
        file_count = int(file_matches[0])

    step_count = 0
    step_matches = re.findall(r'(\d+)\s*步', request)
    if step_matches:
        step_count = int(step_matches[0])

    paths = re.findall(r'(?:\./|/)?[\w\-./]+\.[a-zA-Z]+', request)
    return {"file_ext": ext, "file_count": file_count, "step_count": step_count, "paths": paths, "length": len(request)}


def detect_critical_reasons(request: str) -> list[str]:
    """检查是否命中红线——一旦命中直接 BLOCKED"""
    reasons: list[str] = []
    lowered = request.lower()
    for action in CRITICAL_ACTIONS:
        if action.lower() in lowered:
            reasons.append(f"命中红线动作: {action}")
    return reasons


def detect_risk(request: str, parsed: dict) -> tuple:
    """返回 (risk_level, reasons, required_confirmations)"""
    reasons: list[str] = []
    confirmations: list[str] = []
    risk_level = "low"

    for path in SENSITIVE_PATHS:
        if path.lower() in request.lower():
            reasons.append(f"命中敏感路径关键词: {path}")
            risk_level = "high"

    for action in SENSITIVE_ACTIONS:
        if action.lower() in request.lower():
            reasons.append(f"命中敏感动作: {action}")
            risk_level = "high"

    for kw in HIGH_RISK_KEYWORDS:
        if kw in request:
            reasons.append(f"高风险操作: {kw}")
            if risk_level == "low":
                risk_level = "high"

    for kw in MEDIUM_RISK_KEYWORDS:
        if kw in request:
            reasons.append(f"中风险操作: {kw}")
            if risk_level == "low":
                risk_level = "medium"

    if parsed["file_count"] > L1_LIMITS["max_files"]:
        reasons.append(f"文件数({parsed['file_count']})超过 L1 上限({L1_LIMITS['max_files']})")
        risk_level = "medium"

    if parsed["step_count"] > L1_LIMITS["max_steps"]:
        reasons.append(f"步数({parsed['step_count']})超过 L1 上限({L1_LIMITS['max_steps']})")
        risk_level = "medium"

    return risk_level, reasons, confirmations


def detect_task_type(request: str) -> str:
    type_patterns = [
        ("security", ["权限", "安全", "认证", "加密", "证书"]),
        ("data", ["数据", "迁移", "导入", "导出", "备份"]),
        ("config", ["配置", ".env", ".yaml", ".yml", ".toml", "config"]),
        ("infra", ["部署", "发布", "上线", "运维", "监控"]),
        ("doc", ["文档", "README", "注释", "文档", "说明"]),
        ("code", ["代码", "修改", "函数", "类", "接口", "bug", "test"]),
    ]
    for ttype, kws in type_patterns:
        if any(kw in request for kw in kws):
            return ttype
    return "unknown"


def detect_scope(request: str, parsed: dict) -> list:
    scope = parsed["paths"]
    if not scope:
        if re.search(r'\bREADME\b', request, re.IGNORECASE):
            scope.append("README.md")
        if re.search(r'\bconfig\b', request, re.IGNORECASE):
            scope.append("*.yaml / *.yml / *.toml")
        if re.search(r'\btest\b', request, re.IGNORECASE):
            scope.append("*test*")
    return scope


def write_audit(decision: IntakeDecision, audit_dir: Path) -> None:
    """写 intake_decision 审计事件"""
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{today()}.jsonl"
    event = {
        "event_type": "intake_decision",
        "timestamp": now_iso(),
        **asdict(decision),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def run_intake(user_request: str, enhance_available: bool = False) -> IntakeDecision:
    """
    执行 IntakeGate 裁决

    返回 IntakeDecision dataclass：
    {
        "decision": "L1 | L2 | BLOCKED | ASK_USER",
        "task_type": "code | doc | ...",
        "risk_level": "low | medium | high | critical",
        ...
    }
    """
    parsed = parse_user_request(user_request)

    # 第一步：红线检测（critical）
    critical_reasons = detect_critical_reasons(user_request)
    if critical_reasons:
        return IntakeDecision(
            decision="BLOCKED",
            task_type=detect_task_type(user_request),
            risk_level="critical",
            scope=[],
            required_confirmations=[],
            reasons=critical_reasons + ["secret_disclosure_forbidden"],
            next_action="block",
            evidence=[{"source": "intake", "summary": user_request[:80]}],
        )

    # 第二步：风险检测（high/medium/low）
    risk_level, reasons, confirmations = detect_risk(user_request, parsed)
    task_type = detect_task_type(user_request)
    scope = detect_scope(user_request, parsed)

    if risk_level in ("high", "critical"):
        if "生产" in user_request:
            confirmations.append("是否确认在生产环境执行此操作？")
        if "delete" in user_request.lower() or "删除" in user_request:
            confirmations.append("是否确认执行删除操作？数据不可恢复。")

        if not confirmations:
            decision = "L2"
            next_action = "create_plan"
        else:
            decision = "ASK_USER"
            next_action = "ask_user"
    elif risk_level == "medium":
        if enhance_available:
            decision = "L2"
            next_action = "create_plan"
        else:
            decision = "ASK_USER"
            next_action = "ask_user"
    else:
        decision = "L1"
        next_action = "create_plan"

    # BLOCKED 降级保护（L2 不可用时高风险必须阻塞）
    if risk_level == "high" and not enhance_available:
        decision = "BLOCKED"
        next_action = "block"
        reasons = reasons + ["high_risk_without_l2"]

    return IntakeDecision(
        decision=decision,
        task_type=task_type,
        risk_level=risk_level,
        scope=scope,
        required_confirmations=confirmations if decision in ("ASK_USER", "BLOCKED") else [],
        reasons=reasons[:5],
        next_action=next_action,
        evidence=[{"source": "intake", "summary": user_request[:80]}],
    )


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: intake_gate.py <request> [--enhance-available]"}))
        sys.exit(1)

    user_request = sys.argv[1]
    enhance_available = "--enhance-available" in sys.argv

    result = run_intake(user_request, enhance_available)

    # 写审计
    write_audit(result, Path(".omc/audit"))

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    # exit code: 0 = L1/L2, 1 = ASK_USER/BLOCKED
    if result.decision in ("L1", "L2"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
