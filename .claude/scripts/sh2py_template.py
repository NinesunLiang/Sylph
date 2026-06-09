#!/usr/bin/env python3
"""
Python 跨平台脚本模板
替换 #!/usr/bin/env bash 的通用等价实现

跨平台注意点：
  1. 路径：用 pathlib.Path，不用手工拼接
  2. 临时文件：tempfile.NamedTemporaryFile / mkdtemp
  3. 子进程：subprocess.run(capture_output=True, text=True)
  4. 日期：datetime.now()
  5. 信号处理：signal.signal()
  6. 文件判存：Path.exists()/.is_file()
  7. sleep：time.sleep()
  8. mktemp：tempfile.mkstemp() / mkdtemp()
  9. read：input() / sys.stdin.read()
  10. trap EXIT：atexit.register()
"""
import sys
import os
import subprocess
import json
import time
import tempfile
import signal
import atexit
from datetime import datetime
from pathlib import Path


def run(cmd, **kwargs):
    """subprocess.run 封装，替代 $(command)"""
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    result = subprocess.run(cmd, **default)
    return result.stdout.strip(), result.returncode, result.stderr


def ensure_dir(p: Path):
    """mkdir -p 的 Python 等价"""
    p.mkdir(parents=True, exist_ok=True)


def write_lines(path: Path, lines: list[str]):
    """覆盖写入多行到文件"""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_line(path: Path, line: str):
    """追加单行到文件"""
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_lines(path: Path) -> list[str]:
    """读取文件全部行"""
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def find_files(root: Path, pattern: str, max_depth: int = -1) -> list[Path]:
    """替代 find. 不支持复杂模式时用 glob(**/)"""
    result = []
    for p in root.rglob(pattern):
        result.append(p)
    return result


def main():
    """Main entry point - to be overridden by each script"""
    pass


if __name__ == "__main__":
    main()
