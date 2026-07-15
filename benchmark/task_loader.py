"""CarrorOS Benchmark — 任务加载器

Loads task definitions from YAML files, validates them,
and provides iteration over task sets.
"""

from __future__ import annotations
import os
import re
import sys
import json
from pathlib import Path
from typing import Iterator
from schemas import TaskDefinition, Difficulty


BENCHMARK_DIR = Path(__file__).resolve().parent
TASKS_DIR = BENCHMARK_DIR / "tasks"

# Task count targets (from spec)
DIFFICULTY_TARGETS = {
    Difficulty.EASY: 20,
    Difficulty.MEDIUM: 30,
    Difficulty.HARD: 20,
    Difficulty.ADVERSARIAL: 10,
}

CATEGORIES = [
    "01_repo_locate",
    "02_multi_file",
    "03_cross_module",
    "04_migration",
    "05_fuzzy_req",
    "06_test_fix",
    "07_perf_concur",
    "08_long_recovery",
    "09_high_risk",
    "10_adversarial",
]

CATEGORY_LABELS = {
    "01_repo_locate": "仓库定位与小修复",
    "02_multi_file": "多文件重构",
    "03_cross_module": "跨模块 Bug",
    "04_migration": "依赖升级/迁移",
    "05_fuzzy_req": "模糊需求实现",
    "06_test_fix": "测试修复",
    "07_perf_concur": "性能或并发问题",
    "08_long_recovery": "长期恢复任务",
    "09_high_risk": "高风险任务",
    "10_adversarial": "对抗性任务",
}


# ─── Simple YAML parser (no PyYAML dependency) ───

def _parse_yaml(text: str) -> dict:
    """Minimal YAML parser for task definition files."""
    result = {}
    current_section = None
    current_list_key = None
    current_list = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            _flush_list(result, current_list_key, current_list)
            current_list_key = None
            current_list = []
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            # Handle inline lists like [a, b, c]
            if item.startswith("[") and item.endswith("]"):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, list):
                        current_list.extend(parsed)
                        continue
                except json.JSONDecodeError:
                    pass
            if current_list_key:
                current_list.append(item)
            continue

        _flush_list(result, current_list_key, current_list)
        current_list_key = None
        current_list = []

        if ":" in stripped:
            colon_idx = stripped.index(":")
            key = stripped[:colon_idx].strip()
            value = stripped[colon_idx + 1:].strip()

            # Handle quoted strings
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]

            # Multi-line string marker
            if value == "|" or value == ">":
                current_section = key
                continue

            if value:
                # Try parsing as number or bool
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                else:
                    try:
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except (ValueError, TypeError):
                        pass

                if indent == 0:
                    result[key] = value
                elif current_section:
                    section_key = f"{current_section}.{key}"
                    result[section_key] = value
            else:
                current_section = key

    _flush_list(result, current_list_key, current_list)
    return result


def _flush_list(result: dict, key: str | None, lst: list) -> None:
    if key and lst:
        result[key] = lst


# ─── Task loading ───

def load_task(task_path: Path) -> TaskDefinition | None:
    """Load a single task definition from a .yaml file."""
    if not task_path.exists():
        return None

    text = task_path.read_text(encoding="utf-8")
    raw = _parse_yaml(text)

    task_id = raw.get("task_id", task_path.stem)
    category = raw.get("category", "")
    diff_str = raw.get("difficulty", "medium")

    try:
        difficulty = Difficulty(diff_str)
    except ValueError:
        print(f"  ⚠  Unknown difficulty '{diff_str}' in {task_path.name}, defaulting to medium")
        difficulty = Difficulty.MEDIUM

    # Parse list fields
    def _parse_list(val) -> list:
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            if val.startswith("[") and val.endswith("]"):
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    pass
            return [v.strip() for v in val.split(",") if v.strip()]
        return []

    allowed = _parse_list(raw.get("allowed_files", raw.get("allowed_files")))
    forbidden = _parse_list(raw.get("forbidden_files", raw.get("forbidden_files")))
    seeds_raw = _parse_list(raw.get("seeds", "1, 2, 3"))
    seeds = [int(s) for s in seeds_raw]
    if not seeds:
        seeds = [1, 2, 3]

    return TaskDefinition(
        task_id=task_id,
        category=category,
        difficulty=difficulty,
        title=raw.get("title", task_id),
        description=raw.get("description", ""),
        repo_url=raw.get("repo_url", ""),
        repo_commit=raw.get("repo_commit", ""),
        allowed_files=allowed,
        forbidden_files=forbidden,
        max_tool_calls=int(raw.get("max_tool_calls", 30)),
        max_wall_time_seconds=int(raw.get("max_wall_time_seconds", 600)),
        verify_script=raw.get("verify_script", ""),
        build_command=raw.get("build_command"),
        lint_command=raw.get("lint_command"),
        test_command=raw.get("test_command"),
        depends_on=_parse_list(raw.get("depends_on", "")),
        seeds=seeds,
    )


def load_all_tasks() -> list[TaskDefinition]:
    """Load all task definitions from the tasks directory."""
    tasks = []
    for cat_dir in sorted(TASKS_DIR.glob("*")):
        if not cat_dir.is_dir():
            continue
        for task_file in sorted(cat_dir.glob("*.yaml")):
            task = load_task(task_file)
            if task:
                tasks.append(task)
            else:
                print(f"  ❌ Failed to load task: {task_file}")
    return tasks


def load_tasks_by_category() -> dict[str, list[TaskDefinition]]:
    """Load tasks organized by category."""
    by_cat: dict[str, list[TaskDefinition]] = {c: [] for c in CATEGORIES}
    for task in load_all_tasks():
        if task.category in by_cat:
            by_cat[task.category].append(task)
        else:
            # Auto-detect from directory
            task_dir = task.category
            for cat in CATEGORIES:
                if cat.endswith(task_dir) or task_dir.endswith(cat):
                    by_cat[cat].append(task)
                    break
            else:
                by_cat.setdefault(task.category, []).append(task)
    return by_cat


def validate_task(task: TaskDefinition) -> list[str]:
    """Validate a task definition. Returns list of issues (empty = valid)."""
    issues = []
    if not task.task_id:
        issues.append("Missing task_id")
    if not task.category:
        issues.append("Missing category")
    if not task.description:
        issues.append("Missing description (prompt)")
    if not task.repo_url:
        issues.append("Missing repo_url")
    if not task.repo_commit:
        issues.append("Missing repo_commit (fixed commit required)")
    if not task.verify_script:
        issues.append("Missing verify_script (hidden verification)")
    if len(task.description) < 50:
        issues.append(f"Description too short ({len(task.description)} chars, min 50)")
    return issues


def summary(tasks: list[TaskDefinition]) -> str:
    """Print summary of loaded tasks."""
    lines = [f"📋 任务总数: {len(tasks)}"]
    by_diff: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for t in tasks:
        by_diff[t.difficulty.value] = by_diff.get(t.difficulty.value, 0) + 1
        by_cat[t.category] = by_cat.get(t.category, 0) + 1

    lines.append(f"   难度分布: {by_diff}")
    lines.append(f"   类别分布:")
    for cat, count in sorted(by_cat.items()):
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"     {cat}: {count} ({label})")

    return "\n".join(lines)


if __name__ == "__main__":
    tasks = load_all_tasks()
    print(summary(tasks))
    issues_found = 0
    for t in tasks:
        issues = validate_task(t)
        if issues:
            print(f"  ❌ {t.task_id}: {'; '.join(issues)}")
            issues_found += 1
    if issues_found == 0:
        print("✅ 所有任务验证通过")
