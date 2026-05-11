#!/usr/bin/env python3
"""standardize-hook-headers.py — v2: 标准化所有 hook 脚本的头部身份标签

保留 shebang 和 harness-kit:managed 行，添加 standardized role header。

格式：
  #!/usr/bin/env bash  (保留原样)
  # harness-kit:managed vX.X.X  (保留原样)
  # <hook-name>.sh — <Event[:Matcher]> — 一句话身份
  # Role: 一句话作用描述
"""

import os
import re

HOOKS_DIR = os.path.join(os.path.dirname(__file__), '..', 'hooks')

HOOK_DEFS = [
    ("auto-snapshot", "Stop / PostToolUse:Edit|Write", "会话结束时自动保存状态快照（分支/轮次/未提交文件）"),
    ("build-validator", "PostToolUse:Bash / PostToolUseFailure:Bash", "构建失败自动记录错误日志并给出针对性修复建议"),
    ("compact-detect", "UserPromptSubmit", "检测 /compact 命令，保存 compact 前 usage 供 token 追踪"),
    ("completion-gate", "PostToolUse:TaskUpdate", "强制 TaskUpdate 前提供结构化证据文件"),
    ("context-guard", "PreToolUse:Edit|Write", "基于真实 token 百分比阻断写操作，防止上下文溢出"),
    ("edit-guard", "PreToolUse:Edit", "编辑源文件前强制先 Read，实施 Read-before-Edit 门禁"),
    ("error-dna", "PostToolUse:Bash / PostToolUseFailure:Bash", "捕获结构化错误 DNA 写入跨会话错误记忆"),
    ("feature-probe", "工具脚本（非 Hook）", "手动诊断工具，检查 feature 的 L1-L4 证据链完整性"),
    ("flywheel-report", "SessionStart", "读取飞轮日志，生成 30 天频率摘要注入会话"),
    ("harness_config", "共享库（非 Hook）", "共享配置库，提供 hc_get/hc_enabled 等 harness.yaml 读取函数"),
    ("inject-project-knowledge", "SessionStart", "注入 .claude/ 核心知识到 AI context"),
    ("lsp-suggest", "PreToolUse:Grep", "检测 Grep 搜索导出符号时建议改用 LSP 工具"),
    ("permission-gate", "PreToolUse:Bash", "执行危险命令前检查权限申请格式"),
    ("plan-gate", "PreToolUse:Edit|Write [默认关闭]", "编辑前检查是否跳过规划阶段"),
    ("posttool-bash-audit", "PostToolUse:Bash / PostToolUseFailure:Bash", "Bash 执行后审计权限上下文，只提醒不阻断"),
    ("posttool-edit-quality", "PostToolUse:Edit|Write", "编辑后自查代码风格、文档同步、方案复用检测"),
    ("posttool-read-cite", "PostToolUse:Read [默认关闭]", "读取文件后提示引用规范"),
    ("posttool-subagent-audit", "PostToolUse:Task", "子 agent 执行后审计 content 用量，超限告警"),
    ("posttool-write-cite", "PostToolUse:Write|Edit", "检测写入 claude-next.md 时验证教训格式"),
    ("posttool-write-lock", "PostToolUse:Edit|Write", "写操作后释放 OMA 并发锁"),
    ("pretool-edit-scope", "PreToolUse:Edit|Write", "范围冻结拦截，阻止越界编辑 + 核心文件警告"),
    ("pretool-rule-anchor", "PreToolUse:Edit|Write", "长对话防漂移，高轮次时注入锚定规则"),
    ("pretool-user-correction", "UserPromptSubmit", "检测用户纠正信号，强制记录到 claude-next.md"),
    ("pretool-write-lock", "PreToolUse:Edit|Write", "写操作前获取 OMA 并发锁，防止多终端冲突"),
    ("privacy-gate", "PreToolUse:Bash|Read|Grep", "防止隐私数据泄露（DLP 门禁）"),
    ("proactive-handoff", "PostToolUse:Write|Edit [未注册]", "主动会话交接，当前未注册到 settings.json"),
    ("read-tracker", "PostToolUse:Read", "记录已读文件路径供 edit-guard 检查 Read-before-Edit"),
    ("skill-flywheel", "Stop", "停止时更新 skill 使用频率，驱动飞轮优化"),
    ("stop-drain", "Stop", "Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）"),
    ("subagent-guard", "PreToolUse:Task", "约束子 agent 用量，防账单雪崩（软约束+事后对账）"),
    ("token_writer", "PostToolUse:.* / SessionStart", "写入 token 用量追踪索引供 context-guard 计算"),
    ("turn-counter", "UserPromptSubmit", "统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测"),
]

def main():
    for name, event, role in HOOK_DEFS:
        fname = f"{name}.sh"
        fpath = os.path.join(HOOKS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"⚠️  不存在: {fname}")
            continue

        with open(fpath, 'r') as f:
            content = f.read()

        lines = content.split('\n')

        # 提取 shebang 和 harness-kit marker
        shebang = ''
        harness_marker = ''
        header_end_idx = 0

        for i, line in enumerate(lines):
            if line.startswith('#!'):
                shebang = line
                continue
            if re.search(r'harness-kit:managed', line):
                harness_marker = line.rstrip()
                continue
            if line.startswith('#'):
                continue
            # 遇到第一个非注释行
            header_end_idx = i
            break

        # 构建新 header
        header_lines = [shebang] if shebang else []
        if harness_marker:
            header_lines.append(harness_marker)
        header_lines.append(f"# {fname} — {event} — {role}")
        header_lines.append(f"# Role: {role}")

        # 找到 body 开始（第一个有意义的代码行）
        body_lines = []
        found_code = False
        for line in lines[header_end_idx:]:
            stripped = line.strip()
            if not found_code:
                if stripped and not stripped.startswith('#'):
                    body_lines.append(line)
                    found_code = True
                # skip blank lines and remnant comment lines
            else:
                body_lines.append(line)

        new_content = '\n'.join(header_lines) + '\n\n' + '\n'.join(body_lines)
        new_content = new_content.rstrip() + '\n'

        with open(fpath, 'w') as f:
            f.write(new_content)

        print(f"✅ {fname}")


if __name__ == '__main__':
    main()
