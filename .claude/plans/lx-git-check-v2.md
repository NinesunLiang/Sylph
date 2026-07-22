# lx-git-check 审计方案（含 lx-pre-commit/lx-pre-push去向）

## 当前状态
- SKILL.md: 122行，通用语言检测(go/node/python/rust)
- 5个Python脚本(~18K)
- pre-commit(编译/测试/lint/审查) + pre-push(commit规范/安全扫描/变更审计)
- 声明"合并自 lx-pre-commit v2.0.0 + lx-pre-push v2.0.0"

## 定位差异
- lx-git-check = 结构化强制门禁序列
- CC原生 = AI自行决定是否跑测试（可能忘记或跑错命令）
- 价值：结构化+语言自适应+commit规范学习+安全扫描

## 核心问题
1. lx-git-check 在Base保留还是Enhance？
2. lx-pre-commit/lx-pre-push 是否应删除？（已合并进lx-git-check，可能为旧文件）
3. ROI高不高？（5脚本18K代码 vs CC原生能力）
