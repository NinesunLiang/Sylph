#!/usr/bin/env python3
"""
pretool-level-gate.py — L1/L2 判级门禁

CC hook: UserPromptSubmit
根据 forth.md levelgate 规则，在用户发送任务时自动判级。

核心规则（forth.md §一）：
  L2 清单（命中任一条 → L2，不可降级）：
    1. 动了 auth / payment / migration / infra / secret 相关路径
    2. 不可逆（删除/发布/部署）
    3. 涉及文件 > 3
    4. 跨模块 / 架构变更
    5. 长期无人执行
    6. 用户明确要求高可靠
  除此之外 → L1（模型可事后手动升级，不可降级）

Hook 协议: 打印 JSON 行到 stdout，stderr 输出给用户看。
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 令牌路径 ───
LEVEL_GATE_TOKEN = Path.cwd() / ".omc" / "tokens" / "level-gate.json"

# ─── L2 硬条件 ───
L2_PATHS = ("auth", "payment", "migration", "infra", "secret", "password", "credential")
L2_KEYWORDS = ("删除", "发布", "部署", "发布", "迁移", "重构", "权限",
               "delete", "deploy", "release", "migrate", "refactor", "permission",
               "无人", "autonomous", "高可靠", "跨模块", "架构变更")

def _scan_user_prompt(prompt: str, paths: list[str]) -> dict:
    """
    扫描用户输入，返回判级结果。
    返回: {"level": "L1"|"L2", "reasons": [...]}
    """
    prompt_lower = prompt.lower()
    reasons = []

    # 1. 路径扫描
    for path in paths:
        path_lower = path.lower()
        for lp in L2_PATHS:
            if lp in path_lower:
                reasons.append(f"命中敏感路径: {path} ({lp})")
                break  # 一个路径只计一次

    # 2. 关键词扫描
    for kw in L2_KEYWORDS:
        if kw.lower() in prompt_lower:
            reasons.append(f"命中 L2 关键词: {kw}")

    # 3. 文件数量判断（从 prompt 中提取文件引用数）
    file_refs = re.findall(r'[\w./-]+\.\w+', prompt)
    if len(set(file_refs)) > 3:
        reasons.append(f"涉及文件 > 3: {len(set(file_refs))} 个")

    # 4. 模型可升级不可降级 — 如果是空任务直接 L1
    level = "L2" if reasons else "L1"
    return {"level": level, "reasons": reasons}


def _get_active_limit() -> str:
    """从 token.json 或 plan.md 获取当前的 scope 限制"""
    # 简化实现：从 .omc/state/tokens/ 读最近的 token
    tokens_dir = Path.cwd() / ".omc" / "state" / "tokens"
    if tokens_dir.exists():
        for f in sorted(tokens_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    plan_dir = data.get("plan_dir", "")
                    if plan_dir:
                        return plan_dir
                except (json.JSONDecodeError, OSError):
                    pass
    return ""


def main():
    # ─── 读取 stdin ───
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True}))
        return

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return

    # ─── 提取用户输入 — 兼容多种格式 ───
    # CC/OC UserPromptSubmit: {"prompt": "...", "tool_input": {...}}
    # CC 原生: {"tool_name":"UserPromptSubmit","tool_input":{"prompt":"..."}}
    # 纯文本: {"prompt": "..."}
    prompt = ""
    for key in ("prompt", "text", "message", "input"):
        val = payload.get(key, "")
        if isinstance(val, str) and val.strip():
            prompt = val.strip()
            break

    if not prompt:
        tool_input = payload.get("tool_input", {})
        if isinstance(tool_input, dict):
            for key in ("prompt", "text", "message", "input"):
                val = tool_input.get(key, "")
                if isinstance(val, str) and val.strip():
                    prompt = val.strip()
                    break
        elif isinstance(tool_input, str):
            prompt = tool_input.strip()
    if not prompt or len(prompt) < 5:
        # 太短的输入不判级（5字符以下，如"hi"、"ok"）
        print(json.dumps({"continue": True}))
        return

    # ‍提取路径列表（从 prompt 中找文件路径）
    paths = re.findall(r'[\w./-]+\.\w+', prompt)

    # ─── 判级 ───
    result = _scan_user_prompt(prompt, paths)

    # ─── 落令牌 ───
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_dir = LEVEL_GATE_TOKEN.parent
    token_dir.mkdir(parents=True, exist_ok=True)
    if result["level"] == "L2":
        token = {
            "level": "L2",
            "reasons": result["reasons"],
            "judged_at": now_utc,
            "l2_workflow": True,
        }
        LEVEL_GATE_TOKEN.write_text(json.dumps(token, ensure_ascii=False, indent=2))
    else:
        # L1 — 删令牌（确保下次重新判）
        if LEVEL_GATE_TOKEN.exists():
            LEVEL_GATE_TOKEN.unlink()

    # ─── 输出 ───
    if result["level"] == "L2":
        msg = f"🔴 L2 判级: {', '.join(result['reasons'])}"
        sys.stderr.write(f"[LevelGate] {msg}\n")
        print(json.dumps({
            "continue": True,  # 仅 warn，不断
            "output_additional_context": [
                "## 🚨 LevelGate: 任务已判级为 L2（高治理级别）",
                f"**原因**: {', '.join(result['reasons'])}",
                "",
                "**必须切换到 L2 工作流**:",
                "1. **三段式水位**: 每 3 步检查上下文水位，>40% 先 compact",
                "2. **Oracle 审核**: 含架构变更的步骤先跑 Oracle 门禁",
                "3. **学习飞轮**: 完成后触发 flywheel 归档经验",
                "4. **VerifyGate**: 每步必须通过 verify 才能继续",
                "",
                "L1 规则（不再适用）: ❌ 不跑 Oracle / Multi-Judge / 飞轮",
                "L2 规则（当前生效）: ✅ 三段式水位 + Oracle + 飞轮",
            ]
        }))
    else:
        # L1 — 静默放行
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
