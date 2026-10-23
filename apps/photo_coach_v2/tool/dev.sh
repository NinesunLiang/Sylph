#!/usr/bin/env bash
# 摄影助手 v2 —— 本机开发环境准备 + 验证脚本
#
# 为什么需要它：本机原本没有 Flutter。SDK 装在仓库内 `.tooling/flutter`，
# 并且要把 HOME / PUB_CACHE 指到仓库内（否则 Flutter 会去写
# `~/.config/flutter`，在某些受限环境下会直接失败）。
#
# 用法：
#   bash apps/photo_coach_v2/tool/dev.sh env      # 打印可 source 的环境变量
#   bash apps/photo_coach_v2/tool/dev.sh verify   # 跑 analyze + test（服务端迁入后含 node --test）
#   bash apps/photo_coach_v2/tool/dev.sh doctor   # 看还缺什么（Xcode / Android SDK）
#
# 相关脚本：
#   tool/check_no_google.sh  构建后机器验证「无谷歌系依赖」红线（每次出包必跑）
#   tool/build_apk.sh        出 APK + 自动跑 check_no_google.sh

set -uo pipefail

# ⚠️ 必须用 /bin/pwd，不能用内建 pwd。
# 原因（实测复现）：调用方的 PWD 是相对路径时（部分宿主/工具环境如此），
# `cd 相对脚本路径/../../..` 归一化后就是 "."，内建 pwd 原样返回 "."，
# 于是下面的 PATH 成了相对路径；子 shell 里一 `cd $APP_DIR` 就找不到 flutter，
# analyze/test 会被跳过并只报 "flutter: command not found"。
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && /bin/pwd)"
TOOLING="$REPO_ROOT/.tooling"
FLUTTER_DIR="$TOOLING/flutter"
APP_DIR="$REPO_ROOT/apps/photo_coach_v2"

export_repo_local_env() {
  export HOME="$TOOLING/home"
  export PUB_CACHE="$TOOLING/pub-cache"
  export GRADLE_USER_HOME="$TOOLING/gradle"
  export ANDROID_HOME="$TOOLING/android-sdk"
  export ANDROID_SDK_ROOT="$TOOLING/android-sdk"
  export PATH="$FLUTTER_DIR/bin:$PATH"
  # JDK 装在仓库内（目录名带版本号，macOS 版还嵌一层 Contents/Home），
  # 只能找 java 可执行文件，不能硬编码路径（与 check_device_ready.sh 同法）。
  if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME:-/nonexistent}/bin/java" ]; then
    local repo_java
    repo_java="$(find "$TOOLING/jdk" -type f -name java -path "*/bin/java" 2>/dev/null | head -1 || true)"
    if [ -n "$repo_java" ]; then
      export JAVA_HOME="$(dirname "$(dirname "$repo_java")")"
      export PATH="$JAVA_HOME/bin:$PATH"
    fi
  fi
}

cmd_env() {
  echo "export HOME=\"$TOOLING/home\""
  echo "export PUB_CACHE=\"$TOOLING/pub-cache\""
  echo "export PATH=\"$FLUTTER_DIR/bin:\$PATH\""
}

cmd_verify() {
  export_repo_local_env
  local rc=0

  echo "=== 客户端: flutter analyze ==="
  ( cd "$APP_DIR" && flutter analyze ) || rc=1

  echo "=== 客户端: flutter test ==="
  ( cd "$APP_DIR" && flutter test ) || rc=1

  # 服务端 S4 才迁入（server/server.mjs），存在才跑
  if [ -d "$APP_DIR/server" ]; then
    echo "=== 服务端: node --test ==="
    ( cd "$APP_DIR/server" && node --test ) || rc=1
  fi

  if [ "$rc" -eq 0 ]; then
    echo "=== 全部通过 ==="
  else
    echo "=== 有失败项，退出码 $rc ==="
  fi
  return "$rc"
}

cmd_doctor() {
  export_repo_local_env
  flutter doctor -v
}

case "${1:-verify}" in
  env) cmd_env ;;
  verify) cmd_verify ;;
  doctor) cmd_doctor ;;
  *) echo "用法: bash apps/photo_coach_v2/tool/dev.sh {env|verify|doctor}"; exit 2 ;;
esac
