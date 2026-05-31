#!/usr/bin/env bash
# context-compressor.sh — SessionStart — 渐进式披露：源文件精简版注入缓存
# Role: 检测源文件 mtime → 拼接精简内容 → 缓存到 .omc/state/context-cache.md
# 哲学 #1 (less is more): CLAUDE.md 指向缓存，每次会话只注入 ~3KB
# 哲学 #4 (验证): mtime 防过期

source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_compressor" || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
STATE_DIR="$PROJECT_ROOT/.omc/state"
CACHE="$STATE_DIR/context-cache.md"

mkdir -p "$STATE_DIR"

FORCE_REGEN=false

if [ ! -f "$CACHE" ]; then
    cat > "$CACHE" <<'BOOTSTRAP'
<!-- CONTEXT-COMPRESSOR: bootstrap 自动生成 -->
铁律:
1.禁止编造:断言必有file:line/命令输出,找不到→BLOCKED
2.用户裁定:验收/选型/冲突由Boss决定,AI不可自判
3.证据门禁:无VERIFIED证据禁止说"已完成/已验证"
4.Git门禁:编译→功能→报告→Boss批准→提交,跳步=回滚
5.范围冻结:一次一个Step,非核心只写TODO,越界撤销
6.隐私防线:禁读.env/私钥,禁Bash敲明文Token
7.断言真实:百分比/评分须有来源URL/file:line,无来源标注[内部自检]
8.哲学先行:问人前先过哲学7条,哲学能裁决→[哲学先行:#N→action]直接执行
#8细则:过程性问题直接执行/抉择性问题哲学裁决
禁止问:"跑X?"→[#4→执行] "A还是B?"→[#2→选A]
哲学优先级:#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)
软完成语禁令→必须VERIFIED:
应该没问题/基本完成/理论上/看起来正常/差不多了/之前验证过
should be fine/basically done/mostly complete/seems to work
操作约束:
-编辑:Read-before-Edit|current-scope越界→BLOCKED
-Bash:git commit/push|rm -rf|sudo→BLOCKED
-完成:VERIFIED|evidence≥60|fresh≤300s
-隐私:.env|Token|密钥→BLOCKED
权威:Boss指令>项目宪法>PRD>Skill>设计文档>代码
---
BOOTSTRAP
    echo "[context-compressor] bootstrap: 最小脱水上下文已生成" >&2
    FORCE_REGEN=true
fi

_stat_mtime() { stat -f%m "$1" 2>/dev/null || stat -c%Y "$1" 2>/dev/null || echo 0; }

SRC_FILES="
$PROJECT_ROOT/AGENTS.md
$CLAUDE_DIR/anti-patterns.md
$CLAUDE_DIR/claude-next.md
$CLAUDE_DIR/kernel.md
"

NEED_REGEN=false
if [ ! -f "$CACHE" ]; then
    NEED_REGEN=true
else
    CACHE_MTIME=$(_stat_mtime "$CACHE")
    set -f
    for src_file in $SRC_FILES; do
        [ ! -f "$src_file" ] && continue
        SRC_MTIME=$(_stat_mtime "$src_file")
        if [ "$SRC_MTIME" -gt "$CACHE_MTIME" ]; then
            NEED_REGEN=true
            break
        fi
    done
fi

if [ "$NEED_REGEN" = false ] && [ "$FORCE_REGEN" = false ]; then
    flywheel_event "context_compressor" "cache_hit" "L0" || true
    exit 0
fi

flywheel_event "context_compressor" "regenerating" "L1" || true

> "$CACHE"
{
    echo "<!-- CONTEXT-COMPRESSOR: $(date +%Y-%m-%dT%H:%M:%S) 自动生成 -->"
    echo "<!-- 源文件: AGENTS.md + anti-patterns.md + claude-next.md + kernel.md -->"
    echo "<!-- 渐进式披露: 注入精简版，完整版请 Read 源文件 -->"
    echo ""
} >> "$CACHE"

ALL_OK=true
set -f
for src_file in $SRC_FILES; do
    if [ -f "$src_file" ]; then
        head -80 "$src_file" >> "$CACHE"
        { echo ""; echo "---"; echo ""; } >> "$CACHE"
    else
        echo "[context-compressor] ⚠️ 源文件缺失: $src_file" >&2
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    CACHE_SIZE=$(wc -c < "$CACHE" | tr -d ' ')
    echo "[context-compressor] ✅ 缓存已更新: $CACHE ($CACHE_SIZE bytes)" >&2
else
    echo "[context-compressor] ⚠️ 部分源文件缺失，缓存不完整" >&2
fi
exit 0
