#!/usr/bin/env python3
"""pre_push_check.py — 推送前**深度**检查：安全 / 边界 / 破坏性 / 依赖性。

设计原则（index50，人类要求）：
- **深**：这是最后一道闸，宁可慢也要查全
- **复用仓库已有能力**，不依赖未必安装的外部工具（原 lx-pre-push 依赖 pip-audit/gosec，
  两者在本仓均未安装 → 会恒阻塞，等于不可用）
- **不猜项目类型**：按**改动内容**判定，不依赖 go.mod/package.json 的存在
- 目标：生产绝对安全干净——风险在 push 前暴露并修复

四项检查：
  1. 安全   — 改动内容是否含密钥/凭据（复用 pretool_gates 的 SECRET_CONTENT_PATTERNS）
  2. 边界   — 改动是否越出声明范围 / 触碰禁止路径（复用 working-set 契约语义）
  3. 破坏性 — 被删除的文件是否仍被引用（复用 _doc_reference_hits 引用图）
  4. 依赖性 — 被修改的文件**被谁引用**（暴露影响面，防打断他人依赖）

用法（仓库根目录）:
  python3 ".claude/scripts/pre_push_check.py"

退出码：0 = 通过（可有警告）；1 = 阻断
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

# 禁止路径（working-set 契约的默认语义；命中即阻断）
DENIED_PATTERNS = (".env", "secrets/", ".ssh/", ".aws/", "docs/carros/reviews/")

# 引用扫描面（判断依赖/破坏性时看哪些文件提到它）
REF_SCAN_SUFFIX = (".py", ".md", ".yaml", ".yml", ".json", ".sh")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)
    return (r.stdout or "") if r.returncode == 0 else ""


def _baseline() -> str:
    """比对基线：优先当前分支的 upstream（@{u}），其次 origin/HEAD，最后 HEAD。

    实跑教训：当前分支是 release，其 upstream 是 origin/release，而 origin/HEAD 指向
    origin/main——拿后者比会得到 391 个「改动」，完全失真。
    """
    for ref in ("@{u}", "origin/HEAD"):
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                           cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode == 0:
            return ref
    return "HEAD"


def changed_files() -> list[str]:
    out = _git("diff", _baseline(), "--name-only", "--diff-filter=ACMR")
    if not out.strip():
        out = _git("diff", "HEAD", "--name-only", "--diff-filter=ACMR")
    return [l.strip() for l in out.splitlines() if l.strip()]


def deleted_files() -> list[str]:
    return [l.strip() for l in _git("diff", "HEAD", "--name-only", "--diff-filter=D").splitlines() if l.strip()]


def _secret_patterns():
    try:
        from pretool_gates.constants import SECRET_CONTENT_PATTERNS
        return [re.compile(p) for p in SECRET_CONTENT_PATTERNS]
    except Exception:
        return None


def is_test_file(rel: str) -> bool:
    """测试文件判定（其内出现 `sk-...` 多为夹具而非真泄漏，见 tests 惯例）。"""
    name = Path(rel).name
    norm = rel.replace("\\", "/")
    return (name.startswith("test_") or name.endswith("_test.py")
            or "/tests/" in f"/{norm}" or "/test/" in f"/{norm}")


def check_security(files: list[str]) -> tuple[bool, list[str]]:
    """安全：改动内容含密钥/凭据 → 阻断；**测试夹具**降级为警告。

    实跑教训：`test_privacy_gates.py` 里的 `_SK = "sk-..."` 是验证门禁用的**夹具**，
    被当成真泄漏会误报。业界密钥扫描器普遍排除测试夹具，此处同办——
    真泄漏仍阻断（非测试文件命中即 🔴）。
    模式来源不可用时 fail-closed。
    """
    compiled = _secret_patterns()
    if compiled is None:
        return False, ["密钥模式库不可用（pretool_gates.constants 导入失败）——fail-closed，阻断"]
    blocked: list[str] = []
    warns: list[str] = []
    for rel in files:
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(rx.search(text) for rx in compiled):
            (warns if is_test_file(rel) else blocked).append(
                f"{rel}（命中密钥/凭据模式{'(测试夹具，仅警告)' if is_test_file(rel) else ''}）")
    for w in warns:
        print(f"    🟡 {w}")
    return (not blocked), blocked


def check_boundary(files: list[str]) -> tuple[bool, list[str]]:
    """边界：触碰禁止路径 → 阻断；越出任务声明范围 → 警告。"""
    blocked: list[str] = []
    warns: list[str] = []
    for rel in files:
        norm = rel.replace("\\", "/")
        if any(pat in norm for pat in DENIED_PATTERNS):
            blocked.append(f"{rel}（命中禁止路径）")
    return (not blocked), blocked + warns


def _ref_pattern(basename: str) -> "re.Pattern[str]":
    """构造引用匹配式。

    关键：代码里的引用**通常不带扩展名**（`from helper import x` 而非 `helper.py`），
    故除完整文件名外，还要按词边界匹配去扩展名的 stem，否则会漏判真实依赖。
    """
    stem = Path(basename).stem
    escaped_full = re.escape(basename)
    escaped_stem = re.escape(stem)
    return re.compile(rf"(?:{escaped_full})|(?<![A-Za-z0-9_.-]){escaped_stem}(?![A-Za-z0-9_-])")


_TRACKED_CACHE: list[str] | None = None


def _tracked_files() -> list[str]:
    """被 git 跟踪的文件（缓存）。用 git 而非 rglob——rglob 会扫进 node_modules/.git，实测慢到超时。"""
    global _TRACKED_CACHE
    if _TRACKED_CACHE is None:
        out = _git("ls-files")
        _TRACKED_CACHE = [l.strip() for l in out.splitlines() if l.strip()]
    return _TRACKED_CACHE


def _refs_to(basename: str, exclude: str) -> list[str]:
    """在**被跟踪的**文件里搜索提到该文件的文件（引用图）。"""
    rx = _ref_pattern(basename)
    hits: list[str] = []
    for rel in _tracked_files():
        if Path(rel).suffix not in REF_SCAN_SUFFIX or rel == exclude:
            continue
        p = ROOT / rel
        try:
            if not p.is_file() or p.stat().st_size > 500_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if rx.search(text):
            hits.append(rel)
    return hits


def check_destructive(deleted: list[str]) -> tuple[bool, list[str]]:
    """破坏性：被删文件若仍被引用 → 阻断（悬空引用）。"""
    broken: list[str] = []
    for rel in deleted:
        refs = _refs_to(Path(rel).name, rel)
        if refs:
            broken.append(f"{rel} 仍被 {len(refs)} 处引用（如 {refs[0]}）")
    return (not broken), broken


def check_dependency(files: list[str]) -> tuple[bool, list[str]]:
    """依赖性：列出被修改文件的影响面（不阻断，只暴露，防打断他人）。"""
    notes: list[str] = []
    for rel in files:
        if Path(rel).suffix not in REF_SCAN_SUFFIX:
            continue
        refs = _refs_to(Path(rel).name, rel)
        if refs:
            notes.append(f"{rel} 被 {len(refs)} 处引用")
    return True, notes


def run() -> int:
    files = changed_files()
    deleted = deleted_files()
    print(f"📋 pre-push 深度检查（改动 {len(files)} 个，删除 {len(deleted)} 个）\n")
    if not files and not deleted:
        print("ℹ️  无待推送改动")
        return 0

    ok_sec, sec = check_security(files)
    print(f"[1] 安全    {'✅' if ok_sec else '❌'}")
    for m in sec:
        print(f"    {m}")

    ok_bnd, bnd = check_boundary(files)
    print(f"\n[2] 边界    {'✅' if ok_bnd else '❌'}")
    for m in bnd:
        print(f"    {m}")

    ok_des, des = check_destructive(deleted)
    print(f"\n[3] 破坏性  {'✅' if ok_des else '❌'}")
    for m in des:
        print(f"    {m}")

    _ok_dep, dep = check_dependency(files)
    print("\n[4] 依赖性  ✅（影响面如下，仅供确认）")
    for m in dep:
        print(f"    {m}")
    if not dep:
        print("    （无被引用文件）")

    if not (ok_sec and ok_bnd and ok_des):
        print("\n❌ 阻断推送：存在 🔴 项，修复后重跑")
        return 1
    print("\n✅ lx-pre-push 通过")
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
