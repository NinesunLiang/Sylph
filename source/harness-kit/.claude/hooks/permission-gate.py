#!/usr/bin/env python3
# permission-gate.py — PreToolUse:Python — 执行危险命令前检查权限申请格式
# Role: 执行危险命令前检查权限申请格式
# 转换自 permission-gate.sh

import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Use shared mode detection from harness_lib (single source of truth)
from harness_lib import is_mode_active, _mode_append_to_list

# ============================================================
# harness.yaml 配置读取（替代 Bash hc_get/hc_enabled）
# ============================================================

_HC_PROJECT_ROOT = (Path(__file__).resolve().parent.parent.parent).as_posix()
_HC_YAML = os.path.join(_HC_PROJECT_ROOT, '.claude', 'harness.yaml')
_HC_STATE_DIR = os.path.join(_HC_PROJECT_ROOT, '.omc', 'state')
_HC_CACHE = os.path.join(_HC_STATE_DIR, '.harness-cache')
_HC_CACHE_DATA = {}  # 解析后的缓存 dict


def _hc_ensure_cache():
    """确保 harness.yaml 缓存已加载，返回 True=可用 False=空/不可用"""
    if _HC_CACHE_DATA:
        return True

    os.makedirs(_HC_STATE_DIR, exist_ok=True)

    # 检查缓存文件
    if os.path.isfile(_HC_CACHE) and os.path.getsize(_HC_CACHE) > 0:
        # 检查 sentinel
        with open(_HC_CACHE, 'r', encoding='utf-8') as f:
            first = f.readline().strip()
        if first.startswith('__parsed_count__='):
            # 检查 yaml 新鲜度
            if not os.path.isfile(_HC_YAML):
                _load_cache_file()
                return bool(_HC_CACHE_DATA)
            yaml_mtime = os.path.getmtime(_HC_YAML)
            cache_mtime = os.path.getmtime(_HC_CACHE)
            if cache_mtime >= yaml_mtime:
                _load_cache_file()
                return bool(_HC_CACHE_DATA)
        # 缓存损坏或过期，重新构建
        try:
            os.remove(_HC_CACHE)
        except OSError:
            pass

    if not os.path.isfile(_HC_YAML):
        return False

    # 重建缓存
    return _rebuild_cache()


def _load_cache_file():
    """从缓存文件加载 key=value 数据"""
    global _HC_CACHE_DATA
    _HC_CACHE_DATA = {}
    try:
        with open(_HC_CACHE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('__parsed_count__='):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    _HC_CACHE_DATA[key] = value
    except (IOError, OSError):
        _HC_CACHE_DATA = {}


def _rebuild_cache():
    """使用 Python 解析器重建 harness.yaml 缓存（无需 PyYAML）"""
    global _HC_CACHE_DATA

    def parse_yaml_simple(path):
        """简单 YAML 解析器：处理 2 层嵌套 + 简单列表（无需 PyYAML）"""
        result = {}
        current_section = ""
        current_list_key = ""
        current_list = []

        with open(path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.rstrip('\n\r')
                stripped = line.strip()

                if not stripped or stripped.startswith('#'):
                    if current_list_key and current_list:
                        result[current_list_key] = ' '.join(current_list)
                        current_list_key = ""
                        current_list = []
                    continue

                indent = len(line) - len(line.lstrip())

                if stripped.startswith('- '):
                    if current_list_key:
                        item = stripped[2:].strip().strip('"').strip("'")
                        current_list.append(item)
                    continue

                if current_list_key and current_list:
                    result[current_list_key] = ' '.join(current_list)
                    current_list_key = ""
                    current_list = []

                if ':' in stripped:
                    colon_idx = stripped.index(':')
                    key = stripped[:colon_idx].strip()
                    value = stripped[colon_idx + 1:].strip()

                    if value and value[0] in ('"', "'") and value[-1] == value[0]:
                        value = value[1:-1]

                    if indent == 0:
                        if value:
                            result[key] = value
                        else:
                            current_section = key
                    elif indent > 0 and current_section:
                        flat_key = f"{current_section}.{key}"
                        if value:
                            result[flat_key] = value
                        else:
                            current_list_key = flat_key
                            current_list = []

        if current_list_key and current_list:
            result[current_list_key] = ' '.join(current_list)

        return result

    try:
        data = parse_yaml_simple(_HC_YAML)
        min_keys = int(os.environ.get('HC_MIN_PARSED_KEYS', '50'))

        if len(data) < min_keys:
            _HC_CACHE_DATA = {}
            return False

        # 写入缓存文件
        tmp_cache = _HC_CACHE + '.tmp.' + str(os.getpid())
        with open(tmp_cache, 'w', encoding='utf-8') as f:
            f.write(f"__parsed_count__={len(data)}\n")
            for k, v in sorted(data.items()):
                v_escaped = str(v).replace('\n', '\\n')
                f.write(f"{k}={v_escaped}\n")
        os.rename(tmp_cache, _HC_CACHE)
        _HC_CACHE_DATA = data
        return True
    except Exception:
        _HC_CACHE_DATA = {}
        return False


def hc_get(key, default=""):
    """从 harness.yaml 获取配置值，不存在返回 default"""
    if not _hc_ensure_cache():
        return default
    return _HC_CACHE_DATA.get(key, default)


def hc_enabled(feature_name):
    """检查 feature 是否启用（默认 true）"""
    hook_key = feature_name.replace('-', '_')
    val = hc_get(f"hooks_enabled.{hook_key}", "")
    if val:
        return val == "true"
    val = hc_get(f"skills_enabled.{feature_name}", "")
    if val:
        return val == "true"
    return True


def flywheel_event(hook_name, event_type, severity="P2", project="carror-os"):
    """记录 flywheel 事件到日志"""
    flywheel_log = os.path.join(os.path.expanduser("~"), ".claude", "flywheel.log")
    try:
        os.makedirs(os.path.dirname(flywheel_log), exist_ok=True)
        with open(flywheel_log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d')},{hook_name}_{event_type},{severity},{project}\n")
    except (IOError, OSError):
        pass


# ============================================================
# 主逻辑
# ============================================================

def hc_emit_hook_json(event_name="PostToolUse", continue_val=True, message=""):
    """输出标准化 JSON hook 响应"""
    result = {
        "continue": continue_val,
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": message
        }
    }
    print(json.dumps(result, ensure_ascii=True))


def generate_token(length=8):
    """生成随机 hex token（多级降级）"""
    byte_count = length // 2
    try:
        return secrets.token_hex(byte_count)
    except Exception:
        import random
        import string
        return ''.join(random.choice(string.hexdigits.lower()) for _ in range(length))


# ============================================================
# 主逻辑
# ============================================================

def main():
    # 检查 permission_gate 是否启用
    if not hc_enabled("permission_gate"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 读取 stdin（JSON 输入）
    stdin_data = sys.stdin.read()
    if not stdin_data:
        # 无输入 → 放行（没有输入就没有命令需要检查）
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        data = json.loads(stdin_data)
    except json.JSONDecodeError:
        print("⛔ [Permission Gate] 无法解析输入 JSON — 安全门禁默认阻断。", file=sys.stderr)
        hc_emit_hook_json("PreToolUse", False,
                          "[Permission Gate] JSON 解析失败，安全门禁默认阻断。请人类在终端手动执行此命令，或明确确认放行。")
        sys.exit(2)

    # 提取 command 字段
    command = ""
    if isinstance(data, dict):
        command = data.get("tool_input", {}).get("command", "") or data.get("args", {}).get("command", "")

    # 命令为空 → 放行（没有命令需要检查，不是失败场景）
    if not command:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 从 harness.yaml 读取 regex 模式（fallback 为内置默认值）
    git_commit_re = hc_get("permission_gate.git_commit_regex",
                           r'git\s+(commit|add\s+--?all|\badd\b.*-A)')
    git_push_force_re = hc_get("permission_gate.git_push_force_regex",
                               r'git\s+push\s+(\S+\s+)?(\S+\s+)?--?force|git\s+push\s+--?force')
    git_push_re = hc_get("permission_gate.git_push_regex",
                         r'git\s+push\b')
    destructive_re = hc_get("permission_gate.destructive_regex",
                            r'\brm\s+-rf\b|\bdrop\s+(table|database|collection|schema)\b|\btruncate(\s+table)?\s+\S|\bdelete\s+from\b')
    sudo_re = hc_get("permission_gate.sudo_regex",
                     r'^\s*sudo\b|sudo\s')
    gh_write_re = hc_get("permission_gate.gh_write_regex",
                         r'gh\s+(release\s+(upload|create|edit|delete)|pr\s+(create|merge|close|review)|issue\s+(create|close|comment)|repo\s+(create|delete|rename)|variable\s+set|secret\s+set|workflow\s+(run|disable|enable)|gist\s+create|api\s+.*(-X\s+(PUT|POST|PATCH|DELETE)|--method\s+(PUT|POST|PATCH|DELETE)|-f\b))')
    bypass_re = hc_get("permission_gate.bypass_regex",
                       r'base64\s+(-d|--decode).*\|.*\b(bash|sh|dash|zsh)\b|xxd\s+-r.*\|.*\b(bash|sh)\b|printf\s+[\"\'\\047]%[bdh]|eval\s+\$\(echo')
    scope_write_re = hc_get("permission_gate.scope_write_regex",
                            r'current-scope\.txt|sensitive-approved|permission-approved')
    c1_whitelist = hc_get("permission_gate.c1_whitelist", "")

    # ── 路径变量 ──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    state_dir = os.path.join(project_root, ".omc", "state")

    # ================================================================
    # C1: encoding bypass detection (DG-11)
    # ================================================================
    if re.search(bypass_re, command, re.IGNORECASE):
        if c1_whitelist and re.search(c1_whitelist, command):
            pass  # 白名单匹配，跳过 C1 阻断
        else:
            # _c1_block
            bypass_token = generate_token(12)
            print(file=sys.stderr)
            print("🚫 [Permission Gate] 编码绕过检测 — 强制终端执行模式", file=sys.stderr)
            print("", file=sys.stderr)
            print("检测到编码执行绕过企图 (base64|xxd|printf|eval 管道)。AI 不被允许执行编码命令。", file=sys.stderr)
            print("请复制以下命令到您自己的终端执行：", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"  {command}", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"验证 Token: {bypass_token}", file=sys.stderr)
            print("", file=sys.stderr)
            hc_emit_hook_json("PreToolUse", False,
                              f"[Permission Gate] 编码绕过检测触发。AI 永远不能执行编码/动态执行命令。请人类在自己的终端中执行（Token: {bypass_token}）。")
            flywheel_event("permission_gate", "blocked_encoding_bypass", "P1")
            sys.exit(2)

    # ================================================================
    # 危险命令检测
    # ================================================================
    is_dangerous = False
    danger_type = ""

    # git commit 检测 — token 模式：AI 永不代提交
    if re.search(git_commit_re, command, re.IGNORECASE):
        if not re.search(r'git\s+commit\s+--dry-run|git\s+commit\s+--help', command, re.IGNORECASE):
            commit_token = generate_token(12)
            print(file=sys.stderr)
            print("🔐 [Permission Gate] Git Commit — 强制终端执行模式", file=sys.stderr)
            print("", file=sys.stderr)
            print("AI 不被允许执行 git commit。请复制以下命令到您自己的终端执行：", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"  {command}", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"验证 Token: {commit_token}", file=sys.stderr)
            print("", file=sys.stderr)
            hc_emit_hook_json("PreToolUse", False,
                              f"[Permission Gate] Git commit 已阻断。AI 永远不能代执行 git commit。请人类在自己的终端中执行命令（Token: {commit_token}）。执行后可继续其他操作。")
            flywheel_event("permission_gate", "blocked_git_commit", "P1")
            sys.exit(2)

    # git push 检测
    if re.search(git_push_force_re, command, re.IGNORECASE):
        is_dangerous = True
        danger_type = "git push --force"
    elif re.search(git_push_re, command, re.IGNORECASE) and not re.search(r'git\s+push\s+--?dry-run|git\s+push\s+--help', command, re.IGNORECASE):
        is_dangerous = True
        danger_type = "git push"

    # 删除/破坏性操作检测 — token 模式：AI 永不代执行
    if re.search(destructive_re, command, re.IGNORECASE):
        destroy_token = generate_token(12)
        print(file=sys.stderr)
        print("🚫 [Permission Gate] 破坏性操作 — 强制终端执行模式", file=sys.stderr)
        print("", file=sys.stderr)
        print("AI 不被允许执行破坏性操作。请复制以下命令到您自己的终端执行：", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  {command}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"验证 Token: {destroy_token}", file=sys.stderr)
        print("", file=sys.stderr)
        hc_emit_hook_json("PreToolUse", False,
                          f"[Permission Gate] 破坏性操作已阻断。AI 永远不能代执行 rm/drop/truncate/delete。请人类在自己的终端中执行命令（Token: {destroy_token}）。执行后可继续其他操作。")
        flywheel_event("permission_gate", "blocked_destructive", "P1")
        sys.exit(2)

    # sudo 检测
    if re.search(sudo_re, command, re.IGNORECASE):
        is_dangerous = True
        danger_type = "sudo"

    # gh 写操作检测
    if re.search(gh_write_re, command, re.IGNORECASE):
        is_dangerous = True
        danger_type = "gh external write"

    # scope 文件写入检测（防止 AI 自绕过 scope gate）
    if re.search(scope_write_re, command, re.IGNORECASE):
        # 排除只读操作
        readonly_pattern = (
            r'^\s*ls\b|^\s*cat\b|echo\s+"[^">]*"$|echo\s+\'[^\']*\'$'
            r'|echo\s+[\'\"][^\'\"]+[\'\"]\s*>>'
            r'|python3\s+-c\s|^\s*source\b|^\s*\.\s'
            r'|grep\b|wc\b|head\b|tail\b|^f=|^d=|^fn=|^a='
        )
        if not re.search(readonly_pattern, command, re.IGNORECASE):
            is_dangerous = True
            danger_type = "scope gate bypass"

    # 非危险命令 → 放行
    if not is_dangerous:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 缓存 ──────────────────────────────────
    cache_file = os.path.join(state_dir, "approved-ops.json")
    approved_ops_ttl = int(hc_get("permission_gate.approved_ops_ttl", "1800"))

    # 检查缓存：相同命令签名在 TTL 内是否已批准
    def check_cache(cmd_sig):
        if not os.path.isfile(cache_file):
            return False
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                d = json.load(f)
            entry = d.get(cmd_sig)
            if entry and time.time() - entry.get('ts', 0) < approved_ops_ttl:
                return True
        except Exception:
            pass
        return False

    def write_cache(cmd_sig):
        try:
            d = {}
            if os.path.isfile(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                except Exception:
                    d = {}
            d[cmd_sig] = {"ts": int(time.time()), "type": danger_type}
            tmp = cache_file + '.tmp.' + str(os.getpid())
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            os.rename(tmp, cache_file)
        except Exception:
            pass

    # 统一模式检测: ghost/unattended 降级为"记录+跳过"，不阻断
    mode = is_mode_active(state_dir)
    if mode != "normal":
        flywheel_event("permission_gate", f"mode_skip_{danger_type.replace(' ', '_')}", "P1")
        skipped_file = os.path.join(state_dir, "skipped-errors.md")
        try:
            with open(skipped_file, 'a', encoding='utf-8') as f:
                f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — permission-gate {mode} mode [{danger_type}]\n")
                f.write("```\n")
                f.write(f"{command}\n")
                f.write("```\n")
        except (IOError, OSError):
            pass

        # 同步写入模式 JSON 的 skipped_risks
        _ts = datetime.now(timezone.utc).isoformat()
        _escaped_cmd = json.dumps(command)
        _risk_json = json.dumps({"type": danger_type, "command": command, "timestamp": _ts})
        _mode_append_to_list(state_dir, mode, "skipped_risks", _risk_json)

        print(f"[{mode}] 已记录 {danger_type}: {command[:120]}...（模式降级，不阻断）", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 检查缓存：TTL 秒内已批准的同签名操作 → 自动放行
    cmd_sig = command[:120]
    if check_cache(cmd_sig):
        print(f"[权限缓存] {approved_ops_ttl} 秒内已批准的同签名操作: {command[:80]}...", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 随机验证码审批机制 ──────────────────────
    permission_marker = os.path.join(state_dir, "permission-approved")
    permission_required = os.path.join(state_dir, "permission-required")

    # 检查是否有待处理的验证码
    if os.path.isfile(permission_required):
        try:
            with open(permission_required, 'r', encoding='utf-8') as f:
                expected_code = f.read().strip()
        except (IOError, OSError):
            expected_code = ""

        if os.path.isfile(permission_marker):
            try:
                with open(permission_marker, 'r', encoding='utf-8') as f:
                    actual_code = f.read().strip()
            except (IOError, OSError):
                actual_code = ""

            if actual_code == expected_code:
                # 检查标记文件新鲜度
                try:
                    age = time.time() - os.path.getmtime(permission_marker)
                    fresh = age < approved_ops_ttl
                except OSError:
                    fresh = True
                if fresh:
                    # 验证码匹配 → 有效授权，清理并放行 + 写入缓存
                    write_cache(cmd_sig)
                    try:
                        os.remove(permission_marker)
                    except OSError:
                        pass
                    try:
                        os.remove(permission_required)
                    except OSError:
                        pass
                    print(json.dumps({"continue": True}))
                    sys.exit(0)

        # 标记文件过期或验证码不匹配 → 清理旧码
        try:
            os.remove(permission_required)
        except OSError:
            pass

    # 阻断：无有效权限申请 → 生成随机验证码
    if danger_type in ("git push --force",):
        severity = "🔴 致命"
    elif danger_type in ("destructive operation",):
        severity = "🔴 致命"
    else:
        severity = "🟡 高危"

    # 生成随机 8 位 hex 验证码
    approval_code = generate_token(8)
    if not approval_code:
        approval_code = f"{os.getpid() * int(time.time()) & 0xFFFFFFFF:08x}"

    # 写入 permission-required 文件
    os.makedirs(state_dir, exist_ok=True)
    try:
        with open(permission_required, 'w', encoding='utf-8') as f:
            f.write(approval_code + "\n")
    except (IOError, OSError) as e:
        print(f"⛔ [Permission Gate] 无法写入验证码文件: {e}", file=sys.stderr)
        print(json.dumps({"continue": False}))
        sys.exit(2)

    flywheel_event("permission_gate", f"blocked_captcha_{danger_type.replace(' ', '_')}", "P1")

    # 输出 CAPTCHA 阻断信息（等效 agentic_captcha 函数）
    title = f"Permission Gate: {severity} {danger_type}"
    approve_file = os.path.join(".omc", "state", "permission-approved")
    description = "🚫 危险操作已阻断！AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）。"

    print(f"🔑 [{title}] 需要批准 — 请查看 AI 的说明", file=sys.stderr)
    # 输出 hook JSON
    captcha_msg = (
        f"[CAPTCHA] {title} | 验证码: {approval_code} | "
        f"批准文件: {approve_file} | {description} | "
        f"终端执行: echo \"{approval_code}\" > {approve_file} | "
        f"批准后 AI 行动协议: 检查批准文件是否存在(cat {approve_file} 2>/dev/null)，存在则重试被阻断的原操作，不存在则等待用户批准"
    )
    hc_emit_hook_json("PreToolUse", True, captcha_msg)
    sys.exit(2)


if __name__ == "__main__":
    main()
