#!/usr/bin/env bash
# 摄影助手 v2 · v0.2.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/，
#       并更新版本记录（add-only，不覆盖旧文件）。
#
# 为什么要单独一个脚本：AI 会话的沙箱只能写仓库内，写不了 ~/Desktop/app/，
# 所以这一步由你在**自己的终端**里跑一次。幂等：重复跑安全（覆盖 v2 自己的文件）。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.2.0.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.2.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.2.0.txt" <<EOF
摄影助手 v2 · v0.2.0 (build 2002)
========================================

⚠️ 这是**重新新建的 v2 App**（全新包名，与旧版共存）
  包名: com.photocoach.photo_coach_v2（旧版是 com.photocoach.photo_coach）
  图标名: 摄影助手v2
  → 直接安装即可，**不用卸载旧版**，两个 App 各是各的
  → 也可以直接覆盖安装 v0.1.0

代码版本: $(cd "$APP_DIR/../../.." && git rev-parse --short HEAD 2>/dev/null || echo 未知)（分支 photo-coach-v2-rebuild）
sha256:   $SHA
测试:     299 个用例全过 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查，含相机插件）

这一版有什么（v2 渐进迁移第 3 站：完整拍摄体验）
------------------------------------------------

1. 真实拍摄页（相机已接上，替换 v0.1.0 的「迁移中」占位）：
   · 后摄取景预览，点屏幕对焦
   · 测光 / 场景识别：自动量亮度，给 EV 修正建议 + 场景预设
     （逆光 / 人像 / 室内 / 夜景）
   · 右上角齿轮 → 设置页：曝光补偿 / 变焦 / 闪光灯 / 对焦
   · 拍照存相册：照片文件名带姿势名（方便按姿势整理）

2. **实时引导**（旧版的 F5 能力，应你确认提前到本版一起迁入）：
   · 拍摄页开「实时引导」→ 取景框上出现主体位置叠加层，
     实时提示你该往哪挪，把人摆到姿势要求的位置
   · 纯本地像素分析（900ms 一帧，无 AI、无联网）—— 华为上完全可用

3. 姿势 → 拍摄 全链路打通：
   姿势页选姿势 →「送到拍摄页」→ 拍摄页出现姿势叠加层 + 引导目标框

还没有的（按里程碑继续）：
   · v0.3.0 教练（拍照后 AI 点评建议，需配 DeepSeek key）
   · v1.0.0 与旧版 v0.19.2 功能对齐（唯一砍掉：本机姿态测量，
     那是 ML Kit 的能力，v2 无谷歌依赖故不可得）

装完试（这一版请在华为上验这 6 件事，逐条回报）：
  1. 点图标 → 能打开（和 v0.1.0 一样的底线）
  2. 拍摄 tab → 弹相机权限，允许后能看到取景画面
  3. 点屏幕能对焦（有对焦框动画）
  4. 按快门拍照 → 系统相册里能看到这张照片
  5. 「实时引导」按钮一点有反应（叠加层出现/消失）
  6. 姿势页送一个姿势 → 拍摄页出现姿势叠加层
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.2.0 (build 2002)  ← 重新新建的 v2 App

要装的 APK：
  versions/摄影助手v2-v0.2.0.apk

这个版本改了什么：
  versions/摄影助手v2-v0.2.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ v2 是全新 App（包名 com.photocoach.photo_coach_v2）：
  直接安装即可，与旧版（摄影助手）共存，不用卸载。
  这一版验收 6 件事：打开 / 取景 / 对焦 / 存相册 / 实时引导 / 姿势联动。
EOF

# RELEASES.md 追加 v2 v0.2.0 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.2.0 (build 2002) —— $(date '+%Y-%m-%d %H:%M')

> 渐进迁移第 3 站：拍摄（F1/F2/F3 相机链路）+ 实时引导（F5，经用户确认
> 由 v0.5.0 提前到本版，因为拍摄页与实时引导在同一页上解耦不开，而实时引导
> 是纯本地像素分析、零谷歌依赖，提前无红线风险）。

- **APK**: \`versions/摄影助手v2-v0.2.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 299 pass / analyze 0 issue（S2 的 40 个基础上，迁入拍摄/参数/设置/引导相关 15 个测试文件）
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层：依赖声明 / 合并清单 / 原生库；camera 插件无谷歌痕迹）
- **权限**: CAMERA / RECORD_AUDIO / READ_MEDIA_IMAGES / 读写存储（按 gal 官方权限表写 maxSdkVersion）；无 INTERNET（教练页 v0.3.0 才加）

### 这一版有什么

完整拍摄体验：真实取景 / 点按对焦 / 测光与场景预设 / 参数设置页 /
拍照存相册（文件名带姿势名）/ 实时引导叠加层（纯本地）/ 姿势→拍摄全链路。
教练（AI 点评）留待 v0.3.0。
EOF
)
if grep -q "【v2 重建】v0.2.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  echo "RELEASES.md 已有 v0.2.0 段落，跳过追加（幂等）"
else
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v0.2.0 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
echo
echo "装完请在华为上验 6 件事（详见 versions/摄影助手v2-v0.2.0.txt 末尾）："
echo "  打开 / 取景 / 对焦 / 存相册 / 实时引导 / 姿势联动"
