#!/usr/bin/env bash
# cross-platform-smoke-test.sh — SessionStart — 检测 stat 和 sed 的跨平台兼容性，永不阻断
# 检测 stat -c "%Y" (Linux) 和 stat -f "%m" (macOS)，都不存在时记录问题
# 检测 sed --version | grep GNU 判断 sed 命令
# 有兼容性问题时 flywheel_event 记录

source "$(dirname "$0")/harness_config.sh"
hc_enabled "cross_platform_smoke_test" || { echo '{"continue": true}'; exit 0; }

hc_init

HAS_PROBLEM=0

# ─── 检测 stat 命令 ───
if command -v stat &>/dev/null; then
    STAT_OUTPUT=$(stat --version 2>&1 || true)
    if echo "$STAT_OUTPUT" | grep -qi "usage\|illegal option\|invalid option\|unrecognized" 2>/dev/null; then
        # macOS stat (BSD variant) — 检查 -f "%m" 是否可用
        if ! stat -f "%m" "$0" &>/dev/null; then
            flywheel_event "cross_platform_smoke_test" "stat_macos_broken" "P3" "carror-os"
            HAS_PROBLEM=1
        fi
    else
        # Linux stat (GNU variant) — 检查 -c "%Y" 是否可用
        if ! stat -c "%Y" "$0" &>/dev/null; then
            flywheel_event "cross_platform_smoke_test" "stat_linux_broken" "P3" "carror-os"
            HAS_PROBLEM=1
        fi
    fi
else
    flywheel_event "cross_platform_smoke_test" "stat_missing" "P3" "carror-os"
    HAS_PROBLEM=1
fi

# ─── 检测 sed 命令 ───
if command -v sed &>/dev/null; then
    SED_VERSION=$(sed --version 2>&1 || true)
    if echo "$SED_VERSION" | grep -qi "gnu" 2>/dev/null; then
        # GNU sed — 标准兼容
        :
    else
        # BSD sed (macOS) — 检查 -i.bak 是否可用（常见兼容性问题）
        if ! echo "test" | sed -i.bak "s/test/ok/" /dev/null 2>/dev/null; then
            flywheel_event "cross_platform_smoke_test" "sed_bsd_issue" "P3" "carror-os"
            HAS_PROBLEM=1
        fi
    fi
else
    flywheel_event "cross_platform_smoke_test" "sed_missing" "P3" "carror-os"
    HAS_PROBLEM=1
fi

# ─── 汇总结果 ───
if [ "$HAS_PROBLEM" -eq 1 ]; then
    echo "[cross-platform-smoke-test] WARN: 检测到跨平台兼容性问题，已记录 flywheel" >&2
fi

echo '{"continue": true}'
exit 0
