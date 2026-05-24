#!/usr/bin/env bash
# token-bill.sh — 跨会话 Token 经济历史账单
# 用法: bash .claude/scripts/token-bill.sh [--json]
set -uo pipefail

SAVINGS=".omc/state/token-savings.json"
SAVINGS_LOG=".omc/state/token-savings.jsonl"
JSON_OUT=false; [ "${1:-}" = "--json" ] && JSON_OUT=true

if [ "$JSON_OUT" = true ]; then
    # JSON 输出
    ${PYTHON_BIN:-python3} -c "
import json, os
tf='$SAVINGS'; tl='$SAVINGS_LOG'
sessions = []
if os.path.exists(tl):
    with open(tl) as f:
        for l in f:
            if l.strip(): sessions.append(json.loads(l))
d = {}
if os.path.exists(tf):
    with open(tf) as f: d = json.load(f)
print(json.dumps({
    'cumulative': d,
    'sessions': sessions[-10:],  # last 10
    'session_count': len(sessions)
}, indent=2, ensure_ascii=False))
"
else
    # 人类可读账单
    ${PYTHON_BIN:-python3} -c "
import json, os
tf='$SAVINGS'; tl='$SAVINGS_LOG'

# 累计数据
d = {}
if os.path.exists(tf):
    with open(tf) as f: d = json.load(f)

# 会话历史
sessions = []
if os.path.exists(tl):
    with open(tl) as f:
        for l in f:
            if l.strip(): sessions.append(json.loads(l))

COST_PER_1M = 2.0  # \$2/1M input tokens
CHARS_PER_TOKEN = 4

# 兼容新旧字段名: cumulative_bytes(新) / compact+total(旧)
cum_bytes = d.get('cumulative_bytes', 0) or d.get('compact', 0)
cum_events = d.get('cumulative_events', 0) or d.get('compact_events', 0)
cum_tokens = cum_bytes / CHARS_PER_TOKEN
cum_cost = cum_tokens / 1000000 * COST_PER_1M

print('╔══════════════════════════════════════╗')
print('║  💰 Token 经济历史账单              ║')
print('╚══════════════════════════════════════╝')
print()
print(f'  📊 累计数据 (跨{cum_events}次会话):')
print(f'     累计节省: {cum_bytes:,} bytes ≈ {cum_tokens:,.0f} tokens')
print(f'     累计省下: \${cum_cost:.3f} (按 \$2/1M tokens)')
print(f'     最后更新: {d.get(\"last_updated\", \"?\")}')
print()

# 本次会话
sess_bytes = d.get('session_bytes', 0)
sess_ratio = d.get('session_ratio_pct', 0)
sess_tokens = sess_bytes / CHARS_PER_TOKEN
print(f'  📍 本次会话:')
print(f'     节省: {sess_bytes:,} bytes ≈ {sess_tokens:,.0f} tokens')
print(f'     压缩率: {sess_ratio}%')
print(f'     本次省: \${sess_tokens / 1000000 * COST_PER_1M:.4f}')
print()

# 历史趋势
if len(sessions) > 1:
    print(f'  📈 历史趋势 (共{len(sessions)}次):')
    ratios = [s['ratio_pct'] for s in sessions[-5:]]
    avg_ratio = sum(ratios) / len(ratios)
    saved_list = [s['saved_bytes'] for s in sessions[-5:]]
    total_saved = sum(saved_list)
    print(f'     近5次平均压缩率: {avg_ratio:.1f}%')
    print(f'     近5次累计节省: {total_saved:,} bytes')
    print()

    print(f'  📋 最近会话:')
    for s in sessions[-5:]:
        print(f'     {s[\"ts\"][:16]}  {s[\"ratio_pct\"]:5.1f}%  {s[\"saved_bytes\"]:>10,}b → {s[\"compact_bytes\"]:>6,}b')
elif len(sessions) == 1:
    print(f'  📋 仅1次记录: {sessions[0][\"ts\"][:16]}  {sessions[0][\"ratio_pct\"]}%')
else:
    print(f'  ⚠️  暂无历史记录')

print()
print('═══ 换算说明 ═══')
print('  每1M input tokens ≈ \$2.00')
print('  每4字符 ≈ 1 token (估算)')
print('  只计算知识注入侧节省，不含AI侧消耗')
"
fi
