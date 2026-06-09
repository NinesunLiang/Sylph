#!/usr/bin/env python3
"""
snapshot-helper.py — 非 git 环境的规范化快照工具
Cross-platform Python resolution (DG-105)

背景：
  Carror OS 本身非 git 工作区，铁律 #4（Git 门禁）降级为 "sha256 + 人工批准"。
  本脚本提供标准化的 before/after 快照 + diff，让证据门禁在非 git 环境仍可闭环。

用法：
  python3 .claude/scripts/snapshot-helper.py before <file1> [file2 ...]
    → 生成 .omc/state/snapshot-before-<TS>.txt
  python3 .claude/scripts/snapshot-helper.py after  <file1> [file2 ...]
    → 生成 .omc/state/snapshot-after-<TS>.txt （复用最近一次 before 的 TS）
  python3 .claude/scripts/snapshot-helper.py diff
    → 对比最近一组 before/after（sha256 变化 / 行数变化）
  python3 .claude/scripts/snapshot-helper.py clean
    → 清理 .omc/state/snapshot-*.txt

每份快照包含：路径 · sha256 · wc -l · mtime
输出格式稳定可 diff：每行 "sha256  lines  mtime  path"

退出码：0=成功；1=参数错误；2=文件不存在；3=无 before 快照可对比
"""
import sys
import os
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(str(PROJECT_ROOT))

STATE_DIR = Path(".omc/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

# ─── sha256 helper ───
def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


# ─── stat mtime helper ───
def _mtime(path_str):
    p = Path(path_str)
    if not p.exists():
        return "-"
    ts = p.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


def _lines(path_str):
    p = Path(path_str)
    if not p.exists():
        return "0"
    return str(sum(1 for _ in p.open('rb')))


MODE = sys.argv[1] if len(sys.argv) > 1 else ""
args = sys.argv[2:]

if MODE == "before":
    if not args:
        print("usage: snapshot-helper.py before <file>...")
        sys.exit(1)
    TS = datetime.now().strftime("%Y%m%d-%H%M%S")
    OUT = STATE_DIR / f"snapshot-before-{TS}.txt"
    lines_out = []
    for f in args:
        fp = Path(f)
        if not fp.exists():
            lines_out.append(f"missing  0  -  {f}")
        else:
            sha = _sha256(f)
            lc = _lines(f)
            mt = _mtime(f)
            lines_out.append(f"{sha}  {lc}  {mt}  {f}")
    with open(OUT, "w") as fh:
        for line in lines_out:
            fh.write(line + "\n")
    # 记录"最近一次 before 的 TS"，after/diff 复用
    (STATE_DIR / ".snapshot-last-ts").write_text(TS)
    print(f"before snapshot → {OUT}")
    for line in lines_out:
        print(line)
elif MODE == "after":
    if not args:
        print("usage: snapshot-helper.py after <file>...")
        sys.exit(1)
    ts_file = STATE_DIR / ".snapshot-last-ts"
    if not ts_file.exists():
        print("error: no before snapshot")
        sys.exit(3)
    TS = ts_file.read_text().strip()
    OUT = STATE_DIR / f"snapshot-after-{TS}.txt"
    lines_out = []
    for f in args:
        fp = Path(f)
        if not fp.exists():
            lines_out.append(f"missing  0  -  {f}")
        else:
            sha = _sha256(f)
            lc = _lines(f)
            mt = _mtime(f)
            lines_out.append(f"{sha}  {lc}  {mt}  {f}")
    with open(OUT, "w") as fh:
        for line in lines_out:
            fh.write(line + "\n")
    print(f"after snapshot → {OUT}")
    for line in lines_out:
        print(line)
elif MODE == "diff":
    ts_file = STATE_DIR / ".snapshot-last-ts"
    if not ts_file.exists():
        print("error: no snapshot pair")
        sys.exit(3)
    TS = ts_file.read_text().strip()
    BEFORE = STATE_DIR / f"snapshot-before-{TS}.txt"
    AFTER = STATE_DIR / f"snapshot-after-{TS}.txt"
    if not BEFORE.exists() or not AFTER.exists():
        print(f"error: {BEFORE} or {AFTER} missing")
        sys.exit(3)
    print(f"=== snapshot diff (TS={TS}) ===")

    def load(p):
        m = {}
        with open(p) as f:
            for line in f:
                parts = line.strip().split(None, 3)
                if len(parts) == 4:
                    sha, lines_c, mtime, path = parts
                    m[path] = (sha, lines_c, mtime)
        return m

    b = load(BEFORE)
    a = load(AFTER)
    paths = sorted(set(b) | set(a))
    changed = 0
    unchanged = 0
    for p in paths:
        bs, bl, _ = b.get(p, ('-', '-', '-'))
        as_, al, _ = a.get(p, ('-', '-', '-'))
        if bs == as_:
            print(f"  =  {p}  (sha unchanged, {al} lines)")
            unchanged += 1
        else:
            print(f"  ≠  {p}  sha {bs[:12]}→{as_[:12]}  lines {bl}→{al}")
            changed += 1
    print(f"\n changed: {changed}  unchanged: {unchanged}  total: {len(paths)}")
elif MODE == "clean":
    for f in STATE_DIR.glob("snapshot-before-*.txt"):
        f.unlink()
    for f in STATE_DIR.glob("snapshot-after-*.txt"):
        f.unlink()
    ts_file = STATE_DIR / ".snapshot-last-ts"
    if ts_file.exists():
        ts_file.unlink()
    print("cleaned all snapshot files")
else:
    print("snapshot-helper.py — 非 git 环境的规范化快照工具")
    print()
    print("用法：")
    print("  python3 .claude/scripts/snapshot-helper.py before <file>...   # 记录修改前状态")
    print("  python3 .claude/scripts/snapshot-helper.py after  <file>...   # 记录修改后状态")
    print("  python3 .claude/scripts/snapshot-helper.py diff               # 对比最近一组")
    print("  python3 .claude/scripts/snapshot-helper.py clean              # 清理快照")
    print()
    print("每份快照含：sha256 · 行数 · mtime · 路径")
    sys.exit(1)
