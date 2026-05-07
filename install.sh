#!/bin/bash
# Carror OS 根级安装入口
# 版本：v6.1.8-stable | 日期：2026-05-07
# 委托到 scripts/install.sh（实际的安装逻辑）
# 用法：bash install.sh [base|enhanced|harness|skills]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/install.sh" "$@"
