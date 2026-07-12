# Changelog

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
