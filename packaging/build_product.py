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
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"组装 {PRODUCT_NAME}")
    ap.add_argument("--check", action="store_true", help="只自检，不写盘")
    args = ap.parse_args(argv)
    return build(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
