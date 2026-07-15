"""CarrorOS Benchmark — 消融组配置

Defines 7 ablation groups (A-G) and builds per-group environments.
Each group selectively enables/disables CarrorOS components.
"""

from __future__ import annotations
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

from schemas import AblationGroup, AblationConfig


# ─── Group Definitions ───

GROUP_DEFS: dict[AblationGroup, AblationConfig] = {
    AblationGroup.A_BARE: AblationConfig(
        group=AblationGroup.A_BARE,
        description="裸模型 — 无任何 CarrorOS 组件",
        agents_md=False, claude_md=False, kernel_md=False, index_yaml=False,
        prompt_engine=False, context_engine=False, harness_engine=False,
        settings_json_hooks=False, pretool_gate_py=False, user_approve_py=False,
        carros_base_scripts=False, skills=False, error_dna=False, oracle=False,
    ),
    AblationGroup.B_ENTRY_PROMPT: AblationConfig(
        group=AblationGroup.B_ENTRY_PROMPT,
        description="AGENTS + Prompt Engine",
        agents_md=True, claude_md=True, kernel_md=False, index_yaml=False,
        prompt_engine=True, context_engine=False, harness_engine=False,
        settings_json_hooks=False, pretool_gate_py=False, user_approve_py=False,
        carros_base_scripts=False, skills=False, error_dna=False, oracle=False,
    ),
    AblationGroup.C_ROUTING_KERNEL: AblationConfig(
        group=AblationGroup.C_ROUTING_KERNEL,
        description="AGENTS + INDEX + kernel + Prompt Engine",
        agents_md=True, claude_md=True, kernel_md=True, index_yaml=True,
        prompt_engine=True, context_engine=False, harness_engine=False,
        settings_json_hooks=False, pretool_gate_py=False, user_approve_py=False,
        carros_base_scripts=False, skills=False, error_dna=False, oracle=False,
    ),
    AblationGroup.D_WITHOUT_HARNESS: AblationConfig(
        group=AblationGroup.D_WITHOUT_HARNESS,
        description="完整认知层（文档+上下文），不启用物理 hooks",
        agents_md=True, claude_md=True, kernel_md=True, index_yaml=True,
        prompt_engine=True, context_engine=True, harness_engine=False,
        settings_json_hooks=False, pretool_gate_py=False, user_approve_py=False,
        carros_base_scripts=True, skills=True, error_dna=False, oracle=False,
    ),
    AblationGroup.E_FULL: AblationConfig(
        group=AblationGroup.E_FULL,
        description="完整 CarrorOS — 所有组件启用",
        agents_md=True, claude_md=True, kernel_md=True, index_yaml=True,
        prompt_engine=True, context_engine=True, harness_engine=True,
        settings_json_hooks=True, pretool_gate_py=True, user_approve_py=True,
        carros_base_scripts=True, skills=True, error_dna=True, oracle=True,
    ),
    AblationGroup.F_FULL_FIXED_BUDGET: AblationConfig(
        group=AblationGroup.F_FULL_FIXED_BUDGET,
        description="完整 CarrorOS + 等预算（30 工具调用，无 oracle/retry）",
        agents_md=True, claude_md=True, kernel_md=True, index_yaml=True,
        prompt_engine=True, context_engine=True, harness_engine=True,
        settings_json_hooks=True, pretool_gate_py=True, user_approve_py=True,
        carros_base_scripts=True, skills=True, error_dna=True, oracle=True,
        # F differs from E only in experiment budget constraints
    ),
    AblationGroup.G_FULL_TEST_TIME_SCALING: AblationConfig(
        group=AblationGroup.G_FULL_TEST_TIME_SCALING,
        description="完整 CarrorOS + 以量换智（90 工具调用，oracle + error_dna + retry）",
        agents_md=True, claude_md=True, kernel_md=True, index_yaml=True,
        prompt_engine=True, context_engine=True, harness_engine=True,
        settings_json_hooks=True, pretool_gate_py=True, user_approve_py=True,
        carros_base_scripts=True, skills=True, error_dna=True, oracle=True,
    ),
}


CARROS_ROOT = Path(__file__).resolve().parents[1]  # ~/Desktop/CarrorOS/


def get_config(group: AblationGroup) -> AblationConfig:
    """Get ablation config for a group."""
    return GROUP_DEFS[group]


def iter_groups() -> Iterator[tuple[AblationGroup, AblationConfig]]:
    """Iterate over all ablation groups."""
    for group, cfg in GROUP_DEFS.items():
        yield group, cfg


# ─── File copy manifests ───

_COMPONENT_FILES = {
    "agents_md": ["AGENTS.md"],
    "claude_md": ["CLAUDE.md"],
    "kernel_md": [".claude/kernel.md"],
    "index_yaml": [".claude/index.md"],
    "prompt_engine": [
        ".claude/references/prompt-templates/",
    ],
    "context_engine": [
        ".claude/scripts/context.py",
        ".claude/scripts/context_engine.py",
        ".claude/hooks/pretool-compact-writer.py",
    ],
    "settings_json_hooks": [".claude/settings.json"],
    "pretool_gate_py": [".claude/hooks/pretool-gate.py"],
    "user_approve_py": [".claude/hooks/pretool-user-approve.py"],
    "carros_base_scripts": [
        ".claude/scripts/carros_base.py",
        ".claude/scripts/verify_tests.py",
        ".claude/hooks/hook-launcher.sh",
    ],
    "skills": [".claude/skills/"],
    "error_dna": [".omc/error-dna.jsonl"],
    "oracle": [
        ".claude/scripts/meta-oracle-review.py",
        ".claude/scripts/oracle_spawn.py",
    ],
    "harness_lib": [
        ".claude/hooks/carroros_hooklib.py",
        ".claude/hooks/hook-launcher.sh",
    ],
}


def build_environment(
    target_dir: Path,
    group: AblationGroup,
    task_repo_dir: Path | None = None,
) -> Path:
    """Build a test environment for a given ablation group.

    Creates a copy of the task repo (or CarrorOS if no task repo)
    with only the CarrorOS components enabled by the ablation group.

    Returns the path to the built environment.
    """
    cfg = get_config(group)
    env_dir = target_dir / f"env_{group.value}"
    if env_dir.exists():
        shutil.rmtree(env_dir)

    # Start from task repo or CarrorOS
    if task_repo_dir and task_repo_dir.exists():
        shutil.copytree(task_repo_dir, env_dir, symlinks=False)
    else:
        env_dir.mkdir(parents=True, exist_ok=True)

    # Inject CarrorOS components based on ablation config
    for field_name in cfg.to_dict():
        if field_name == "group" or field_name == "description":
            continue
        enabled = getattr(cfg, field_name, False)
        component_files = _COMPONENT_FILES.get(field_name, [])
        for rel_path in component_files:
            src = CARROS_ROOT / rel_path
            dst = env_dir / rel_path
            if enabled and src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            elif not enabled and dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()

    return env_dir
