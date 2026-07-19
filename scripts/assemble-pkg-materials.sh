#!/usr/bin/env bash
# assemble-pkg-materials.sh — 为 CarrorOS 三模型优化委员会生成材料包
# 输出: improve_plan/CarrorOS_second_time/round1/materials/{shared,pkg-a,pkg-b,pkg-c}.md
# 所有输出经 sk-* 脱敏。幂等:每次全量重建。
set -euo pipefail

OUT="improve_plan/CarrorOS_second_time/round1/materials"
mkdir -p "$OUT"

HEAD_SHA=$(git rev-parse HEAD)
DATE="2026-07-19"

redact() { sed -E 's/sk-[A-Za-z0-9]{16,}/<REDACTED>/g'; }

# 输出一个文件全文(带行号),标题为相对路径
emit_file() { # $1=dest $2=path $3=标题备注(可空)
  local dest="$1" path="$2" note="${3:-}"
  if [[ ! -f "$path" ]]; then
    printf '\n### `%s`\n\n(文件不存在)\n' "$path" >> "$dest"
    return 0
  fi
  printf '\n### `%s`%s\n\n```\n' "$path" "$note" >> "$dest"
  nl -ba "$path" | redact >> "$dest"
  printf '```\n' >> "$dest"
}

emit_range() { # $1=dest $2=path $3=起 $4=止 $5=备注
  local dest="$1" path="$2" from="$3" to="$4" note="${5:-}"
  printf '\n### `%s` 第 %s-%s 行%s\n\n```\n' "$path" "$from" "$to" "$note" >> "$dest"
  nl -ba "$path" | sed -n "${from},${to}p" | redact >> "$dest"
  printf '```\n' >> "$dest"
}

emit_head() { # $1=dest $2=path $3=行数
  local dest="$1" path="$2" n="$3"
  printf '\n### `%s`(前 %s 行)\n\n```\n' "$path" "$n" >> "$dest"
  nl -ba "$path" | head -"$n" | redact >> "$dest"
  printf '```\n' >> "$dest"
}

emit_cmd() { # $1=dest $2=标题 $3=命令
  local dest="$1" title="$2" cmd="$3"
  printf '\n### %s\n\n命令: `%s`\n\n```\n' "$title" "$cmd" >> "$dest"
  eval "$cmd" 2>&1 | redact >> "$dest" || printf '(命令退出码 %s)\n' "$?" >> "$dest"
  printf '```\n' >> "$dest"
}

header() { # $1=dest $2=包名 $3=说明
  printf '# %s 材料包\n\n> 基线: `%s` | 生成: %s | 密钥已脱敏为 <REDACTED>\n> %s\n' \
    "$2" "$HEAD_SHA" "$DATE" "$3" > "$1"
}

# ============ shared ============
S="$OUT/shared.md"
header "$S" "shared(三方共用)" "仓库级真相源;本机无 rg,验证引用搜索以 grep -rnE 等价实现"
emit_cmd "$S" "TRACKED FILES" "git ls-files"
emit_cmd "$S" "STATUS" "git status --short"
emit_cmd "$S" "HEAD" "git rev-parse HEAD"
emit_cmd "$S" "ROOT LISTING" "ls -la"
emit_file "$S" ".gitignore"
# 验证引用全量搜索(本机无 rg,用 grep -rnE 等价实现)
# 防自吞:输出先写 /tmp,grep 完成后再移入;并排除 improve_plan(非源码,且是输出目录)
RG_OUT="$OUT/shared-rg-validation.txt"
RG_TMP=$(mktemp /tmp/carroros-rg-XXXXXX)
grep -rnE --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=vendor --exclude-dir=dist \
  --exclude-dir=build --exclude-dir=improve_plan \
  'verify_gate|oracle_gate|cmd_verify|_check_verified|--pipeline|R6|S1|verified|verification|验证|证据' . \
  | redact > "$RG_TMP" || true
mv "$RG_TMP" "$RG_OUT"
RG_LINES=$(wc -l < "$RG_OUT" | tr -d ' ')
printf '\n### VALIDATION REFERENCES(rg 全量)\n\n共 %s 行,全量在 `shared-rg-validation.txt`。前 200 行:\n\n```\n' "$RG_LINES" >> "$S"
head -200 "$RG_OUT" >> "$S"
printf '```\n' >> "$S"

# ============ pkg-a (opus-4.8,验证链重设计) ============
A="$OUT/pkg-a.md"
header "$A" "PKG-A(opus-4.8)" "验证链完整重设计。Q1-Q7 整合器答复见文末附录。"
emit_file "$A" ".claude/scripts/verify_gate.py" " — 孤儿,全文"
emit_range "$A" ".claude/scripts/carros_base.py" 700 900 " — cmd_verify 区域(全文见 pkg-b)"
emit_range "$A" ".claude/hooks/pretool-gate.py" 240 290 " — _check_verified 区域"
emit_range "$A" ".claude/hooks/pretool-gate.py" 530 590 " — verify-gate 门区域"
emit_file "$A" ".claude/scripts/capture_evidence.py" " — 机械证据 capture"
emit_file "$A" "scripts/test-verify-gate.py" " — 现测试(测的是漂移副本)"
emit_file "$A" ".claude/skills/lx-task-spec/SKILL.md" " — task-spec 模板/verify 规则"
emit_file "$A" ".claude/skills/TEMPLATE.md" " — skill 模板"
T=$(ls -d .omc/tokens/20260718/skill-hook-adaptive-opt 2>/dev/null || true)
if [[ -n "$T" ]]; then
  emit_file "$A" "$T/token.json" " — token CAS 样例"
  emit_file "$A" "$T/plan.md" " — plan 样例(空)"
fi
TD=$(ls -d .omc/tasks/20260714/* 2>/dev/null | head -1 || true)
if [[ -n "$TD" ]]; then
  emit_file "$A" "$TD/plan.md" " — 历史 plan 样例"
  emit_file "$A" "$TD/executor.md" " — 执行证据样例"
fi
emit_cmd "$A" "audit 日志样例(尾 15 行)" "ls .omc/state/audit/ && tail -15 \$(ls .omc/state/audit/*.jsonl | tail -1)"
emit_cmd "$A" "对抗任务库清单" "ls benchmark/tasks/10_adversarial/"
F=$(ls benchmark/tasks/10_adversarial/*.yaml 2>/dev/null | head -1 || true)
[[ -n "$F" ]] && emit_file "$A" "$F" " — 对抗任务样例"
cat >> "$A" << 'EOF'

## 附录:整合器对 Q1-Q7 的答复
- Q1: cmd_verify = `.claude/scripts/carros_base.py:788-864`(本包 700-900 行段);_check_verified = `.claude/hooks/pretool-gate.py:254-274`,调用点 :268;:543-572 为 verify-gate 门。S1 重放路径:audit 事件不绑定 task_id,读端见任意历史 VERIFIED 即放行。
- Q2: verify_gate.py = `.claude/scripts/verify_gate.py`(403 行,全文如上),生产链路零调用者(孤儿);设计意图=证据分级 E3>E2>E1>E0 + trust 模式(只认机械证据)。
- Q3: task-spec = lx-task-spec SKILL.md(如上);plan.md 模板要求每步带 `- verify:` 规则;无 JSON schema 强校验。
- Q4: 证据=executor.md(人工贴)+ .omc/state/audit/*.jsonl(机器写);无哈希/签名防篡改——这正是你要设计的 trust 模式。
- Q5: 对抗用例 = AI 绕过验证的攻击场景;现成库 benchmark/tasks/10_adversarial/(清单如上);验收:跨任务同名 S1 verify 必须 REJECTED + trust 模式下手写 executor 证据必须 REJECTED + test-verify-gate.py(重写后)exit 0。
- Q6: 边界——6 处重复验证的枚举与统一归 PKG-B;verify_gate.py 文件属主归你(PKG-A);handoff 计数失真归 PKG-C,你不依赖它。
- Q7: PreCompact hook 归 PKG-C,不在你范围。
EOF

# ============ pkg-b (gpt-5.6Sol,验证契约统一) ============
B="$OUT/pkg-b.md"
header "$B" "PKG-B(gpt-5.6Sol)" "验证契约统一。git ls-files/status/HEAD/rg 全量见 shared.md,此处为完整原文集。"
emit_file "$B" ".claude/scripts/carros_base.py" " — cmd_verify 所在,全文"
emit_file "$B" ".claude/hooks/pretool-gate.py" " — _check_verified 所在,全文"
emit_file "$B" ".claude/scripts/verify_gate.py"
emit_file "$B" ".claude/scripts/verify_tests.py"
emit_file "$B" ".claude/scripts/runtime_verify.py"
emit_file "$B" ".claude/scripts/runtime_verify2.py"
emit_file "$B" ".omc/scripts/feature_verify.py"
emit_file "$B" ".omc/scripts/oracle_gate.py" " — 双源副本 A"
emit_file "$B" ".claude/scripts/oracle_gate.py" " — 双源副本 B(与 A 比对)"
emit_file "$B" "scripts/test-verify-gate.py"
emit_cmd "$B" "含 --pipeline 的文件清单" "grep -rlE --exclude-dir=.git --exclude-dir=improve_plan -- '--pipeline' ."
emit_cmd "$B" ".claude 下全部 .sh 清单" "find .claude -name '*.sh' -not -path '*__pycache__*'"
for f in $(find .claude -name '*.sh' -not -path '*__pycache__*'); do
  emit_file "$B" "$f"
done
emit_file "$B" ".claude/skills/lx-validate-skill/SKILL.md"
emit_file "$B" ".claude/skills/lx-rpe/SKILL.md"
emit_file "$B" ".claude/skills/lx-oma/SKILL.md"
emit_file "$B" ".claude/references/feature-registry.yaml"
emit_file "$B" ".claude/schemas/registry.yaml"
emit_file "$B" ".claude/skills/skill-dependencies.yaml"
emit_file "$B" ".claude/skills/SKILLS.md"
emit_file "$B" ".claude/settings.json" " — hook 注册配置(已脱敏)"

# ============ pkg-c (grok-4.5,生命周期/handoff) ============
C="$OUT/pkg-c.md"
header "$C" "PKG-C(grok-4.5)" "生命周期/handoff 完整性。最低开工子集 A1+A2+A3+B4+B5+C7+C8 已全含。"
printf '\n## 块 A:hooks 注册与现网实现\n' >> "$C"
emit_file "$C" ".claude/settings.json" " — A1 注册表(已脱敏)"
emit_file "$C" ".claude/references/feature-registry.yaml" " — A1 宣传的 20+ 特性"
emit_cmd "$C" "A2 hook 目录列表" "ls -la .claude/hooks/"
for f in .claude/hooks/hook-launcher.sh .claude/hooks/pretool-gate.py .claude/hooks/carroros-night-deny.py \
         .claude/hooks/pretool-user-approve.py .claude/hooks/posttool-gate.py .claude/hooks/session-start.py \
         .claude/hooks/stop-flywheel.py .claude/hooks/statusline-command.sh; do
  emit_head "$C" "$f" 80
done
emit_cmd "$C" "A3 compact/session/handoff 命名文件" "find . -iname '*compact*' -o -iname '*handoff*' -o -iname '*session*' | grep -v -e node_modules -e '\.git/' -e __pycache__ | head -40"
printf '\n## 块 B:handoff 多源与计数\n' >> "$C"
emit_file "$C" ".claude/scripts/context_engine.py" " — B4 compact-write 所在,全文"
emit_file "$C" ".claude/hooks/pretool-user-approve.py" " — B4 prompt 环注入,全文"
emit_file "$C" "state/session-handoff.md" " — B4 副本 1"
emit_file "$C" ".omc/session-handoff.md" " — B4 副本 2"
emit_file "$C" ".omc/state/token.json" " — B5 计数真相源(当前 active token)"
printf '\n## 块 C:goal/ghost 状态\n' >> "$C"
emit_file "$C" ".omc/scripts/goal_state_machine.py" " — C7/C8 goal 状态机"
emit_file "$C" ".claude/skills/lx-goal/SKILL.md"
emit_file "$C" ".claude/skills/lx-ghost/SKILL.md"
emit_file "$C" ".omc/state/goal-report.md" " — goal 退出报告样例"
emit_cmd "$C" "互斥检查搜证(autonomous.active 等)" "grep -rnE 'autonomous.active|互斥|ghost.*goal|goal.*ghost' .claude .omc 2>/dev/null | grep -v __pycache__ | head -40"
printf '\n## 块 D/E:启动链路 + 测试入口\n' >> "$C"
emit_cmd "$C" "测试入口清单" "ls scripts/ && ls benchmark/*.sh 2>/dev/null"

echo "== 生成完毕 =="
wc -l "$OUT"/shared.md "$OUT"/pkg-a.md "$OUT"/pkg-b.md "$OUT"/pkg-c.md "$RG_OUT"
du -sh "$OUT"
