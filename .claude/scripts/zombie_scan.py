#!/usr/bin/env python3
"""zombie_scan.py — 僵尸 .py 探测器（新增特性时清理死代码）

CarrorOS 僵尸机制：未被其他代码(import/from)、配置(settings/harness)或文档(.md 路径)
引用的 .py = 死代码候选 → 建议清理(归档到 retired/)。测试树(test_*/conftest/__init__)
由 pytest 全量收集，视为活着。

用法：
  python3 .claude/scripts/zombie_scan.py            # 列候选(默认 .claude/scripts + .claude/hooks)
  python3 .claude/scripts/zombie_scan.py --archive  # 把候选归档到 <root>/.claude/retired/<name>.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

EXCLUDE_FRAGS = ("__pycache__", "/archived/", "/retired/", ".omo/", ".omc/", "node_modules/", "/dist/", "/.git/")
_LIVE_PREFIX = ("test_", "conftest", "__init__")


def _is_candidate(p: Path) -> bool:
    rel = p.as_posix()
    if any(f in rel for f in EXCLUDE_FRAGS):
        return False
    name = p.name
    return name.endswith(".py") and not name.startswith(_LIVE_PREFIX) and name != "__init__.py"


def find_zombies(root, scan_roots: tuple[str, ...] = (".",)) -> list[str]:
    """返回僵尸候选的仓库相对路径。

    引用来源 = 该文件之外的其它文件文本（import/from 点分、.py 路径/文件名）。
    仅扫描 scan_roots（hooks 由 hook-launcher 按目录动态拉起，不在文本中留 .py 引用，
    故默认只扫 .claude/scripts 顶层，避免把活跃 hook 误判成僵尸）。
    """
    root = Path(root).resolve()
    candidates = []
    for sr in scan_roots:
        base = root / sr
        if not base.exists():
            continue
        candidates.extend(p for p in base.rglob("*.py") if _is_candidate(p))

    # 索引：stem -> 引用它的文件集合
    ref_by: dict[str, set[Path]] = {}
    for src in root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.as_posix()
        if any(f in rel for f in EXCLUDE_FRAGS):
            continue
        if src.name == "zombie_scan.py":
            continue
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # 路径/文件名形式：x.py（文件名允许连字符，如 temp-bypass.py）
        for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_-]{1,80})\.py\b", text):
            ref_by.setdefault(m.group(1), set()).add(src)
        # import x / from a.b import x（含点分链，逐段登记）
        for m in re.finditer(r"\b(?:import|from)\s+([A-Za-z_][A-Za-z0-9_.]*)", text):
            for seg in m.group(1).split("."):
                if seg:
                    ref_by.setdefault(seg, set()).add(src)

    out = []
    for c in candidates:
        stem = c.stem
        refs = ref_by.get(stem, set())
        if refs - {c}:  # 被任一其他文件提及即活
            continue
        out.append(c.relative_to(root).as_posix())
    return sorted(out)


def _archive(cands: list[str], root) -> None:
    root = Path(root).resolve()
    retired = root / ".claude" / "retired"
    retired.mkdir(parents=True, exist_ok=True)
    for rel in cands:
        src = root / rel
        if not src.exists():
            continue
        dst = retired / src.name
        n = 1
        while dst.exists():
            dst = retired / f"{src.stem}.{n}{src.suffix}"
            n += 1
        shutil.move(str(src), str(dst))
        print(f"  归档 {rel} -> .claude/retired/{dst.name}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="僵尸 .py 探测器")
    ap.add_argument("--root", default=".")
    ap.add_argument("--archive", action="store_true", help="把候选归档到 .claude/retired/")
    ap.add_argument("roots", nargs="*", default=[".claude/scripts"])
    args = ap.parse_args(argv)
    cands = find_zombies(args.root, tuple(args.roots))
    print(f"僵尸候选 {len(cands)} 个:")
    for rel in cands:
        print(f"  - {rel}")
    if args.archive and cands:
        _archive(cands, args.root)
    return 1 if cands else 0


if __name__ == "__main__":
    sys.exit(main())
