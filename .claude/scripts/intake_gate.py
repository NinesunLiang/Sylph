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
"""

import json
import re
import sys

# ─── 风险标签定义（config policy 替代品）───

SENSITIVE_PATHS = [
    "/etc/",
    "~/.ssh/",
    "~/.aws/",
    "~/.kube/",
    ".env",
    "credentials",
    "secrets",
    "token",
    "password",
    "生产",
    "production",
]

SENSITIVE_ACTIONS = [
    "delete",
    "drop",
    "truncate",
    "rm -rf",
    "shutdown",
    "reboot",
    "chmod 777",
    "生产发布",
    "数据迁移",
    "支付",
    "退款",
    "改密码",
    "提权",
]

HIGH_RISK_KEYWORDS = [
    "删除数据库",
    "全量删除",
    "批量修改",
    "运维操作",
    "生产环境",
    "正式上线",
    "对外发布",
    "数据迁移",
    "表结构变更",
]

MEDIUM_RISK_KEYWORDS = [
    "改配置",
    "修改权限",
    "跨模块",
    "重构",
    "迁移",
    "批量",
    "发布",
]

L1_LIMITS = {
    "max_files": 8,
    "max_steps": 5,
    "max_modules": 1,
}


def parse_user_request(request: str) -> dict:
    """解析用户目标的路径、动作、对象"""
    # 提取文件扩展名
    ext = None
    ext_match = re.search(r'\.(\w+)\b', request)
    if ext_match:
        ext = ext_match.group(1)

    # 提取数字/文件数指标
    file_count = 0
    file_matches = re.findall(r'(\d+)\s*个?\s*文件', request)
    if file_matches:
        file_count = int(file_matches[0])

    step_count = 0
    step_matches = re.findall(r'(\d+)\s*步', request)
    if step_matches:
        step_count = int(step_matches[0])

    # 提取路径
    paths = re.findall(r'(?:\./|/)?[\w\-./]+\.[a-zA-Z]+', request)

    return {
        "file_ext": ext,
        "file_count": file_count,
        "step_count": step_count,
        "paths": paths,
        "length": len(request),
    }


def detect_risk(request: str, parsed: dict) -> tuple:
    """返回 (risk_level, reasons, required_confirmations)"""
    reasons = []
    confirmations = []
    risk_level = "low"

    # 敏感路径
    for path in SENSITIVE_PATHS:
        if path.lower() in request.lower():
            reasons.append(f"命中敏感路径关键词: {path}")
            risk_level = "high"

    # 敏感动作
    for action in SENSITIVE_ACTIONS:
        if action.lower() in request.lower():
            reasons.append(f"命中敏感动作: {action}")
            risk_level = "high"

    # 高风险关键词
    for kw in HIGH_RISK_KEYWORDS:
        if kw in request:
            reasons.append(f"高风险操作: {kw}")
            if risk_level == "low":
                risk_level = "high"

    # 中风险关键词
    for kw in MEDIUM_RISK_KEYWORDS:
        if kw in request:
            reasons.append(f"中风险操作: {kw}")
            if risk_level == "low":
                risk_level = "medium"

    # 统计指标
    if parsed["file_count"] > L1_LIMITS["max_files"]:
        reasons.append(f"文件数({parsed['file_count']})超过 L1 上限({L1_LIMITS['max_files']})")
        risk_level = "medium"

    if parsed["step_count"] > L1_LIMITS["max_steps"]:
        reasons.append(f"步数({parsed['step_count']})超过 L1 上限({L1_LIMITS['max_steps']})")
        risk_level = "medium"

    return risk_level, reasons, confirmations


def detect_task_type(request: str) -> str:
    """识别任务类型"""
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
    """提取 scope 初始边界"""
    scope = parsed["paths"]
    if not scope:
        # 尝试从关键词推断
        if re.search(r'\bREADME\b', request, re.IGNORECASE):
            scope.append("README.md")
        if re.search(r'\bconfig\b', request, re.IGNORECASE):
            scope.append("*.yaml / *.yml / *.toml")
        if re.search(r'\btest\b', request, re.IGNORECASE):
            scope.append("*test*")
    return scope


def run_intake(user_request: str, enhance_available: bool = False) -> dict:
    """
    执行 IntakeGate 裁决

    返回 JSON（1.md 第 4.2 节定义）：
    {
        "decision": "L1 | L2 | BLOCKED | ASK_USER",
        "task_type": "code | doc | config | infra | data | security | unknown",
        "risk_level": "low | medium | high | critical",
        "scope": [],
        "required_confirmations": [],
        "reasons": [],
        "next_action": "create_plan | ask_user | block",
        "evidence": []
    }
    """
    parsed = parse_user_request(user_request)
    risk_level, reasons, confirmations = detect_risk(user_request, parsed)
    task_type = detect_task_type(user_request)
    scope = detect_scope(user_request, parsed)

    # 决策逻辑
    if risk_level in ("high", "critical"):
        # 高风险
        if "生产" in user_request:
            confirmations.append("是否确认在生产环境执行此操作？")
        if "delete" in user_request.lower() or "删除" in user_request:
            confirmations.append("是否确认执行删除操作？数据不可恢复。")

        if not confirmations:
            # 无明确的待确认项 → 直接 L2
            decision = "L2"
            next_action = "create_plan"
        else:
            # 有待确认 → 先问人
            decision = "ASK_USER"
            next_action = "ask_user"
    elif risk_level == "medium":
        # 中风险 → L2（如可用）或 ASK_USER
        if enhance_available:
            decision = "L2"
            next_action = "create_plan"
        else:
            decision = "ASK_USER"
            next_action = "ask_user"
    else:
        # 低风险 → L1
        decision = "L1"
        next_action = "create_plan"

    # BLOCKED 条件
    if risk_level == "critical":
        decision = "BLOCKED"
        next_action = "block"

    return {
        "decision": decision,
        "task_type": task_type,
        "risk_level": risk_level,
        "scope": scope,
        "required_confirmations": confirmations,
        "reasons": reasons[:5],  # 最多 5 条
        "next_action": next_action,
        "evidence": [f"intake: {user_request[:80]}..."],
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: intake_gate.py <request> [--enhance-available]"}))
        sys.exit(1)

    user_request = sys.argv[1]
    enhance_available = "--enhance-available" in sys.argv

    result = run_intake(user_request, enhance_available)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # exit code: 0 = L1/L2, 1 = ASK_USER/BLOCKED
    if result["decision"] in ("L1", "L2"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
