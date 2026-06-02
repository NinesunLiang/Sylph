#!/usr/bin/env bash
# knowledge-condenser.sh — Stop — 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
# Role: 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
# GS-003: 自动知识抽取 — 支持 [seed:*] 和 @YYYY-MM-DD 两种格式

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "knowledge_condenser" || exit 0

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
KERNEL_MD="$PROJECT_ROOT/.claude/kernel.md"

[ -f "$CLAUDE_NEXT" ] || exit 0

AUTO_EXECUTE=$(hc_get "sublimation.auto_execute" "true")
SUBLIMATION_LOG="$PROJECT_ROOT/.omc/state/sublimation-log.jsonl"

PY_OUTPUT=$(${PYTHON_BIN:-python3} - "$CLAUDE_NEXT" "$KERNEL_MD" "$AUTO_EXECUTE" <<'PYEOF'
import json, re, sys, subprocess, os
from datetime import datetime, date

try:
    next_path = sys.argv[1]
    kernel_path = sys.argv[2]
    auto_execute = sys.argv[3].lower() == 'true'
except IndexError:
    auto_execute = False

with open(next_path, encoding="utf-8") as f:
    text = f.read()

lines = text.split('\n')
entries = []
current_entry = None

for i, line in enumerate(lines):
    line_stripped = line.strip()

    # Match: ### [seed:xxx] Description @YYYY-MM-DD hits:N
    m1 = re.match(r'^###\s+\[([^\]]+)\]\s+(.+?)(?:\s+@(\d{4}-\d{2}-\d{2}))?\s+hits:(\d+)', line_stripped)
    if m1:
        tag = m1.group(1)
        desc = m1.group(2).strip()
        hits = int(m1.group(4))
        d = m1.group(3)
        entry_date = datetime.strptime(d, '%Y-%m-%d').date() if d else None
        entries.append((tag, hits, entry_date, desc, i + 1))
        continue

    # Match: ### @YYYY-MM-DD hits:N or ### Description @YYYY-MM-DD hits:N
    m2 = re.match(r'^###\s+(.+?)\s+@(\d{4}-\d{2}-\d{2})\s+hits:(\d+)', line_stripped)
    if m2:
        desc = m2.group(1).strip()
        hits = int(m2.group(3))
        d = m2.group(2)
        entry_date = datetime.strptime(d, '%Y-%m-%d').date()
        entries.append((desc[:50], hits, entry_date, desc, i + 1))
        continue

    # Match: ### [rpe-NNN] Description @YYYY-MM-DD hits:N
    m3 = re.match(r'^###\s+\[([^\]]+)\]\s+@(\d{4}-\d{2}-\d{2})\s+hits:(\d+)', line_stripped)
    if m3:
        tag = m3.group(1)
        hits = int(m3.group(3))
        d = m3.group(2)
        entry_date = datetime.strptime(d, '%Y-%m-%d').date()
        entries.append((tag, hits, entry_date, '', i + 1))
        continue

today = date.today()
suggestions = []

for tag, hits, entry_date, desc, ln in entries:
    if hits < 2:  # P1.3: threshold lowered from 3 to 2
        continue

    age = (today - entry_date).days if entry_date else 0

    # Check if already in kernel.md (keyword fuzzy search)
    found_in_kernel = False
    if tag and kernel_path:
        try:
            result = subprocess.run(
                ['grep', '-i', '-c', tag, kernel_path],
                capture_output=True, text=True, timeout=5
            )
            count = int(result.stdout.strip())
            found_in_kernel = count > 0
        except Exception:
            pass

    in_kernel = "found" if found_in_kernel else "missing"

    if hits >= 5 and age >= 10 and found_in_kernel:
        action = "更新 kernel.md（规则已存在但需补证据）"
    elif hits >= 5 and age >= 10 and not found_in_kernel:
        action = "升华至 kernel.md"
    elif hits >= 3 and age >= 7 and found_in_kernel:
        action = "更新 kernel.md（修表述/补证据）"
    elif hits >= 3 and age >= 7 and not found_in_kernel:
        action = "升华至 kernel.md"
    elif hits >= 3 and age >= 5 and found_in_kernel:
        action = "更新 kernel.md（修表述/补证据）"
    elif hits >= 3 and age >= 5 and not found_in_kernel:
        action = "建议升华，待确认"
    elif hits >= 3 and age < 5:
        action = f"待稳定后再升华（仅 {age} 天）"
    else:
        continue

    tag_display = tag or desc[:50]
    suggestions.append((tag_display, hits, age, action, ln, in_kernel))

if not suggestions:
    sys.exit(0)

# Sort by hits desc, then age desc
suggestions.sort(key=lambda x: (-x[1], -x[2]))
suggestions = suggestions[:7]

# === 自动升华：auto_execute 开启 + 条件达标条目 ===
sublimation_log_path = os.path.join(os.path.dirname(os.path.dirname(next_path)), '.omc', 'state', 'sublimation-log.jsonl')
auto_sublimated = []
if auto_execute:
    for tag_display, hits, age, action, ln, in_kernel in suggestions:
        if action == "升华至 kernel.md" and hits >= 5 and age >= 10 and not in_kernel:
            # Read full claude-next.md content for this entry
            with open(next_path, encoding="utf-8") as f:
                full_text = f.read()
            # Find the entry block in claude-next.md
            entry_lines = full_text.split('\n')
            entry_block = []
            capture = False
            entry_marker = None
            for j, el in enumerate(entry_lines):
                if j + 1 == ln:
                    capture = True
                    entry_marker = el.strip()
                if capture:
                    entry_block.append(el)
                    # Stop at next ### or end
                    if j + 1 > ln and el.strip().startswith('### '):
                        break
            if entry_block and entry_block[-1].strip().startswith('### '):
                entry_block = entry_block[:-1]
            entry_text = '\n'.join(entry_block).strip()

            # Append to kernel.md
            kernel_lines = []
            if os.path.exists(kernel_path):
                with open(kernel_path, encoding="utf-8") as f:
                    kernel_lines = f.read().split('\n')
            # Find insertion point: before last line if it's blank/empty, or append
            insertion = len(kernel_lines)
            for j in range(len(kernel_lines) - 1, -1, -1):
                if kernel_lines[j].strip():
                    insertion = j + 1
                    break
            sublimation_block = f"\n## 自动升华: {tag_display}\n\n{entry_text}\n\n— 自动升华自 claude-next.md:{ln} (hits:{hits}, age:{age}天)\n"
            kernel_lines.insert(insertion, sublimation_block)
            with open(kernel_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(kernel_lines))

            # Write sublimation log
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "source": "claude-next.md",
                "source_line": ln,
                "tag": tag_display,
                "hits": hits,
                "age_days": age,
                "target": kernel_path,
                "action": "auto_sublimate"
            }
            os.makedirs(os.path.dirname(sublimation_log_path), exist_ok=True)
            with open(sublimation_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            auto_sublimated.append(tag_display)

lines_out = [f"[knowledge-condenser] {len(suggestions)} 个高频模式可升华:"]
for tag_display, hits, age, action, ln, in_kernel in suggestions:
    lines_out.append(f" · {tag_display} (hits:{hits}, {age}天) → {action}")
    lines_out.append(f"   证据: claude-next.md:{ln}, kernel.md: {in_kernel}")

# === 自动归档：低命中 + 超龄条目（hits=1, age>30天）===
old_low_hit = [(ln, desc[:60]) for tag, hits, entry_date, desc, ln in entries
               if hits == 1 and entry_date and (today - entry_date).days > 30]
if old_low_hit:
    lines_out.append(f"[knowledge-condenser] {len(old_low_hit)} 条低命中超龄记录(hits=1, >30天):")
    for ln, d in old_low_hit[:5]:
        lines_out.append(f" · 行{ln}: {d}")
    lines_out.append("  建议: 审查后从 claude-next.md 移除或标记为已归档")

# === 总量告警：超过 40 条时建议整理 ===
if len(entries) > 40:
    lines_out.append(f"[knowledge-condenser] 警告: claude-next.md 当前 {len(entries)} 条，建议审查归档低价值条目至 <30 条")

if auto_sublimated:
    lines_out.append(f"[knowledge-condenser] 自动升华: {len(auto_sublimated)} 条已写入 kernel.md — {', '.join(auto_sublimated)}")

print('|'.join(lines_out))
PYEOF
)

if [ -n "$PY_OUTPUT" ]; then
    # Stop hook 不支持 additionalContext，stderr 输出会导致 JSON 校验错误
    echo "$PY_OUTPUT" > "$PROJECT_ROOT/.omc/state/knowledge-condenser-report.txt"
    flywheel_event "knowledge_condenser" "sublimation_scan" "P2" "scanned_and_suggested"
fi
exit 0
