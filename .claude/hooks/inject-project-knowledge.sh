#!/usr/bin/env bash
# inject-project-knowledge.sh — SessionStart — 注入极简路由表到 AI context
# 哲学 #1 (less is more): AGENTS.md + kernel.md + index.md 已由 CLAUDE.md 的 @ 引用链
# 自动注入（Claude Code 内置机制），此处不再重复注入。
# 仅注入 @ 引用链无法覆盖的补充文件（如 feature-registry 摘要）。
# 其余所有文件通过渐进式披露 (Read on demand)

source "$(dirname "$0")/harness_config.sh"
hc_enabled "inject_project_knowledge" || exit 0
