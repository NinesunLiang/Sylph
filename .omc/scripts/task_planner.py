#!/usr/bin/env python3
"""
task_planner.py — spec.md → 原子任务分解引擎

分析 spec.md 目标/AC/边界，生成可执行的 plan.json（最小原子任务列表）。

输入: spec.md + 可选约束（level、max_concurrency）
输出: plan.json — {task_id, steps: [{id, goal, ac_refs, deps, files, type}]}

管道位置: clarify → task_planner → sub_agent_manager → dispatch → poll → collect → verify

用法:
    python3 task_planner.py <spec_path> [--output plan.json] [--level L2]
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ─── AC 类型标签 ───
AC_TYPES = {
    "command:": "命令行可验证",
    "file:": "文件存在/内容可验证",
    "assertion:": "逻辑断言可验证",
}

# ─── 默认分解规则 ───
DEFAULT_MAX_CONCURRENCY = 3  # 默认最多 3 个子任务并行
DEFAULT_MAX_RETRIES = 3      # 默认重试上限

# step 类型
STEP_TYPES = {
    "doc": "纯文档/研究",
    "code": "代码修改",
    "config": "配置修改",
    "test": "测试/验证",
    "review": "评审/审核",
    "deploy": "部署/发布",
}


def parse_spec(spec_path: Path) -> dict:
    """解析 spec.md 提取结构化信息"""
    if not spec_path.exists():
        raise FileNotFoundError(f"spec.md not found: {spec_path}")

    text = spec_path.read_text()

    result = {
        "title": _extract_title(text),
        "goal": _extract_goal(text),
        "acs": _extract_acs(text),
        "scope_in": _extract_scope_in(text),
        "scope_out": _extract_scope_out(text),
        "deps": _extract_deps(text),
    }
    return result


def _extract_title(text: str) -> str:
    m = re.search(r"^#\s*Spec:\s*(.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else "unnamed"


def _extract_goal(text: str) -> str:
    """提取 ## 目标 下的第一段内容"""
    m = re.search(r"##\s*目标\s*\n+([^#]+)", text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_acs(text: str) -> list:
    """提取验收条件列表 — 返回 [{id, type, desc}]"""
    acs = []
    section = _extract_section(text, "验收条件")
    if not section:
        return acs

    for line in section.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # AC1 [command:] desc 或 - AC1 [command:] desc
        m = re.match(r"-?\s*(AC\d+)?\s*\[?(command:|file:|assertion:)\]?\s*(.+)", line)
        if m:
            ac_id = m.group(1) or f"AC{len(acs) + 1}"
            ac_type = m.group(2) or "assertion:"
            desc = m.group(3).strip()
            acs.append({"id": ac_id, "type": ac_type, "desc": desc})

    return acs


def _extract_scope_in(text: str) -> list:
    """提取 In Scope 列表"""
    section = _extract_section(text, "边界")
    if not section:
        return []

    # 找 ### In Scope 子段落
    m = re.search(r"###\s*In Scope\s*\n(.+?)(?=\n###|\n##|\Z)", section, re.DOTALL)
    if not m:
        return []

    items = []
    for line in m.group(1).split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and not line.startswith("#") and not line.startswith("**"):
            items.append(line)
    return items


def _extract_scope_out(text: str) -> list:
    """提取 Out of Scope 列表"""
    section = _extract_section(text, "边界")
    if not section:
        return []

    m = re.search(r"###\s*Out\s*of\s*Scope\s*\n(.+?)(?=\n###|\n##|\Z)", section, re.DOTALL)
    if not m:
        return []

    items = []
    for line in m.group(1).split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and not line.startswith("#") and not line.startswith("**"):
            items.append(line)
    return items


def _extract_deps(text: str) -> str:
    """提取依赖部分"""
    section = _extract_section(text, "依赖")
    if section:
        return section.strip()
    return ""


def _extract_section(text: str, heading: str) -> str:
    """按标题提取 markdown 段落 — 支持 heading 后有括号/注释等 trailing 内容"""
    # heading 后面可能跟着括号/中括号等附加内容
    pattern = rf"##\s*{re.escape(heading)}[^#\n]*\n(.+?)(?=\n##|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # fallback: 宽松匹配 — 只取 heading 的关键词
    pattern = rf"##[^#]*{re.escape(heading)}[^#\n]*\n(.+?)(?=\n##|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def decompose(parsed: dict, level: str = "L1", max_concurrency: int = None) -> dict:
    """将解析后的 spec 分解为 plan.json

    Args:
        parsed: parse_spec() 的返回结果
        level: L1=单步, L2=多步+子任务
        max_concurrency: 并行子任务上限

    Returns:
        {plan_id, level, steps: [{id, goal, ac_refs, deps, files, type}], concurrency}
    """
    if max_concurrency is None:
        max_concurrency = DEFAULT_MAX_CONCURRENCY

    acs = parsed["acs"]
    scope_in = parsed["scope_in"]

    # 从 scope_in 推断涉及文件
    files = _infer_files(scope_in)

    steps = []

    if level == "L1":
        # 单步任务: 所有 AC 打包为一个步骤
        steps.append({
            "id": "S1",
            "goal": parsed["goal"],
            "ac_refs": [ac["id"] for ac in acs],
            "deps": [],
            "files": files,
            "type": _infer_step_type(parsed["goal"], files),
            "subtasks": [],
        })
    else:
        # L2: 按 AC 类型分解为多个子任务
        subtask_index = 0
        for ac in acs:
            subtask_index += 1
            step_id = f"S{subtask_index}"
            step = _ac_to_step(ac, parsed, step_id, files)
            steps.append(step)

        # 如果有剩余 scope 项没被 AC 覆盖，也生成步骤
        if not steps:
            steps.append({
                "id": "S1",
                "goal": parsed["goal"],
                "ac_refs": [],
                "deps": [],
                "files": files,
                "type": "code",
                "subtasks": [],
            })

    return {
        "plan_id": f"plan-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
        "level": level,
        "goal": parsed["goal"],
        "title": parsed["title"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "max_concurrency": max_concurrency,
        "max_retries": DEFAULT_MAX_RETRIES,
        "steps": steps,
        "ac_registry": acs,
    }


def _infer_files(scope_in: list) -> list:
    """从 In Scope 列表中推断文件路径"""
    files = []
    for item in scope_in:
        # 按逗号/空格分割可能的路径
        for part in re.split(r"[,，]", item):
            part = part.strip().strip("`")
            if part and ("./" in part or "/" in part or part.endswith(".py") or
                         part.endswith(".md") or part.endswith(".yaml") or
                         part.endswith(".json") or part.endswith(".sh")):
                if part not in files:
                    files.append(part)
    return files


def _infer_step_type(goal: str, files: list) -> str:
    """根据目标推断步骤类型"""
    goal_lower = goal.lower()
    if any(w in goal_lower for w in ["文档", "研究", "调查", "research", "doc"]):
        return "doc"
    if any(w in goal_lower for w in ["部署", "发布", "deploy", "release"]):
        return "deploy"
    if any(w in goal_lower for w in ["测试", "验证", "test", "verify"]):
        return "test"
    if any(w in goal_lower for w in ["配置", "config", "setting"]):
        return "config"
    if any(w in goal_lower for w in ["评审", "审核", "review", "audit"]):
        return "review"
    if any(f.endswith(".py") or f.endswith(".js") or f.endswith(".ts") for f in files):
        return "code"
    return "code"


def _ac_to_step(ac: dict, parsed: dict, step_id: str, files: list) -> dict:
    """将单个 AC 转换为步骤定义"""
    step_files = files.copy()
    if ac["type"] == "file:":
        # file AC 涉及的具体文件
        m = re.search(r"`([^`]+)`", ac["desc"])
        if m and m.group(1) not in step_files:
            step_files.append(m.group(1))

    return {
        "id": step_id,
        "goal": ac["desc"],
        "ac_refs": [ac["id"]],
        "deps": [],
        "files": step_files,
        "type": _infer_step_type(ac["desc"], step_files),
        "subtasks": [ac["desc"]],
    }


def save_plan(plan: dict, output_path: Path) -> Path:
    """保存 plan.json"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    return output_path


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="spec.md → 原子任务分解引擎")
    parser.add_argument("spec_path", help="spec.md 文件路径")
    parser.add_argument("--output", "-o", default=None, help="plan.json 输出路径")
    parser.add_argument("--level", default="L1", choices=["L1", "L2"],
                       help="分解粒度 (默认: L1=单步, L2=多步)")
    parser.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY,
                       help="并行子任务上限 (默认: 3)")

    args = parser.parse_args(argv)

    spec_path = Path(args.spec_path)
    if not spec_path.exists():
        print(f"❌ spec not found: {spec_path}", file=sys.stderr)
        return 2

    # 解析
    parsed = parse_spec(spec_path)
    print(f"📋 Spec: {parsed['title']}")
    print(f"   Goal: {parsed['goal'][:60]}")
    print(f"   ACs: {len(parsed['acs'])}")
    print(f"   In Scope: {len(parsed['scope_in'])} items")

    # 分解
    plan = decompose(parsed, level=args.level, max_concurrency=args.max_concurrency)
    print(f"   Steps: {len(plan['steps'])} ({args.level})")

    # 输出
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = spec_path.parent / "plan.json"

    save_plan(plan, output_path)
    print(f"✅ Plan saved: {output_path}")
    print(f"   Concurrency: {plan['max_concurrency']}, Max retries: {plan['max_retries']}")

    # 打印步骤摘要
    for i, step in enumerate(plan["steps"]):
        deps_str = f" (deps: {step['deps']})" if step["deps"] else ""
        print(f"   {i+1}. [{step['type']}] {step['id']}: {step['goal'][:50]}{deps_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
