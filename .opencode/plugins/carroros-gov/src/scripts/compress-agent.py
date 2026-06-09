#!/usr/bin/env python3
"""compress-agent.py — 从 AGENTS.md 自动生成 AGENTS.compact.md
跨平台（macOS / Windows python3 兼容）

只提取：
1. 「哲学铁律」段（到「编码内核」前）
2. 「编码内核」段中的难度分级 + Oracle/Meta-Oracle
3. 软完成语禁令（一行）

总行数 ≤ 35 行，适合低阶模型 context 注入。
"""

import os
import re
import sys


def compress_agents(source_path: str) -> str:
    if not os.path.isfile(source_path):
        return ""

    with open(source_path, encoding='utf-8') as f:
        content = f.read()

    out = []
    out.append("# Carror OS — 核心治理（压缩版）")
    out.append("")

    # 只在 "哲学铁律" 到 "编码内核" 之间的段
    m = re.search(r'哲学铁律\n(.+?)\n编码内核', content, re.DOTALL)
    if m:
        text = m.group(1)
        for line in text.split('\n'):
            line = line.strip()
            # 跳过无效行
            if not line or line.startswith('#') or line.startswith('─'):
                continue
            out.append(line)

    # 从 "难度分级" 段提取（整个段到空行/下一个段前）
    diff_m = re.search(r'(难度分级.*?)(?=\n\n)', content, re.DOTALL)
    if diff_m:
        text = diff_m.group(1)
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('─'):
                continue
            out.append(line)

    # 软完成语禁令（一行）
    soft = re.search(r'软完成语[^#\n]+', content)
    if soft:
        t = soft.group(0).strip()
        t = ' '.join(t.split())
        if len(t) > 100:
            t = t[:100] + '…'
        out.append(t)

    # 操作约束（一行）
    ops = re.search(r'操作约束[^#\n]+', content)
    if ops:
        t = ops.group(0).strip()
        t = ' '.join(t.split())
        if len(t) > 150:
            t = t[:150] + '…'
        out.append(t)

    return '\n'.join(out)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    agents_md = os.path.join(project_root, 'AGENTS.md')
    compact_md = os.path.join(project_root, '.claude', 'AGENTS.compact.md')

    compact_content = compress_agents(agents_md).strip()
    if not compact_content:
        print("[compress-agent] ❌ AGENTS.md not found or empty")
        return 1

    lines = compact_content.split('\n')
    print(f"[compress-agent] 生成 AGENTS.compact.md ({len(lines)} lines)")

    if '--check' in sys.argv:
        if os.path.isfile(compact_md):
            with open(compact_md, encoding='utf-8') as f:
                existing = f.read().strip()
            if existing == compact_content:
                print("[compress-agent] ✅ AGENTS.compact.md 与 AGENTS.md 一致")
                return 0
            else:
                print("[compress-agent] ❌ AGENTS.compact.md 需要更新")
                return 1
        else:
            print("[compress-agent] ❌ AGENTS.compact.md 不存在")
            return 1

    os.makedirs(os.path.dirname(compact_md), exist_ok=True)
    with open(compact_md, 'w', encoding='utf-8') as f:
        f.write(compact_content)
    print(f"[compress-agent] ✅ 已写入 {compact_md}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
