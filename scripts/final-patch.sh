#!/usr/bin/env bash
set -euo pipefail
cd /Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW

echo "=== 最终修复补丁 ==="

# 1. AppLayout.tsx — 移除settings按钮、默认不展示弹窗
# 已改好，不动了

# 2. 修复 console/index.scss 的 hint 文案
sed -i '' 's/发送 \/ 换行/发送 \/ ⌘↵ 换行/g' src/pages/console/index.module.scss

# 3. console/index.tsx — 加 emoji 欢迎语
sed -i '' 's/h2 className={styles.greeting_text}>晚上好/h2 className={styles.greeting_text}>👋 晚上好/g' src/pages/console/index.tsx

pnpm run typecheck && echo "✅ TypeCheck OK" || echo "❌ TypeCheck FAIL"
