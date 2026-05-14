#!/usr/bin/env bash
# pre-commit-self-review.sh — E6 自我矛盾防线（P2a）
# 角色：提交前的 AI 自检工具。检查 CAPTCHA 绕过(R43)、域规则误用(R42)、新 hook 注册完整性(Oracle WARN)。
# 用途：在 git commit 之前运行，预防 AI 引入自我矛盾的设计漏洞
# 不是 Hook — 是手动审查工具。不注册到 settings.json，不通过 harness.yaml 开关控制。
#
# 使用方法:
#   bash .claude/scripts/pre-commit-self-review.sh "commit message"
#   bash .claude/scripts/pre-commit-self-review.sh  # 仅检查 staged diff
#
# 输出格式:
#   ✅ PASS (a): ...   — 未发现问题
#   ⚠️ WARN (b): ...  — 非阻断性警告（exit 0 + additionalContext）
#   🔴 FAIL (c): ...  — 阻断性漏洞（exit 2）
#
# 返回码:
#   0 — 全部通过 或 仅警告
#   2 — 发现明确安全/设计漏洞

set -u
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 99

COMMIT_MSG="${1:-}"
HAS_BLOCKING=false
HAS_WARNING=false
RESULTS=""

echo "=== pre-commit-self-review: E6 自我矛盾防线 ==="
echo ""

# 获取 staged diff（即将提交的变更）
STAGED_DIFF=$(git diff --cached 2>/dev/null || echo "")
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")

# 获取新增文件列表（staged + unstaged 中 diff-filter=A 的）
NEW_FILES_STAGED=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || echo "")
NEW_FILES_UNSTAGED=$(git diff --name-only --diff-filter=A 2>/dev/null || echo "")
NEW_FILES=$(echo -e "${NEW_FILES_STAGED}\n${NEW_FILES_UNSTAGED}" | sort -u | grep -v '^$')

# 合并 diff 文本用于模式扫描
ALL_DIFF="${STAGED_DIFF}"

# 添加新文件完整内容扫描（新文件在 diff 中可能只显示添加行，但有些工具只 check 新文件名）
# 对新创建的 shell/python 文件，直接读取内容做深度扫描
NEW_SCRIPT_FILES=""
while IFS= read -r f; do
    case "$f" in
        *.sh|*.py|*.js|*.ts) NEW_SCRIPT_FILES="${NEW_SCRIPT_FILES}${f}"$'\n' ;;
    esac
done <<< "$NEW_FILES"

echo "  提交信息: ${COMMIT_MSG:-（未提供）}"
echo "  新增文件: $(echo "${NEW_FILES}" | tr '\n' ' ')"
echo ""

# ============================================================
# Check (a): CAPTCHA 设计绕过 — R43 安全门
# 检测模式：创建 AI 可从 Bash 调用的批准/授权通道
# ============================================================
echo "--- Check (a): CAPTCHA 设计绕过 ---"

A_WARNINGS=""
A_FAILURES=""
A_PASS=true

# 1. 检测 diff 中是否有脚本写入敏感批准文件
if echo "$ALL_DIFF" | grep -nE 'sensitive-approved|permission-approved' | grep -vE '^\+\+\+|^---|^diff |^index ' > /dev/null 2>&1; then
    # 检查是否在脚本文件中（非注释/readme）
    if echo "$NEW_FILES" | grep -qE '\.(sh|py|js)$'; then
        A_PASS=false
        MATCHING_FILES=$(echo "$NEW_FILES" | grep -E '\.(sh|py|js)$' | tr '\n' ' ')
        A_FAILURES="${A_FAILURES}  检测到脚本文件操作 CAPTCHA 批准文件 (sensitive-approved/permission-approved)
  R43: AI 可通过 Bash 调用创建批准标记 = 设计级安全漏洞
  涉及文件: ${MATCHING_FILES}
  请删除该机制，改用原生 permissionDecision:ask + CAPTCHA 用户输入模式
"
        HAS_BLOCKING=true
    fi
fi

# 2. 检测新脚本中是否包含 "approve" / "auto-approve" / "bypass" 等批准语义
for script_path in $NEW_SCRIPT_FILES; do
    if [ ! -f "$script_path" ]; then
        continue
    fi
    script_content=$(cat "$script_path" 2>/dev/null || echo "")
    if echo "$script_content" | grep -qiE '(approve|bypass|auto.approve|skip.gate|skip.permission)'; then
        # 排除注释中提及历史教训的情形（如 # R43: 禁止创建... 这是合法引用）
        approved_lines=$(echo "$script_content" | grep -inE '(approve|bypass|auto.approve|skip.gate)' | grep -vE '^\s*#.*(R43|教训|禁止|不)')
        if [ -n "$approved_lines" ]; then
            A_PASS=false
            A_FAILURES="${A_FAILURES}  新脚本 ${script_path} 包含批准/绕过语义
  这可能创建 AI 可调用的 CAPTCHA 批准通道 (R43)
  相关行: $(echo "$approved_lines" | head -3 | tr '\n' ';')
"
            HAS_BLOCKING=true
        fi
    fi

    # 3. 检测新脚本中是否直接读取 permission-required 并写入 permission-approved
    if echo "$script_content" | grep -qE 'permission-required' && echo "$script_content" | grep -qE 'permission-approved|sensitive-approved'; then
        A_PASS=false
        A_FAILURES="${A_FAILURES}  新脚本 ${script_path} 同时引用 permission-required 和批准文件
  这是自动批准通道的特征 (R43)
"
        HAS_BLOCKING=true
    fi
done

# 4. 检测 .zshrc/.bashrc 中是否添加批准绕过
if echo "$NEW_FILES" | grep -qE '\.(zshrc|bashrc|bash_profile|zprofile)$'; then
    for rc_file in $(echo "$NEW_FILES" | grep -E '\.(zshrc|bashrc|bash_profile|zprofile)$'); do
        if [ -f "$rc_file" ]; then
            rc_content=$(cat "$rc_file" 2>/dev/null || echo "")
            if echo "$rc_content" | grep -qE 'sensitive-approved|permission-approved|approve-sen'; then
                A_PASS=false
                A_FAILURES="${A_FAILURES}  shell rc 文件 ${rc_file} 包含 CAPTCHA 批准引用
  可能将批准工具暴露为 shell 别名/函数 (R43)
"
                HAS_BLOCKING=true
            fi
        fi
    done
fi

if [ "$A_PASS" = true ]; then
    echo "  ✅ PASS (a): 未检测到 CAPTCHA 设计绕过"
elif [ -z "$A_FAILURES" ]; then
    echo "  ⚠️ WARN (a): 模糊信号，非阻断性提示"
    HAS_WARNING=true
else
    echo "  🔴 FAIL (a): CAPTCHA 设计绕过检测"
    echo "${A_FAILURES}"
fi
echo ""

# ============================================================
# Check (b): 域规则误用 — R42 域隔离
# 检测模式：将一个域的规则错误应用到另一个域
# ============================================================
echo "--- Check (b): 域规则误用 ---"

B_PASS=true
B_WARNINGS=""
B_FAILURES=""
B_WARN_ONLY=false

# 1. 检测 diff 中是否将 hook 注册规则（settings.json 检查）应用到 skill 文件
if echo "$ALL_DIFF" | grep -nE '(settings\.json|harness\.yaml).*skill' > /dev/null 2>&1; then
    B_PASS=false
    B_WARNINGS="${B_WARNINGS}  检测到 settings.json/harness.yaml 与 skill 关联引用
  R42: Skill 不需要 settings.json 注册。SKILL.md 在 .claude/skills/<name>/ 存在 + feature-registry.yaml 引用 = 合法
  请确认这些引用不是将 hook 注册规则应用于 skill
"
    HAS_WARNING=true
fi

# 2. 检测新文件中是否用 hook 注册逻辑检查 skill 文件
for script_path in $NEW_SCRIPT_FILES; do
    if [ ! -f "$script_path" ]; then
        continue
    fi
    script_content=$(cat "$script_path" 2>/dev/null || echo "")
    # 检测脚本中是否同时引用 settings.json 和 .claude/skills/
    if echo "$script_content" | grep -qE 'settings\.json' && echo "$script_content" | grep -qE '\.claude/skills/'; then
        # 排除合法的场景：ghost 模式代码中明确区分两者的上下文
        if echo "$script_content" | grep -qE 'Hook.*zombie|Skill.*zombie|区分.*类型'; then
            B_WARN_ONLY=true
        fi
        B_PASS=false
        B_WARNINGS="${B_WARNINGS}  新脚本 ${script_path} 同时引用 settings.json 和 .claude/skills/
  R42: 确认不是将 hook 注册规则（settings.json）错误应用到 skill 验收
  如果脚本已明确区分两种类型（hook zombie vs skill zombie），可忽略此警告
"
        HAS_WARNING=true
    fi

    # 3. 检测是否有代码检查 skills 目录下的文件在 settings.json 中的注册
    if echo "$script_content" | grep -qE '\.claude/skills/.*settings\.json'; then
        B_PASS=false
        B_WARNINGS="${B_WARNINGS}  用 settings.json 注册验证 skill 文件 — 域规则误用
  R42: Skill 不需要 settings.json 注册。这是 hook 的注册规则
"
        HAS_BLOCKING=true
    fi
done

# 4. 检测 ghost mode 相关变更中是否有域混淆
if echo "$ALL_DIFF" | grep -qiE 'zombie.*(scan|detect|clean|remov)' && echo "$ALL_DIFF" | grep -qE 'settings\.json'; then
    # 检查是否明确区分了 hook 和 skill
    if ! echo "$ALL_DIFF" | grep -qE '(Hook.*zombie|Skill.*zombie|区分.*类型|different.*criteria)'; then
        B_PASS=false
        B_WARNINGS="${B_WARNINGS}  检测到僵尸清理逻辑而未区分 Hook/Skill 两种判定标准
  R42: 僵尸扫描必须区分 hook（R23 规则）和 skill（disk + feature-registry.yaml）
  建议添加类型区分逻辑，否则可能误删 skill
"
        HAS_BLOCKING=true
    fi
fi

if [ "$B_PASS" = true ]; then
    echo "  ✅ PASS (b): 未检测到域规则误用"
elif [ "$B_WARN_ONLY" = true ] && [ -z "$B_FAILURES" ]; then
    echo "  ✅ PASS (b): 域规则误用 — 脚本已明确区分，无实际问题"
elif [ -n "$B_FAILURES" ] || [ "$HAS_BLOCKING" = true -a -n "${B_WARNINGS}" ]; then
    echo "  🔴 FAIL (b): 域规则误用检测"
    echo "${B_WARNINGS}"
    echo "${B_FAILURES}"
else
    echo "  ⚠️ WARN (b): 域规则交叉引用，建议人工审查"
    echo "${B_WARNINGS}"
fi
echo ""

# ============================================================
# Check (c): 新机制完整性 — Oracle Stage 1: WARNING 级别
# 检测模式：新 hook 必须有 harness.yaml 开关 + hc_enabled 调用
# ============================================================
echo "--- Check (c): 新机制完整性 ---"

C_PASS=true
C_WARNINGS=""

# 1. 检测新增加/修改的 hook 脚本
HOOK_NEW_FILES=$(echo "$NEW_FILES" | grep -E '\.claude/hooks/[^/]+\.sh$' || echo "")
HOOK_MODIFIED_FILES=$(echo "$STAGED_FILES" | grep -E '\.claude/hooks/[^/]+\.sh$' || echo "")
HOOK_ALL_FILES=$(echo -e "${HOOK_NEW_FILES}\n${HOOK_MODIFIED_FILES}" | sort -u | grep -v '^$')

# 排除 harness_config.sh（它是共享库，不是 hook）
HOOK_ALL_FILES=$(echo "$HOOK_ALL_FILES" | grep -v 'harness_config\.sh$')

for hook_path in $HOOK_ALL_FILES; do
    hook_name=$(basename "$hook_path" .sh)
    yaml_key=$(echo "$hook_name" | tr '-' '_')
    script_content=""
    [ -f "$hook_path" ] && script_content=$(cat "$hook_path" 2>/dev/null || echo "")

    # 从 diff 中获取如果文件不存在则 fallback
    if [ -z "$script_content" ]; then
        continue
    fi

    MISSING_HC=false
    MISSING_YAML=false

    # Check (c1): 脚本是否调用 hc_enabled
    if ! echo "$script_content" | grep -qE 'hc_enabled[[:space:]]'; then
        MISSING_HC=true
    fi

    # Check (c2): harness.yaml 是否有对应开关
    if [ -f ".claude/harness.yaml" ]; then
        if ! grep -qE "hooks_enabled:\s*$" .claude/harness.yaml; then
            # 检查是否在 hooks_enabled 块下有该 key
            in_section=false
            found=false
            while IFS= read -r line; do
                if echo "$line" | grep -qE 'hooks_enabled:'; then
                    in_section=true
                    continue
                fi
                if [ "$in_section" = true ]; then
                    if echo "$line" | grep -qE '^\s'; then
                        if echo "$line" | grep -qE "^\s+${yaml_key}:"; then
                            found=true
                            break
                        fi
                    else
                        in_section=false
                    fi
                fi
            done < ".claude/harness.yaml"
            if [ "$found" = false ]; then
                MISSING_YAML=true
            fi
        fi
    fi

    if [ "$MISSING_HC" = true ] || [ "$MISSING_YAML" = true ]; then
        C_PASS=false
        C_WARNINGS="${C_WARNINGS}  ⚠️  ${hook_path}:
"
        if [ "$MISSING_HC" = true ]; then
            C_WARNINGS="${C_WARNINGS}     缺少 hc_enabled 调用 — 请添加 hc_enabled \"${yaml_key}\" || exit 0
"
        fi
        if [ "$MISSING_YAML" = true ]; then
            C_WARNINGS="${C_WARNINGS}     harness.yaml 缺少 hooks_enabled.${yaml_key} 条目
"
        fi
        C_WARNINGS="${C_WARNINGS}     （Oracle Stage 1: 这是 WARNING，非阻断 — sync 在发布时完成）
"
        HAS_WARNING=true
    fi
done

# 2. 检测 harness.yaml 自身的变更（手动关闭开关但脚本仍在）
if echo "$STAGED_FILES" | grep -q 'harness\.yaml'; then
    # 检查是否有 hooks_enabled 设置为 false 但脚本仍在 settings.json 注册
    YAML_DISABLED=$(grep -E '^\s+\w+:\s*false' .claude/harness.yaml 2>/dev/null | grep -oE '^\s+\w+' | tr -d ' ' || echo "")
    if [ -n "$YAML_DISABLED" ]; then
        for yk in $YAML_DISABLED; do
            script_name=$(echo "$yk" | tr '_' '-').sh
            if [ -f ".claude/hooks/$script_name" ] && ! echo "$script_name" | grep -q 'harness_config\.sh'; then
                if grep -q "$script_name" .claude/settings.json 2>/dev/null; then
                    C_PASS=false
                    C_WARNINGS="${C_WARNINGS}  ⚠️  ${script_name}: harness.yaml 禁用但 settings.json 仍注册
    R36: 三方同步要求 — 禁用需同步 settings.json 移除注册
    （Oracle Stage 1: WARNING 级别 — 可能是有意保留的占位）
"
                    HAS_WARNING=true
                fi
            fi
        done
    fi
fi

if [ "$C_PASS" = true ]; then
    echo "  ✅ PASS (c): 新机制完整性检查通过"
else
    echo "  ⚠️ WARN (c): 新机制完整性 — 发现可改进项"
    echo "${C_WARNINGS}"
fi
echo ""


# ============================================================
# Check (d): settings.json command 语法校验 — DF-04 防止 shell 引号损坏
# 检测模式：所有 hook command 必须通过 bash -n 语法检查
# ============================================================
echo "--- Check (d): settings.json command 语法校验 ---"

D_PASS=true
D_FAILURES=""

# 仅在 settings.json 在 staged 变更中时做深度校验
if echo "$STAGED_FILES" | grep -q 'settings\.json' || [ -f ".claude/settings.json" ]; then
    if command -v python3 &>/dev/null; then
        # 提取所有 command 字符串并做 bash -n 语法检查
        BAD_CMDS=$(python3 -c "
import json, subprocess, tempfile, os
with open('.claude/settings.json') as f:
    data = json.load(f)
bad = []
for event, matchers in data.get('hooks', {}).items():
    if isinstance(matchers, list):
        for m in matchers:
            for h in m.get('hooks', []):
                cmd = h.get('command', '')
                if not cmd:
                    continue
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tf:
                    tf.write('#!/usr/bin/env bash\n')
                    tf.write(cmd + '\n')
                    tf.flush()
                    tf_path = tf.name
                try:
                    r = subprocess.run(['bash', '-n', tf_path], capture_output=True, text=True, timeout=5)
                    if r.returncode != 0:
                        bad.append(f'{cmd[:80]}  ->  {r.stderr.strip()[:100]}')
                except Exception as e:
                    bad.append(f'{cmd[:80]}  ->  parse error: {e}')
                finally:
                    os.unlink(tf_path)
if bad:
    for b in bad[:10]:
        print(b)
" 2>/dev/null)

        if [ -n "$BAD_CMDS" ]; then
            D_PASS=false
            D_FAILURES="${D_FAILURES}  以下 settings.json command 未通过 bash -n 语法检查:
${BAD_CMDS}

  DF-04: 损坏的 shell 语法会导致 hook 无法执行，系统完全不能自愈
  修复: 用纯文本绝对路径 'bash /path/to/script.sh' 替代含引号变量展开
"
            HAS_BLOCKING=true
        fi
    else
        echo "  ⚠️ SKIP (d): python3 不可用，跳过 command 语法校验"
    fi
else
    echo "  ⏭️ SKIP (d): settings.json 未变更，跳过 command 语法校验"
fi

if [ "$D_PASS" = true ] && [ -z "$D_FAILURES" ]; then
    echo "  ✅ PASS (d): settings.json command 语法校验通过"
elif [ -n "$D_FAILURES" ]; then
    echo "  🔴 FAIL (d): settings.json command 语法错误"
    echo "${D_FAILURES}"
fi
echo ""

# ============================================================
# Final verdict
# ============================================================
echo "========================================"
if [ "$HAS_BLOCKING" = true ]; then
    echo "  VERDICT: 🔴 BLOCKING — 存在安全/设计漏洞"
    echo "  修复后重新运行此检查，确认无 FAIL 后再提交"
    echo "========================================"
    exit 2
elif [ "$HAS_WARNING" = true ]; then
    echo "  VERDICT: ⚠️ PASS WITH WARNINGS — 建议审查上述警告"
    echo "  非阻断：提交前确认警告不涉及设计级问题即可继续"
    echo "========================================"
    exit 0
else
    echo "  VERDICT: ✅ ALL PASS — 三项自检全部通过"
    echo "========================================"
    exit 0
fi
