#!/usr/bin/env bash
# build-pkg-b-evidence.sh — 按 gpt-5.6Sol 的指定结构生成 pkg-b 关键证据包
# 环境适配(机械等价,非内容改写):
#   1) rg → grep -rnE(本机无 rg);\bR6\b → R6(BSD grep 兼容)
#   2) sha256sum → shasum -a 256(macOS 无 sha256sum)
#   3) 输出先写 /tmp 再移入 + 排除 improve_plan/自身输出(防 grep 自吞反馈循环)
#   4) 分片加 .txt 后缀(上传器不认无类型扩展名)
#   5) 第一段 grep 排除 audit/state 目录与 *.jsonl(运行时审计/状态产物,非源码,
#      否则证据包从 ~200KB 膨胀到 3.3MB;机械排除,不含内容取舍)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

OUT_TMP=$(mktemp /tmp/pkg-b-evidence-XXXXXX.txt)
{
  printf '%s\n' '=== BASELINE ==='
  git rev-parse HEAD

  printf '%s\n' '=== VERIFY DEFINITIONS AND CALLS ==='
  grep -rnE -C 12 -I --exclude-dir=__pycache__ --exclude-dir=audit --exclude-dir=state \
    --exclude='*.jsonl' \
    'def cmd_verify|def _check_verified|cmd_verify|_check_verified|verify_gate|oracle_gate|--pipeline|R6' \
    .claude .omc 2>/dev/null || true

  printf '%s\n' '=== RELEVANT FILE LIST ==='
  git ls-files | grep -E '(^|/)(verify_gate|oracle_gate|oracle_engine|carros_base|pretool.*oracle|.*verify.*hook|.*pipeline.*|.*\.sh$|lx-.*\.md$|task-spec|shared\.md)' || true

  printf '%s\n' '=== VERIFY GATE FILES ==='
  for f in \
    .claude/scripts/verify_gate.py \
    .omc/scripts/verify_gate.py \
    .claude/scripts/oracle_gate.py \
    .omc/scripts/oracle_gate.py \
    .claude/scripts/oracle_engine.py \
    .omc/scripts/oracle_engine.py \
    .claude/hooks/pretool-oracle-gate.py
  do
    if [ -f "$f" ]; then
      printf '\n=== FILE %s ===\n' "$f"
      nl -ba "$f"
    fi
  done

  printf '%s\n' '=== PIPELINE REFERENCES ==='
  grep -rlE -I --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=vendor \
    --exclude-dir=dist --exclude-dir=build --exclude-dir=__pycache__ --exclude-dir=improve_plan \
    --exclude-dir=pkg-b-evidence-parts --exclude=pkg-b-evidence.txt --exclude-dir=artifacts \
    -- '--pipeline|R6' . 2>/dev/null |
  while IFS= read -r f; do
    printf '\n=== FILE %s ===\n' "$f"
    nl -ba "$f"
  done
} > "$OUT_TMP"

mv "$OUT_TMP" pkg-b-evidence.txt
test -s pkg-b-evidence.txt
printf 'evidence_exit=0\n'
wc -c pkg-b-evidence.txt

rm -rf pkg-b-evidence-parts
mkdir -p pkg-b-evidence-parts
split -b 30000 -d -a 3 pkg-b-evidence.txt pkg-b-evidence-parts/part-
for f in pkg-b-evidence-parts/part-*; do mv "$f" "$f.txt"; done
shasum -a 256 pkg-b-evidence.txt pkg-b-evidence-parts/part-*.txt > pkg-b-evidence-parts/SHA256SUMS

cat pkg-b-evidence-parts/part-*.txt > /tmp/pkg-b-evidence-reassembled.txt
cmp -s pkg-b-evidence.txt /tmp/pkg-b-evidence-reassembled.txt
printf 'cmp_exit=%s\n' "$?"
wc -c pkg-b-evidence.txt pkg-b-evidence-parts/part-*.txt > pkg-b-evidence-parts/SIZES
ls pkg-b-evidence-parts/
