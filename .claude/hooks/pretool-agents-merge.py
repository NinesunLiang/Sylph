#!/usr/bin/env python3
"""
pretool-agents-merge.py — AGENTS.md 智能合并策略

触发: PostToolUse(Edit|Write) 作用于 AGENTS.md
也可由 install.sh / harness-kit-install.sh 在覆盖安装后手动调用。

流程:
  1. 读取当前 AGENTS.md（发布包标准版）
  2. 备份旧 AGENTS.md → .omc/state/AGENTS.user.md（幂等: 不重复备份）
  3. diff 提取用户自定义内容（旧有而新无的行块）
  4. 将用户自定义内容插入新 AGENTS.md 头部，加分割注释

安全铁律:
  - exit 0 确保永不阻断
  - 输出 JSON {"continue": true} 兼容 hook 协议
  - 不依赖 set -e
  - 所有文件读写用 try/except 保护
"""
import difflib
import json
import os
import sys
from pathlib import Path

# ──────────── 配置 ────────────
PROJECT_ROOT = Path.cwd()
AGENTS_PATH = PROJECT_ROOT / "AGENTS.md"
BACKUP_PATH = PROJECT_ROOT / ".omc" / "state" / "AGENTS.user.md"
MERGE_DONE_MARKER = PROJECT_ROOT / ".omc" / "state" / "AGENTS.merge-done"

# 标准版头部标记（这些行属于 Carror OS 标准内容，不作为用户自定义提取）
STANDARD_HEADERS = {
    "@.claude/kernel.md",
    "@.claude/index.md",
    "# Carror OS — 行为治理路由",
    "## ═══ Carror OS 治理框架═══",
    "## ═══════ Carror OS 治理框架═══",
}

# 标准版内容前缀匹配（行如果匹配这些前缀，视为标准内容）
STANDARD_PREFIXES = (
    "@.claude/",
    "# Carror OS",
    "## ═══",
    "## ═════",
)


def read_file(path: Path) -> list[str]:
    """读文件为行列表，文件不存在返回空列表。"""
    try:
        if path.exists() and path.stat().st_size > 0:
            return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError) as e:
        print(f"[agents-merge] ⚠️ 读取失败 {path}: {e}", file=sys.stderr)
    return []


def write_file(path: Path, lines: list[str]) -> bool:
    """写行列表到文件，创建父目录。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError as e:
        print(f"[agents-merge] ⚠️ 写入失败 {path}: {e}", file=sys.stderr)
        return False


def is_standard_line(line: str) -> bool:
    """判断一行是否属于标准版内容（应排除在用户自定义之外）。"""
    stripped = line.strip()
    if not stripped:
        return False  # 空行不判定，交由上下文判断
    if stripped in STANDARD_HEADERS:
        return True
    if any(stripped.startswith(p) for p in STANDARD_PREFIXES):
        return True
    # 路由索引表中的分隔线和常见表头
    if stripped.startswith("|") and any(
        kw in stripped
        for kw in ["域 | 说明", "name            | what", "───"]
    ):
        return True
    return False


def extract_user_content(old_lines: list[str], new_lines: list[str]) -> list[str]:
    """
    从旧 AGENTS.md 中提取用户自定义内容（旧有而新无的行块）。
    
    使用 difflib.Differ 做行级 diff，找出 old-only 的连续行块。
    然后进一步过滤：排除标准版头部标记、标准前缀行。
    
    返回用户自定义的行列表（含行末换行符）。
    """
    if not old_lines:
        return []

    # 用 Differ 做序列比较
    differ = difflib.Differ()
    diff_result = list(differ.compare(old_lines, new_lines))

    # 收集只出现在旧文件中的行（前缀 '- '）
    user_lines = []
    current_block = []

    for line in diff_result:
        if line.startswith("- "):
            # 旧文件独有的行
            content = line[2:]  # 去掉 '- ' 前缀
            current_block.append(content)
        else:
            # 如果当前有积累的块，收尾并追加
            if current_block:
                # 过滤掉完全是标准内容的块
                filtered = _filter_standard_block(current_block)
                user_lines.extend(filtered)
                current_block = []

    # 处理最后一个块
    if current_block:
        filtered = _filter_standard_block(current_block)
        user_lines.extend(filtered)

    return user_lines


def _filter_standard_block(lines: list[str]) -> list[str]:
    """
    过滤块中的标准内容行。
    策略：
    - 如果整块都是标准头/前缀行，返回空
    - 如果块中混有用户内容和标准行，保留用户内容行
    """
    if not lines:
        return []

    # 检查是否整块都是标准内容
    non_standard = [l for l in lines if not is_standard_line(l)]
    if not non_standard:
        return []  # 整块都是标准内容，丢弃

    return non_standard


def agents_merge() -> bool:
    """
    执行 AGENTS.md 智能合并。
    
    返回 True 表示有变更，False 表示无需变更。
    """
    # 读取新 AGENTS.md（当前文件）
    new_lines = read_file(AGENTS_PATH)
    if not new_lines:
        # 没有 AGENTS.md，不处理
        print("[agents-merge] ℹ️ AGENTS.md 不存在，跳过", file=sys.stderr)
        return False

    # 读取旧备份
    old_lines = read_file(BACKUP_PATH)

    if not old_lines:
        # 首次运行：仅备份当前 AGENTS.md，不合并
        write_file(BACKUP_PATH, new_lines)
        touch_file(MERGE_DONE_MARKER)
        print(
            "[agents-merge] ✅ 首次备份 AGENTS.md → .omc/state/AGENTS.user.md",
            file=sys.stderr,
        )
        return True

    # 检查是否内容完全相同（sha256 快速判断）
    old_content = "".join(old_lines)
    new_content = "".join(new_lines)
    if old_content == new_content:
        print("[agents-merge] ℹ️ AGENTS.md 无变化，跳过合并", file=sys.stderr)
        return False

    # 提取用户自定义内容
    user_lines = extract_user_content(old_lines, new_lines)

    if not user_lines:
        # 用户没有添加任何自定义内容，只备份新版本
        write_file(BACKUP_PATH, new_lines)
        touch_file(MERGE_DONE_MARKER)
        print(
            "[agents-merge] ℹ️ 未检测到用户自定义内容，仅更新备份",
            file=sys.stderr,
        )
        return True

    # 合并：用户自定义内容 → 头部 + 分割注释 + 新标准内容
    header_comment = [
        "<!-- ═══════════════════════════════════════════════════ -->\n",
        "<!-- ⚠️ 用户自定义内容（自动保留自 .omc/state/AGENTS.user.md） -->\n",
        "<!-- ═══════════════════════════════════════════════════ -->\n",
        "\n",
    ]
    # 确保用户内容以换行符结尾
    user_content_clean = []
    for line in user_lines:
        if not line.endswith("\n"):
            line += "\n"
        user_content_clean.append(line)
    if user_content_clean and user_content_clean[-1].strip():
        user_content_clean.append("\n")

    separator = [
        "<!-- ═══════════════════════════════════════════════════ -->\n",
        "<!-- ▼ 标准 Carror OS 治理模板 ▼ -->\n",
        "<!-- ═══════════════════════════════════════════════════ -->\n",
        "\n",
    ]

    merged_lines = header_comment + user_content_clean + separator + new_lines

    # 写回 AGENTS.md
    if write_file(AGENTS_PATH, merged_lines):
        # 更新备份为当前合并后的版本（包含用户内容，下次 diff 可继续）
        write_file(BACKUP_PATH, merged_lines)
        touch_file(MERGE_DONE_MARKER)
        print(
            f"[agents-merge] ✅ 已合并 {len(user_lines)} 行用户自定义内容到 AGENTS.md",
            file=sys.stderr,
        )
        return True
    return False


def touch_file(path: Path) -> None:
    """幂等地创建标记文件。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    except OSError:
        pass


def main():
    """主入口：处理 CLI 参数并执行合并。"""
    # CLI 参数处理：支持 --install 模式（install.sh 调用时跳过某些检查）
    force = "--force" in sys.argv

    # 如果指定了 AGENTS.md 路径，使用自定义路径
    global AGENTS_PATH, BACKUP_PATH
    for i, arg in enumerate(sys.argv):
        if arg == "--agents-path" and i + 1 < len(sys.argv):
            AGENTS_PATH = Path(sys.argv[i + 1])
        if arg == "--backup-path" and i + 1 < len(sys.argv):
            BACKUP_PATH = Path(sys.argv[i + 1])

    try:
        changed = agents_merge()
        # 输出 JSON 给 hook 框架
        result = {"continue": True, "changed": changed}
        print(json.dumps(result))
    except Exception as e:
        print(f"[agents-merge] ⚠️ 异常: {e}", file=sys.stderr)
        print(json.dumps({"continue": True, "error": str(e)}))

    # 安全铁律：始终 exit 0
    sys.exit(0)


if __name__ == "__main__":
    main()
