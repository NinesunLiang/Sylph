#!/usr/bin/env python3
"""cruise-bootstrap.py — 初始化巡航模式基础设施
调用: python3 .claude/scripts/cruise-bootstrap.py <feature-name>
创建: .cruising 信号文件 + feature/<name>/ 文档结构
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

FEATURE_NAME = sys.argv[1] if len(sys.argv) > 1 else ""
if not FEATURE_NAME:
    print("Usage: cruise-bootstrap.py <feature-name>")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
FEATURE_DIR = PROJECT_ROOT / "feature" / FEATURE_NAME
STATE_DIR = PROJECT_ROOT / ".omc/state"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# 1. 创建 .cruising 信号文件（物理开关）
(PROJECT_ROOT / ".cruising").write_text(NOW + "\n", encoding="utf-8")
print("[cruise] .cruising 信号文件已激活")

# 2. 创建 feature/ 文档结构
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

# prd.md — 目标方向
(FEATURE_DIR / "prd.md").write_text(
f"""# PRD: {FEATURE_NAME}
> 创建时间: {NOW} | 模式: 巡航

## 目标

## 验收标准
- [ ] 

## 硬边界
- [ ] 不可操作项清单
""", encoding="utf-8")

# plan.md — 执行路径
(FEATURE_DIR / "plan.md").write_text(
f"""# Plan: {FEATURE_NAME}
> 创建时间: {NOW}

## Step 清单
- [ ] Step 1: 
- [ ] Step 2: 
- [ ] Step 3: 

## 依赖
- 
""", encoding="utf-8")

# checklist.md — 通关标准
(FEATURE_DIR / "checklist.md").write_text(
f"""# Checklist: {FEATURE_NAME}
> 每完成一步打勾，全部打勾 = 巡航结束

- [ ] Step 1 完成
- [ ] Step 2 完成
- [ ] Step 3 完成
- [ ] 所有测试通过
- [ ] Oracle 审核通过
- [ ] 无 smoke 告警
""", encoding="utf-8")

# error_log.md — 摔跤记录
(FEATURE_DIR / "error_log.md").write_text(
f"""# Error Log: {FEATURE_NAME}

## 记录格式
```
[时间] [严重度] 现象 → 根因 → 修复
```

---

""", encoding="utf-8")

print(f"[cruise] 文档结构已创建: feature/{FEATURE_NAME}/")
print("  ├── prd.md       (目标方向)")
print("  ├── plan.md      (执行路径)")
print("  ├── checklist.md (通关标准)")
print("  └── error_log.md (摔跤记录)")

# 3. 记录到 session-handoff
history_file = STATE_DIR / "cruise-history.log"
STATE_DIR.mkdir(parents=True, exist_ok=True)
with history_file.open("a", encoding="utf-8") as f:
    f.write(f"{NOW} | cruise-bootstrap | feature={FEATURE_NAME} | mode=activated\n")

sys.exit(0)
