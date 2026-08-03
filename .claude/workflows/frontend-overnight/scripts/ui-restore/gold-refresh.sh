#!/bin/bash
# GOLD REFRESH — 原型真值采集（低频：原型变更时才跑）
# 用法: bash .claude/workflows/frontend-overnight/scripts/ui-restore/gold-refresh.sh [task] [proto-url]
# 铁律：gold 视口必须与 task.json viewport 一致（measure 采集同视口），否则坐标 diff 全是垃圾
# 通用化：proto URL / 视口 / DSF 全部读 .omc/ui-autopilot/<task>/task.json；proto-url 参数可覆盖
set -euo pipefail

TASK="${1:-home_page}"
DIR=".claude/workflows/frontend-overnight/scripts/ui-restore"
GOLD=".omc/ui-autopilot/${TASK}/gold"
CFG=".omc/ui-autopilot/${TASK}/task.json"

if [ ! -f "$CFG" ]; then
  echo "ERROR: 缺少任务配置 $CFG（按 STYLE-DIFF-MECHANISM.md §十一 创建）" >&2
  exit 1
fi

# 从 task.json 读 proto/viewport/dsf（jq 不一定装 → node 兜底）
# 多断点（§十二）：viewports[] 存在时逐断点采集，文件名加 -<w>x<h> 后缀；单断点保持 legacy 命名
GOLD_CLICK_TEXT="$(node -e "const c=require('./$CFG'); console.log(c.goldClickText || '')")"
read -r PROTO_URL DSF <<< "$(node -e "
const c = require('./$CFG');
console.log([c.proto || '', c.dsf ?? 2].join(' '));
")"
PROTO_URL="${2:-$PROTO_URL}"
if [ -z "$PROTO_URL" ]; then
  echo "ERROR: task.json 未配 proto 且未传 proto-url 参数" >&2
  exit 1
fi

VPS="$(node -e "
const c = require('./$CFG');
const vps = Array.isArray(c.viewports) && c.viewports.length
  ? c.viewports
  : [{ w: c.viewport?.w ?? 1510, h: c.viewport?.h ?? 860 }];
const multi = vps.length > 1;
vps.forEach(v => console.log([v.w, v.h, multi ? '-' + v.w + 'x' + v.h : ''].join(' ')));
")"

mkdir -p "$GOLD"

echo "$VPS" | while read -r VW VH SUF; do
  echo "[1/2] extracting computed styles → $GOLD/proto-styles${SUF}.json (${VW}x${VH}, proto 慢流式 wait 40s)"
  EXTRA=()
  if [ -n "$GOLD_CLICK_TEXT" ]; then EXTRA+=(--click-text "$GOLD_CLICK_TEXT"); fi
  node "$DIR/extract-styles.mjs" "$PROTO_URL" "$GOLD/proto-styles${SUF}.json" --dismiss-modal --vw "$VW" --vh "$VH" --wait 40000 "${EXTRA[@]}"

  echo "[2/2] capturing screenshot → $GOLD/proto${SUF}.png"
  node "$DIR/capture-impl.mjs" "$PROTO_URL" "$GOLD/proto${SUF}.png" --wait 40000 --dismiss-modal --vw "$VW" --vh "$VH" --dsf "$DSF"
done

echo "gold refreshed → $GOLD"
