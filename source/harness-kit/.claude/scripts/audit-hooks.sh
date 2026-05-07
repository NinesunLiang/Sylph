#!/usr/bin/env bash
# audit-hooks.sh — Carror OS harness 完整性审计
# 用途：检测 settings.json / harness.yaml / disk 三方漂移，防止 Claude Code 升级改事件名后悄然僵尸化
#
# 三方对账：
#   A. 磁盘脚本: .claude/hooks/*.sh（执行实体）
#   B. settings.json 注册: Claude Code 运行时入口
#   C. harness.yaml hooks_enabled: 产品语义开关
#
# 异常等级：
#   🔴 产品开了 + 磁盘有 + settings 没注册  → 僵尸脚本，永不触发
#   🔴 settings 注册了 + 磁盘没脚本        → 注册到空文件，运行时报错
#   🟡 settings 注册了 + 产品开关关闭      → 浪费 hook 调用
#   🟡 产品开了 + settings 没注册 + 磁盘没 → 缺失的能力
#   🟡 settings matcher=.* 但脚本内部 case "$TOOL_NAME" 仅匹配子集 → R26 漂移面（P1-1 新增）
#   🟢 三方一致 或 产品关闭+settings 无注册 → 正常
#
# 退出码：0=全绿；>0=发现 $n 个 🔴 级问题
#
# 用法：bash .claude/scripts/audit-hooks.sh [--json] [--scan-internal-filter]

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99

JSON_OUT=false
SCAN_INTERNAL=false
for arg in "$@"; do
    case "$arg" in
        --json) JSON_OUT=true ;;
        --scan-internal-filter) SCAN_INTERNAL=true ;;
    esac
done

python3 - "$JSON_OUT" "$SCAN_INTERNAL" <<'PYEOF'
import json, os, re, sys, glob

json_out = sys.argv[1].lower() == 'true'
scan_internal = sys.argv[2].lower() == 'true'

# === A. Disk ===
disk = set()
for f in glob.glob('.claude/hooks/*.sh'):
    name = os.path.basename(f)
    if name == 'harness_config.sh':  # library, not a hook
        continue
    disk.add(name)

# === B. settings.json ===
registered = {}  # script -> set(events)
try:
    with open('.claude/settings.json') as f:
        s = json.load(f)
    for event, arr in s.get('hooks', {}).items():
        for block in arr:
            for h in block.get('hooks', []):
                m = re.search(r'\.claude/hooks/([^\s]+)', h.get('command', ''))
                if m:
                    registered.setdefault(m.group(1), set()).add(event)
except Exception as e:
    print(f'ERROR: cannot read settings.json: {e}')
    sys.exit(99)

# === C. harness.yaml hooks_enabled (简易解析) ===
yaml_enabled = {}  # yaml_key -> bool
try:
    in_section = False
    with open('.claude/harness.yaml') as f:
        for line in f:
            if line.startswith('hooks_enabled:'):
                in_section = True
                continue
            if in_section:
                if line and not line.startswith(' ') and not line.startswith('\t'):
                    in_section = False
                    continue
                m = re.match(r'\s+(\S+):\s*(true|false)', line)
                if m:
                    yaml_enabled[m.group(1)] = (m.group(2) == 'true')
except FileNotFoundError:
    pass

# Script → harness.yaml key 映射（按命名约定推断）
def script_to_yaml_key(script):
    # foo.sh → foo; posttool-bash-audit.sh → posttool_bash_audit
    base = script[:-3] if script.endswith('.sh') else script
    return base.replace('-', '_')

# CLI 工具（不是 hook，不在三方对账范围）
NON_HOOKS = {'feature-probe.sh', 'token_writer.sh', 'harness_config.sh'}

issues = []  # list of (level, script, message)
all_scripts = disk | set(registered.keys())

for script in sorted(all_scripts):
    if script in NON_HOOKS:
        continue
    on_disk = script in disk
    reg_events = registered.get(script, set())
    yaml_key = script_to_yaml_key(script)
    yaml_on = yaml_enabled.get(yaml_key)  # None if not listed

    if not on_disk and reg_events:
        issues.append(('🔴', script, f'settings 注册了 {reg_events} 但磁盘无脚本 — 运行时会报错'))
        continue
    if on_disk and not reg_events and yaml_on is True:
        issues.append(('🔴', script, f'harness.yaml.{yaml_key}=true 磁盘有但 settings 未注册 — 僵尸脚本'))
        continue
    if reg_events and yaml_on is False:
        issues.append(('🟡', script, f'settings 注册 {reg_events} 但 harness.yaml.{yaml_key}=false — 浪费 hook 调用'))
        continue
    if on_disk and not reg_events and yaml_on is None:
        # 磁盘有、settings 没、yaml 没提 — 通常是 CLI 工具，跳过
        continue

# === P1-1: 脚本内部工具白名单 vs settings.json matcher 漂移扫描 ===
# 背景：R26 发现 context-guard 的 matcher=.* 与脚本内 case "$TOOL_NAME" in edit|write|bash)
#       早退形成漂移 — 产品承诺"所有工具受门禁"但实际放行 Read/Grep。
# 策略：如果 settings 中 matcher 宽于脚本内部 case 白名单，报 🟡。
# 豁免：脚本顶部含 `# audit-hooks:filter-ok` 注释时跳过扫描（允许显式收窄）。
WIDE_MATCHER = {'.*', '*', ''}
# matcher 里已声明的工具集（例如 "Edit|Write" → {edit, write}）
def matcher_tools(m):
    if m in WIDE_MATCHER:
        return None  # 宽 matcher，无上界
    return {t.strip().lower() for t in m.split('|') if t.strip()}

def script_case_whitelist(path):
    """返回脚本内 case "$TOOL_NAME" 声明的工具小写集合；None 表示未发现此类过滤。"""
    try:
        with open(path) as f:
            text = f.read()
    except Exception:
        return None
    # 豁免注释
    if re.search(r'#\s*audit-hooks:filter-ok', text):
        return 'exempt'
    # 匹配 case "$TOOL_NAME" in ... ;; *) exit 0 ;; esac
    # 同时兼容 ${TOOL_NAME} 与 $tool_name 小写变量
    pat = re.compile(
        r'case\s+"?\$\{?(?:TOOL_NAME|tool_name)\}?"?\s+in\s+(.+?)esac',
        re.DOTALL | re.IGNORECASE
    )
    m = pat.search(text)
    if not m:
        return None
    body = m.group(1)
    # 检查是否有兜底 *) 早退
    if not re.search(r'\*\)\s*(exit\s+0|return|;;)', body):
        return None
    # 提取显式分支（如 Edit|Write) 或 edit|write))
    branches = re.findall(r'(?:^|\n|;;)\s*([A-Za-z][A-Za-z0-9_|\-]*)\s*\)', body)
    tools = set()
    for b in branches:
        for t in b.split('|'):
            t = t.strip().lower()
            if t and t != '*':
                tools.add(t)
    return tools if tools else None

if scan_internal:
    for script, events in registered.items():
        path = f'.claude/hooks/{script}'
        if not os.path.isfile(path):
            continue
        cw = script_case_whitelist(path)
        if cw in (None, 'exempt'):
            continue  # 无内部过滤或显式豁免
        # 对每个注册事件的 matcher 核对
        for event, arr in json.load(open('.claude/settings.json')).get('hooks', {}).items():
            if event not in events:
                continue
            for block in arr:
                matcher = block.get('matcher', '')
                has_script = any(
                    re.search(rf'\.claude/hooks/{re.escape(script)}\b', h.get('command',''))
                    for h in block.get('hooks', [])
                )
                if not has_script:
                    continue
                mt = matcher_tools(matcher)
                if mt is None:
                    # 宽 matcher vs 脚本白名单 → 漂移
                    issues.append((
                        '🟡', script,
                        f'{event} matcher={matcher!r} 派发全工具，但脚本内 case 仅匹配 {sorted(cw)}；'
                        f'加 `# audit-hooks:filter-ok` 注释豁免或统一范围'
                    ))
                elif mt - cw:
                    # matcher 列出的工具超出脚本白名单
                    extra = sorted(mt - cw)
                    issues.append((
                        '🟡', script,
                        f'{event} matcher={matcher!r} 派发 {extra} 但脚本内 case 不覆盖；'
                        f'matcher 与脚本白名单语义不一致'
                    ))

result = {
    'disk_count': len(disk),
    'registered_count': len(registered),
    'issue_count_red': sum(1 for lvl, _, _ in issues if lvl == '🔴'),
    'issue_count_yellow': sum(1 for lvl, _, _ in issues if lvl == '🟡'),
    'issues': [{'level': lvl, 'script': s, 'message': m} for lvl, s, m in issues],
}

if json_out:
    print(json.dumps(result, ensure_ascii=False, indent=2))
else:
    print(f"=== harness 完整性审计 ===")
    print(f"磁盘脚本: {result['disk_count']}")
    print(f"已注册脚本: {result['registered_count']}")
    print(f"🔴 严重: {result['issue_count_red']}")
    print(f"🟡 次要: {result['issue_count_yellow']}")
    if issues:
        print()
        print("=== 问题列表 ===")
        for lvl, s, m in issues:
            print(f"  {lvl}  {s}: {m}")
    else:
        print("\n✅ 无异常")

sys.exit(result['issue_count_red'])
PYEOF
