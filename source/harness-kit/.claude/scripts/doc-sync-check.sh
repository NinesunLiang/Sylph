#!/usr/bin/env bash
# doc-sync-check.sh — 文档-代码一致性全量校验 v2.0
#
# 覆盖范围:
#   - [已验证: path:line] 交叉引用完整性
#   - 裸 file:line 引用验证
#   - 数值声明 vs 实际计数（hook/skill 数量）
#   - 营销文档中的技术断言检测
#   - hooks-table / skills-catalog 与磁盘一致性
#
# Usage:
#   bash .claude/scripts/doc-sync-check.sh                  # 默认: 全部检查
#   bash .claude/scripts/doc-sync-check.sh --check-refs     # 仅交叉引用
#   bash .claude/scripts/doc-sync-check.sh --check-counts   # 仅数值声明
#   bash .claude/scripts/doc-sync-check.sh --check-marketing # 仅营销断言
#   bash .claude/scripts/doc-sync-check.sh --check-tables   # 仅 table 一致性
#   bash .claude/scripts/doc-sync-check.sh --verbose        # 详细输出
#   bash .claude/scripts/doc-sync-check.sh --json           # JSON 输出
#
# 注意: 本脚本始终 exit 0（符合 kernel.md Hook 铁律）。问题数量通过 stdout 报告。

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ISSUES=0
WARNINGS=0
VERBOSE=false
JSON_OUT=false
ISSUE_LOG_FILE="$(mktemp "${TMPDIR:-/tmp}/doc-sync-issues.XXXXXX")"

# 检查模式
DO_REFS=true
DO_COUNTS=true
DO_MARKETING=true
DO_TABLES=true

# 解析参数
for arg in "$@"; do
    case "$arg" in
        --check-refs) DO_REFS=true; DO_COUNTS=false; DO_MARKETING=false; DO_TABLES=false ;;
        --check-counts) DO_REFS=false; DO_COUNTS=true; DO_MARKETING=false; DO_TABLES=false ;;
        --check-marketing) DO_REFS=false; DO_COUNTS=false; DO_MARKETING=true; DO_TABLES=false ;;
        --check-tables) DO_REFS=false; DO_COUNTS=false; DO_MARKETING=false; DO_TABLES=true ;;
        --verbose) VERBOSE=true ;;
        --json) JSON_OUT=true ;;
    esac
done

log_issue() {
    local severity="$1"  # error / warning
    local category="$2"  # ref / count / marketing / table
    local msg="$3"
    echo "${severity}: [${category}] ${msg}" >> "$ISSUE_LOG_FILE"
    if [ "$severity" = "error" ]; then
        ISSUES=$((ISSUES + 1))
    else
        WARNINGS=$((WARNINGS + 1))
    fi
}

# ─────────────────────────────────────────────────────
# Check 1: 交叉引用完整性
# ─────────────────────────────────────────────────────
check_cross_refs() {
    local ref_count=0 valid_count=0 broken_count=0

    # 搜索范围: docs/ + .claude/reference/ + 治理文件
    local search_dirs=(
        "$ROOT/docs"
        "$ROOT/.claude/reference"
        "$ROOT/.claude"
    )

    for search_dir in "${search_dirs[@]}"; do
        if [ ! -d "$search_dir" ]; then
            continue
        fi

        # 使用 while 循环读取 grep 结果
        local grep_out
        grep_out="$(grep -rn '\[已验证:' "$search_dir" --include="*.md" 2>/dev/null || true)"
        if [ -z "$grep_out" ]; then
            continue
        fi

        while IFS= read -r line; do
            [ -z "$line" ] && continue
            ref_count=$((ref_count + 1))

            # 提取 file:line 格式: 匹配 "path:line" 或 "path"
            local doc_file
            doc_file="$(echo "$line" | cut -d: -f1)"
            local doc_line
            doc_line="$(echo "$line" | cut -d: -f2)"

            # 提取 [已验证: ...] 内的内容
            local verified_content
            verified_content="$(echo "$line" | sed -n 's/.*\[已验证:[[:space:]]*\([^]]*\)\].*/\1/p')"

            if [ -z "$verified_content" ]; then
                continue
            fi

            # 尝试提取 path:line 或仅 path
            local ref_path ref_line
            if echo "$verified_content" | grep -q ':'; then
                # 分离路径和行号（处理 range 格式 :30-34 和普通格式 :42）
                # macOS sed 需要 -E 才能支持 + 量词
                ref_line="$(echo "$verified_content" | grep -oE ':[0-9]+' | tail -1 | tr -d ':')"
                ref_path="$(echo "$verified_content" | sed -E 's/:[0-9]+-[0-9]+$//' | sed -E 's/:[0-9]+$//')"

                # 剥离路径后非路径的尾部内容: R-notation / 中文描述
                # 例如: "claude-next.md R27" → "claude-next.md"
                #       "completion-gate.sh 评分逻辑" → "completion-gate.sh"
                # 仅当空格前的部分以已知扩展名结尾时才剥离
                local clean
                clean="$(echo "$ref_path" | sed -E 's/[[:space:]].*$//')"
                if echo "$clean" | grep -qE '\.(md|sh|yaml|json|py|txt|ts|js|go|html|css)$'; then
                    ref_path="$clean"
                fi
            else
                ref_path="$verified_content"
                ref_line=""
            fi

            # 去除首尾空格
            ref_path="$(echo "$ref_path" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

            # 跳过明显的非文件路径引用（如示例/占位符）
            case "$ref_path" in
                "所有文件"|"战区"*|"file"|"path"|"..."|"") continue ;;
                "some_file"|"some_dir"|"example"|"test"|"TODO"|"REF"|"N/A") continue ;;
                *".git"*) continue ;;
            esac

                # 剥离路径后非路径的尾部内容: R-notation / 中文描述
                # 例如: "claude-next.md R27" → "claude-next.md"
                #       "completion-gate.sh 评分逻辑" → "completion-gate.sh"
                # 仅当空格前的部分以已知扩展名结尾时才剥离
                clean="$(echo "$ref_path" | sed -E 's/[[:space:]].*$//')"
                if echo "$clean" | grep -qE '\.(md|sh|yaml|json|py|txt|ts|js|go|html|css)$'; then
                    ref_path="$clean"
                fi

            # 跳过不以已知扩展名或已知目录开头的引用（减少假阳性）
            if ! echo "$ref_path" | grep -qE '\.(md|sh|yaml|json|py|txt|ts|js|go|html|css)$|^\.claude/|^docs/|^source/|^packages/|^scripts/|^rpe/|\.omc/'; then
                # 路径不含已知特征 — 可能是示例文本
                if $VERBOSE; then
                    echo "  ~ $ref_path (跳过 — 不含已知路径特征)"
                fi
                continue
            fi

            # 解析路径
            local target
            if [ "${ref_path:0:1}" = "/" ]; then
                target="$ref_path"
            else
                target="$ROOT/$ref_path"
            fi

            if [ ! -f "$target" ] && [ ! -d "$target" ]; then
                broken_count=$((broken_count + 1))
                log_issue "error" "ref" "断链: $ref_path (引用于 $doc_file:$doc_line)"
            else
                valid_count=$((valid_count + 1))
                if $VERBOSE; then
                    echo "  ✓ $ref_path ($doc_file:$doc_line)"
                fi

                # 如果指定了行号，验证该行存在
                if [ -n "$ref_line" ] && [ -f "$target" ]; then
                    local total_lines
                    total_lines="$(wc -l < "$target" 2>/dev/null || echo 0)"
                    if [ "$ref_line" -gt "$total_lines" ] 2>/dev/null; then
                        log_issue "warning" "ref" "行号偏移: $ref_path:$ref_line 超出文件 ($total_lines 行) (引用于 $doc_file:$doc_line)"
                    fi
                fi
            fi
        done <<< "$grep_out"
    done

    echo "  [交叉引用] 总计: $ref_count, 有效: $valid_count, 失效: $broken_count, 警告: $WARNINGS"
    return $broken_count
}

# ─────────────────────────────────────────────────────
# Check 2: 数值声明验证
# ─────────────────────────────────────────────────────
check_numeric_claims() {
    local count_issues=0

    # 2a: Hook 数量声明
    local actual_hooks
    actual_hooks="$(ls "$ROOT/.claude/hooks/"*.sh 2>/dev/null | wc -l | tr -d ' ')"
    # 排除 harness_config.sh（共享库）
    local hooks_minus_lib
    hooks_minus_lib=$((actual_hooks - 1))

    # 检查 CLAUDE.md 中的声明
    if [ -f "$ROOT/CLAUDE.md" ]; then
        local claude_claim
        claude_claim="$(grep -oE '[0-9]+ 个 hook' "$ROOT/CLAUDE.md" 2>/dev/null || true)"
        if [ -n "$claude_claim" ]; then
            echo "  CLAUDE.md 声称: $claude_claim"
            echo "  实际 .sh 文件: $actual_hooks (排除共享库: $hooks_minus_lib)"
        fi

        # 检查 "38 个 hook 默认激活" 声明
        if grep -q '38 个 hook 默认激活' "$ROOT/CLAUDE.md" 2>/dev/null; then
            local actual_enabled
            actual_enabled="$(grep -cE '^[[:space:]]*[a-z_]+: true$' "$ROOT/.claude/harness.yaml" 2>/dev/null || echo 0)"
            actual_enabled="${actual_enabled:-0}"
            log_issue "warning" "count" "CLAUDE.md 声称 38 个激活 hook，harness.yaml 实际 ~$actual_enabled 个 true 值 (含 sub-feature toggles)"
            count_issues=$((count_issues + 1))
        fi
    fi

    # 检查 source mirror CLAUDE.md
    if [ -f "$ROOT/source/harness-kit/CLAUDE.md" ]; then
        if grep -q '38 个 hook 默认激活' "$ROOT/source/harness-kit/CLAUDE.md" 2>/dev/null; then
            log_issue "warning" "count" "source/harness-kit/CLAUDE.md 同样声称 38 个激活 hook — 与 root 同源漂移"
            count_issues=$((count_issues + 1))
        fi
    fi

    # 2b: hooks-table 数量声明
    if [ -f "$ROOT/.claude/reference/hooks-table.md" ]; then
        if grep -q '共 40 个' "$ROOT/.claude/reference/hooks-table.md" 2>/dev/null; then
            local table_entries
            table_entries="$(grep -cE '^\|`[a-z]' "$ROOT/.claude/reference/hooks-table.md" 2>/dev/null || echo 0)"
            table_entries="${table_entries:-0}"
            log_issue "warning" "count" "hooks-table.md 声称 40 个，实际表格条目约 $table_entries 个"
            count_issues=$((count_issues + 1))
        fi
    fi

    # 2c: Skill 数量声明
    local actual_skills
    actual_skills="$(find "$ROOT/.claude/skills" -maxdepth 2 -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')"
    actual_skills="${actual_skills:-0}"

    if [ -f "$ROOT/docs/guides/cn/skills-catalog.md" ]; then
        local cn_count_claims
        cn_count_claims="$(grep -oE '[0-9]+ 个( Skill|lx-| )' "$ROOT/docs/guides/cn/skills-catalog.md" 2>/dev/null || true)"
        if [ -n "$cn_count_claims" ]; then
            echo "  skills-catalog CN 声称: $cn_count_claims"
            echo "  实际 SKILL.md: $actual_skills"
            if ! echo "$cn_count_claims" | grep -q "$actual_skills"; then
                log_issue "error" "count" "skills-catalog.md (CN) 声明的 skill 数量与磁盘 ($actual_skills) 不符"
                count_issues=$((count_issues + 1))
            fi
        fi
    fi

    if [ -f "$ROOT/docs/guides/us/skills-catalog.md" ]; then
        local us_claim
        us_claim="$(grep -oE '[0-9]+ lx- skills' "$ROOT/docs/guides/us/skills-catalog.md" 2>/dev/null || true)"
        if [ -n "$us_claim" ]; then
            echo "  skills-catalog US 声称: $us_claim"
            echo "  实际 SKILL.md: $actual_skills"
            if ! echo "$us_claim" | grep -q "$actual_skills"; then
                log_issue "error" "count" "skills-catalog.md (US) 声明的 skill 数量与磁盘 ($actual_skills) 不符"
                count_issues=$((count_issues + 1))
            fi
        fi
    fi

    # 2d: feature-registry 重复条目检测
    if [ -f "$ROOT/.claude/feature-registry.yaml" ]; then
        local registry_hooks
        registry_hooks="$(grep -cE '^[[:space:]]*- name:' "$ROOT/.claude/feature-registry.yaml" 2>/dev/null)"
        registry_hooks="${registry_hooks:-0}"
        echo "  feature-registry.yaml 总条目: $registry_hooks (实际唯一 hook/skill 应约 68)"
        if [ "$registry_hooks" -gt 100 ] 2>/dev/null; then
            log_issue "error" "count" "feature-registry.yaml 条目数 ($registry_hooks) 异常膨胀 — 疑似 snake_case/kebab-case 重复"
            count_issues=$((count_issues + 1))
        fi
    fi

    echo "  [数值声明] 发现问题: $count_issues"
    return $count_issues
}

# ─────────────────────────────────────────────────────
# Check 3: 营销文档技术断言
# ─────────────────────────────────────────────────────
check_marketing_claims() {
    local marketing_dir="$ROOT/docs/marketing"
    local marketing_issues=0

    if [ ! -d "$marketing_dir" ]; then
        echo "  [营销断言] 无营销文档目录"
        return 0
    fi

    # 搜索营销文档中的技术性数字/百分比声明（降低噪音：仅匹配明显的性能/度量声明）
    local number_claims
    number_claims="$(grep -rn '[0-9]\+\.[0-9]\+%\|[0-9]\{2,\}%\|减少.*[0-9]\|提升.*[0-9]\|节省.*[0-9]\|[0-9]\+\s*倍' "$marketing_dir" --include="*.md" 2>/dev/null || true)"

    while IFS= read -r match; do
        [ -z "$match" ] && continue
        local m_file m_line
        m_file="$(echo "$match" | cut -d: -f1)"
        m_line="$(echo "$match" | cut -d: -f2)"

        # 检查同一段是否有来源引用
        local context
        context="$(sed -n "$((m_line - 2)),$((m_line + 2))p" "$m_file" 2>/dev/null || true)"
        if echo "$context" | grep -qE '\[已验证:|file:line|来源:|source:|http'; then
            : # 有来源引用，OK
        else
            # 检查是否为常见无害数字 (日期/列表序号)
            if echo "$match" | grep -qE '202[0-9]|#[0-9]+|[0-9]+\.[0-9]+\.[0-9]+'; then
                : # 版本号/日期/序号，忽略
            elif echo "$match" | grep -qE 'v[0-9]+\.[0-9]+|第[0-9]+|[0-9]+年'; then
                : # 版本/序数/年份，忽略
            else
                log_issue "warning" "marketing" "营销文档无来源数字: $m_file:$m_line — 建议添加来源标注"
                marketing_issues=$((marketing_issues + 1))
            fi
        fi
    done <<< "$number_claims"

    echo "  [营销断言] 可疑数字声明: $marketing_issues"
    return $marketing_issues
}

# ─────────────────────────────────────────────────────
# Check 4: Hooks/Skills Table 一致性
# ─────────────────────────────────────────────────────
check_table_consistency() {
    local table_issues=0

    # 4a: hooks-table.md 中列出的 hook 是否都有对应 .sh 文件
    if [ -f "$ROOT/.claude/reference/hooks-table.md" ]; then
        local listed_hooks
        listed_hooks="$(grep -oE '[a-z][-a-z]+\.sh' "$ROOT/.claude/reference/hooks-table.md" 2>/dev/null | sort -u)"

        local missing_on_disk=0 extra_on_disk=0

        # 检查文档中列出但磁盘上缺失的
        while IFS= read -r hook_name; do
            [ -z "$hook_name" ] && continue
            if [ ! -f "$ROOT/.claude/hooks/$hook_name" ]; then
                log_issue "error" "table" "hooks-table 引用但磁盘缺失: $hook_name"
                missing_on_disk=$((missing_on_disk + 1))
            fi
        done <<< "$listed_hooks"

        # 检查磁盘上有但文档中缺失的（排除 harness_config.sh 共享库）
        local disk_hooks
        disk_hooks="$(ls "$ROOT/.claude/hooks/"*.sh 2>/dev/null | xargs -n1 basename | grep -v 'harness_config\.sh' | sort)"
        while IFS= read -r disk_hook; do
            [ -z "$disk_hook" ] && continue
            if ! echo "$listed_hooks" | grep -qF "$disk_hook"; then
                log_issue "warning" "table" "磁盘存在但 hooks-table 缺失: $disk_hook"
                extra_on_disk=$((extra_on_disk + 1))
            fi
        done <<< "$disk_hooks"

        echo "  hooks-table: 缺失于磁盘=$missing_on_disk, 缺失于文档=$extra_on_disk"
        table_issues=$((table_issues + missing_on_disk + extra_on_disk))
    fi

    # 4b: skills-catalog 中列出的 skill 是否都有对应 SKILL.md
    for catalog in "$ROOT/docs/guides/cn/skills-catalog.md" "$ROOT/docs/guides/us/skills-catalog.md"; do
        [ ! -f "$catalog" ] && continue
        local catalog_label
        catalog_label="$(basename "$(dirname "$(dirname "$catalog")")")/$(basename "$catalog")"

        local catalog_skills
        catalog_skills="$(grep -oE '`/lx-[a-z][-a-z]*`' "$catalog" 2>/dev/null | tr -d '`/' | sort -u)"

        local disk_skills
        disk_skills="$(find "$ROOT/.claude/skills" -maxdepth 2 -name "SKILL.md" 2>/dev/null | xargs -n1 dirname | xargs -n1 basename | sort)"

        local missing_in_catalog=0
        while IFS= read -r skill_name; do
            [ -z "$skill_name" ] && continue
            if ! echo "$catalog_skills" | grep -qF "$skill_name"; then
                if [ "$catalog_label" = "cn/skills-catalog.md" ]; then
                    log_issue "warning" "table" "CN catalog 缺失: $skill_name"
                else
                    log_issue "warning" "table" "US catalog 缺失: $skill_name"
                fi
                missing_in_catalog=$((missing_in_catalog + 1))
            fi
        done <<< "$disk_skills"

        echo "  $catalog_label: 缺失 skill=$missing_in_catalog"
        table_issues=$((table_issues + missing_in_catalog))
    done

    echo "  [Table 一致性] 发现问题: $table_issues"
    return $table_issues
}

# ─────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────
main() {
    echo "=== doc-sync-check v2.0 ==="
    echo ""

    local total_issues=0

    if $DO_REFS; then
        check_cross_refs
        total_issues=$((total_issues + $?))
        echo ""
    fi

    if $DO_COUNTS; then
        check_numeric_claims
        total_issues=$((total_issues + $?))
        echo ""
    fi

    if $DO_MARKETING; then
        check_marketing_claims
        total_issues=$((total_issues + $?))
        echo ""
    fi

    if $DO_TABLES; then
        check_table_consistency
        total_issues=$((total_issues + $?))
        echo ""
    fi

    # 汇总报告
    echo "════════════════════════════════════════════"
    if [ "$total_issues" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
        echo "✅ doc-sync-check: 全部通过"
    elif [ "$total_issues" -eq 0 ]; then
        echo "⚠️  doc-sync-check: $WARNINGS 个警告 (无错误)"
    else
        echo "❌ doc-sync-check: $total_issues 个错误, $WARNINGS 个警告"
    fi
    echo "════════════════════════════════════════════"

    # 输出详细问题列表
    if [ "$total_issues" -gt 0 ] || [ "$WARNINGS" -gt 0 ]; then
        echo ""
        echo "--- 问题明细 ---"
        if [ -f "$ISSUE_LOG_FILE" ]; then
            sort "$ISSUE_LOG_FILE" | while IFS= read -r log_line; do
                echo "  $log_line"
            done
        fi
    fi

    # 清理临时文件
    rm -f "$ISSUE_LOG_FILE"

    # JSON 输出模式
    if $JSON_OUT; then
        echo ""
        echo "{"
        echo "  \"errors\": $total_issues,"
        echo "  \"warnings\": $WARNINGS,"
        echo "  \"checks\": {"
        echo "    \"cross_refs\": $($DO_REFS && echo true || echo false),"
        echo "    \"numeric_claims\": $($DO_COUNTS && echo true || echo false),"
        echo "    \"marketing\": $($DO_MARKETING && echo true || echo false),"
        echo "    \"table_consistency\": $($DO_TABLES && echo true || echo false)"
        echo "  }"
        echo "}"
    fi
}

main
exit 0
