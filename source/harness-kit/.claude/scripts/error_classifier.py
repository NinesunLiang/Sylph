#!/usr/bin/env python3
"""
Shared error classification library for Carror OS hooks.
Zero external dependencies (pure Python standard library).

Usage:
    python3 error_classifier.py classify <cmd> <exit_code> <output>   -> JSON array
    python3 error_classifier.py signature <cmd> <exit_code> <type>    -> hex string
    python3 error_classifier.py classify-by-cmd <cmd>                 -> type string
"""

import hashlib
import json
import re
import sys
from typing import Any


# 症状分类映射（E5: symptom-level grouping for cross-session pattern detection）
# 每个 type → symptom 的映射，用于发现跨 session 的症状重复模式
SYMPTOM_MAP: dict[str, str] = {
    "go_compile": "compile_error",
    "go_undefined": "compile_error",
    "go_unused_import": "compile_error",
    "typescript": "compile_error",
    "rust_compile": "compile_error",
    "missing_module": "dependency_missing",
    "python_missing_module": "dependency_missing",
    "python_error": "runtime_error",
    "make_error": "build_failure",
    "permission": "permission_denied",
    "oom": "resource_exhaustion",
    "unknown": "unclassified",
}


def classify_error(cmd: str, exit_code: str | int, output: str) -> list[dict[str, Any]]:
    """Multi-language error classifier. Returns list of error dicts."""
    categories: list[dict[str, Any]] = []

    # --- Go errors ---
    if re.search(r'\.go:\d+:\d+:', output):
        go_errors = re.findall(r'(\S+\.go:\d+:\d+):\s*(.+)', output)
        if go_errors:
            file_path, error_msg = go_errors[0]
            categories.append({
                "type": "go_compile",
                "symptom": "compile_error",
                "file": file_path.split(':')[0],
                "line": file_path.split(':')[1],
                "message": error_msg.strip()[:200],
                "suggestions": [
                    f"检查 {file_path.split(':')[0]}:{file_path.split(':')[1]} 的语法",
                    "运行 `go vet ./...` 检查潜在问题",
                    "确认导入包路径正确 (`go mod tidy`)"
                ]
            })
    if 'undefined:' in output.lower() or 'undeclared name' in output.lower():
        categories.append({
            "type": "go_undefined",
            "symptom": "compile_error",
            "message": "未定义的标识符",
            "suggestions": [
                "检查变量/函数名拼写是否正确",
                "确认是否在正确的包作用域内",
                "运行 `go mod tidy` 确保依赖完整"
            ]
        })
    if 'imported and not used' in output:
        categories.append({
            "type": "go_unused_import",
            "symptom": "compile_error",
            "message": "导入了未使用的包",
            "suggestions": [
                "删除未使用的 import",
                "如果需要使用 side effect，改为 `_ \"package\"`"
            ]
        })
    # --- TypeScript/JavaScript errors ---
    ts_match = re.search(r'error\s+(TS\d+):\s*(.+)', output)
    if ts_match:
        categories.append({
            "type": "typescript",
            "symptom": "compile_error",
            "code": ts_match.group(1),
            "message": ts_match.group(2).strip()[:200],
            "suggestions": [
                "查阅 TypeScript 文档: https://www.typescriptlang.org/docs/handbook/release-notes/",
                "运行 `npx tsc --noEmit` 查看完整类型错误列表",
                "检查 tsconfig.json 的 strict 设置"
            ]
        })
    if "cannot find module" in output.lower() or "module not found" in output.lower():
        categories.append({
            "type": "missing_module",
            "symptom": "dependency_missing",            "message": "找不到模块",
            "suggestions": [
                "运行 `npm install` 或 `pnpm install` 安装依赖",
                "检查 import 路径是否正确",
                "确认 node_modules 是否存在 (`ls node_modules/`)"
            ]
        })
    # --- Python errors ---
    py_match = re.search(r'((?:Type|Value|Import|Attribute|Name|Key|Index|Runtime|Syntax)Error):\s*(.+)', output)
    if py_match:
        categories.append({
            "type": "python_error",
            "symptom": "runtime_error",
            "error_type": py_match.group(1),
            "message": py_match.group(2).strip()[:200],
            "suggestions": [
                f"检查 {py_match.group(1)} 的具体原因",
                "运行 `python -m py_compile <file>` 检查语法",
                "确认虚拟环境已激活且依赖已安装 (`pip list`)"
            ]
        })
    if "no module named" in output.lower():
        categories.append({
            "type": "python_missing_module",
            "symptom": "dependency_missing",            "message": "找不到 Python 模块",
            "suggestions": [
                "运行 `pip install <module_name>` 安装缺失的包",
                "确认使用了正确的 Python 解释器 (`which python`)",
                "检查 PYTHONPATH 环境变量"
            ]
        })
    # --- Rust errors ---
    if re.search(r'error\[E\d+\]:', output):
        rust_match = re.search(r'error\[(E\d+)\]:\s*(.+)', output)
        if rust_match:
            categories.append({
                "type": "rust_compile",
                "symptom": "compile_error",
                "code": rust_match.group(1),
                "message": rust_match.group(2).strip()[:200],
                "suggestions": [
                    f"运行 `rustc --explain {rust_match.group(1)}` 获取详细解释",
                    "运行 `cargo check` 快速验证",
                    "检查 borrow checker 相关的所有权和生命周期"
                ]
            })
    # --- Make errors ---
    if "make:" in output or "Makefile" in output:
        categories.append({
            "type": "make_error",
            "symptom": "build_failure",            "message": "Make 构建失败",
            "suggestions": [
                "检查 Makefile 中的目标和依赖",
                "运行 `make -n` 查看实际执行的命令",
                "确认所有依赖工具已安装"
            ]
        })
    # --- Generic error patterns ---
    if "permission denied" in output.lower():
        categories.append({
            "type": "permission",
            "symptom": "permission_denied",            "message": "权限被拒绝",
            "suggestions": [
                "检查文件/目录权限 (`ls -la`)",
                "确认有足够的执行权限",
                "不要使用 sudo，检查项目目录所有权"
            ]
        })
    if "out of memory" in output.lower() or "oom" in output.lower():
        categories.append({
            "type": "oom",
            "symptom": "resource_exhaustion",            "message": "内存不足",
            "suggestions": [
                "减少并行度 (如 `GOMAXPROCS=1` 或 `--max-old-space-size`)",
                "关闭其他占用内存的程序",
                "增加 swap 空间"
            ]
        })
    # --- No match fallback ---
    if not categories:
        categories.append({
            "type": "unknown",
            "symptom": "unclassified",
            "message": f"构建命令退出码 {exit_code}",
            "suggestions": [
                "仔细阅读第一条错误信息（通常后续错误是级联的）",
                "运行 `git diff` 确认最近的改动",
                "尝试最小化复现：只编译修改的文件",
                "检查 CI/CD 是否有相同的失败"
            ]
        })
    return categories


def classify_by_command(cmd: str) -> str:
    """Simple command-based error type classification (for error-dna.sh lightweight usage)."""
    cmd_lower = cmd.lower()
    if any(x in cmd_lower for x in ['go build', 'go test', 'npm run build', 'npm build', 'cargo build', 'tsc']):
        return 'build'
    elif any(x in cmd_lower for x in ['go test', 'npm test', 'pytest', 'jest']):
        return 'test'
    elif any(x in cmd_lower for x in ['git']):
        return 'git'
    elif any(x in cmd_lower for x in ['npm install', 'go get', 'pip install']):
        return 'dependency'
    elif any(x in cmd_lower for x in ['lint', 'eslint', 'golangci-lint']):
        return 'lint'
    elif any(x in cmd_lower for x in ['docker']):
        return 'docker'
    elif any(x in cmd_lower for x in ['curl', 'wget', 'http']):
        return 'network'
    elif any(x in cmd_lower for x in ['find', 'grep', 'sed', 'awk']):
        return 'file_ops'
    else:
        return 'runtime'


def generate_signature(cmd: str, exit_code: str | int, error_type: str) -> str:
    """Generate stable MD5 signature from command + exit code + error type."""
    raw = f"{cmd}|{exit_code}|{error_type}"
    # usedforsecurity=False: 本用途为错误去重指纹，非安全/加密用途 (Python 3.9+)
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:16]


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    subcommand = sys.argv[1]

    if subcommand == 'classify':
        cmd = sys.argv[2] if len(sys.argv) > 2 else ''
        exit_code = sys.argv[3] if len(sys.argv) > 3 else '1'
        output = sys.argv[4] if len(sys.argv) > 4 else ''
        errors = classify_error(cmd, exit_code, output)
        print(json.dumps(errors, ensure_ascii=False))

    elif subcommand == 'signature':
        cmd = sys.argv[2] if len(sys.argv) > 2 else ''
        exit_code = sys.argv[3] if len(sys.argv) > 3 else '0'
        error_type = sys.argv[4] if len(sys.argv) > 4 else 'unknown'
        sig = generate_signature(cmd, exit_code, error_type)
        print(sig)

    elif subcommand == 'classify-by-cmd':
        cmd = sys.argv[2] if len(sys.argv) > 2 else ''
        print(classify_by_command(cmd))

    else:
        print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
