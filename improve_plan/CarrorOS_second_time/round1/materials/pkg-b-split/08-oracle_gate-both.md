# oracle_gate.py 双副本

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 双源复制实证:两个目录逐字节比对
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.omc/scripts/oracle_gate.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_gate.py — Oracle 门禁执行器
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_gate.py --check <trigger_id> [--path <path>] [--command <cmd>]
     7	
     8	Returns: JSON with verdict/reason
     9	"""
    10	import json
    11	import os
    12	import re
    13	import sys
    14	import time
    15	from datetime import datetime, timezone
    16	from pathlib import Path
    17	
    18	TRIGGER_RULES = {
    19	    "cross_system": {
    20	        "pattern": r"^(/etc/|/usr/local/|/Applications/|/System/)",
    21	        "type": "hard_block",
    22	        "description": "跨系统操作",
    23	    },
    24	    "irreversible": {
    25	        "pattern": r"\b(rm -rf|dd |diskutil |sudo |chmod 777|> /dev/)",
    26	        "type": "hard_block",
    27	        "description": "不可逆操作",
    28	    },
    29	    "security": {
    30	        "pattern": r"(\.ssh/|/\.env|credentials|secret|id_rsa)",
    31	        "type": "hard_block",
    32	        "description": "安全/权限变更",
    33	    },
    34	    "deploy": {
    35	        "pattern": r"\b(deploy|release|publish|push --force|npm publish)\b",
    36	        "type": "soft_gate",
    37	        "description": "发布动作",
    38	    },
    39	    "long_idle": {
    40	        "type": "soft_gate",
    41	        "description": "长时间无人",
    42	        "check": "long_idle",
    43	    },
    44	}
    45	
    46	BYPASS_DIR = Path(".omc/state/oracle_bypass")
    47	BYPASS_TTL = 86400  # 24h
    48	
    49	
    50	def _check_bypass(task_id):
    51	    """检查是否有有效的 bypass 文件"""
    52	    if not BYPASS_DIR.exists():
    53	        return False
    54	    for f in BYPASS_DIR.glob(f"{task_id}_approved.md"):
    55	        mtime = f.stat().st_mtime
    56	        if time.time() - mtime < BYPASS_TTL:
    57	            return True
    58	    return False
    59	
    60	
    61	def _clean_expired_bypass():
    62	    """删除过期 bypass 文件"""
    63	    if not BYPASS_DIR.exists():
    64	        return
    65	    now = time.time()
    66	    for f in BYPASS_DIR.iterdir():
    67	        if now - f.stat().st_mtime > BYPASS_TTL:
    68	            f.unlink()
    69	
    70	
    71	def oracle_check(trigger_id, path=None, command=None):
    72	    """执行 Oracle 门禁检查"""
    73	    rule = TRIGGER_RULES.get(trigger_id)
    74	    if not rule:
    75	        return {"verdict": "ACCEPT", "reason": f"Unknown trigger: {trigger_id}"}
    76	
    77	    _clean_expired_bypass()
    78	
    79	    # 检查 bypass
    80	    task_id = os.environ.get("CARROROS_TASK_ID", "unknown")
    81	    if _check_bypass(task_id):
    82	        return {"verdict": "ACCEPT", "reason": "Bypass file active"}
    83	
    84	    if trigger_id == "long_idle":
    85	        return {"verdict": "WARN", "reason": "长时间无人，建议确认后操作"}
    86	
    87	    # 路径匹配
    88	    check_target = command or path or ""
    89	    pattern = rule["pattern"]
    90	    if re.search(pattern, check_target):
    91	        if rule["type"] == "hard_block":
    92	            return {
    93	                "verdict": "REJECT",
    94	                "reason": f"[{rule['description']}] 操作被 Oracle 门禁拦截: {check_target[:80]}",
    95	            }
    96	        else:
    97	            return {
    98	                "verdict": "WARN",
    99	                "reason": f"[{rule['description']}] 需要人工确认: {check_target[:80]}",
   100	            }
   101	
   102	    return {"verdict": "ACCEPT", "reason": "No trigger matched"}
   103	
   104	
   105	def main():
   106	    args = sys.argv[1:]
   107	    trigger_id = None
   108	    path = None
   109	    command = None
   110	
   111	    i = 0
   112	    while i < len(args):
   113	        if args[i] == "--check" and i + 1 < len(args):
   114	            trigger_id = args[i + 1]
   115	            i += 2
   116	        elif args[i] == "--path" and i + 1 < len(args):
   117	            path = args[i + 1]
   118	            i += 2
   119	        elif args[i] == "--command" and i + 1 < len(args):
   120	            command = args[i + 1]
   121	            i += 2
   122	        else:
   123	            i += 1
   124	
   125	    if not trigger_id:
   126	        print(json.dumps({"verdict": "ACCEPT", "reason": "No trigger specified"}))
   127	        return 0
   128	
   129	    result = oracle_check(trigger_id, path=path, command=command)
   130	    print(json.dumps(result))
   131	
   132	    if result["verdict"] == "REJECT":
   133	        return 2
   134	    return 0
   135	
   136	
   137	if __name__ == "__main__":
   138	    sys.exit(main())
```

## `.claude/scripts/oracle_gate.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_gate.py — Oracle 门禁执行器
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_gate.py --check <trigger_id> [--path <path>] [--command <cmd>]
     7	
     8	Returns: JSON with verdict/reason
     9	"""
    10	import json
    11	import os
    12	import re
    13	import sys
    14	import time
    15	from datetime import datetime, timezone
    16	from pathlib import Path
    17	
    18	TRIGGER_RULES = {
    19	    "cross_system": {
    20	        "pattern": r"^(/etc/|/usr/local/|/Applications/|/System/)",
    21	        "type": "hard_block",
    22	        "description": "跨系统操作",
    23	    },
    24	    "irreversible": {
    25	        "pattern": r"\b(rm -rf|dd |diskutil |sudo |chmod 777|> /dev/)",
    26	        "type": "hard_block",
    27	        "description": "不可逆操作",
    28	    },
    29	    "security": {
    30	        "pattern": r"(\.ssh/|/\.env|credentials|secret|id_rsa)",
    31	        "type": "hard_block",
    32	        "description": "安全/权限变更",
    33	    },
    34	    "deploy": {
    35	        "pattern": r"\b(deploy|release|publish|push --force|npm publish)\b",
    36	        "type": "soft_gate",
    37	        "description": "发布动作",
    38	    },
    39	    "long_idle": {
    40	        "type": "soft_gate",
    41	        "description": "长时间无人",
    42	        "check": "long_idle",
    43	    },
    44	}
    45	
    46	BYPASS_DIR = Path(".omc/state/oracle_bypass")
    47	BYPASS_TTL = 86400  # 24h
    48	
    49	
    50	def _check_bypass(task_id):
    51	    """检查是否有有效的 bypass 文件"""
    52	    if not BYPASS_DIR.exists():
    53	        return False
    54	    for f in BYPASS_DIR.glob(f"{task_id}_approved.md"):
    55	        mtime = f.stat().st_mtime
    56	        if time.time() - mtime < BYPASS_TTL:
    57	            return True
    58	    return False
    59	
    60	
    61	def _clean_expired_bypass():
    62	    """删除过期 bypass 文件"""
    63	    if not BYPASS_DIR.exists():
    64	        return
    65	    now = time.time()
    66	    for f in BYPASS_DIR.iterdir():
    67	        if now - f.stat().st_mtime > BYPASS_TTL:
    68	            f.unlink()
    69	
    70	
    71	def oracle_check(trigger_id, path=None, command=None):
    72	    """执行 Oracle 门禁检查"""
    73	    rule = TRIGGER_RULES.get(trigger_id)
    74	    if not rule:
    75	        return {"verdict": "ACCEPT", "reason": f"Unknown trigger: {trigger_id}"}
    76	
    77	    _clean_expired_bypass()
    78	
    79	    # 检查 bypass
    80	    task_id = os.environ.get("CARROROS_TASK_ID", "unknown")
    81	    if _check_bypass(task_id):
    82	        return {"verdict": "ACCEPT", "reason": "Bypass file active"}
    83	
    84	    if trigger_id == "long_idle":
    85	        return {"verdict": "WARN", "reason": "长时间无人，建议确认后操作"}
    86	
    87	    # 路径匹配
    88	    check_target = command or path or ""
    89	    pattern = rule["pattern"]
    90	    if re.search(pattern, check_target):
    91	        if rule["type"] == "hard_block":
    92	            return {
    93	                "verdict": "REJECT",
    94	                "reason": f"[{rule['description']}] 操作被 Oracle 门禁拦截: {check_target[:80]}",
    95	            }
    96	        else:
    97	            return {
    98	                "verdict": "WARN",
    99	                "reason": f"[{rule['description']}] 需要人工确认: {check_target[:80]}",
   100	            }
   101	
   102	    return {"verdict": "ACCEPT", "reason": "No trigger matched"}
   103	
   104	
   105	def main():
   106	    args = sys.argv[1:]
   107	    trigger_id = None
   108	    path = None
   109	    command = None
   110	
   111	    i = 0
   112	    while i < len(args):
   113	        if args[i] == "--check" and i + 1 < len(args):
   114	            trigger_id = args[i + 1]
   115	            i += 2
   116	        elif args[i] == "--path" and i + 1 < len(args):
   117	            path = args[i + 1]
   118	            i += 2
   119	        elif args[i] == "--command" and i + 1 < len(args):
   120	            command = args[i + 1]
   121	            i += 2
   122	        else:
   123	            i += 1
   124	
   125	    if not trigger_id:
   126	        print(json.dumps({"verdict": "ACCEPT", "reason": "No trigger specified"}))
   127	        return 0
   128	
   129	    result = oracle_check(trigger_id, path=path, command=command)
   130	    print(json.dumps(result))
   131	
   132	    if result["verdict"] == "REJECT":
   133	        return 2
   134	    return 0
   135	
   136	
   137	if __name__ == "__main__":
   138	    sys.exit(main())
```
