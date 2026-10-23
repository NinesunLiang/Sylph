#!/usr/bin/env bash
# 摄影助手 v2 · v0.7.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/versions/，
#       并更新版本记录（add-only，不覆盖旧文件）。幂等：重复跑安全。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.7.0.sh

set -euo pipefail

# 防 C locale 下 bash 把 $VAR 后紧跟的 UTF-8 字符首字节吞进变量名（unbound variable）
export LC_ALL=C.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.7.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
GIT_HASH=$(git -C "$APP_DIR/../.." rev-parse --short HEAD 2>/dev/null || echo 未知)
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.7.0.txt" <<EOF
摄影助手 v2 · v0.7.0 (build 2007)
========================================

⚠️ 这是 v2 App 的**覆盖升级**（同包名 com.photocoach.photo_coach_v2）
  直接安装即可，会覆盖 v0.6.0，数据不受影响。

代码版本: ${GIT_HASH}（分支 photo-coach-v2-rebuild，三版工作已补提交）
sha256:   $SHA
测试:     456 个用例全绿 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查）

这一版有什么（面部光影教练——教练长了「眼睛」）
------------------------------------------------

以前教练看光线，是看整张照片的平均亮度猜的。
现在它会先在手机里找到人脸，再量「脸上」的光——
照片不出手机、不联网、离线可用。

1. 分析完照片，方案下面多一张「📐 面部光影（手机量出来的，不是模型判断）」
   · 五档光：逆光 / 过曝 / 欠曝 / 侧光 / 平光
   · 每档给具体调整建议（换方向 / 降低曝光 / 加补光 等）

2. 找脸失败时诚实降级（不崩、不装懂）：
   · 没找到脸 → 卡片写「没找到脸，给不了判断」
   · 脸太小 / 模型加载失败 → 同样给提示，原建议照常输出

3. 人脸检测在手机上跑（YuNet 模型 228KB 打包 + OpenCV 开源 C++ 库）
   · APK 比 v0.6.0 大约 21MB（OpenCV 原生库，一次性代价）

装完试（逐条回报，方便定位）：
  1. 点图标能打开、不闪退（底线）
  2. 教练 tab 送一张有脸的照片 → 点「让 AI 给建议」→ 出方案卡
  3. 方案下出现「面部光影」卡（有脸的照片 → 五档之一 + 建议）
  4. 送一张没有脸的照片 → 面部光影卡显示「没找到脸」（不崩）
  5. 点「发送到拍摄页」→ 跳拍摄页，顶部方案条（v0.5.0 回归）
  6. 拍摄 tab / 姿势 tab 正常（回归）
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.7.0 (build 2007)  ← 面部光影教练版

要装的 APK：
  versions/摄影助手v2-v0.7.0.apk
  （同包名覆盖升级，直接装即可）

这个版本改了什么：
  · 教练分析照片时先找脸（手机本地），再量「脸上」的光线
  · 新增「📐 面部光影」卡：逆光/过曝/欠曝/侧光/平光 五档 + 具体建议
  · 照片不出手机、离线可用；找脸失败诚实提示，不装懂
  详情：versions/摄影助手v2-v0.7.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ 验收 6 件事：打开 / 送有脸照片出面部光影卡 / 送没脸照片诚实提示 /
  发送到拍摄页回归 / 拍摄回归 / 姿势回归。
EOF

# RELEASES.md 追加 v2 v0.7.0 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.7.0 (build 2007) —— $(date '+%Y-%m-%d %H:%M')

> 面部光影教练（端上）：opencv_dart 2.2.2（YuNet）找脸 + 纯 Dart 五档光影判定。
> 照片不出手机、离线可用；检测失败（没脸/脸太小/模型加载失败）诚实降级，
> 不崩不装懂。新增 _FaceLightCard 端上测量卡；prompt 注入【本地测量·面部光影】段。
> 依赖：opencv_dart 2.2.2 钉版（2.3.1 需 Dart≥3.13，本 SDK 3.12.x 不动）+
> YuNet 模型 228KB 进 assets/models/；arm64 APK +21MB。

- **APK**: \`versions/摄影助手v2-v0.7.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 456 pass / analyze 0 issue（face_light 9 + face_detector 12 新增；
  投射闭环测试修复：scrollUntilVisible 语义 = 构建即停，按钮被新卡片顶出屏外 21.5px，
  改手动拖到中心进视野后 tap 命中）
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层）
- **权限**: 无新增（人脸检测纯端上，不需要相机权限）

### 这一版有什么

教练页：送照片 → 分析 → 方案卡下新增「📐 面部光影（手机量出来的，不是模型判断）」——
YuNet 端上找脸 + 脸部网格亮度 → 逆光/过曝/欠曝/侧光/平光 五档判定 + 具体调整建议；
AI prompt 注入本地测量段，模型回答会参考手机量出的光。v0.5.0/v0.6.0 工作同批补提交
（git 88bf059）。
EOF
)
if grep -q "【v2 重建】v0.7.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  echo "RELEASES.md 已有 v0.7.0 段落，跳过（幂等）"
else
  if [ ! -f "$DEST_DIR/RELEASES.md" ]; then
    # 历史欠账：v0.5.0/v0.6.0 交付时未建 RELEASES.md（目录里没有），
    # 这里补一个完整 v2 历史头，再追加 v0.7.0。
    cat > "$DEST_DIR/RELEASES.md" <<'HISTORY'
# 摄影助手 v2 · 版本历史

> v2 重建线（无谷歌依赖，包名 com.photocoach.photo_coach_v2）。
> v1 线（摄影助手 v0.2.3~v0.19.2）与本文件无关，见各版 txt。

## 【v2 重建】v0.5.0 (build 2005) —— 三模块职责重构
- 教练=环境方案 / 姿势=人 / 拍摄=对位+系统相机；方案「发送到拍摄页」投射闭环
- 详见 versions/摄影助手v2-v0.5.0.txt

## 【v2 重建】v0.6.0 (build 2006) —— 拍照秘诀模块
- 6 招秘诀卡（光线/角度/距离/构图/高度/时机，SVG 插图，离线、零 token）
- 详见 versions/摄影助手v2-v0.6.0.txt
HISTORY
    echo "✅ 补建 RELEASES.md（含 v0.5.0/v0.6.0 历史头）"
  fi
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v0.7.0 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
echo
echo "装完请在手机上验 6 件事（详见 versions/摄影助手v2-v0.7.0.txt 末尾）："
echo "  打开 / 送有脸照片出面部光影卡 / 送没脸照片诚实提示 /"
echo "  发送到拍摄页回归 / 拍摄回归 / 姿势回归"
