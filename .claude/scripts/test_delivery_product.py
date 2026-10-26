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


def test_flow_doc_is_user_facing(product):
    """使用说明是写给用户看的：任务导向、可照抄执行，不是实现者手册。"""
    flow = product / "docs" / "FLOW.md"
    assert flow.is_file(), "缺 docs/FLOW.md"
    text = flow.read_text(encoding="utf-8")

    # 用户旅程必须有：上手 / 发起 / 澄清 / 发生什么 / 离开 / 验收 / 客户报告 / 排障
    for kw in ("30 秒上手", "发起一个目标", "AI 会问你一次", "你的项目会发生什么",
               "你能离开多久", "回来怎么验收", "给客户的交付报告", "出问题了怎么办",
               "它不做什么"):
        assert kw in text, f"使用说明缺用户小节: {kw}"

    # 可照抄的命令（用户真正会敲的）
    assert "/lx-goal" in text
    assert "report --format client" in text
    assert "resume .omc/tasks/" in text

    # 两个核心机制要用用户语言讲到
    assert "固定地址" in text, "任务地址机制未以用户语言呈现"
    assert "task-isolated" in text, "独立分支隔离未以用户可见方式呈现"

    # 不得泄漏实现细节 / 治理内部语汇（这些属于代码注释与 ADR，不属于用户文档）
    forbidden = ("_link_ledger", "_check_worktree_scope", "resolve_task_document",
                 "_TASK_NAME_RE", "enter_isolation_if_complete", "人类裁决", "第 13 道")
    leaked = [f for f in forbidden if f in text]
    assert leaked == [], f"使用说明泄漏实现细节: {leaked}"

    # 完整版入口（产品 → 完整 CarrorOS 的漏斗）
    assert "github.com/NinesunLiang/Sylph" in text


def test_worktree_isolation_wired_in_product(product):
    """隔离能力必须真随包发出去：创建器 + 门禁 + 链接逻辑都在。"""
    wt = product / ".claude" / "scripts" / "worktree_utils.py"
    assert wt.is_file(), "缺 worktree_utils.py"
    wt_text = wt.read_text(encoding="utf-8")
    assert "_link_ledger" in wt_text, "缺账本反向链接实现"
    assert "WORKTREES_DIR" in wt_text
    checks = (product / ".claude" / "hooks" / "pretool_gates" / "checks.py").read_text(encoding="utf-8")
    assert "_check_worktree_scope" in checks, "缺 worktree-scope 门禁"
    tp = (product / ".claude" / "scripts" / "lib" / "task_paths.py").read_text(encoding="utf-8")
    assert "_TASK_NAME_RE" in tp, "缺任务名校验"
    assert "resolve_task_document" in tp, "缺任务地址解析"


def test_readme_points_to_flow_and_repo(product):
    text = (product / "README.md").read_text(encoding="utf-8")
    assert "CARROROS-FLOW.md" in text, "README 应指明装完后的使用说明文件名"
    assert "github.com/NinesunLiang/Sylph" in text, "README 应保留仓库链接"
    assert "curl | bash" in text or "管道执行" in text, "需说明为何不推荐管道执行"
    # 不把产品写成"残缺版"：不得出现与其它版本的对比/劝退话术
    for bad in ("想要完整版", "刻意做小", "门槛劝退", "25 道门禁"):
        assert bad not in text, f"README 不得出现削弱产品的表述: {bad}"


def test_installer_deploys_flow_doc(product):
    """流程文档必须在安装后落到目标根目录（不能只躺在包里）。"""
    body = (product / "install.sh").read_text(encoding="utf-8")
    assert "CARROROS-FLOW.md" in body, "安装器应把流程文档装到目标根目录"
    assert (product / "docs" / "FLOW.md").is_file()


def test_single_file_installer_built(product):
    """一行命令部署：dist/ 下必须有自解压单文件安装器。"""
    build = _load(PKG / "build.py", "product_build_selfextract")
    prod = _load(PKG / "build_product.py", "product_selfextract")
    manifest = build.yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    installer = prod.make_selfextract(product, manifest)
    assert installer.is_file()
    text = installer.read_text(encoding="utf-8")
    # 头部必须有退出哨兵，否则 shell 会把 base64 当命令执行
    assert "\nexit 0\n" in text, "自解压脚本缺 exit 哨兵"
    assert "#===BASE64_PAYLOAD===" in text
    assert installer.stat().st_size > 100_000
