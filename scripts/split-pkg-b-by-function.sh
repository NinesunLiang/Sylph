#!/usr/bin/env bash
# split-pkg-b-by-function.sh — 把 PKG-B 材料按函数边界切成 ~15 个 md
# 输出: improve_plan/CarrorOS_second_time/round1/materials/pkg-b-split/
# 规则:每个文件含完整函数/完整小文件,保留原始行号;每文件 <200KB;全部脱敏。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

OUT="improve_plan/CarrorOS_second_time/round1/materials/pkg-b-split"
rm -rf "$OUT"
mkdir -p "$OUT"
HEAD_SHA=$(git rev-parse HEAD)

redact() { sed -E 's/sk-[A-Za-z0-9]{16,}/<REDACTED>/g'; }

new_file() { # $1=文件名 $2=标题 $3=内容说明
  CUR="$OUT/$1"
  printf '# %s\n\n> 基线: `%s`(+工作区未提交改动) | PKG-B 函数级分片 | %s\n> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号\n\n' \
    "$2" "$HEAD_SHA" "$3" > "$CUR"
}

emit_range() { # $1=path $2=起 $3=止
  printf '\n## `%s` 第 %s-%s 行\n\n```python\n' "$1" "$2" "$3" >> "$CUR"
  nl -ba "$1" | sed -n "${2},${3}p" | redact >> "$CUR"
  printf '```\n' >> "$CUR"
}

emit_full() { # $1=path
  printf '\n## `%s`(全文)\n\n```\n' "$1" >> "$CUR"
  nl -ba "$1" | redact >> "$CUR"
  printf '```\n' >> "$CUR"
}

emit_cmd() { # $1=标题 $2=命令(行内容截断至 1000 字符防日志单行爆炸,行号/文件名完整)
  printf '\n## %s\n\n命令: `%s`\n\n```\n' "$1" "$2" >> "$CUR"
  eval "$2" 2>&1 | cut -c1-1000 | redact >> "$CUR" || true
  printf '```\n' >> "$CUR"
}

CB=.claude/scripts/carros_base.py
PG=.claude/hooks/pretool-gate.py

# 01-04 carros_base.py 四分(函数边界: 1-588 / 589-923 / 924-1694 / 1695-末)
new_file 01-carros_base-part1.md "carros_base.py [1/4]" "token CAS 助手/audit/cmd_init(第 1-588 行)"
emit_range $CB 1 588
new_file 02-carros_base-part2.md "carros_base.py [2/4] ★验证核心" "cmd_status/cmd_tick/_run_dual_judge/**cmd_verify 788-864**/cmd_report(第 589-923 行)"
emit_range $CB 589 923
new_file 03-carros_base-part3.md "carros_base.py [3/4]" "cmd_archive/cmd_lint/cmd_bench/cmd_gate/dispatch-poll-collect-cancel(第 924-1694 行)"
emit_range $CB 924 1694
new_file 04-carros_base-part4.md "carros_base.py [4/4]" "cmd_oracle/cmd_fallback/cmd_plan/cmd_auto/cmd_token_write/main(第 1695-2382 行)"
emit_range $CB 1695 2382

# 05-06 pretool-gate.py 两分(函数边界: 1-542 / 543-末)
new_file 05-pretool-gate-part1.md "pretool-gate.py [1/2] ★_check_verified" "助手/**_check_verified 254-278**/sensitive/fallback/action/plan/edit-scope 门(第 1-542 行)"
emit_range $PG 1 542
new_file 06-pretool-gate-part2.md "pretool-gate.py [2/2] ★verify-gate 门" "_check_verify_gate 543/oracle 门/文档质量/G2-G6/main(第 543-879 行)"
emit_range $PG 543 879

# 07-09 gpt 点名的全文文件
new_file 07-verify_gate-full.md "verify_gate.py 全文" "孤儿验证门,403 行"
emit_full .claude/scripts/verify_gate.py
new_file 08-oracle_gate-both.md "oracle_gate.py 双副本" "双源复制实证:两个目录逐字节比对"
emit_full .omc/scripts/oracle_gate.py
emit_full .claude/scripts/oracle_gate.py
new_file 09-oracle_engine-both.md "oracle_engine.py 双副本" "同上"
emit_full .omc/scripts/oracle_engine.py
emit_full .claude/scripts/oracle_engine.py

# 10-11 六处重复验证候选
new_file 10-runtime_verify.md "runtime_verify.py ×2" "重复验证实现候选"
emit_full .claude/scripts/runtime_verify.py
emit_full .claude/scripts/runtime_verify2.py
new_file 11-verify-tests.md "verify_tests + feature_verify + test-verify-gate" "验证实现与现测试(现测试测的是漂移副本)"
emit_full .claude/scripts/verify_tests.py
emit_full .omc/scripts/feature_verify.py
emit_full scripts/test-verify-gate.py

# 12 grep 证据集(源码目录,行号级)
new_file 12-grep-evidence.md "grep 证据集" "--pipeline / R6 / _check_verified 调用点 / 验证引用(源码目录)"
emit_cmd "--pipeline 全部行号" "grep -rnE -I --exclude-dir=__pycache__ --exclude-dir=improve_plan --exclude-dir=artifacts --exclude-dir=audit --exclude-dir=state --exclude-dir=repos -- '--pipeline' .claude .omc scripts benchmark 2>/dev/null | head -60"
emit_cmd "R6 全部行号(源码与规则)" "grep -rnE -I --exclude-dir=__pycache__ --exclude-dir=artifacts --exclude-dir=audit --exclude-dir=state 'R6' .claude .omc scripts 2>/dev/null | head -60"
emit_cmd "_check_verified 定义与全部调用点" "grep -rnE '_check_verified' .claude .omc scripts 2>/dev/null | grep -v __pycache__"
emit_cmd "verify_gate/oracle_gate 引用(源码目录)" "grep -rnE 'verify_gate|oracle_gate' .claude/scripts .claude/hooks .omc/scripts scripts 2>/dev/null | grep -v __pycache__ | head -80"

# 13 git 信息
new_file 13-git-info.md "git 基线信息" "HEAD/status/ls-files/.gitignore"
emit_cmd "HEAD" "git rev-parse HEAD"
emit_cmd "status --short" "git status --short"
emit_cmd "ls-files" "git ls-files"
emit_full .gitignore

# 14 skill 验证契约 + 注册表
new_file 14-skills-and-registries.md "验证类 skill 契约 + 注册表" "lx-validate-skill/lx-rpe/lx-oma + 三份 registry + SKILLS.md"
emit_full .claude/skills/lx-validate-skill/SKILL.md
emit_full .claude/skills/lx-rpe/SKILL.md
emit_full .claude/skills/lx-oma/SKILL.md
emit_full .claude/skills/references/oma/pipeline-contract.md
emit_full .claude/references/feature-registry.yaml
emit_full .claude/schemas/registry.yaml
emit_full .claude/skills/skill-dependencies.yaml
emit_full .claude/skills/SKILLS.md

# 15 hook 配置与小脚本
new_file 15-settings-and-hooks.md "hook 注册配置 + hook 小脚本" "settings.json(脱敏)/全部 .sh"
emit_full .claude/settings.json
for f in $(find .claude -name '*.sh' -not -path '*__pycache__*'); do
  emit_full "$f"
done

# 00 INDEX(最后生成,汇总所有文件的 sha256+字节)
{
printf '# PKG-B 函数级分片索引\n\n> 基线: `%s`(+工作区未提交改动) | 生成: 2026-07-19\n' "$HEAD_SHA"
printf '> 拆分规则:只按函数/文件边界切,不切任何函数体;行号=原文件真实行号;全部脱敏。\n\n'
printf '## 阅读顺序与验收要点\n\n'
printf '| 文件 | 内容 | gpt 需求映射 |\n|---|---|---|\n'
printf '| 01-04 | carros_base.py 四分 | **cmd_verify 完整函数在 02**(788-864) |\n'
printf '| 05-06 | pretool-gate.py 两分 | **_check_verified 在 05**(254-278);verify-gate 门在 06(543-) |\n'
printf '| 07 | verify_gate.py 全文 | 点名证据 |\n'
printf '| 08-09 | oracle_gate/oracle_engine 双副本 | 孤儿裁决+双源实证 |\n'
printf '| 10-11 | 其余验证实现+测试 | 六处重复验证取证 |\n'
printf '| 12 | grep 证据集 | --pipeline/R6/调用点行号 |\n'
printf '| 13 | git 信息 | ls-files/status/HEAD |\n'
printf '| 14 | skill 契约+注册表 | 验证契约统一范围 |\n'
printf '| 15 | hook 配置+脚本 | 注册与执行约定 |\n\n'
printf '## 完整性校验\n\n```\n'
( cd "$OUT" && shasum -a 256 *.md | grep -v 00-INDEX )
printf '```\n\n## 字节数\n\n```\n'
( cd "$OUT" && wc -c *.md | grep -v 00-INDEX )
printf '```\n'
} > "$OUT/00-INDEX.md"

echo "== 生成完毕 =="
ls -la "$OUT"
echo "-- 超过 200KB 的文件(应为空) --"
find "$OUT" -name '*.md' -size +200k
