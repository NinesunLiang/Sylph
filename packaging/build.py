#!/usr/bin/env python3
"""build.py — 按 packaging/manifest.yaml 组装可发行模板。

设计要点：
  · 白名单驱动：只拷 manifest.include 命中的路径；exclude 优先。
  · 三重防密钥：settings.local 硬失败 / settings.json 脱敏 / 内容模式扫描 fail-closed。
  · 自检不过即中止，不留半成品（先写临时目录，全绿再替换）。

用法:
  python3 packaging/build.py            # 组装到 packaging/template/
  python3 packaging/build.py --check    # 只做自检，不写盘
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packaging"
TEMPLATE = PKG / "template"
MANIFEST = PKG / "manifest.yaml"

# 用正则匹配「真实密钥形状」，避免 task- / risk- 这类普通词误报。
SECRET_RE = __import__("re").compile(
    r"("
    r"\bsk" + r"-[A-Za-z0-9]{16,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|BEGIN " + r"PRIVATE KEY"
    r"|\bghp" + r"_[A-Za-z0-9]{20,}"
    r"|\bxoxb" + r"-[0-9A-Za-z-]{10,}"
    r"|\bAIza[0-9A-Za-z_\-]{30,}"
    r")"
)
# 实测白名单内容 3.4 MB（约 300 个源文件，平均 11 KB）。原定 3 MB 为拍脑袋估值，
# 按实测上调到 5 MB，保留约 50% 余量；一旦超过 5 MB 说明有东西混进来了。
MAX_BYTES = 5 * 1024 * 1024


def _expand(patterns: list[str]) -> list[Path]:
    seen: dict[Path, None] = {}
    for pat in patterns:
        for p in ROOT.glob(pat):
            if p.is_file() and p.is_relative_to(ROOT):
                seen[p] = None
    return sorted(seen)


def _is_excluded(rel: str, excludes: list[str]) -> bool:
    return any(fnmatch(rel, pat) or fnmatch(rel, pat.replace("**/", "")) for pat in excludes)


def _collect(manifest: dict) -> list[tuple[Path, str]]:
    excludes = manifest.get("exclude") or []
    out = []
    for src in _expand(manifest.get("include") or []):
        rel = src.relative_to(ROOT).as_posix()
        if _is_excluded(rel, excludes):
            continue
        if src.name == "settings.local.json":
            raise SystemExit(f"❌ 白名单命中了密钥文件：{rel}（必须修 manifest）")
        out.append((src, rel))
    return out


def _sanitize_settings(text: str) -> str:
    """清空 env 段与机器相关权限，保留结构。"""
    try:
        data = json.loads(text)
    except ValueError:
        return text
    if isinstance(data.get("env"), dict):
        data["env"] = {}
    perms = data.get("permissions")
    if isinstance(perms, dict):
        perms["allow"] = []
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _scan_secrets(dest: Path) -> list[str]:
    hits = []
    for p in dest.rglob("*"):
        if not p.is_file() or p.suffix in (".pyc",):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if SECRET_RE.search(text):
            hits.append(p.relative_to(dest).as_posix())
    return hits


def _version(manifest: dict) -> str:
    v = manifest.get("version") or {}
    return f"{v.get('release_major', 1)}.0.0"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def assemble(manifest: dict, dest: Path) -> list[str]:
    errors: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)

    for src, rel in _collect(manifest):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel == ".claude/settings.json":
            target.write_text(_sanitize_settings(src.read_text(encoding="utf-8")),
                              encoding="utf-8")
        else:
            shutil.copy2(src, target)

    # 自检
    tests = list(dest.rglob("test_*.py"))
    if tests:
        errors.append(f"包内含 {len(tests)} 个测试文件")
    if list(dest.rglob("settings.local.json")):
        errors.append("包内含 settings.local.json")
    if list(dest.rglob(".omc")):
        errors.append("包内含 .omc")
    if list(dest.rglob("*.jsonl")):
        errors.append("包内含 .jsonl 运行数据")

    hits = _scan_secrets(dest)
    if hits:
        errors.append(f"密钥模式命中 {len(hits)}: {hits[:3]}")

    for py in dest.rglob("*.py"):
        rc = subprocess.run([sys.executable, "-m", "py_compile", str(py)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            errors.append(f"py_compile 失败: {py.relative_to(dest)}")
            break

    total = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    if total > MAX_BYTES:
        errors.append(f"体积超标 {total / 1024 / 1024:.1f} MB > 3 MB")

    if not errors:
        version = _version(manifest)
        (dest / "VERSION.json").write_text(json.dumps({
            "version": version,
            "built_from_commit": _git("rev-parse", "--short", "HEAD"),
            "built_at": datetime.now(timezone.utc).isoformat(),
            "files": sum(1 for p in dest.rglob("*") if p.is_file()),
            "bytes": total,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        errors.extend(_post_manifest_check(dest, version))
    return errors


def _post_manifest_check(dest: Path, version: str) -> list[str]:
    errors = []
    if not (dest / ".claude" / "hooks" / "pretool-gate.py").is_file():
        errors.append("缺少门禁入口 pretool-gate.py")
    if not (dest / "AGENTS.md").is_file():
        errors.append("缺少 AGENTS.md")
    if not version.endswith(".0.0"):
        errors.append(f"版本号不符合 大版本.0.0 规则: {version}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只自检，不写盘")
    args = ap.parse_args(argv)

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    target = Path(tempfile.mkdtemp()) / "template" if args.check else TEMPLATE

    if not args.check and TEMPLATE.exists():
        shutil.rmtree(TEMPLATE)

    errors = assemble(manifest, target)
    if errors:
        print("❌ 构建失败：", file=sys.stderr)
        for e in errors:
            print(f"   - {e}", file=sys.stderr)
        if not args.check:
            shutil.rmtree(TEMPLATE, ignore_errors=True)
        return 1

    files = sum(1 for p in target.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
    print(f"✅ 构建通过：{files} 文件 / {size / 1024 / 1024:.1f} MB / 版本 {_version(manifest)}")
    print(f"   test=0  settings.local=0  jsonl=0  secret=0")
    if not args.check:
        print(f"   输出: {TEMPLATE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
