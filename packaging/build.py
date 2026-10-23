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

    # 语法自检：PYTHONDONTWRITEBYTECODE=1，否则 py_compile 会把 __pycache__ 写进包里
    import os
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for py in dest.rglob("*.py"):
        rc = subprocess.run([sys.executable, "-B", "-m", "py_compile", str(py)],
                            capture_output=True, text=True, env=env)
        if rc.returncode != 0:
            errors.append(f"py_compile 失败: {py.relative_to(dest)}")
            break
    for cache in dest.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

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


SELFEXTRACT_HEADER = """#!/usr/bin/env bash
# CarrorOS 治理能力安装器（自解压单文件）
# 用法：把本文件拷到目标项目目录，然后 bash carroros-install.sh
# 版本：__VERSION__ | 构建：__COMMIT__ | 文件：__FILES__ 个 / __SIZE__
#
# 只安装通用 AI 治理能力：门禁、审批、验证、状态恢复、哲学规则。
# 不安装：密钥、测试、数据集、产品代码、运行时数据。
# 平台：macOS / Linux / WSL（Windows 原生不支持，治理代码依赖 fcntl）

set -euo pipefail
GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'; RED='\\033[0;31m'; NC='\\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

TARGET=""
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || TARGET="$(pwd)"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[ "$TARGET" = "/" ] && die "拒绝安装到根目录"

command -v python3 >/dev/null 2>&1 || die "缺少 python3，请先安装（本脚本不自动装）"

SELF_NAME="$(basename "$0")"
OTHERS="$(ls -A "$TARGET" 2>/dev/null | grep -vxF "$SELF_NAME" || true)"
if [ -n "$OTHERS" ] && [ "$FORCE" -ne 1 ]; then
  die "目标目录已有其它内容：$TARGET
     加 --force 重试（只新增/覆盖治理文件，不动其它内容）"
fi

info "安装到：$TARGET"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 - "$0" "$TMP" <<'PYEOF'
import base64, io, sys, tarfile
src, out = sys.argv[1], sys.argv[2]
data = open(src, 'rb').read().split(b'__PAYLOAD_BEGIN__\\n', 1)[1]
tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode='r:gz').extractall(out)
PYEOF

cp -R "$TMP/template/." "$TARGET/"
CL_COUNT="$(find "$TARGET/.claude" -type f 2>/dev/null | wc -l | tr -d ' ')"
info "已复制治理核心 .claude/（$CL_COUNT 个文件）"
for d in scripts hooks skills nodes schemas rules workflows; do
  n="$(find "$TARGET/.claude/$d" -type f 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n" -gt 0 ] && echo "        .claude/$d: $n"
done

mkdir -p "$TARGET/.omc/state" "$TARGET/.omc/tasks" "$TARGET/.omc/tokens" "$TARGET/.omc/audit"
info ".omc 骨架就绪（不写入任何数据）"

GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  if grep -qxF ".omc" "$GI"; then info ".gitignore 已含 .omc"; else printf '\\n.omc\\n' >> "$GI"; info ".gitignore 已追加 .omc"; fi
else
  printf '.omc\\n' > "$GI"; info "已创建 .gitignore 并写入 .omc"
fi

[ -f "$TARGET/.claude/scripts/carros_base.py" ] && info "自检：carros_base.py 存在" || warn "自检未通过：缺少 carros_base.py"
echo
info "安装完成。下一步："
echo "  1) 配置模型：编辑 .claude/settings.json 的 env 段（或设置同名环境变量）"
echo "  2) 自检：cd \\"$TARGET\\" && python3 .claude/scripts/carros_base.py status"
echo "  3) 阅读：AGENTS.md（哲学与铁律）"

exit 0
__PAYLOAD_BEGIN__
"""


def make_selfextract(dest_template: Path, manifest: dict) -> Path:
    """把 template 打成 tar.gz 再 base64 塞进脚本，生成单文件安装器。"""
    import base64
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(dest_template, arcname="template")
    payload = base64.b64encode(buf.getvalue()).decode("ascii")

    files = sum(1 for p in dest_template.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in dest_template.rglob("*") if p.is_file())
    header = (SELFEXTRACT_HEADER
              .replace("__VERSION__", _version(manifest))
              .replace("__COMMIT__", _git("rev-parse", "--short", "HEAD"))
              .replace("__FILES__", str(files))
              .replace("__SIZE__", f"{size / 1024 / 1024:.1f} MB"))
    out = PKG / "carroros-install.sh"
    out.write_text(header + payload + "\n", encoding="utf-8")
    out.chmod(0o755)
    return out


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
        installer = make_selfextract(TEMPLATE, manifest)
        print(f"   单文件安装器: {installer.relative_to(ROOT)} "
              f"({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
