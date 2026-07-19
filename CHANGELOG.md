# Changelog

## v7.2.0 (2026-07-20)

### Changed（R0-R4 评分冲刺：验证链 + 契约统一 + 补缺）
- R0：hook matcher 扩展 Read/Grep/Glob（H2）；hook-launcher fail-closed（H3）；oracle_gate 双源符号链接（H6-lite）；anti-patterns 测试污染回退
- R1（PKG-B）：oracle_gate 僵尸双删；R6 三方漂移统一为 .py/.sh 白名单 + py_compile/bash -n 语法门；--pipeline 所有权单点化（仅 /lx-oma split）；lx-oma 校验缺失改 BLOCKED fail-closed
- R2（PKG-A）：cmd_verify 接线 verify_gate（fail-closed，无证据不 [x]）；audit 自动绑 task_id（跨任务重放失效）；_check_verified step+task 双绑定、None 通配删除；L1 无规则降级留痕 verify_degraded
- R4：E1 edit-scope WARN→BLOCK（CARROROS_EDIT_SCOPE=warn 可恢复柔性）；oracle FORCE 关键词截断修复（aut→auth）；新增 secret-scan 门防明文密钥入库（H9 半，轮换需人工）；error-dna <8 字符噪声过滤 + 存量隔离；feature-registry 增加 runtime_reality 真相对齐（69 目录 vs 6 注册）；lx-race/lx-stepwise/lx-test-gen 幽灵路由清理（S1）；lx-varlock markdown 修复（S2）；verify_gate 审计日期格式统一 %Y%m%d（H10）

## v7.1.0 (2026-07-12)

### Refactor
- Asset boundary cleanup: move runtime files (session-handoff, last-user-prompt) from `.claude/` → `.omc/`
- Archive design docs: move `重构指导文档/` → `.claude/references/design-docs/`
- Clean nested `.omc/.omc/` directory
- Update AGENTS.md/kernel.md/index.md for Base model clarity
- kernel.md: mark L2 Enhance (飞轮/水位) as skeleton (⚪) with runtime notes
- index.md: fix Hook routes (7 individual → 1 unified pretool-gate.py)
- index.md: add scripts quick index table

### Added
- VERSION file (v7.1.0)
- CHANGELOG.md
- CarrorOS-全览图.md (comprehensive project overview)
- CarrorOS-优化建议.md (architectural review with optimization suggestions)
