#!/usr/bin/env bash
# CarrorOS 通用治理能力安装器
# 用法: bash install.sh [目标目录] [--force]
#
# 只安装「通用 AI 治理能力」：门禁、审批、验证、状态恢复、哲学规则。
# 不安装：密钥、测试、数据集、产品代码、运行时数据。
#
# 平台支持：macOS / Linux / Windows-WSL。
# Windows 原生（cmd/PowerShell）不支持——治理代码依赖 fcntl 文件锁，该模块在 Windows 不存在。
#
# 安装包已随仓库提交（packaging/template/），克隆后可直接运行本脚本，无需构建。
# 仅当修改了 manifest 或治理源码后，才需要 python3 packaging/build.py 重新生成并提交。

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$HERE/template"

TARGET=""
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || TARGET="$(pwd)"

# ── 依赖 ──
command -v python3 >/dev/null 2>&1 || die "缺少 python3，请先安装（本脚本不自动装）"
command -v git >/dev/null 2>&1 || die "缺少 git，请先安装（本脚本不自动装）"

[ -d "$TEMPLATE" ] || die "找不到安装包：$TEMPLATE
     安装包随仓库提交，缺失说明克隆不完整；
     或运行 python3 packaging/build.py 重新生成。"

# ── 目标校验 ──
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

if [ "$TARGET" = "/" ]; then
  die "拒绝安装到根目录"
fi

if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ] && [ "$FORCE" -ne 1 ]; then
  die "目标目录非空：$TARGET
     确认无冲突后加 --force 重试（只会新增/覆盖治理文件，不动其它内容）"
fi

info "安装到：$TARGET"

# ── 拷贝治理文件 ──
cp -R "$TEMPLATE/." "$TARGET/"
info "已复制治理文件"

# ── .omc 骨架（幂等：已存在则不动）──
mkdir -p "$TARGET/.omc/state" "$TARGET/.omc/tasks" "$TARGET/.omc/tokens" "$TARGET/.omc/audit"
info ".omc 骨架就绪（不写入任何数据）"

# ── .gitignore 加一行 .omc ──
GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  if grep -qxF ".omc" "$GI"; then
    info ".gitignore 已含 .omc"
  else
    printf '\n.omc\n' >> "$GI"
    info ".gitignore 已追加 .omc"
  fi
else
  printf '.omc\n' > "$GI"
  info "已创建 .gitignore 并写入 .omc"
fi

# ── 自检 ──
if [ -f "$TARGET/.claude/scripts/carros_base.py" ]; then
  info "自检：carros_base.py 存在"
else
  warn "自检未通过：缺少 .claude/scripts/carros_base.py"
fi

if [ -f "$TARGET/.claude/settings.local.json" ]; then
  warn "检测到 settings.local.json —— 请确认其中没有硬编码密钥"
fi

echo
info "安装完成。下一步："
echo "  1) 配置模型：编辑 .claude/settings.json 的 env 段（或设置同名环境变量）"
echo "  2) 自检：cd \"$TARGET\" && python3 .claude/scripts/carros_base.py status"
echo "  3) 阅读：AGENTS.md（哲学与铁律）"
