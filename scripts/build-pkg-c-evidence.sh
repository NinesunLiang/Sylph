#!/usr/bin/env bash
# build-pkg-c-evidence.sh — 按 grok-4.5 round2 ③节脚本生成 PKG-C 证据包
# 环境适配(机械等价,非内容改写):
#   1) sha256sum → shasum -a 256(macOS 无 sha256sum;输出格式相同,sha256sum -c 可校验)
#   2) 排除 __pycache__/*.pyc(grok 的 -iname '*session*' 会匹配 session-start.cpython-*.pyc 二进制)
#   3) 全部 txt/md 经 sk-* → <REDACTED> 机械脱敏(settings.json 含明文 token,grok 原脚本无脱敏)
# 整合器范围扩展(新增,不替代 grok 原规范):
#   4) 02b/03b/05b:grok 的 find/grep 只覆盖 .claude,但 handoff/goal 真相源在
#      .omc/ 与 state/ 根目录(state/session-handoff.md、.omc/session-handoff.md、
#      .omc/scripts/goal_state_machine.py);用同一组 iname/正则模式补充
#   5) 扩展搜索排除 .omc/audit、.omc/artifacts(运行时审计日志,单文件 689KB+,非源码)
#   6) 03c:git grep 只覆盖 tracked 文件,补充 grep -rnE 覆盖未追踪文件(如 scripts/test-hook-launcher.sh)
#   7) >24000B 文件自动分片(grok 规范: split -b 24000 -d -a 3),分片加 .txt 后缀(上传器不认无扩展名)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

STAGE=/tmp/carroros-pkg-c-evidence
DEST=improve_plan/CarrorOS_second_time/round2/materials/pkg-c-evidence
rm -rf "$STAGE" "$DEST"
mkdir -p "$STAGE" "$DEST"

# ---------- grok ③ 原规范 ----------
git rev-parse HEAD > "$STAGE/00-head.txt"

find .claude/hooks -maxdepth 2 -type f -not -path '*__pycache__*' -print \
  | LC_ALL=C sort > "$STAGE/01-hooks-files.txt"

find .claude -type f \( \
  -iname '*compact*' -o \
  -iname '*handoff*' -o \
  -iname '*session*' -o \
  -iname '*subagent*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' -o \
  -iname '*snapshot*' \
\) -not -path '*__pycache__*' -print \
  | LC_ALL=C sort > "$STAGE/02-lifecycle-files.txt"

git grep -nE \
  'PreCompact|SessionEnd|SubagentStop|handoff|goal|ghost|auto-snapshot|turn-counter|compact-write|compact_write' \
  -- .claude \
  > "$STAGE/03-lifecycle-grep.txt" || test "$?" -eq 1

for file in \
  .claude/settings.json \
  .claude/references/feature-registry.yaml \
  .claude/hooks/hook-launcher.sh \
  .claude/hooks/pretool-gate.py \
  .claude/hooks/posttool-gate.py \
  .claude/hooks/session-start.py \
  .claude/hooks/stop-flywheel.py \
  .claude/hooks/statusline-command.sh
do
  if test -f "$file"; then
    printf '\n===== %s =====\n' "$file"
    nl -ba "$file"
  else
    printf '\n===== MISSING: %s =====\n' "$file"
  fi
done > "$STAGE/04-entrypoints.txt"

while IFS= read -r file; do
  test -f "$file" || continue
  printf '\n===== %s =====\n' "$file"
  nl -ba "$file"
done < "$STAGE/02-lifecycle-files.txt" \
  > "$STAGE/05-lifecycle-content.txt"

# grok ②.3-E: 真实失真样例(handoff/goal/ghost/counter 前 240 行)
while IFS= read -r file; do
  test -f "$file" || continue
  printf '\n===== %s =====\n' "$file"
  nl -ba "$file" | sed -n '1,240p'
done < <(find .claude -type f \( \
  -iname '*handoff*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' \
\) -not -path '*__pycache__*' -print | LC_ALL=C sort) \
  > "$STAGE/06-distortion-samples.txt"

# ---------- 整合器扩展(02b/03b/05b/03c) ----------
find .omc state -type f \( \
  -iname '*compact*' -o \
  -iname '*handoff*' -o \
  -iname '*session*' -o \
  -iname '*subagent*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' -o \
  -iname '*snapshot*' \
\) -not -path '*__pycache__*' \
  -not -path '.omc/audit/*' \
  -not -path '.omc/artifacts/*' \
  -print | LC_ALL=C sort > "$STAGE/02b-lifecycle-files-ext.txt"

git grep -nE \
  'PreCompact|SessionEnd|SubagentStop|handoff|goal|ghost|auto-snapshot|turn-counter|compact-write|compact_write' \
  -- .omc scripts state ':(exclude).omc/audit' ':(exclude).omc/artifacts' \
  > "$STAGE/03b-lifecycle-grep-ext.txt" || test "$?" -eq 1

# 03c: 未追踪文件补充(git grep 盲区),单行截断 1000 字符防日志单行爆炸
grep -rnE -I \
  --exclude-dir=__pycache__ \
  --exclude-dir=audit \
  --exclude-dir=artifacts \
  --exclude='*.jsonl' \
  'PreCompact|SessionEnd|SubagentStop|handoff|goal|ghost|auto-snapshot|turn-counter|compact-write|compact_write' \
  .claude .omc scripts state 2>/dev/null \
  | cut -c1-1000 > "$STAGE/03c-lifecycle-grep-untracked.txt" || test "$?" -eq 1

while IFS= read -r file; do
  test -f "$file" || continue
  printf '\n===== %s =====\n' "$file"
  nl -ba "$file"
done < "$STAGE/02b-lifecycle-files-ext.txt" \
  > "$STAGE/05b-lifecycle-content-ext.txt"

# ---------- 整合器说明(07) ----------
cat > "$STAGE/07-integrator-notes.md" << 'NOTES'
# 整合器说明（随证据包交付，非 grok 原规范内容）

1. **附件归属裁决**：你 round1 收到的是 `pkg-c.md`（正确），用户口误说成 `pkg-a.md`。你的门禁拦截正确。
2. **运行时事件支持**：当前运行时为 Claude Code，**支持 PreCompact / SessionEnd / SubagentStop 三类 hook 事件**，注册方式与现有 PreToolUse/PostToolUse 相同（settings.json 的 hooks 下按事件名注册，stdin 收 JSON，退出码语义：0=放行，2=阻断）。本包 04-entrypoints.txt 的 5 个现存 hook 即 stdin JSON 解析的现成范例。
3. **环境等价替换**：`shasum -a 256` 替代 `sha256sum`（macOS），输出格式相同，`sha256sum -c SHA256SUMS` 可直接校验。
4. **脱敏声明**：全部 txt/md 经 `s/sk-[A-Za-z0-9]{16,}/<REDACTED>/g` 机械替换（settings.json 含明文 API token）。无其他内容改动。
5. **范围扩展（整合器补充，非你的原规范）**：
   - `02b/05b`：你的 find 只扫 `.claude`，但 handoff 真相源在仓库根 `state/session-handoff.md` 与 `.omc/session-handoff.md`，goal 状态机在 `.omc/scripts/goal_state_machine.py`。已用同一组 iname 模式补充。
   - `03b`：同一正则扩展到 `.omc scripts state`（git grep，tracked）。
   - `03c`：同一正则为覆盖**未追踪文件**的补充（git grep 盲区，如 scripts/test-hook-launcher.sh）。
   - 扩展搜索排除 `.omc/audit`、`.omc/artifacts`：运行时审计/产物日志（单文件 689KB+，单行 JSON），非源码，机械排除。
6. **pyc 排除**：你的 `-iname '*session*'` 会匹配 `__pycache__/session-start.cpython-*.pyc`（二进制），已机械排除 `__pycache__`。
7. **分片规范**：>24000B 的文件已按你的规范 `split -b 24000 -d -a 3` 分片于 `parts/`，分片加 `.txt` 后缀（上传器不认无扩展名），`parts/SHA256SUMS.parts` 可校验。若 tar.gz 可上传，优先 tar.gz（自包含）。
8. **现状线索（非结论，供你验证后采纳或推翻）**：
   - 三份 handoff 候选：`state/session-handoff.md`、`.omc/session-handoff.md`，第三份（若存在）待你在 02/02b 清单中证实。
   - goal 状态机：`.omc/scripts/goal_state_machine.py`（在 05b 全文中）。
   - `auto-snapshot`、`turn-counter`、`context-guard`、`token-writer` 的接线真相：见 04 的 feature-registry.yaml **全文 498 行**（你此前只读到 ~179 行）。
   - 工作区现有 141 个在途未提交改动（含 hook-launcher/pretool-gate 修改与新 hook 测试 scripts/test-hook-launcher.sh），本证据包快照=工作区实况，与基线 91954a0 的偏差以 00-head.txt + 你 V5 的 git status 对账为准。
NOTES

# ---------- 脱敏(机械替换,然后重算哈希) ----------
for f in "$STAGE"/*.txt "$STAGE"/*.md; do
  sed -i.bak -E 's/sk-[A-Za-z0-9]{16,}/<REDACTED>/g' "$f"
  rm -f "$f.bak"
done

# ---------- 校验和 ----------
( cd "$STAGE" && shasum -a 256 *.txt *.md > SHA256SUMS )

# ---------- 分片(>24000B) ----------
mkdir -p "$STAGE/parts"
for f in "$STAGE"/*.txt "$STAGE"/*.md; do
  size=$(wc -c < "$f" | tr -d ' ')
  if [ "$size" -gt 24000 ]; then
    base=$(basename "$f")
    split -b 24000 -d -a 3 "$f" "$STAGE/parts/$base.part-"
    for part in "$STAGE/parts/$base.part-"*; do
      mv "$part" "$part.txt"
    done
  fi
done
if ls "$STAGE/parts/"*.txt >/dev/null 2>&1; then
  ( cd "$STAGE/parts" && shasum -a 256 *.txt > SHA256SUMS.parts )
fi

# ---------- 归档 ----------
COPYFILE_DISABLE=1 tar -C /tmp -czf "$DEST/pkg-c-evidence.tar.gz" carroros-pkg-c-evidence
cp -R "$STAGE"/ "$DEST"/

echo "== 生成完毕 =="
ls -la "$DEST"
echo "-- 各文件字节数 --"
wc -c "$DEST"/*.txt "$DEST"/*.md "$DEST"/*.gz 2>/dev/null
echo "-- 分片 --"
ls "$DEST/parts/" 2>/dev/null || echo "(无 >24KB 文件,未分片)"
echo "-- 脱敏自检(应为 0) --"
grep -rc 'sk-Xrwon' "$DEST" --include='*.txt' --include='*.md' 2>/dev/null | grep -v ':0$' || echo "0 (clean)"
