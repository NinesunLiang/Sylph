#!/bin/bash
# task-commit-uirestore.sh — 提交 xsimplechat UI 还原本轮成果
# 范围：UI 还原工程 + frontend-overnight 机制文档/脚本 + 测量工具
# 不含：其他工作流改动（lx-goal/domain.py/AGENTS.md/README.md/rpe 旧档删除）
set -euo pipefail

cd /Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW

# --- 工程骨架 ---
git add index.html
git add vite.config.ts
git add tsconfig.json
git add tsconfig.app.json
git add tsconfig.node.json
git add package.json
git add pnpm-lock.yaml
git add package-lock.json

# --- 实现与资产 ---
git add src/
git add public/

# --- 机制文档与闭环脚本 ---
git add .claude/workflows/frontend-overnight/FIX-CONTRACT.md
git add .claude/workflows/frontend-overnight/STYLE-DIFF-MECHANISM.md
git add .claude/workflows/frontend-overnight/scripts/ui-restore/

# --- 测量/采集工具（仓库根 scripts/） ---
git add scripts/analyze-prototype.mjs
git add scripts/autopilot-batch.sh
git add scripts/autopilot-daemon.mjs
git add scripts/autopilot-loop.mjs
git add scripts/build-token-catalog.py
git add scripts/deep-measure.mjs
git add scripts/extract-tokens.mjs
git add scripts/final-patch.sh
git add scripts/improve-impl.ts
git add scripts/iter-fix.mjs
git add scripts/loop.sh
git add scripts/measure-scores.mjs
git add scripts/orchestrator-tick.py
git add scripts/run-autopilot-round.mjs
git add scripts/run-token-bootstrap-fallback.py
git add scripts/run-token-bootstrap.py
git add scripts/take-screenshots.mjs
git add scripts/visual-compare.mjs

# --- 任务计划档案 ---
git add rpe/uixsimplechatcom-vite8react19dev/

echo "=== 暂存清单 ==="
git diff --cached --stat | tail -5

git commit -m "feat: xsimplechat.com UI 还原闭环——基页 0.9742 + 二级 UI 24 态（StateDiff 81→5）" -m "- Vite8+React19+TS 工程骨架（src/public/vite/tsconfig）
- 二级 UI：Tip 组件类化（运行时视口钳位）/AdvancedParams 新建/ModelDropdown 非均匀行距 nth-child 补偿/折叠保挂载 key 重挂载
- 交互态机制：discover-states/capture-states/state-diff 三件套 + base.json 伪缺失校正 + 时变文本归一 + 绝对路径铁律（SOP 十二节）
- 门禁 7 项全过；剩余 5 项 diff 为字体度量残差类（x+3，物理上限）已归档
- 包管理 npm 切换 pnpm（删 package-lock）

Co-Authored-By: Claude <noreply@anthropic.com>"

echo "=== 提交完成 ==="
git log --oneline -1
