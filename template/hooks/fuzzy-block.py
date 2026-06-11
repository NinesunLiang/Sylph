#!/usr/bin/env python3
"""fuzzy-block.py — PreToolUse — 模糊指令硬阻断（C1 指令清晰度门禁）
Role: 模糊指令硬阻断 — turn-counter 标记模糊指令后阻断所有工具调用，强制 AI 先澄清

等效移植自 fuzzy-block.sh:
- 读取 .fuzzy-block-active 标记文件（由 turn-counter.sh 创建）
- 智能恢复：当前工具调用有 file_path 或 command 时自动解除标记
- 自主模式（ghost/goal）降级为记录不阻断
- 硬阻断时调用 agentic_menu_two 输出菜单（通过 stderr + sys.exit(2)）
"""

import json
import os
import sys
import time
import zlib
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event, is_mode_active

# ─── 路径解析 ───

_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"
_FUZZY_MARKER = _STATE_DIR / ".fuzzy-block-active"


# ─── C5: 原子写 + CRC 辅助函数 ───

def _write_marker_atomic(content_bytes):
    """Atomic write to .fuzzy-block-active via .tmp + mv + CRC."""
    tmp = _STATE_DIR / ".fuzzy-block-active.tmp"
    try:
        tmp.write_bytes(content_bytes)
        tmp.rename(_FUZZY_MARKER)
    except OSError:
        # Fallback direct write
        _FUZZY_MARKER.write_bytes(content_bytes)


def _make_marker_with_crc(text):
    """Create marker content with CRC32 suffix for integrity verification."""
    text_bytes = text.encode("utf-8")
    crc = format(zlib.crc32(text_bytes) & 0xFFFFFFFF, '08x')
    return text_bytes + b"||" + crc.encode("utf-8")


def main():
    # ── 门禁检查 ──
    if not hc_enabled("fuzzy_block"):
        print('{"continue": true}')
        sys.exit(0)

    # ── 没有标记 → 直接放行 ──
    if not _FUZZY_MARKER.exists():
        print('{"continue": true}')
        sys.exit(0)

    # ── C5: CRC 校验 + 自愈超时 ──
    # CRC 校验：标记内容 > 50 字节时校验完整性（防止截断/损坏）
    marker_integrity = False
    try:
        marker_bytes = _FUZZY_MARKER.read_bytes()
        if len(marker_bytes) > 50:
            # 格式: content||crc32_hex
            marker_text = marker_bytes.decode("utf-8", errors="replace")
            if "||" in marker_text:
                parts = marker_text.rsplit("||", 1)
                if len(parts) == 2:
                    content_part = parts[0].encode("utf-8")
                    stored_crc = parts[1].strip()
                    computed_crc = format(zlib.crc32(content_part) & 0xFFFFFFFF, '08x')
                    if stored_crc == computed_crc:
                        marker_integrity = True
                    else:
                        # CRC 不匹配 → 标记损坏
                        _FUZZY_MARKER.unlink(missing_ok=True)
                        print("[fuzzy-block] CRC 校验失败：标记文件损坏，已自动清除并放行",
                              file=sys.stderr, flush=True)
                        flywheel_event("fuzzy_block", "crc_fail_autoclean", "P2")
                        print('{"continue": true}')
                        sys.exit(0)
            else:
                # 旧格式无 CRC → 补写带 CRC 版本（增强迁移）
                new_content = marker_text.strip() + "||" + format(zlib.crc32(marker_bytes) & 0xFFFFFFFF, '08x')
                _write_marker_atomic(new_content.encode("utf-8"))
                marker_integrity = True
        else:
            # 短内容直接信任
            marker_integrity = True
    except Exception:
        # 读取失败 → 清除并放行
        _FUZZY_MARKER.unlink(missing_ok=True)
        print("[fuzzy-block] 标记读取异常，已清除并放行",
              file=sys.stderr, flush=True)
        flywheel_event("fuzzy_block", "read_error_autoclean", "P2")
        print('{"continue": true}')
        sys.exit(0)

    # ── C5: 自愈超时 — 标记存在 >30 秒自动清除（防止僵尸标记） ──
    if marker_integrity:
        try:
            mtime = _FUZZY_MARKER.stat().st_mtime
            if time.time() - mtime > 30:
                _FUZZY_MARKER.unlink(missing_ok=True)
                print("[fuzzy-block] 自愈超时：标记存在 >30 秒，已自动清除并放行",
                      file=sys.stderr, flush=True)
                flywheel_event("fuzzy_block", "self_heal_timeout", "P2")
                print('{"continue": true}')
                sys.exit(0)
        except OSError:
            pass

    # ── 读取 stdin ──
    stdin_data = sys.stdin.read()

    # ── 智能恢复：检查当前工具调用是否明确（有具体 file_path 或 command 则自动解除） ──
    if stdin_data and stdin_data.strip():
        try:
            payload = json.loads(stdin_data)
            tool_name = payload.get("tool_name", "") or payload.get("tool", "")
            tool_input = payload.get("tool_input", {}) or payload.get("input", {})
            file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
            command = tool_input.get("command", "")
            if file_path or command:
                _FUZZY_MARKER.unlink(missing_ok=True)
                print(f"[fuzzy-block] 自动解除：当前指令明确（{tool_name}）",
                      file=sys.stderr, flush=True)
                flywheel_event("fuzzy_block", "auto_release", "P3")
                # 透传 stdin
                sys.stdout.write(stdin_data)
                sys.exit(0)
        except (json.JSONDecodeError, Exception):
            pass

    # ── 读取标记中的警告信息 ──
    try:
        warning_msg = _FUZZY_MARKER.read_text(encoding="utf-8").strip()
    except Exception:
        warning_msg = "模糊指令"

    # ── 自动/无人值守模式降级为记录 ──
    mode = is_mode_active(str(_STATE_DIR))
    if mode != "normal":
        print(f"[fuzzy-block] {warning_msg}（{mode}模式，降级为记录不阻断）",
              file=sys.stderr, flush=True)
        _FUZZY_MARKER.unlink(missing_ok=True)
        print('{"continue": true}')
        sys.exit(0)

    # ── 硬阻断：标记存在 + 非自主模式 → 输出 Agentic UI 菜单 ──
    flywheel_event("fuzzy_block", "blocked", "P2")

    reason = warning_msg[:200]  # 截断，等效 head -c 200
    sep = "═" * 55
    menu_lines = [
        "",
        f"📋 [模糊指令阻断]",
        sep,
        f"指令不明确，无法执行具体工具调用。原因: {reason}",
        "",
        "请选择：",
        "  1. 向用户澄清具体目标 — 暂停执行，向用户提问明确后再继续",
        "  2. 取消操作 — 不执行任何操作",
        "",
    ]
    print("\n".join(menu_lines), file=sys.stderr, flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
