#!/usr/bin/env bash
# 出 APK（debug 签名）+ 无谷歌依赖红线审计
#
# 用法：
#   bash tool/build_apk.sh                # release + split-per-abi（全 ABI）+ 审计
#   bash tool/build_apk.sh release arm64  # release + 只 arm64（🔴 出包推荐：
#                                          #   v0.7.0 起带 OpenCV 原生库，全 ABI = 每 ABI 各编一次
#   bash tool/build_apk.sh debug          # debug 包（开发机 attach 用）
#
# 交付模式与 v1 相同：release 构建 + debug 签名（无签名基础设施，
# debug 凭据是公开的，自用机手测足够；正式签名 S6 再配）。
# --split-per-abi 只出手机要的 arm64-v8a 大小，避免 fat 包的体积浪费。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
REPO_ROOT="$(cd "$APP_DIR/../.." && /bin/pwd)"
TOOLING="$REPO_ROOT/.tooling"

export HOME="$TOOLING/home"
export PUB_CACHE="$TOOLING/pub-cache"
# ⚠️ 关键：macOS 上 JVM 的 user.home 不跟 $HOME 走（取系统账户目录），
# 不设 GRADLE_USER_HOME 的话 gradle wrapper 会去写 $真实家目录/.gradle。
export GRADLE_USER_HOME="$TOOLING/gradle"
export ANDROID_HOME="$TOOLING/android-sdk"
export ANDROID_SDK_ROOT="$TOOLING/android-sdk"
export PATH="$TOOLING/flutter/bin:$PATH"
# JDK 装在仓库内（目录名带版本号，macOS 版还嵌一层 Contents/Home）
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME:-/nonexistent}/bin/java" ]; then
  repo_java="$(find "$TOOLING/jdk" -type f -name java -path "*/bin/java" 2>/dev/null | head -1 || true)"
  [ -n "$repo_java" ] && {
    export JAVA_HOME="$(dirname "$(dirname "$repo_java")")"
    export PATH="$JAVA_HOME/bin:$PATH"
  }
fi

# 确保 debug keystore 存在（标准 Android debug 凭据，任何环境可复现）
KEYSTORE="$APP_DIR/android/app/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
  echo "生成 debug keystore: $KEYSTORE"
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$KEYSTORE" -alias androiddebugkey \
    -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android \
    -dname "CN=Android Debug,O=Android,C=US"
fi

# 默认出 release（与 v1 交付同一模式：release 构建 + debug 签名），
# --split-per-abi：fat debug 包里有 46MB 的 kernel_blob + 15MB 的
# Vulkan 验证层 + 三种 CPU 架构，167MB；手机只需要 arm64-v8a。
mode="${1:-release}"
abi="${2:-all}"   # all = --split-per-abi（全 ABI）；arm64 = 只编 arm64（出包推荐，OpenCV 只编一次）
cd "$APP_DIR"
out_dir="build/app/outputs/flutter-apk"
if [ "$abi" = "arm64" ]; then
  # --target-platform 产出单包 app-<mode>.apk（只含 arm64）
  flutter build apk --"$mode" --target-platform android-arm64
  out_file="app-$mode.apk"
else
  # --split-per-abi 产出各 ABI 分包，手机要的是 arm64-v8a 那个
  flutter build apk --"$mode" --split-per-abi
  out_file="app-arm64-v8a-$mode.apk"
fi
# 守卫查**本次实际产出**的文件（index：2026-10-20 修复——原先 arm64 模式
# 也查 split 文件名，会命中上次全 ABI 构建留下的旧包，把过期 APK 当交付物）。
[ -f "$out_dir/$out_file" ] || { echo "❌ 构建产物缺失: $out_dir/$out_file"; exit 1; }

echo
echo "构建完成（arm64，手机用这个）: $APP_DIR/$out_dir/$out_file"
ls -la "$out_dir"/app-*-$mode.apk || true
# 红线审计：发现谷歌系痕迹 → 非零退出，禁止交付
bash "$SCRIPT_DIR/check_no_google.sh" "$APP_DIR/$out_dir/$out_file"
