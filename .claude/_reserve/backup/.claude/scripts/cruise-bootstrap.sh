#!/usr/bin/env bash
# cruise-bootstrap.sh — 初始化巡航模式基础设施
# 调用: bash .claude/scripts/cruise-bootstrap.sh <feature-name>
# 创建: .cruising 信号文件 + feature/<name>/ 文档结构

FEATURE_NAME="${1:-}"
if [ -z "$FEATURE_NAME" ]; then
    echo "Usage: cruise-bootstrap.sh <feature-name>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FEATURE_DIR="$PROJECT_ROOT/feature/$FEATURE_NAME"
STATE_DIR="$PROJECT_ROOT/.omc/state"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 1. 创建 .cruising 信号文件（物理开关）
echo "$NOW" > "$PROJECT_ROOT/.cruising"
echo "[cruise] .cruising 信号文件已激活"

# 2. 创建 feature/ 文档结构
mkdir -p "$FEATURE_DIR"

# prd.md — 目标方向
cat > "$FEATURE_DIR/prd.md" <<EOF
# PRD: $FEATURE_NAME
> 创建时间: $NOW | 模式: 巡航

## 目标


## 验收标准
- [ ] 

## 硬边界
- [ ] 不可操作项清单
EOF

# plan.md — 执行路径
cat > "$FEATURE_DIR/plan.md" <<EOF
# Plan: $FEATURE_NAME
> 创建时间: $NOW

## Step 清单
- [ ] Step 1: 
- [ ] Step 2: 
- [ ] Step 3: 

## 依赖
- 
EOF

# checklist.md — 通关标准
cat > "$FEATURE_DIR/checklist.md" <<EOF
# Checklist: $FEATURE_NAME
> 每完成一步打勾，全部打勾 = 巡航结束

- [ ] Step 1 完成
- [ ] Step 2 完成
- [ ] Step 3 完成
- [ ] 所有测试通过
- [ ] Oracle 审核通过
- [ ] 无 smoke 告警
EOF

# error_log.md — 摔跤记录
cat > "$FEATURE_DIR/error_log.md" <<EOF
# Error Log: $FEATURE_NAME

## 记录格式
\`\`\`
[时间] [严重度] 现象 → 根因 → 修复
\`\`\`

---

EOF

echo "[cruise] 文档结构已创建: feature/$FEATURE_NAME/"
echo "  ├── prd.md       (目标方向)"
echo "  ├── plan.md      (执行路径)"
echo "  ├── checklist.md (通关标准)"
echo "  └── error_log.md (摔跤记录)"

# 3. 记录到 session-handoff
echo "$NOW | cruise-bootstrap | feature=$FEATURE_NAME | mode=activated" >> "$STATE_DIR/cruise-history.log" 2>/dev/null

exit 0
