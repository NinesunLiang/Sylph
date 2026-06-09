#!/usr/bin/env python3
"""audit-hooks.py — Carror OS harness 完整性审计
Cross-platform Python resolution (DG-105)

用途：检测 settings.json / harness.yaml / disk 三方漂移，防止 Claude Code 升级改事件名后悄然僵尸化

三方对账：
  A. 磁盘脚本: .claude/hooks/*.py（执行实体）
  B. settings.json 注册: Claude Code 运行时入口
  C. harness.yaml hooks_enabled: 产品语义开关

异常等级：
  🔴 产品开了 + 磁盘有 + settings 没注册  → 僵尸脚本，永不触发
  🔴 settings 注册了 + 磁盘没脚本        → 注册到空文件，运行时报错
  🟡 settings 注册了 + 产品开关关闭      → 浪费 hook 调用
  🟡 产品开了 + settings 没注册 + 磁盘没 → 缺失的能力
  🟡 settings matcher=.* 但脚本内部只有子集匹配 → R26 漂移面（P1-1 新增）
  🟢 三方一致 或 产品关闭+settings 无注册 → 正常

退出码：0=全绿；>0=发现 $n 个 🔴 级问题

用法：python3 .claude/scripts/audit-hooks.py [--json] [--scan-internal-filter]
"""
import sys
import os
import re
import json
import glob
import hashlib
from pathlib import Path

# Change to project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
os.chdir(str(PROJECT_ROOT))

JSON_OUT = False
SCAN_INTERNAL = False
CHECK_INDEX = False
SYNC_INDEX = False
CHECK_SOURCE_MIRROR = False
CHECK_REGISTRY = False

for arg in sys.argv[1:]:
    if arg == "--json": JSON_OUT = True
    elif arg == "--scan-internal-filter": SCAN_INTERNAL = True
    elif arg == "--check-index": CHECK_INDEX = True
    elif arg == "--sync-index": SYNC_INDEX = True
    elif arg == "--check-source-mirror": CHECK_SOURCE_MIRROR = True
    elif arg == "--check-registry": CHECK_REGISTRY = True

# === A. Disk ===
disk = set()
for f in glob.glob(".claude/hooks/*.py") + glob.glob(".claude/hooks/*.sh"):
    name = os.path.basename(f)
    if name in ("harness_config.sh",):
        continue
    disk.add(name)

# === B. settings.json ===
registered = {}  # script -> set(events)
try:
    with open(".claude/settings.json") as f:
        s = json.load(f)
    for event, arr in s.get("hooks", {}).items():
        for block in arr:
            for h in block.get("hooks", []):
                m = re.search(r'\.claude/hooks/([^\s\'"]+)', h.get("command", ""))
                if m:
                    registered.setdefault(m.group(1), set()).add(event)
except Exception as e:
    print(f"ERROR: cannot read settings.json: {e}")
    sys.exit(99)

# === C. harness.yaml hooks_enabled ===
yaml_enabled = {}  # yaml_key -> bool
try:
    import yaml
    with open(".claude/harness.yaml") as f:
        data = yaml.safe_load(f)
    raw = data.get("hooks_enabled", {}) if isinstance(data, dict) else {}
    for k, v in raw.items():
        if isinstance(v, bool):
            yaml_enabled[k] = v
except Exception:
    try:
        in_section = False
        with open(".claude/harness.yaml") as f:
            for line in f:
                clean = line.split("#")[0].rstrip()
                if clean.startswith("hooks_enabled:"):
                    in_section = True
                    continue
                if in_section:
                    if clean and clean[0] not in (" ", "\t"):
                        in_section = False
                        continue
                    m = re.match(r"\s+(\S+):\s*(true|false)", clean)
                    if m:
                        yaml_enabled[m.group(1)] = (m.group(2) == "true")
    except FileNotFoundError:
        pass

SCRIPT_KEY_OVERRIDES = {
    "posttool-format-gate.sh": "posttool_output_format",
    "pretool-retry-check.sh": "retry_budget_check",
    "pretool-user-correction.sh": "user_correction_detector",
}

def script_to_yaml_key(script):
    if script in SCRIPT_KEY_OVERRIDES:
        return SCRIPT_KEY_OVERRIDES[script]
    base = script[:-3] if script.endswith(".sh") else script
    return base.replace("-", "_")

NON_HOOKS = {"token_writer.sh", "harness_config.sh"}

issues = []  # list of (level, script, message)
all_scripts = disk | set(registered.keys())

for script in sorted(all_scripts):
    if script in NON_HOOKS:
        continue
    on_disk = script in disk
    reg_events = registered.get(script, set())
    yaml_key = script_to_yaml_key(script)
    yaml_on = yaml_enabled.get(yaml_key)

    if not on_disk and reg_events:
        issues.append(("🔴", script, f"settings 注册了 {reg_events} 但磁盘无脚本 — 运行时会报错"))
        continue
    if on_disk and not reg_events and yaml_on is True:
        issues.append(("🔴", script, f"harness.yaml.{yaml_key}=true 磁盘有但 settings 未注册 — 僵尸脚本"))
        continue
    if reg_events and yaml_on is False:
        issues.append(("🟡", script, f"settings 注册 {reg_events} 但 harness.yaml.{yaml_key}=false — 浪费 hook 调用"))
        continue
    if on_disk and not reg_events and yaml_on is None:
        continue

# === P1-1: 脚本内部工具白名单 vs settings.json matcher 漂移扫描 ===
WIDE_MATCHER = {".*", "*", ""}

def matcher_tools(m):
    if m in WIDE_MATCHER:
        return None
    return {t.strip().lower() for t in m.split("|") if t.strip()}

def script_case_whitelist(path):
    try:
        with open(path) as f:
            text = f.read()
    except Exception:
        return None
    if re.search(r"#\s*audit-hooks:filter-ok", text):
        return "exempt"
    pat = re.compile(
        r'case\s+"?\$\{?(?:TOOL_NAME|tool_name)\}?"?\s+in\s+(.+?)esac',
        re.DOTALL | re.IGNORECASE
    )
    m = pat.search(text)
    if not m:
        return None
    body = m.group(1)
    if not re.search(r'\*\)\s*(exit\s+0|return|;;)', body):
        return None
    branches = re.findall(r'(?:^|\n|;;)\s*([A-Za-z][A-Za-z0-9_|\-]*)\s*\)', body)
    tools = set()
    for b in branches:
        for t in b.split("|"):
            t = t.strip().lower()
            if t and t != "*":
                tools.add(t)
    return tools if tools else None

if SCAN_INTERNAL:
    for script, events in registered.items():
        path = f".claude/hooks/{script}"
        if not os.path.isfile(path):
            continue
        cw = script_case_whitelist(path)
        if cw in (None, "exempt"):
            continue
        with open(".claude/settings.json") as f:
            settings = json.load(f)
        for event, arr in settings.get("hooks", {}).items():
            if event not in events:
                continue
            for block in arr:
                matcher = block.get("matcher", "")
                has_script = any(
                    re.search(rf'\.claude/hooks/{re.escape(script)}\b', h.get("command", ""))
                    for h in block.get("hooks", [])
                )
                if not has_script:
                    continue
                mt = matcher_tools(matcher)
                if mt is None:
                    issues.append((
                        "🟡", script,
                        f"{event} matcher={matcher!r} 派发全工具，但脚本内 case 仅匹配 {sorted(cw)}；"
                        f"加 `# audit-hooks:filter-ok` 注释豁免或统一范围"
                    ))
                elif mt - cw:
                    extra = sorted(mt - cw)
                    issues.append((
                        "🟡", script,
                        f"{event} matcher={matcher!r} 派发 {extra} 但脚本内 case 不覆盖；"
                        f"matcher 与脚本白名单语义不一致"
                    ))

# === D. Index.md hooks 速查表对账 ===
if check_index or sync_index:
    TABLE_PATH = ".claude/reference/hooks-table.md"
    index_src = Path(TABLE_PATH).read_text(encoding="utf-8")

    def _parse_index_table(content):
        hooks = {}
        m = re.search(r'\|.*?\n\|.*?\n((?:\|.*?\n)+)', content)
        if not m:
            return hooks
        for line in m.group(1).split("\n"):
            if not line.startswith("|") or line.startswith("|---"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1]:
                hooks[parts[1].strip("`")] = {"trigger": parts[2].strip("`"), "desc": parts[3].strip("`")}
        return hooks

    def _script_desc(name):
        try:
            with open(f".claude/hooks/{name}") as f:
                lines = f.readlines()
            header_skipped = False
            for line in lines:
                s = line.strip()
                if not s.startswith("#"):
                    continue
                content = s.lstrip("# ").strip()
                if not content or content.startswith("---") or "harness-kit:" in content:
                    continue
                if not header_skipped:
                    header_skipped = True
                    continue
                return content[:80]
        except Exception:
            pass
        return ""

    def _yaml_key(s):
        return s[:-3].replace("-", "_") if s.endswith(".sh") else s.replace("-", "_")

    cur_hooks = _parse_index_table(index_src)
    cur_names = set(cur_hooks.keys())

    cur_disabled = set()
    for line in index_src.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- `"):
            name = stripped.split("`")[1]
            if name:
                cur_disabled.add(name)

    act_rows = []
    dis_rows = []
    active_names = set()
    disabled_names = set()

    for script in sorted(disk | set(registered.keys())):
        if script in NON_HOOKS:
            continue
        name = script.replace(".sh", "")
        events = registered.get(script, set())
        if not events:
            continue
        yk = _yaml_key(script)
        if yaml_enabled.get(yk) is False:
            disabled_names.add(name)
        else:
            active_names.add(name)

    for script in sorted(disk | set(registered.keys())):
        if script in NON_HOOKS:
            continue
        name = script.replace(".sh", "")
        events = registered.get(script, set())
        trig = " / ".join(sorted(events)) if events else "(未注册)"
        desc = cur_hooks.get(script, {}).get("desc", "") or _script_desc(script)
        yk = _yaml_key(script)
        if yaml_enabled.get(yk) is False:
            dis_rows.append((name, trig, desc))
        elif events:
            act_rows.append((name, trig, desc))

    missing_in_main = active_names - cur_names
    orphaned_in_main = cur_names - active_names
    missing_in_disabled = disabled_names - cur_disabled
    orphaned_in_disabled = cur_disabled - disabled_names

    if check_index:
        print("\n=== hooks 速查表对账 ===")
        print(f"  主表: {len(cur_names)} | 实际活跃: {len(active_names)}")
        print(f"  禁用区: {len(cur_disabled)} | 实际禁用: {len(disabled_names)}")
        issues_found = False
        if missing_in_main:
            issues_found = True
            print(f"  🟡 主表缺少 {len(missing_in_main)} 个: {', '.join(sorted(missing_in_main))}")
        if orphaned_in_main:
            issues_found = True
            print(f"  🟡 主表幽灵 {len(orphaned_in_main)} 个: {', '.join(sorted(orphaned_in_main))}")
        if missing_in_disabled:
            issues_found = True
            print(f"  🟡 禁用区缺少 {len(missing_in_disabled)} 个: {', '.join(sorted(missing_in_disabled))}")
        if orphaned_in_disabled:
            issues_found = True
            print(f"  🟡 禁用区幽灵 {len(orphaned_in_disabled)} 个: {', '.join(sorted(orphaned_in_disabled))}")
        if not issues_found:
            print("  ✅ hooks 速查表与实际一致")

    if sync_index:
        st_match = re.search(r'(### 独立工具脚本.*?)(?=\n## |\Z)', index_src, re.DOTALL)
        st_text = st_match.group(1) if st_match else ""

        new_table = f"## Hooks 速查（共 {len(act_rows)} 个）\n"
        new_table += "| Hook | 触发 | 作用|\n|------|------|------|\n"
        for name, trig, desc in act_rows:
            new_table += f"|`{name}` | {trig} | {desc}|\n"

        if dis_rows:
            new_table += f"\n### 已注册但默认禁用的脚本（共 {len(dis_rows)} 个）\n\n"
            new_table += "以下脚本已注册到 settings.json，但在 harness.yaml 中默认关闭，按需启用：\n\n"
            new_table += "| 脚本 | 事件 | 说明 |\n|------|------|------|\n"
            for name, trig, desc in dis_rows:
                new_table += f"| {name} | {trig} | {desc} |\n"

        if st_text:
            new_table += f"\n{st_text}"

        idx_section = re.compile(r'#{1,2} Hooks 速查.*?(?=\n#{1,2} |\Z)', re.DOTALL)
        new_index = idx_section.sub(new_table, index_src)
        if new_index == index_src:
            print(f"\n  ❌ {TABLE_PATH} hooks 表同步失败 — 标题匹配异常，请检查文件格式")
        else:
            Path(TABLE_PATH).write_text(new_index, encoding="utf-8")
            print(f"\n  ✅ {TABLE_PATH} hooks 表已同步（{len(act_rows)} 活跃 + {len(dis_rows)} 禁用）")
            print(f"  🔄 原表 {len(cur_names)} 个 → 新表 {len(active_names)} 个")

# === E. Source Mirror Consistency Check ===
if check_source_mirror:
    if not os.path.isdir("source"):
        print("  ⚠️  source mirror 目录不存在（已废弃），跳过检查")
    else:
        mirror_map = {
            ".claude/hooks": "source/harness-kit/.claude/hooks",
            ".claude/scripts": "source/harness-kit/.claude/scripts",
            ".claude/skills": "source/lx-skills-v5/.claude/skills",
        }
        _EXCLUDED_CONFIG = {"settings.local.json", "scheduled_tasks.json"}
        _INTENTIONAL_DIVERGENCE = {"AGENTS.md", "CLAUDE.md", "settings.json"}
        config_files = {}
        for _cf in glob.glob(".claude/*.json") + glob.glob(".claude/*.yaml"):
            _name = os.path.basename(_cf)
            if _name in _EXCLUDED_CONFIG or _name in _INTENTIONAL_DIVERGENCE:
                continue
            _mirror = os.path.join("source/harness-kit/.claude", _name)
            config_files[_cf] = _mirror
        mirror_issues = 0
        for src_dir, mirror_dir in mirror_map.items():
            if not os.path.isdir(mirror_dir):
                issues.append(("🔴", mirror_dir, "source mirror 目录不存在"))
                continue
            src_files = {}
            _extensions = [".py", ".sh", ".json", ".yaml", ".yml", ".md"]
            _is_skills = src_dir.endswith("/.claude/skills")
            if _is_skills:
                for _ext in _extensions:
                    for f in glob.glob(f"{src_dir}/**/*{_ext}", recursive=True):
                        name = os.path.relpath(f, src_dir)
                        try:
                            with open(f, "rb") as fh:
                                h = hashlib.sha256(fh.read()).hexdigest()
                            src_files[name] = (f, h)
                        except Exception:
                            pass
            else:
                for _ext in _extensions:
                    for f in glob.glob(f"{src_dir}/*{_ext}"):
                        name = os.path.basename(f)
                        try:
                            with open(f, "rb") as fh:
                                h = hashlib.sha256(fh.read()).hexdigest()
                            src_files[name] = (f, h)
                        except Exception:
                            pass
            for name, (fpath, src_hash) in src_files.items():
                mpath = os.path.join(mirror_dir, name)
                if not os.path.isfile(mpath):
                    issues.append(("🔴", name, f"source mirror 缺失: {mpath}"))
                    mirror_issues += 1
                    continue
                try:
                    with open(mpath, "rb") as fh:
                        mh = hashlib.sha256(fh.read()).hexdigest()
                    if src_hash != mh:
                        issues.append(("🔴", name, "source mirror 漂移 — sha256 不匹配"))
                        mirror_issues += 1
                except Exception:
                    pass

        for src_path, mirror_path in config_files.items():
            fname = os.path.basename(src_path)
            if not os.path.isfile(mirror_path):
                issues.append(("🔴", fname, f"config mirror 缺失: {mirror_path}"))
                mirror_issues += 1
                continue
            try:
                with open(src_path, "rb") as fh:
                    src_hash = hashlib.sha256(fh.read()).hexdigest()
                with open(mirror_path, "rb") as fh:
                    mh = hashlib.sha256(fh.read()).hexdigest()
                if src_hash != mh:
                    issues.append(("🔴", fname, "config mirror 漂移 — sha256 不匹配"))
                    mirror_issues += 1
            except Exception:
                pass

        if mirror_issues == 0:
            print("  ✅ source mirror 一致性: 全部一致")
        if _INTENTIONAL_DIVERGENCE:
            div_str = ", ".join(sorted(_INTENTIONAL_DIVERGENCE))
            print(f"  ℹ️  有意分歧（不参与 mirror 检查）: {div_str}")

# === H. feature-registry 完整性检查 (--check-registry) ===
if check_registry:
    registry_hooks = set()
    registry_skills = set()
    try:
        import yaml
        with open(".claude/feature-registry.yaml") as f:
            reg_data = yaml.safe_load(f)
        entries = reg_data if isinstance(reg_data, list) else reg_data.get("hooks", []) if isinstance(reg_data, dict) else []
        for entry in entries:
            if isinstance(entry, dict) and entry.get("type") == "hook":
                registry_hooks.add(entry.get("name", ""))
            elif isinstance(entry, dict):
                registry_skills.add(entry.get("name", ""))
    except Exception:
        pass

    all_registered = set(registered.keys())
    registered_keys = set()
    for r in all_registered:
        rk = script_to_yaml_key(r)
        if rk:
            registered_keys.add(rk)
    missing_in_registry = [k for k in sorted(registered_keys) if k and k not in registry_hooks and k not in ("harness_config", "feature_probe")]
    orphan_in_registry = [h for h in sorted(registry_hooks) if h and h not in registered_keys and h not in ("harness_config", "feature_probe")]

    if missing_in_registry:
        for k in missing_in_registry:
            issues.append(("🟡", k, "已注册(settings.json)但 feature-registry 缺少条目"))
    if orphan_in_registry:
        for k in orphan_in_registry:
            issues.append(("🟡", k, "feature-registry 有条目但 settings.json 未注册"))

result = {
    "disk_count": len(disk),
    "registered_count": len(registered),
    "issue_count_red": sum(1 for lvl, _, _ in issues if lvl == "🔴"),
    "issue_count_yellow": sum(1 for lvl, _, _ in issues if lvl == "🟡"),
    "issues": [{"level": lvl, "script": s, "message": m} for lvl, s, m in issues],
}

if JSON_OUT:
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

sys.exit(result["issue_count_red"])
