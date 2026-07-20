#!/usr/bin/env python3
"""
rollback-last-refactor.py — 回滚本次大改动，恢复安全状态
用法: python3 .claude/scripts/rollback-last-refactor.py [--hard|--soft]
  --soft: 仅关闭harness开关，保留代码 (默认)
  --hard: git reset 到备份分支
"""
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def main():
    mode = "--soft" if len(sys.argv) < 2 else sys.argv[1]
    print("=== Carror OS 回滚工具 ===")

    if mode == "--hard":
        backup_branch = "backup/dev-big-refactor-20260531-1059"
        result = run_cmd(["git", "rev-parse", "--verify", backup_branch],
                         cwd=str(PROJECT_ROOT))
        if result.returncode == 0:
            print(f"🔴 硬回滚到: {backup_branch}")
            run_cmd(["git", "reset", "--hard", backup_branch],
                    cwd=str(PROJECT_ROOT))
            print("✅ 已回滚")
        else:
            print(f"❌ 备份分支不存在: {backup_branch}")
            sys.exit(1)
    else:
        print("🟡 软回滚: 关闭新激活的4个hook开关")
        harness_yaml = PROJECT_ROOT / ".claude" / "harness.yaml"
        if harness_yaml.exists():
            text = harness_yaml.read_text(encoding="utf-8")
            replacements = {
                "knowledge_condenser: true": "knowledge_condenser: false",
                "pretool_plan_gate: true": "pretool_plan_gate: false",
                "build_validator: true": "build_validator: false",
                "error_dna_auto_fix: true": "error_dna_auto_fix: false",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            harness_yaml.write_text(text, encoding="utf-8")
        print("  knowledge_condenser: false")
        print("  pretool_plan_gate: false")
        print("  build_validator: false")
        print("  error_dna_auto_fix: false")
        print("✅ 软回滚完成，代码保留")


if __name__ == "__main__":
    main()
