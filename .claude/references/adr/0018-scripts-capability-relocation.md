# 0018. 根 scripts 能力归位迁移

**日期**: 2026-08-13
**来源**: 任务 迁移-根scripts清空-能力域归位

## 上下文

repo 根目录存在 `scripts/`，内含 CarrorOS 治理脚本与 UI 还原门禁（carroros-gates）两套能力。用户通过 grill-me 审阅确立归类标准：**能力**（通用、可复用、下个地方能用）按能力域归属；**信息**（一次性数据）删除。根目录不应有 scripts 目录。cut-sweep-tier1-2 已清走孤儿簇（一次性 UI 脚本），剩余为被引用的能力。

## 决策

清空并删除 repo 根 `scripts/` 目录，按能力域归位：

1. **UI 还原能力** → `.claude/workflows/frontend-overnight/scripts/carroros-gates/`：11 门禁（scope/run_gate/evidence/c7/preflight/finalize/install_hook/morning_report/lock/run_all/abstraction）+ assertion-catalog.yaml + lib/ + smoke/ + templates/
2. **CarrorOS 通用能力** → `.claude/scripts/`：alloc_report_index / gatekeeper_digest / write_lock / run-regression.sh
3. **共享契约** → `.claude/scripts/gate-contract.yaml`（读取方为 hook helpers.py + test_deadweight_cuts.py，非 UI 门禁）
4. **引用联动**：hook `carroros-night-deny.py` / `constants.py` / `helpers.py` 路径正则（用户批准）、frontend `config.py` CARROTOROS_GATES_DIR、carroros-gates 内部自引、8 个 frontend/reference 文档
5. **删除**：根 scripts/ 目录本身 + __pycache__ 构建缓存（信息）

## 替代方案

- **carroros-gates 全归 `.claude/scripts/`**：被否决，因 11 门禁全是 UI 还原专属（引用 FINAL.md v3.1），与 CarrorOS 通用治理概念冲突。
- **根目录保留 scripts（兼容别名/符号链接）**：被否决，违背"根目录不能有 scripts"的硬要求。
- **共享契约 gate-contract 随门禁留 frontend**：被否决，因读取方是 CarrorOS hook 与契约测试，契约属 CarrorOS 真源。

## 理由

- **按能力域归属**：UI 还原门禁属 frontend 工作流（night-overnight），通用治理属 .claude/scripts（CarrorOS 运行时），各归各处语义清晰。
- **契约归治理层**：gate-contract.yaml 是 CarrorOS 治理 hook 的校验真源，放在 .claude/scripts 与其读取方同处。
- **git mv 保历史**：19 文件 rename 记录完整，可追溯。
- **验证无破坏**：迁移后 261 passed，hook/config 语法 OK，零旧路径残留。

## 后果

- 根目录不再有 scripts/，能力分布在两个能力域目录。
- frontend-overnight 文档、SOP、night-loop 中的路径全部指向新位置。
- hook 正则更新后，夜跑门禁（carroros-night-deny）对新路径生效。
- 后续新能力按此标准归位；测试内建（38 个 test_*.py 验证逻辑内建到机制）单独立项。
