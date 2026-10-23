#!/usr/bin/env bash
# 无谷歌依赖红线审计（v2 重建的核心验收条件）
#
# 背景：v1 的 google_mlkit_pose_detection 往包内塞了
# com.google.mlkit.common.internal.MlKitInitProvider（ContentProvider）。
# Android 在进程启动时先于 Flutter/Dart 执行 ContentProvider ——
# 无谷歌服务机型（华为）上初始化即崩，v0.15.0–v0.19.1 每版必崩。
# 本脚本在**构建产物**层面机器验证「谷歌系代码/清单组件不存在」。
#
# 用法：
#   bash tool/check_no_google.sh [APK路径]
#   缺省审计 build/app/outputs/flutter-apk/ 下最新的 app-*.apk。
#
# 退出码：0 = 干净（可交付）；1 = 发现谷歌系痕迹（禁止交付）；2 = 用法/环境错误。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
REPO_ROOT="$(cd "$APP_DIR/../.." && /bin/pwd)"

# 谷歌系特征（命中即失败）。
# 覆盖：mlkit / play services / gms / tensorflow 推理库 / 谷歌地图等。
PATTERN='com\.google|google_mlkit|play_services|googleapis|android\.gms|tensorflow|tflite|libmlkit'

fail=0
note() { echo "   $*"; }
ok()   { echo "✅ $*"; }
bad()  { echo "❌ $*"; fail=1; }

# ── 1) 依赖声明层：pubspec.yaml + pubspec.lock ──
echo "=== [1/3] 依赖声明层（pubspec.yaml / pubspec.lock）==="
lock="$APP_DIR/pubspec.lock"
for f in "$APP_DIR/pubspec.yaml" "$lock"; do
  [ -f "$f" ] || { bad "$f 不存在（pub get 都没跑？）"; continue; }
  # 先剥掉 # 注释再匹配：pubspec 里的「禁止 google_mlkit_*」警示注释
  # 本身就会命中特征词，不算依赖声明。lock 是机器生成的，无注释，此步无副作用。
  hits="$(sed -E 's/#.*$//' "$f" | grep -inE "$PATTERN" || true)"
  if [ -n "$hits" ]; then
    bad "$(basename "$f") 命中谷歌系特征："
    while IFS= read -r line; do note "     $line"; done <<< "$hits"
  else
    ok "$(basename "$f") 无谷歌系依赖"
  fi
done

# ── 2) 清单层：合并后的 AndroidManifest.xml（aapt dump xmltree）──
# MlKitInitProvider 这类组件活在合并清单里 —— 这是 v1 事故的直接现场。
apk="${1:-}"
if [ -z "$apk" ]; then
  # 优先 arm64-v8a（手机交付目标），其次最新构建产物
  apk="$(ls -t "$APP_DIR"/build/app/outputs/flutter-apk/app-*arm64-v8a*.apk 2>/dev/null | head -1 || true)"
  [ -z "$apk" ] && apk="$(ls -t "$APP_DIR"/build/app/outputs/flutter-apk/app-*.apk 2>/dev/null | head -1 || true)"
fi
if [ -z "${apk:-}" ] || [ ! -f "$apk" ]; then
  echo "⚠️ 未找到 APK（先跑 bash tool/build_apk.sh），跳过 [2/3][3/3]，只做声明层审计。"
  exit "$fail"
fi
apk="$(cd "$(dirname "$apk")" && /bin/pwd)/$(basename "$apk")"
echo "=== [2/3] 清单层（合并 AndroidManifest.xml，aapt dump xmltree）==="

AAPT=""
for bt in 36.0.0 34.0.0; do
  c="$REPO_ROOT/.tooling/android-sdk/build-tools/$bt/aapt"
  [ -x "$c" ] && { AAPT="$c"; break; }
done
if [ -z "$AAPT" ]; then
  AAPT="$(command -v aapt2 || command -v aapt || true)"
fi
if [ -z "$AAPT" ]; then
  bad "找不到 aapt/aapt2（.tooling/android-sdk/build-tools 缺失？）—— 清单层无法审计"
  exit 1
fi

manifest_hits="$("$AAPT" dump xmltree "$apk" AndroidManifest.xml 2>/dev/null | grep -inE "$PATTERN" || true)"
if [ -n "$manifest_hits" ]; then
  bad "合并清单命中谷歌系组件（这正是 v1 崩溃形态）："
  while IFS= read -r line; do note "     $line"; done <<< "$manifest_hits"
else
  ok "合并清单无任何 com.google* 组件/权限/服务/接收器"
fi

# 包名/版本确认（交付核对用）
echo "--- badging ---"
"$AAPT" dump badging "$apk" 2>/dev/null | grep -E "^(package|application-label):" || true

# ── 3) 原生库层：APK 内的 .so 文件名（tensorflow/mlkit 推理库会带特征名）──
echo "=== [3/3] 原生库层（APK 内 .so 文件名）==="
so_hits="$(unzip -l "$apk" 2>/dev/null | grep -E '\.so$' | grep -iE "tensorflow|tflite|mlkit|gms" || true)"
if [ -n "$so_hits" ]; then
  bad "APK 内发现谷歌系原生库："
  while IFS= read -r line; do note "     $line"; done <<< "$so_hits"
else
  ok "APK 内无谷歌系 .so"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ 无谷歌依赖审计通过：$(basename "$apk") 可交付"
else
  echo "❌ 无谷歌依赖审计失败：$(basename "$apk") 禁止交付（见上方 ❌ 项）"
fi
exit "$fail"
