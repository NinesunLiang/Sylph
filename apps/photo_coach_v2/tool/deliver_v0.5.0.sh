#!/usr/bin/env bash
# 摄影助手 v2 · v0.5.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/versions/，
#       并更新版本记录（add-only，不覆盖旧文件）。幂等：重复跑安全。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.5.0.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.5.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.5.0.txt" <<EOF
摄影助手 v2 · v0.5.0 (build 2005)
========================================

⚠️ 这是 v2 App 的**覆盖升级**（同包名 com.photocoach.photo_coach_v2）
  直接安装即可，会覆盖 v0.4.0，数据不受影响。

代码版本: $(git -C "$APP_DIR/../../.." rev-parse --short HEAD 2>/dev/null || echo 未知)（分支 photo-coach-v2-rebuild）
sha256:   $SHA
测试:     431 个用例全绿 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查）

这一版有什么（三模块职责重构）
------------------------------------------------

职责按「人 / 环境 / 拍」拆开，三个 tab 各管一段：

1. 教练 tab = 环境：
   · 送一张照片 → 点「让 AI 给建议」（没填 Key 走本地规则离线兜底）
   · 出「环境方案」：构图 / 角度 / 站位 / 光线 / 距离
   · 出方案后多了一个「发送到拍摄页」按钮：点一下只把人带到拍摄页，
     方案写进共享态，不偷偷跳页。

2. 拍摄 tab = 拍：
   · 收到教练的方案后：顶部出现方案条（去哪·含高度 / 方向），
     可展开看光线 / 人站哪 / 远近，可清除。
   · 有方案（哪怕没姿势）自动画目标框 + 开实时引导。
   · 对齐后点快门 → 跳系统相机拍（App 静默退后台，v0.4.0 的流程不变）。

3. 姿势 tab = 人：
   · 姿势建议文案改为「送到拍摄页」，流程上排在教练（环境）之后。

标准流程：教练（环境方案）→ 姿势（人）→ 拍摄（对位 + 跳系统相机）。

装完试（逐条回报，方便定位）：
  1. 点图标能打开、不闪退（底线）
  2. 教练 tab 送一张照片 → 点「让 AI 给建议」→ 出方案卡
     （没填 Key 应带「本地规则」标）
  3. 出方案后点「发送到拍摄页」→ 跳到拍摄 tab，顶部有方案条
  4. 拍摄 tab 有目标框 + 实时引导（没选姿势也有框）
  5. 点快门 → 跳系统相机（回归，v0.4.0 的行为不变）
  6. 姿势 tab 随便点一个姿势 → 正常（回归）
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.5.0 (build 2005)  ← 三模块职责重构版

要装的 APK：
  versions/摄影助手v2-v0.5.0.apk
  （同包名覆盖升级，直接装即可）

这个版本改了什么：
  · 教练 = 环境（出方案后「发送到拍摄页」只导航，方案含目标框）
  · 拍摄 = 拍（收到方案自动画框 + 实时引导，对齐后跳系统相机）
  · 姿势 = 人（文案对齐「送到拍摄页」）
  详情：versions/摄影助手v2-v0.5.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ 这一版的核心流程：教练出环境方案 → 姿势给人建议 → 拍摄对位后跳系统相机。
验收 6 件事：打开 / 教练出方案 / 发送到拍摄页有方案条 / 自动目标框 /
  跳系统相机回归 / 姿势回归。
EOF

# RELEASES.md 追加 v2 v0.5.0 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.5.0 (build 2005) —— $(date '+%Y-%m-%d %H:%M')

> 三模块职责重构（F2）：按「人 / 环境 / 拍」拆分三个 tab 的职责边界。
> 教练负责环境方案（构图/角度/站位/光线/距离），姿势负责人，拍摄负责拍。
> 教练出方案后「发送到拍摄页」按钮只做导航；方案（含目标框）写入共享态，
> 拍摄页消费：方案条（去哪·含高度/方向）+ 有建议即自动目标框 + 实时引导。
> prompt 四项（构图/角度/站位/光线）各自 30 字，站位必须含手机具体高度。

- **APK**: \`versions/摄影助手v2-v0.5.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 431 pass / analyze 0 issue（新增教练投射闭环用例：送图→分析→
  「发送到拍摄页」只导航+建议入共享态；camera_page_test 方案弹层断言对齐通用化）
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层）
- **权限**: 无新增

### 这一版有什么

「环境 / 人 / 拍」三分：教练页出方案后新增「发送到拍摄页」（FilledButton，
点一下只切 tab，不自动跳）；拍摄页 _buildPlanBar 方案条（去哪·含高度/方向一行，
弹层看光/人站哪/远近，可清除）+ 有建议即自动目标框与实时引导（不再要求有姿势）；
姿势页文案「送到拍摄页」。标准流程：教练（环境）→ 姿势（人）→ 拍摄（对位+跳系统相机）。
EOF
)
if grep -q "【v2 重建】v0.5.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  echo "RELEASES.md 已有 v0.5.0 段落，跳过（幂等）"
else
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v0.5.0 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
echo
echo "装完请在手机上验 6 件事（详见 versions/摄影助手v2-v0.5.0.txt 末尾）："
echo "  打开 / 教练出方案 / 发送到拍摄页有方案条 / 自动目标框 /"
echo "  跳系统相机回归 / 姿势回归"
