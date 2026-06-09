#!/usr/bin/env python3
"""detect-oracle-env.py — Oracle 环境自适应检测
Role: 检测运行平台能力, 输出 Oracle 最佳执行路径
输出格式: {"oracle_path":"agent_omc"|"agent_omo"|"local_prompt","agent_available":true|false}
"""
import sys
import json
from pathlib import Path

# 默认: 本地 prompt
ORACLE_PATH = "local_prompt"
AGENT_AVAILABLE = False
PLATFORM = "unknown"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()

# 1. OMC (oh-my-claude): Agent 工具是 Claude Code 原生能力
#    .omc/ 目录存在 = OMC 已安装
if (PROJECT_ROOT / ".omc").is_dir():
    ORACLE_PATH = "agent_omc"
    AGENT_AVAILABLE = True
    PLATFORM = "claude-code-omc"
# 2. OMO (oh-my-opencode): .opencode/plugins/ 存在 OMO 配置
elif (PROJECT_ROOT / ".opencode/plugins").is_dir() and (PROJECT_ROOT / ".opencode/oh-my-openagent.json").is_file():
    ORACLE_PATH = "agent_omo"
    AGENT_AVAILABLE = True
    PLATFORM = "opencode-omo"
# 3. Claude Code 原生 (无 OMC): Agent 工具仍然可用
elif (PROJECT_ROOT / ".claude/settings.json").is_file():
    ORACLE_PATH = "agent_omc"
    AGENT_AVAILABLE = True
    PLATFORM = "claude-code-native"

# Output
if len(sys.argv) > 1 and sys.argv[1] == "--json":
    print(json.dumps({"oracle_path": ORACLE_PATH, "agent_available": AGENT_AVAILABLE, "platform": PLATFORM}, ensure_ascii=False))
else:
    print(ORACLE_PATH)

sys.exit(0)
