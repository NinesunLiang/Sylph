#!/usr/bin/env python3
"""
skillify_generator.py — 技能结构生成器

用于 skillify Phase 1-3 的确定性操作：
  - check_name_available: 检查 lx-{name} 是否已被占用
  - validate_frontmatter: 前置元数据必填字段检查
  - build_skel: 基于 TEMPLATE.md 生成最小有效 SKILL.md 骨架

用法:
  python3 skillify_generator.py --action check-name --name <name>
  python3 skillify_generator.py --action validate-fm --content-file <path>
  python3 skillify_generator.py --action build-skel --name <name> --description "..." [--triggers "..."]
"""

import sys
import os
import json
import argparse
from pathlib import Path


def get_skills_dir() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent  # scripts/ -> lx-skillify/ -> skills/


SKILLS_DIR = get_skills_dir()
TEMPLATE_PATH = SKILLS_DIR / "TEMPLATE.md"

REQUIRED_FRONTMATTER_FIELDS = [
    "name:",
    "version:",
    "description:",
    "when_to_use:",
    "harness_version:",
]


def check_name_available(name: str) -> dict:
    """检查技能名是否可用。"""
    skill_path = SKILLS_DIR / f"lx-{name}"
    exists = skill_path.exists()
    return {
        "name": f"lx-{name}",
        "available": not exists,
        "path": str(skill_path),
        "message": "名称可用" if not exists else f"技能 lx-{name} 已存在: {skill_path}"
    }


def validate_frontmatter(content: str) -> dict:
    """检查前置元数据是否包含所有必填字段。"""
    missing = []
    for field in REQUIRED_FRONTMATTER_FIELDS:
        if field not in content:
            missing.append(field.rstrip(':'))

    return {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "message": "前置元数据完整" if not missing else f"缺少必填字段: {missing}"
    }


def build_skel(name: str, description: str, triggers: str = "") -> dict:
    """基于 TEMPLATE.md 生成最小有效 SKILL.md 骨架。"""
    if not TEMPLATE_PATH.exists():
        return {
            "success": False,
            "error": f"TEMPLATE.md 不存在: {TEMPLATE_PATH}",
            "skel_content": ""
        }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')

    # 读取 VERSION 文件
    version_file = SKILLS_DIR / "VERSION"
    harness_version = "6.2.0"
    if version_file.exists():
        harness_version = version_file.read_text(encoding='utf-8').strip()

    # 生成触发词列表
    trigger_list = f'"/lx-{name}"'
    if triggers:
        extra = [t.strip() for t in triggers.split(',') if t.strip()]
        trigger_list = ', '.join([f'"/lx-{name}"'] + [f'"{t}"' for t in extra[:3]])

    # 替换占位符
    skel = f"""---
name: lx-{name}
version: v1.0.0
description: "{description}"
when_to_use: "Use when user says '/lx-{name}'{',' + triggers if triggers else ''}."
model: sonnet
argument-hint: "[参数提示]"
harness_version: ">={harness_version}"
status: draft
role: "{description[:60]}"
execution_mode: stepwise
triggers:
  - "/lx-{name}"{''.join(chr(10) + '  - "' + t.strip() + '"' for t in (triggers.split(',')[:3] if triggers else []))}
---

# lx-{name}

> {description}

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` | 全程行为约束 |
| report_generator | `../../nodes/report_generator.md` | 生成最终报告 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途 |
|------|------|------|
| 统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各阶段输出格式统一 |

### 状态机
本 skill 使用**私有 {2-4} 阶段状态机**，不引用 `orchestrator.md`。原因：TODO — 说明状态机类型及为什么不引用编排器。

### 私有节点
本 skill 无私有节点。

### 边界声明（不做什么）
| 不做的操作 | 原因 | 推荐替代 |
|-----------|------|---------|
| TODO | TODO | TODO |

---

## 执行流程

### Step 0: 入口检查

### Step 1: TODO

---

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| TODO | TODO | TODO |

## 错误恢复与中止条件

| 场景 | 动作 |
|------|------|
| TODO | TODO |
"""

    return {
        "success": True,
        "skel_content": skel,
        "path": str(SKILLS_DIR / f"lx-{name}" / "SKILL.md"),
        "warning": "骨架已生成，需手动填充 TODO 标记的章节。建议用 /skillify 完整生成。"
    }


def main():
    parser = argparse.ArgumentParser(description="skillify 生成器")
    parser.add_argument("--action", required=True,
                        choices=["check-name", "validate-fm", "build-skel"])
    parser.add_argument("--name", help="技能名称（不含 lx- 前缀）")
    parser.add_argument("--description", help="技能描述")
    parser.add_argument("--triggers", help="触发词，逗号分隔")
    parser.add_argument("--content-file", help="要验证的 SKILL.md 文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 输出")

    args = parser.parse_args()

    result = {}

    if args.action == "check-name":
        if not args.name:
            print("ERROR: --name is required for check-name", file=sys.stderr)
            sys.exit(2)
        result = check_name_available(args.name)

    elif args.action == "validate-fm":
        content_path = args.content_file
        if not content_path:
            print("ERROR: --content-file is required for validate-fm", file=sys.stderr)
            sys.exit(2)
        content = Path(content_path).read_text(encoding='utf-8')
        result = validate_frontmatter(content)

    elif args.action == "build-skel":
        if not args.name or not args.description:
            print("ERROR: --name and --description are required for build-skel", file=sys.stderr)
            sys.exit(2)
        result = build_skel(args.name, args.description, args.triggers or "")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result.get("success") is False:
            print(f"ERROR: {result.get('error', 'unknown error')}")
            sys.exit(1)
        elif result.get("valid") is False:
            print(f"INVALID: {result.get('message', '')}")
            sys.exit(1)
        elif result.get("available") is False:
            print(f"CONFLICT: {result.get('message', '')}")
            sys.exit(1)
        else:
            print(result.get("message", result.get("skel_content", "OK")))

    sys.exit(0)


if __name__ == '__main__':
    main()
