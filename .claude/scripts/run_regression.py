#!/usr/bin/env python3
"""run_regression.py — CarrorOS canonical full regression（D-027，Python 版）。

替代 run-regression.sh：活体信号会污染门禁测试，运行前临时移出、退出时无条件还原。
原脚本里 temp-bypass 的 stash 已删除——该旁路机制已于 D-016 整体移除。

用法: python3 .claude/scripts/run_regression.py
退出码: 0=全过, 1=有失败套件或环境异常
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".omc" / "state"
STASH = Path("/tmp/carros-regression.stash")
LOG = Path("/tmp/carros-regression.pytest.log")
SIGNALS = [STATE / "tokens" / "autonomous.active", STATE / "tokens" / "lx-goal.json"]


def _restore(moved: list[tuple[Path, Path]]) -> None:
    for stash, original in moved:
        try:
            shutil.move(str(stash), str(original))
            print(f"[restore] {original.name} 已还原")
        except OSError as exc:
            print(f"[WARN] 还原失败 {original.name}: {exc}", file=sys.stderr)


def _find_tests() -> list[str]:
    found: list[str] = []
    for d in (".claude/scripts", ".claude/skills", ".claude/hooks"):
        for p in (ROOT / d).rglob("test_*.py"):
            if "__pycache__" not in p.parts and "worktrees" not in p.parts:
                found.append(str(p.relative_to(ROOT)))
    return sorted(found)


def main() -> int:
    if STASH.exists() and any(STASH.iterdir()):
        print(f"ERROR: 发现上次异常退出的 stash 残留 {STASH}", file=sys.stderr)
        return 1

    moved: list[tuple[Path, Path]] = []
    try:
        for sig in SIGNALS:
            if not sig.exists():
                continue
            STASH.mkdir(parents=True, exist_ok=True)
            dst = STASH / sig.name
            shutil.move(str(sig), str(dst))
            moved.append((dst, sig))
            print(f"[stash] {sig.name} 移出(测试后自动还原)")

        tests = _find_tests()
        if not tests:
            print("ERROR: 未发现任何测试文件", file=sys.stderr)
            return 1
        print(f"发现 {len(tests)} 个测试文件（canonical regression manifest）")

        proc = subprocess.run([sys.executable, "-m", "pytest", *tests, "-q"],
                              cwd=str(ROOT), capture_output=True, text=True)
        LOG.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        if proc.returncode == 0:
            print(f"PASS  全量回归（{len(tests)} 个文件）")
            return 0
        print(f"FAIL  全量回归（{len(tests)} 个文件）— 日志: {LOG}", file=sys.stderr)
        print("\n".join((proc.stdout or "").splitlines()[-40:]), file=sys.stderr)
        return 1
    finally:
        _restore(moved)
        shutil.rmtree(STASH, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
