#!/usr/bin/env python3
"""
tdd-asset-boundary.py — TDD 测试：.claude/ → .omc/ 资产边界迁移

两种模式:
  验证迁移前: python3 tdd-asset-boundary.py pre
  验证迁移后: python3 tdd-asset-boundary.py post

测试项:
  1. session-handoff.md 在 .omc/ 下可找到
  2. prompt-ring 文件在 .omc/ 下可找到
  3. scheduled_tasks 在 .omc/ 下可找到
  4. lifecycle/handoff/snapshots 状态在 .omc/state/ 下
  5. meta_oracle.py 在 scripts/ 下
  6. token.schema.json 在 schemas/ 下
  7. hud-state.json 在 .omc/state/ 下
"""
import os
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("PROJECT", ".")).resolve()
mode = sys.argv[1] if len(sys.argv) > 1 else "pre"

errors = []
passes = []

def check(desc, path, exists_expected=True):
    p = PROJECT / path
    if exists_expected:
        if p.exists():
            passes.append(f"  ✅ {desc}: {path}")
        else:
            errors.append(f"  ❌ {desc}: {path} 不存在")
    else:
        if not p.exists():
            passes.append(f"  ✅ {desc}: {path} 已不存在")
        else:
            errors.append(f"  ❌ {desc}: {path} 仍然存在")

def check_ref(file_path, needle):
    """Verify file references 'needle' in its path."""
    fp = PROJECT / file_path
    if not fp.exists():
        errors.append(f"  ❌ 引用检查文件不存在: {file_path}")
        return
    content = fp.read_text(encoding="utf-8", errors="replace")
    if needle in content:
        passes.append(f"  ✅ {file_path} → 引用了 '{needle}'")
    else:
        errors.append(f"  ❌ {file_path} → 未引用 '{needle}'")

def check_not_ref(file_path, needle):
    """Verify file does NOT reference 'needle'."""
    fp = PROJECT / file_path
    if not fp.exists():
        errors.append(f"  ❌ 引用检查文件不存在: {file_path}")
        return
    content = fp.read_text(encoding="utf-8", errors="replace")
    if needle not in content:
        passes.append(f"  ✅ {file_path} → 已移除 '{needle}'")
    else:
        errors.append(f"  ❌ {file_path} → 仍包含 '{needle}'")

if mode == "pre":
    print("=" * 60)
    print("  📋 TDD 迁移前检查 — 旧路径应存在")
    print("=" * 60)

    # 1. session-handoff（当前在 .claude/.omc/）
    check("session-handoff 旧路径（.claude/.omc/）", ".claude/.omc/session-handoff.md")
    # 部分 hook 已写 .omc/session-handoff.md，检测到即可
    if (PROJECT / ".omc/session-handoff.md").exists():
        passes.append("  ✅ session-handoff 有新路径 .omc/session-handoff.md（正常，hooks 已写入）")

    # 2. prompt-ring
    check("prompt-ring 旧路径", ".claude/.prompt-ring.json")
    check("prompt-ring-state 旧路径", ".claude/.prompt-ring-state.json")
    # 验证旧代码路径引用
    check_ref(".claude/hooks/pretool-user-approve.py", '".claude" / ".prompt-ring.json"')

    # 3. scheduled_tasks
    check("scheduled_tasks 旧路径", ".claude/scheduled_tasks.json")

    # 4. lifecycle state
    check("lifecycle 旧路径", ".claude/state/lifecycle.json")
    check("handoff.json 旧路径", ".claude/state/handoff.json")
    check("snapshots 旧路径", ".claude/state/snapshots", exists_expected=True)
    check("lifecycle_ssot 引用旧路径", ".claude/hooks/lib/lifecycle_ssot.py", exists_expected=True)
    check_ref(".claude/hooks/lib/lifecycle_ssot.py", '.claude" / "state"')

    # 5. hud-state
    check("hud-state 旧路径", ".claude/nodes/.omc/state/hud-state.json")

    # 6. meta_oracle.py 在 references（错误位置）
    check("meta_oracle 在 references", ".claude/references/meta_oracle.py")

    # 7. token.schema.json 在 references（错误位置）
    check("token.schema 在 references", ".claude/references/token.schema.json")

    print()
    print(f"  📊 通过: {len(passes)}  ❌ 失败: {len(errors)}")
    for p in passes:
        print(p)
    for e in errors:
        print(e)

elif mode == "post":
    print("=" * 60)
    print("  📋 TDD 迁移后检查 — 新路径可用性")
    print("=" * 60)

    # 1. session-handoff → .omc/
    check("session-handoff 新路径", ".omc/session-handoff.md")
    check("session-handoff 旧路径已删除", ".claude/.omc/session-handoff.md", exists_expected=False)
    check_ref(".claude/hooks/session-start.py", 'OMC / "session-handoff.md"')
    check_ref(".claude/scripts/write-handoff.py", 'OMC / "session-handoff.md"')

    # 2. prompt-ring → .omc/
    check("prompt-ring 新路径", ".omc/.prompt-ring.json")
    check("prompt-ring-state 新路径", ".omc/.prompt-ring-state.json")
    check("prompt-ring 旧路径已删除", ".claude/.prompt-ring.json", exists_expected=False)
    check_not_ref(".claude/hooks/pretool-user-approve.py", '.claude" / ".prompt-ring')
    check_ref(".claude/hooks/pretool-user-approve.py", '.omc" / ".prompt-ring')
    check_not_ref(".claude/scripts/context_engine.py", '.claude" / ".prompt-ring')
    check_ref(".claude/scripts/context_engine.py", '.omc" / ".prompt-ring')

    # 3. scheduled_tasks → .omc/
    check("scheduled_tasks 新路径", ".omc/scheduled_tasks.json")
    check("scheduled_tasks 旧路径已删除", ".claude/scheduled_tasks.json", exists_expected=False)

    # 4. lifecycle state → .omc/state/
    check("lifecycle 新路径", ".omc/state/lifecycle.json")
    check("handoff.json 新路径", ".omc/state/handoff.json")
    check("snapshots 新路径", ".omc/state/snapshots")
    check("lifecycle 旧路径已删除", ".claude/state/lifecycle.json", exists_expected=False)
    check_not_ref(".claude/hooks/lib/lifecycle_ssot.py", '.claude" / "state"')
    check_ref(".claude/hooks/lib/lifecycle_ssot.py", '.omc" / "state"')
    check_not_ref(".claude/hooks/tests/test_pkg_c_lifecycle.py", '.claude" / "state"')
    check_ref(".claude/hooks/tests/test_pkg_c_lifecycle.py", '.omc" / "state"')

    # 5. hud-state → .omc/state/
    check("hud-state 新路径", ".omc/state/hud-state.json")
    check("hud 旧路径已删除", ".claude/nodes/.omc/state/hud-state.json", exists_expected=False)

    # 6. meta_oracle.py → scripts/
    check("meta_oracle 在 scripts", ".claude/scripts/meta_oracle.py")
    check("meta_oracle 旧路径已删除", ".claude/references/meta_oracle.py", exists_expected=False)

    # 7. token.schema.json → schemas/
    check("token.schema 在 schemas", ".claude/schemas/token.schema.json")
    check("token.schema 旧路径已删除", ".claude/references/token.schema.json", exists_expected=False)

    # 8. plans → .omc/
    check("plans 新路径", ".omc/plans")
    check("plans 旧路径已删除", ".claude/plans", exists_expected=False)

    print()
    print(f"  📊 通过: {len(passes)}  ❌ 失败: {len(errors)}")
    for p in passes:
        print(p)
    for e in errors:
        print(e)

else:
    print(f"未知模式: {mode}。用 pre 或 post。")
    sys.exit(1)

sys.exit(1 if errors else 0)
