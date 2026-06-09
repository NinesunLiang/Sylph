#!/usr/bin/env python3
"""
posttool-output-compressor.py — PostToolUse:Read|Bash
产出压缩: 压缩工具输出到适合低阶模型的有效上下文范围

压缩规则（P0 纯规则压缩）:
  Read 工具:
    - 行数 > 100 行 → 首30 + 尾20 + 中间摘要
    - JSON 文件 > 50 行 → schema + 条目数 + 示例前3
    - 重复读 → 仅记录 mtime hash
  Bash 工具:
    - stdout > 2000 chars → 首尾各500 + 中间摘要
    - JSON 数组 > 30 项 → schema + 前3后2
    - exit_code != 0 → 不压缩（保留完整异常信息）
    - 构建/测试 → 仅保留结果摘要

输出: additionalContext 注入给 AI，不修改原始 tool_result
"""

import json
import os
import re
import sys
import hashlib
from pathlib import Path

# ─── 配置（可通过环境变量覆盖） ───
READ_LINE_LIMIT = int(os.environ.get("CC_READ_LINE_LIMIT", "100"))
READ_HEAD_LINES = int(os.environ.get("CC_READ_HEAD_LINES", "30"))
READ_TAIL_LINES = int(os.environ.get("CC_READ_TAIL_LINES", "20"))
BASH_CHAR_LIMIT = int(os.environ.get("CC_BASH_CHAR_LIMIT", "2000"))
BASH_HEAD_CHARS = int(os.environ.get("CC_BASH_HEAD_CHARS", "500"))
BASH_TAIL_CHARS = int(os.environ.get("CC_BASH_TAIL_CHARS", "500"))
JSON_ITEM_LIMIT = int(os.environ.get("CC_JSON_ITEM_LIMIT", "30"))

# ─── 状态目录 ───
STATE_DIR = os.environ.get("STATE_DIR", "")

# 可执行文件名列表（构建/测试工具）
BUILD_TOOLS = {"npm", "yarn", "pnpm", "go", "make", "cmake", "cargo", "mvn",
               "gradle", "bazel", "ninja", "meson", "scons", "tsc", "webpack",
               "vite", "rollup", "esbuild", "jest", "vitest", "pytest",
               "mocha", "rspec", "cargo test", "go test", "python -m pytest"}


def get_cache_dir():
    """获取输出缓存目录"""
    if not STATE_DIR:
        return None
    cache_dir = Path(STATE_DIR) / "output-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_summary(file_path: str, content: str) -> str | None:
    """检查是否为重复读取，返回缓存摘要或 None"""
    cache_dir = get_cache_dir()
    if not cache_dir or not file_path:
        return None
    try:
        st = os.stat(file_path)
        cache_key = f"{file_path}|{st.st_mtime}|{st.st_size}"
        content_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        cache_file = cache_dir / f"{content_hash}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return data.get("summary", "")
            except (json.JSONDecodeError, OSError):
                pass
        # 写缓存
        summary = _compress_read_content(content, file_path)
        cache_file.write_text(json.dumps({
            "path": file_path,
            "mtime": st.st_mtime,
            "size": st.st_size,
            "summary": summary,
            "content_len": len(content)
        }, ensure_ascii=False))
        return None  # 第一次读，返回 None 表示正常压缩
    except (OSError, FileNotFoundError):
        return None


def is_build_output(text: str) -> bool:
    """检测是否为构建/测试输出"""
    first_line = text.split("\n", 1)[0] if text else ""
    for tool in BUILD_TOOLS:
        if first_line.startswith(tool) or f" {tool}" in first_line[:100]:
            return True
    # 检测测试输出模式
    test_patterns = [
        r"^(PASS|FAIL|OK|ERROR)\s",
        r"Tests:\s+\d+",
        r"✅?\s*\d+\s*(passed|failed)",
        r"Ran\s+\d+\s+test",
        r"Test\s+run:\s+\d+",
    ]
    for pat in test_patterns:
        if re.search(pat, text, re.MULTILINE):
            return True
    return False


def compress_build_output(text: str) -> str:
    """压缩构建/测试输出为结果摘要"""
    lines = text.split("\n")
    # 提取关键行
    summary_lines = []
    fail_lines = []
    pass_count = fail_count = skip_count = 0
    for line in lines:
        stripped = line.strip()
        if re.search(r"(FAIL|ERROR|失败|错误|✗|✘|×|❌)", stripped):
            fail_lines.append(stripped[:200])
            fail_count += 1
        elif re.search(r"(PASS|OK|全部通过|✓|✅|✔)", stripped):
            summary_lines.append(stripped[:200])
            pass_count += 1
        elif re.search(r"(Tests?:|测试|Suites?:|套件)", stripped, re.IGNORECASE):
            summary_lines.append(stripped[:200])
        elif re.search(r"(skipped|跳过|SKIP)", stripped, re.IGNORECASE):
            skip_count += 1

    result = f"[构建/测试结果] 通过:{pass_count} 失败:{fail_count} 跳过:{skip_count}"
    if summary_lines:
        result += "\n" + "\n".join(summary_lines[:5])
    if fail_lines:
        result += "\n[失败项]\n" + "\n".join(fail_lines[:10])

    return result


def _compress_read_content(content: str, file_path: str = "") -> str:
    """压缩文件内容读取"""
    lines = content.split("\n")
    if len(lines) <= READ_LINE_LIMIT:
        return ""

    # JSON 文件特殊处理
    if file_path and (file_path.endswith(".json") or file_path.endswith(".jsonl")):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                total = len(data)
                if total > JSON_ITEM_LIMIT:
                    preview = json.dumps(data[:3], ensure_ascii=False, indent=2)
                    return (f"[JSON 数组: {total} 项, {len(content)} chars] "
                            f"前3项预览:\n{preview}")
            elif isinstance(data, dict):
                keys = list(data.keys())
                return (f"[JSON 对象: {len(keys)} 键, {len(content)} chars] "
                        f"键列表: {', '.join(keys[:20])}")
        except (json.JSONDecodeError, ValueError):
            pass

    # 回归代码/文本文件
    head = "\n".join(lines[:READ_HEAD_LINES])
    tail = "\n".join(lines[-READ_TAIL_LINES:]) if READ_TAIL_LINES > 0 else ""
    compressed = len(lines) - READ_HEAD_LINES - READ_TAIL_LINES
    return (f"[Read 压缩: 共{len(lines)}行{len(content)}chars, "
            f"保留首{READ_HEAD_LINES}+尾{READ_TAIL_LINES}行, "
            f"压缩{compressed}行中间内容]\n{head}\n[...压缩{compressed}行...]\n{tail}")


def compress_read_output(content: str, file_path: str) -> str:
    """压缩 Read 工具输出"""
    # 检查是否重复读取
    cached_summary = get_cached_summary(file_path, content)
    if cached_summary:
        return (f"[已缓存: {file_path}] 文件未变，上次读过的内容不再重复\n"
                f"摘要: {cached_summary[:300]}")

    return _compress_read_content(content, file_path)


def compress_bash_output(content: str, exit_code: int, command: str) -> str:
    """压缩 Bash 工具输出"""
    if not content:
        return ""

    # 异常输出保留完整
    if exit_code != 0 and exit_code is not None:
        return ""

    if len(content) <= BASH_CHAR_LIMIT:
        return ""

    # 构建/测试输出
    if is_build_output(content):
        summary = compress_build_output(content)
        if len(summary) < len(content) * 0.7:  # 只输出优于原大小的
            return (f"[Bash 压缩: 构建/测试输出 {len(content)}chars, "
                    f"压缩为摘要]\n{summary}")

    # 通用压缩
    head = content[:BASH_HEAD_CHARS]
    tail = content[-BASH_TAIL_CHARS:] if BASH_TAIL_CHARS > 0 else ""
    compressed = len(content) - BASH_HEAD_CHARS - BASH_TAIL_CHARS
    return (f"[Bash 压缩: 共{len(content)}chars, "
            f"保留首{BASH_HEAD_CHARS}+尾{BASH_TAIL_CHARS}chars, "
            f"压缩{compressed}chars中间]\n{head}\n[...压缩{compressed}chars...]\n{tail}")


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"continue": True}))
            return

        data = json.loads(raw_input)
        event = data.get("hook_event_name", "PostToolUse")
        tool_response = data.get("tool_response", {})

        # 提取内容
        if event == "PostToolUseFailure":
            # 失败事件不压缩，跳过
            print(json.dumps({"continue": True}))
            return

        # 提取 tool_name
        tool_name = data.get("tool_name", "")
        if not tool_name:
            # 从 args 推断
            args = data.get("args", {})
            if "command" in args:
                tool_name = "Bash"
            elif "file_path" in args or "filePath" in args:
                tool_name = "Read"

        # 只处理 Read 和 Bash
        if tool_name not in ("Read", "Bash"):
            print(json.dumps({"continue": True}))
            return

        content = tool_response.get("content", "") or \
                  tool_response.get("stdout", "") or \
                  tool_response.get("stderr", "") or ""
        exit_code = tool_response.get("exit_code")
        file_path = data.get("tool_input", {}).get("file_path", "") or \
                    data.get("args", {}).get("filePath", "") or \
                    data.get("args", {}).get("file_path", "")
        command = data.get("tool_input", {}).get("command", "") or \
                  data.get("args", {}).get("command", "")

        if not content:
            print(json.dumps({"continue": True}))
            return

        # 生成压缩内容
        if tool_name == "Read":
            summary = compress_read_output(content, file_path)
        else:
            summary = compress_bash_output(content, exit_code, command)

        if not summary:
            print(json.dumps({"continue": True}))
            return

        # 注入 additionalContext
        ctx = json.dumps({
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"\n⚡ [输出压缩] 工具: {tool_name}\n{summary}\n"
            }
        }, ensure_ascii=False)
        print(ctx)

    except (json.JSONDecodeError, BrokenPipeError, EOFError):
        print(json.dumps({"continue": True}))
    except Exception as e:
        # 任何异常都不影响主流程
        print(json.dumps({"continue": True}), file=sys.stderr)
        sys.stderr.write(f"[output-compressor] Error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
