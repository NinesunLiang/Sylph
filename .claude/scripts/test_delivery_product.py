"""test_delivery_product.py — 「CarrorOS Delivery」第一个产品的边界与完整性守卫。

产品合同（本测试钉死）：
1. 五套系统齐全：lx-goal / 文档 / 令牌 / 抗compact / hooks
2. 只带一个技能：skills/ 下除 lx-goal 外不得有其它技能目录
3. 不带测试、字节码、运行时数据、密钥
4. 产品专属文件被覆盖：README（四卖点）、install.sh、skills 索引（只列 lx-goal）
5. 能按 manifest 组装且体积达标（build.assemble 自带 3MB 上限与语法检查）
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[2] / "packaging"
MANIFEST = PKG / "manifest-delivery.yaml"
PRODUCT_SRC = PKG / "product"

pytestmark = pytest.mark.skipif(
    not MANIFEST.is_file(), reason="交付版产品清单未启用"
)

REQUIRED = [
    # ① lx-goal
    ".claude/skills/lx-goal/SKILL.md",
    ".claude/skills/lx-goal/scripts/lx-goal.py",
    ".claude/skills/lx-goal/references/exit-report.md",
    # ② 文档系统
    ".claude/scripts/carros_base.py",
    # ③ 令牌系统
    ".claude/scripts/token_lifecycle.py",
    # ④ 抗 compact
    ".claude/hooks/precompact-lifecycle.py",
    ".claude/scripts/lib/handoff_writer.py",
    # ⑤ hooks
    ".claude/hooks/pretool-gate.py",
    ".claude/hooks/hook-launcher.py",
    ".claude/hooks/pretool_gates/checks.py",
    # 指令层与接线
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    ".claude/settings.json",
    ".claude/kernel.md",
]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    build = _load(PKG / "build.py", "product_build")
    prod = _load(PKG / "build_product.py", "product_build_product")
    dest = tmp_path_factory.mktemp("delivery") / "product"
    manifest = build.yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    errors = build.assemble(manifest, dest)
    assert errors == [], f"组装失败: {errors}"
    overlay_errors = prod._overlay_products_files(dest)
    assert overlay_errors == [], f"产品文件缺失: {overlay_errors}"
    return dest


def test_five_systems_present(product):
    missing = [rel for rel in REQUIRED if not (product / rel).is_file()]
    assert missing == [], f"交付版缺件: {missing}"


def test_only_lx_goal_skill(product):
    skills = product / ".claude" / "skills"
    dirs = sorted(p.name for p in skills.iterdir() if p.is_dir())
    assert dirs == ["lx-goal"], f"交付版只应带 lx-goal，实际: {dirs}"


def test_product_readme_has_four_value_props(product):
    text = (product / "README.md").read_text(encoding="utf-8")
    for kw in ("过程可观测", "安全", "敢离开一天", "回来有掌控感"):
        assert kw in text, f"产品 README 缺卖点: {kw}"
    # 不得出现已被证伪的绝对化表述
    assert "密钥写不进代码" not in text, "密钥门禁是 ASK/拦截，不是绝对写不进"


def test_no_tests_bytecode_or_runtime_data(product):
    assert list(product.rglob("test_*.py")) == []
    assert list(product.rglob("__pycache__")) == []
    assert list(product.rglob("*.pyc")) == []
    assert list(product.rglob("*.jsonl")) == []
    assert not (product / ".omc").exists()
    assert not (product / ".claude" / "decisions" / "DECISIONS.md").exists()


def test_installer_and_skills_index_overlaid(product):
    installer = product / "install.sh"
    assert installer.is_file()
    body = installer.read_text(encoding="utf-8")
    assert "CarrorOS Delivery" in body
    assert "--format client" in body, "安装完成提示应包含出报告命令"
    index = (product / ".claude" / "skills" / "index.md").read_text(encoding="utf-8")
    assert "lx-goal" in index
    assert "lx-oracle" not in index, "交付版索引不得列其它技能"
