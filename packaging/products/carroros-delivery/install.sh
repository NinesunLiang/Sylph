#!/usr/bin/env bash
# CarrorOS Delivery 安装器
#
# 用法: bash install.sh [目标目录] [--force]
#
# 装什么：lx-goal 目标模式 + 任务文档系统 + 令牌系统 + 抗 compact 恢复 + hooks 门禁。
# 不动什么：你的代码、你的依赖、你的 .gitignore 里既有的行。
#
# 目标目录可以是**已有的项目**（这就是设计意图）。仅当其中已存在 .claude/ 时
# 才要求 --force，避免覆盖你已有的治理文件。

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET=""
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || TARGET="$(pwd)"

command -v python3 >/dev/null 2>&1 || die "缺少 python3，请先安装（本脚本不自动装）"

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[ "$TARGET" = "/" ] && die "拒绝安装到根目录"
[ -d "$HERE/.claude" ] || die "安装源不完整：找不到 $HERE/.claude（请重新组装产品包）"

if [ -d "$TARGET/.claude" ] && [ "$FORCE" -ne 1 ]; then
  die "目标已存在 .claude/：$TARGET
     若确认要覆盖治理文件，加 --force 重试（不会删除你的其它文件）"
fi

info "安装到：$TARGET"

# ── 拷贝治理层（.claude 整目录 + 根文档）──
cp -R "$HERE/.claude" "$TARGET/.claude"
for f in AGENTS.md CLAUDE.md LICENSE; do
  [ -f "$HERE/$f" ] || continue
  if [ -f "$TARGET/$f" ] && [ "$FORCE" -ne 1 ]; then
    cp "$HERE/$f" "$TARGET/$f.carroros-new"
    warn "已存在 $f，安装版另存为 $f.carroros-new（不覆盖你的原文件）"
  else
    cp "$HERE/$f" "$TARGET/$f"
  fi
done
info "治理层已复制"

# ── 使用说明：装成单一文件，绝不碰你项目里已有的 README.md ──
if [ -f "$HERE/README.md" ]; then
  cp "$HERE/README.md" "$TARGET/CARROROS-FLOW.md"
  info "使用说明：CARROROS-FLOW.md（30 秒上手 / 目标怎么写 / 回来怎么验收 / 出问题怎么办）"
fi

# ── .omc 骨架（幂等，不写数据）──
mkdir -p "$TARGET/.omc/state" "$TARGET/.omc/tasks" "$TARGET/.omc/tokens" "$TARGET/.omc/audit"
info ".omc 骨架就绪（tokens / tasks / audit / state）"

# ── .gitignore 追加（不重复）──
GI="$TARGET/.gitignore"
[ -f "$GI" ] || : > "$GI"
for entry in ".claude" ".omc"; do
  if grep -qxF "$entry" "$GI"; then
    info ".gitignore 已含 $entry"
  else
    printf '%s\n' "$entry" >> "$GI"
    info ".gitignore 已追加 $entry"
  fi
done

# ── 自检 ──
missing=0
for f in ".claude/scripts/carros_base.py" ".claude/scripts/token_lifecycle.py" \
         ".claude/hooks/pretool-gate.py" ".claude/hooks/hook-launcher.py" \
         ".claude/skills/lx-goal/scripts/lx-goal.py"; do
  [ -f "$TARGET/$f" ] || { warn "自检缺失：$f"; missing=1; }
done
[ "$missing" -eq 0 ] && info "自检通过：五大系统文件齐备"

echo
info "安装完成。下一步："
echo "  1) 自检：      cd \"$TARGET\" && python3 .claude/scripts/carros_base.py status"
echo "  2) 起目标：    让 AI 执行 /lx-goal \"<目标>\"；或 python3 .claude/scripts/carros_base.py init --task-mode goal"
echo "  3) 查目标状态：python3 .claude/skills/lx-goal/scripts/lx-goal.py status --task-dir <任务目录>"
echo "  4) 出交付报告：python3 .claude/skills/lx-goal/scripts/lx-goal.py report --format client --out 交付报告.md"
echo "  5) 读宪法：    AGENTS.md + README.md"
