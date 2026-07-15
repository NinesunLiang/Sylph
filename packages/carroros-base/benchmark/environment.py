"""CarrorOS Benchmark — 测试环境构建

Creates isolated test environments for each experiment run:
1. Git checkout task repo at fixed commit
2. Inject CarrorOS components per ablation config
3. Set up control variables
"""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from schemas import AblationGroup
from ablation import build_environment, CARROS_ROOT


BENCHMARK_DIR = Path(__file__).resolve().parent
ENVS_DIR = BENCHMARK_DIR / "envs"
REPOS_DIR = BENCHMARK_DIR / "repos"


def ensure_repo(task_repo_url: str, commit: str) -> Path:
    """Clone or update a task repo at a fixed commit. Returns repo path."""
    # Derive a local name from the URL
    repo_name = task_repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = REPOS_DIR / repo_name

    if repo_path.exists():
        # Check if we already have the right commit
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                capture_output=True, text=True, timeout=30,
            )
            if result.stdout.strip() == commit:
                return repo_path
        except (subprocess.TimeoutExpired, OSError):
            pass
        # Wrong commit → clean checkout
        shutil.rmtree(repo_path)

    # Clone
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  📦 Cloning {task_repo_url} @ {commit[:12]}...")
    try:
        subprocess.run(
            ["git", "clone", task_repo_url, str(repo_path)],
            capture_output=True, text=True, timeout=120,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", commit],
            cwd=str(repo_path),
            capture_output=True, text=True, timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to checkout {commit}: {e.stderr[:200]}") from e

    return repo_path


def build_task_env(
    task_id: str,
    task_repo_url: str,
    task_commit: str,
    group: AblationGroup,
    seed: int,
    run_dir: Path | None = None,
) -> Path:
    """Build a complete test environment for one experiment run.

    Returns the path to the environment directory.
    """
    # Create run directory
    if run_dir is None:
        run_dir = ENVS_DIR / f"run_{task_id}_{group.value}_s{seed}"
    if run_dir.exists():
        shutil.rmtree(run_dir)

    run_dir.mkdir(parents=True, exist_ok=True)

    # Clone task repo
    print(f"  🔧 Building env for {task_id} / {group.value} / seed={seed}")
    print(f"  📦 Acquiring repo...")
    repo_path = ensure_repo(task_repo_url, task_commit)

    # Copy repo to run directory
    print(f"  📋 Copying repo...")
    shutil.copytree(repo_path, run_dir, symlinks=False, dirs_exist_ok=True)

    # Inject CarrorOS components based on ablation group
    print(f"  ⚙  Applying ablation {group.value}...")
    env_path = build_environment(run_dir.parent, group, task_repo_dir=run_dir)

    # Write experiment metadata
    meta = {
        "task_id": task_id,
        "group": group.value,
        "seed": seed,
        "commit": task_commit,
        "env_path": str(env_path),
    }
    (env_path / ".benchmark-meta.json").write_text(
        __import__("json").dumps(meta, indent=2) + "\n"
    )

    return env_path
