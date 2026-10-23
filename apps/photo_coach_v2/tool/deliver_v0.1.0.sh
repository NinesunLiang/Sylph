#!/usr/bin/env bash
# 摄影助手 v2 · v0.1.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/，
#       并更新版本记录（add-only，不覆盖旧文件）。
#
# 为什么要单独一个脚本：AI 会话的沙箱只能写仓库内，写不了 ~/Desktop/app/，
# 所以这一步由你在**自己的终端**里跑一次。幂等：重复跑安全（覆盖 v2 自己的文件）。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.1.0.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.1.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.1.0.txt" <<EOF
摄影助手 v2 · v0.1.0 (build 2001)
========================================

⚠️ 这是**重新新建的 v2 App**（全新包名，与旧版共存）
  包名: com.photocoach.photo_coach_v2（旧版是 com.photocoach.photo_coach）
  图标名: 摄影助手v2
  → 直接安装即可，**不用卸载旧版**，两个 App 各是各的

代码版本: $(cd "$APP_DIR/../../.." && git rev-parse --short HEAD 2>/dev/null || echo 未知)（分支 photo-coach-v2-rebuild）
sha256:   $SHA
测试:     40 个用例全过 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查）

这一版有什么（v2 从零开始，这是第一版）
----------------------------------------

1. 全新的 App，从零搭的壳，**不含任何谷歌系依赖** ——
   华为上「一启动就崩」的那一类问题在结构上不可能再发生
   （v1 崩溃元凶是 google_mlkit 塞进来的启动初始化组件）。

2. 已迁入的功能：
   · 姿势库：站 / 坐 / 躺 共 200+ 张姿势参考图，分类浏览、
     点图翻面看「镜头 / 动作 / 表情 / 为什么好看」指导
   · 点「发到拍摄」→ 切到拍摄页（拍摄页本版还是占位，v0.2.0 迁入）

3. 还没有的（按里程碑逐个迁入）：
   · v0.2.0 拍摄（相机 + 相册）
   · v0.3.0 教练（拍照后 AI 建议，需配 DeepSeek key）
   · v0.5.0 实时引导（取景时实时提示）
   · v1.0.0 与旧版 v0.19.2 功能对齐（唯一砍掉：本机姿态测量，
     那是 ML Kit 的能力，v2 无谷歌依赖故不可得）

装完试（这一版就验一件事）：
  点图标 → 能不能打开、不闪退。姿势库能翻图就算合格。
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.1.0 (build 2001)  ← 重新新建的 v2 App

要装的 APK：
  versions/摄影助手v2-v0.1.0.apk

这个版本改了什么：
  versions/摄影助手v2-v0.1.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ v2 是全新 App（包名 com.photocoach.photo_coach_v2）：
  直接安装即可，与旧版（摄影助手）共存，不用卸载。
  这一版只有一个验收点：华为上能不能打开、不闪退。
EOF

# RELEASES.md 追加 v2 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.1.0 (build 2001) —— $(date '+%Y-%m-%d %H:%M')

> 全新 App（分支 photo-coach-v2-rebuild），包名 com.photocoach.photo_coach_v2，
> 与旧版（摄影助手）共存。背景：v1 的 google_mlkit 在无谷歌服务机型（华为）
> 上一启动就崩，删 provider 后仍不可靠 —— 按用户决定，重建一个**零谷歌依赖**的 App，
> 功能渐进迁入（v0.1.0 姿势库 → v0.2.0 拍摄 → v0.3.0 教练 → v0.5.0 实时引导 → v1.0.0 对齐）。

- **APK**: \`versions/摄影助手v2-v0.1.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 40 pass / analyze 0 issue
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层：依赖声明 / 合并清单 / 原生库）

### 这一版有什么

全新 App 首版：姿势库（站/坐/躺 200+ 参考图，点图翻面看指导，可发往拍摄页占位）。
拍摄/教练/实时引导按里程碑迁入。华为可正常启动是这一版的验收点。
EOF
)
if grep -q "【v2 重建】v0.1.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  echo "RELEASES.md 已有 v2 段落，跳过追加（幂等）"
else
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v2 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
