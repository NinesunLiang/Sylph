# Carror OS 全平台化（sh→py）计划

**基线**: 552 pass / 40 fail / 4 warn（2026-06-05 23:28）

## 按 Story 弧分批

| 批 | 弧 | 名称 | 涉及文件 | 预计数量 |
|----|----|------|---------|:-------:|
| 1 | 弧2-防御 | 门禁骑士团 | hooks: edit-guard, permission-gate, privacy-gate, context-guard... | ~15 |
| 2 | 弧2-防御 | 证据裁判庭 | hooks: completion-gate, pre-completion-gate, posttool-claim-audit... | ~8 |
| 3 | 弧2-防御 | 反模式+错误DNA | hooks: error-dna, anti-pattern-detect, stop-drain... | ~6 |
| 4 | 弧3-记忆 | 记忆神殿 | inject-project-knowledge, compact-detect, knowledge-condenser... | ~8 |
| 5 | 弧5-审判 | Oracle+Meta-Oracle | oracle-*, meta-oracle-* | ~6 |
| 6 | 弧1-地基 | 铁律+哲学 | pre-ask-guard, pretool-retry-check, pretool-edit-scope... | ~8 |
| 7 | 弧4-工程 | 脚本工具 | scripts/ 下 23个安装/打包/验证脚本 | ~23 |
| 8 | 弧6-元环 | 飞轮+发布 | flywheel-*, package-release, audit-hooks | ~10 |
| 9 | 弧7-感官+跨平台 | LSP+跨平台测试 | lsp-*, cross-platform-smoke-test, ecosystem-probe | ~5 |

**每批流程**: 转 .sh→.py → 跑 full-test → 通过打 tag → 更新对应 story 文档
**若 fail 数未增加**: 该批通过
**若 fail 数增加 + story 有简化**: 更新 story 反映代码现状
