#!/usr/bin/env bash
# resolve-doc-path.sh — 根据路径注册表解析文件路径
# 用法: FILE_TYPE=auto-score-report bash .claude/scripts/resolve-doc-path.sh [date]
# 返回: 解析后的路径到 stdout; 未注册类型返回 "UNREGISTERED" 到 stderr + exit 1
set -euo pipefail

FILE_TYPE="${FILE_TYPE:-}"
DATE="${1:-$(date +%Y-%m-%d)}"
TS="$(date +%Y%m%d-%H%M%S)"

if [ -z "$FILE_TYPE" ]; then
    echo "UNREGISTERED: FILE_TYPE not set" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY="$PROJECT_ROOT/.claude/reference/path-registry.yaml"

# 优先从 YAML 注册表读取
if [ -f "$REGISTRY" ] && command -v ${PYTHON_BIN:-python3} &>/dev/null; then
    RESULT=$(${PYTHON_BIN:-python3} -c "
import yaml, sys, os
try:
    with open('$REGISTRY') as f:
        reg = yaml.safe_load(f)
    entry = reg.get('paths', {}).get('$FILE_TYPE', {})
    if entry:
        print(entry.get('path', ''))
    else:
        print('UNREGISTERED')
except:
    print('YAML_ERROR')
" 2>/dev/null)

    if [ "$RESULT" = "UNREGISTERED" ]; then
        echo "UNREGISTERED: $FILE_TYPE 未在路径注册表中" >&2
        exit 1
    elif [ "$RESULT" = "YAML_ERROR" ] || [ -z "$RESULT" ]; then
        # 降级到硬编码
        :
    else
        # 替换模板变量
        RESULT="${RESULT//\{date\}/$DATE}"
        RESULT="${RESULT//\{ts\}/$TS}"
        echo "$RESULT"
        exit 0
    fi
fi

# 降级: YAML 不可用时的硬编码路径 (保持系统可用性)
case "$FILE_TYPE" in
    auto-score-report)    echo ".omc/state/scores/$DATE/auto-score.json" ;;
    score-ux-report)      echo ".omc/state/scores/$DATE/score-ux.json" ;;
    smoke-test-log)       echo ".omc/state/smoke/$DATE/harness-smoke.log" ;;
    smoke-failure)        echo ".omc/state/smoke/$DATE/smoke-failure-$TS.json" ;;
    capability-test-log)  echo ".omc/state/capability/$DATE/capability-matrix-test.log" ;;
    completion-evidence)  echo ".omc/state/evidence/.completion-evidence-$TS" ;;
    plan-document)        echo ".omc/plans/$DATE/" ;;
    task-state)           echo ".omc/state/tasks/$TS/" ;;
    dogfood-record)       echo ".omc/state/dogfood/dogfood-$DATE.yaml" ;;
    capability-test-report) echo "docs/internal/capability-test-report-$DATE.md" ;;
    mode-token)           echo ".omc/state/tokens/$FILE_TYPE.json" ;;
    file-lock)            echo ".omc/locks/default.lock" ;;
    *)                    echo "UNREGISTERED: $FILE_TYPE 未在路径注册表中" >&2; exit 1 ;;
esac
