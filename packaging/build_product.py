#!/usr/bin/env python3
"""build_product.py — 组装「CarrorOS Delivery」第一个产品。

与全量发行包（build.py + manifest.yaml）互不影响：
  · 全量包 = 8.x 全家桶（12 skill + 全部治理）
  · 本产品 = 1.x 交付版（lx-goal + 文档 + 令牌 + 抗compact + hooks）

用法：
  python3 packaging/build_product.py            # 组装到 packaging/products/carroros-delivery/
  python3 packaging/build_product.py --check    # 只自检不写盘

组装后的产品目录自带 install.sh，可直接：
  bash packaging/products/carroros-delivery/install.sh /path/to/your-project
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent
MANIFEST = PKG / "manifest-delivery.yaml"
PRODUCT_SRC = PKG / "product"                     # 产品专属文件（README/install/skills 索引）
OUT = PKG / "products" / "carroros-delivery"

PRODUCT_NAME = "CarrorOS Delivery"

SELFEXTRACT_HEADER = """#!/usr/bin/env bash
# CarrorOS Delivery 安装器（自解压单文件）
# 版本：__VERSION__ | 构建：__COMMIT__ | 文件：__FILES__ 个 / __SIZE__
#
# 用法：
#   bash carroros-delivery-install.sh [目标目录] [--force]
#   curl -fsSL <本文件 URL> | bash -s -- [目标目录]
#
# 装什么：lx-goal 目标模式 / 任务文档 / 令牌 / 抗 compact / hooks 门禁（五套系统）
# 不装什么：其它技能、示例应用、评测数据、运行时数据、密钥
# 平台：macOS / Linux / WSL（Windows 原生不支持，治理代码依赖 fcntl）

set -euo pipefail
GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'; RED='\\033[0;31m'; NC='\\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

TARGET=""
FORCE=""
for arg in "$@"; do
  case "$arg" in
    --force) FORCE="--force" ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || TARGET="$(pwd)"

command -v python3 >/dev/null 2>&1 || die "缺少 python3，请先安装"
command -v tar >/dev/null 2>&1 || die "缺少 tar"

# 自解压包必须能读到自己：管道执行时 $0 会变成 bash，payload 取不到。
case "${0##*/}" in
  bash|sh|-) die "不支持管道执行（curl | bash）。
     请先下载再运行（也更安全，你可以先看一遍脚本）：
       curl -fsSL <本文件 URL> -o carroros-delivery-install.sh
       bash carroros-delivery-install.sh <目标目录>" ;;
esac
[ -r "$0" ] || die "无法读取自身：$0（请下载后以文件方式运行）"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
info "解包到临时目录…"

python3 - "$0" "$TMP" <<'PYEOF'
import base64, io, sys, tarfile
src, dst = sys.argv[1], sys.argv[2]
# 分隔标记用「拼接」构造，避免它在本段源码里字面出现而被提前 split 截断。
marker = "#===BASE64" + "_PAYLOAD==="
raw = open(src, "r", encoding="utf-8").read()
payload = raw.split(marker, 1)[1].strip()
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(payload)), mode="r:gz") as tar:
    tar.extractall(dst)
print("unpacked")
PYEOF

[ -f "$TMP/product/install.sh" ] || die "包内缺少 install.sh（安装包损坏）"
echo
bash "$TMP/product/install.sh" "$TARGET" $FORCE || exit 1

# 关键：payload 紧跟在本行之后，必须在此退出，否则 shell 会把 base64 当成命令执行
exit 0
"""


def make_selfextract(dest: Path, manifest: dict) -> Path:
    """把组装好的产品打成 tar.gz，base64 塞进单文件脚本（一行命令部署）。"""
    import base64
    import io
    import tarfile

    build_mod = _load_build()
    dist = dest / "dist"
    if dist.exists():          # 防二次构建把上次的安装器打进去（递归膨胀）
        shutil.rmtree(dist)

    def _skip_dist(ti):
        return None if "/dist/" in ti.name or ti.name.endswith("/dist") else ti

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(dest, arcname="product", filter=_skip_dist)
    payload = base64.b64encode(buf.getvalue()).decode("ascii")

    files = sum(1 for p in dest.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    header = (SELFEXTRACT_HEADER
              .replace("__VERSION__", build_mod._version(manifest))
              .replace("__COMMIT__", build_mod._git("rev-parse", "--short", "HEAD"))
              .replace("__FILES__", str(files))
              .replace("__SIZE__", f"{size / 1024 / 1024:.1f} MB"))
    out = dist / "carroros-delivery-install.sh"
    dist.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n#===BASE64_PAYLOAD===\n" + payload + "\n", encoding="utf-8")
    out.chmod(0o755)
    return out


def _load_build():
    spec = importlib.util.spec_from_file_location("carroros_build", PKG / "build.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _overlay_products_files(out: Path) -> list[str]:
    """把产品专属文件盖在组装结果上（README / install.sh / 精简版 skills 索引）。"""
    errors: list[str] = []
    if not PRODUCT_SRC.is_dir():
        return [f"缺少产品源目录 {PRODUCT_SRC.relative_to(ROOT)}"]

    pairs = [
        (PRODUCT_SRC / "README.md", out / "README.md"),
        (PRODUCT_SRC / "FLOW.md", out / "docs" / "FLOW.md"),
        (PRODUCT_SRC / "install.sh", out / "install.sh"),
        (PRODUCT_SRC / "skills-index.md", out / ".claude" / "skills" / "index.md"),
    ]
    for src, dst in pairs:
        if not src.is_file():
            errors.append(f"产品源文件缺失: {src.relative_to(ROOT)}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    install = out / "install.sh"
    if install.is_file():
        install.chmod(0o755)
    return errors


def build(check_only: bool = False) -> int:
    build_mod = _load_build()
    manifest = build_mod.yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    dest = Path(build_mod.tempfile.mkdtemp()) / "product" if check_only else OUT

    if not check_only and OUT.exists():
        shutil.rmtree(OUT)

    errors = build_mod.assemble(manifest, dest)
    if errors:
        print(f"❌ {PRODUCT_NAME} 组装失败：", file=sys.stderr)
        for e in errors:
            print(f"   - {e}", file=sys.stderr)
        if not check_only:
            shutil.rmtree(OUT, ignore_errors=True)
        return 1

    errors = _overlay_products_files(dest)
    if errors:
        print(f"❌ {PRODUCT_NAME} 产品文件缺失：", file=sys.stderr)
        for e in errors:
            print(f"   - {e}", file=sys.stderr)
        if not check_only:
            shutil.rmtree(OUT, ignore_errors=True)
        return 1

    files = sum(1 for p in dest.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    version = build_mod._version(manifest)
    print(f"✅ {PRODUCT_NAME} v{version}：{files} 文件 / {size / 1024 / 1024:.1f} MB")
    if not check_only:
        print(f"   输出: {OUT.relative_to(ROOT)}")
        print(f"   安装: bash {OUT.relative_to(ROOT)}/install.sh <目标目录>")
        installer = make_selfextract(OUT, manifest)
        print(f"   单文件: {installer.relative_to(ROOT)} "
              f"({installer.stat().st_size / 1024:.0f} KB，一行命令部署)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"组装 {PRODUCT_NAME}")
    ap.add_argument("--check", action="store_true", help="只自检，不写盘")
    args = ap.parse_args(argv)
    return build(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
