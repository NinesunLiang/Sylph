# Plan — Carror OS Productization

> RPE Version: v1.2 | 最后更新: 2026-05-04
> Status: ✅ Research Complete — Ready for Phase 0 / Phase 1 Execution
> 模式标记: Standard

---

## 调整轮次控制

- 已调整次数：4 / 最大允许次数：3
- 当前轮次：v1.2 — GPT5.5 Plan 评审修正 + Report Advice 评估
- 本轮调整内容：新增 Phase 0 (RPE-000 Reality Check)、修正 Status 措辞、拆分 RPE-001/RPE-008 职责、修复 RPE-016 coordination 矛盾、补充 RPE-012/013/010 依赖关系、新增 degraded status AC、评估 GPT5.5 Report Advice 10 条建议（8/10 已覆盖，2 项记录待讨论）

---

## 0. 模式切换

- 当前模式：Standard

---

## 1. 方案摘要

- 目标：Carror OS 产品化 — 知识库、特性验证、文档化、对外改造、可视化增强
- 影响范围：全量代码库（harness-kit 层 hooks/scripts + skills 层 + docs 目录 + rpe 体系）
- 非范围：不引入 Web Dashboard（保持 CLI-native）、不修改 OMA 锁核心算法（仅增强）
- Oracle 迭代：✅ 3 轮全部完成 (详见 §5 Oracle 迭代完成报告)
- 执行顺序：Phase 0 (Reality Check) → Phase 1 → Phase 1.5 (Observability) → Phase 2 → Phase 3 → Phase 5
- RPE-009 已删除 (AC 分配至 RPE-004/RPE-005/RPE-012)
- RPE-016 独立执行 (原 RPE-014 依赖已删除)

---

## 2. WBS — Oracle 优化版

### Phase 0：仓库现实校验 — Reality Check

> **目的**：在执行任何修改前，先确认仓库完整性，防止本地模型基于空文件/错配文件继续迭代。

#### RPE-000：Repository Reality Check

- **AC-0.1**：生成仓库清单 — hooks 数量、skills 数量、scripts 数量、docs 数量、空文件数量
- **AC-0.2**：验证关键实现路径是否存在（harness hooks、skills、scripts、docs）
- **AC-0.3**：检测空实现文件（`find . -type f -size 0`、仅含注释/占位符的 hook、无功能性内容的 SKILL.md）
- **AC-0.4**：检测文档文件名/内容错配（如 architecture-review 包含无关的 final exam 内容）
- **AC-0.5**：产出 `state/repository-reality-check.md`
- **AC-0.6**：无法确认关键实现路径时，标记后续所有 Phase 为 BLOCKED
- **回滚：** 无代码变更，仅删除报告文件
- **测试：** `find . -type f -size 0 && rg "Final Exam|终极" docs/technical/`

### Phase 1：高优先级·修复 (5 Tasks)

#### RPE-001：Error DNA 重写（Oracle 确认：严重损坏，4 bug）
- **AC-1.1**：error-dna.sh 正常写入 `.omc/state/error-dna.jsonl`（追加日志）+ `.omc/state/error-dna.json`（合并状态）
- **AC-1.2**：PostToolUse:Bash 钩子捕获所有非零退出命令，生成结构化签名（`{ts,signature,cmd,exit_code,error_type,message,output_snippet,session_id}`）
- **AC-1.3**：inject-project-knowledge.sh 会话启动时可注入跨会话错误记忆（含 count/fix_count/status 字段）
- **AC-1.4**：cmd 字段凭据脱敏（`--password\s+\S+` → `***` 等）
- **AC-1.5**：error-dna.jsonl 1MB 自动轮转，保留 3 份归档
- **AC-1.6**：共享 error_classifier.py 尚不可用时使用本地回退分类器，正式共享提取留给 RPE-008
- **回滚：** 恢复原 error-dna.sh（虽不可用但无副作用），删除新增文件
- **Oracle 评估：** 不成熟 — 需 3 轮迭代（rewrite → verify → stabilize）
- **依赖：** RPE-000

#### RPE-002：Loading Benchmark (需求 8)
- **AC-2.1**：`scripts/loading_benchmark.py` 使用 tiktoken cl100k_base 估算（非 Claude 官方 tokenizer）测量 L1/L2/L3 各层 token 数，报告中标注 estimate 级别
- **AC-2.2**：对比条件 A（渐进式披露）+ 条件 B（全量加载），输出结构化报告
- **AC-2.3**：验证 `loading_matrix.md` 声称的"首次加载 394→120 行，减少 70%"
- **AC-2.4**：未经验证前不使用 19,280 / 75% 数字，benchmark 报告必须包含 method/sample size/raw data/mean/limitations
- **回滚：** 无代码变更，仅删除 benchmark.py
- **Oracle 评估：** 不成熟 — 需 3 轮迭代（baseline → measure → validate）
- **依赖：** RPE-000

#### RPE-003：Audit Trail 文件名修复 + 轮转 + error_log 联动 (需求 12)
- **AC-3.1**：read-tracker.sh 与 carror_dashboard.py/skill_trace_report.py 统一文件名（read-files.log → read-tracker.txt 或反向统一）
- **AC-3.2**：read-files.log 添加轮转机制（每 500 条或每会话重置）
- **AC-3.3**：确认 token-tracking-index.json 有写入者（若无法确认则标记为僵尸功能并创建写入者脚本）
- **AC-3.4**：修复 proactive-handoff.sh 依赖不存在的 context_monitor.py 导致静默失效的问题；若 token 源不可用，必须写入 degraded 状态而非静默退出
- **AC-3.5**：同步更新 source/harness-kit/CLAUDE.md 中 hooks 描述为 "26个 hooks，按 YAML 配置自动运行"（当前缺失"按 YAML 配置"限定语）
- **回滚：** 恢复文件名 + 删除轮转逻辑
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-000

#### RPE-004：统一特性注册表 (需求 2)
- **AC-4.1**：创建 `.claude/feature-registry.yaml` — 所有可切换特性的统一目录（hooks + skills）
- **AC-4.2**：在 harness.yaml 增加 `skills_enabled:` 块（23 个 skills）
- **AC-4.3**：扩展 `hc_enabled()` 函数支持 skills_enabled 读取
- **AC-4.4**：创建 `feature-probe.sh` — 每个注册特性的自动探针，输出 L1-L4 证据
- **回滚：** 删除 feature-registry.yaml + harness.yaml skills_enabled 回退
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-000

#### RPE-005：Agentic UI 优先级修复 (需求 13)
- **AC-5.1**：completion-gate.sh 增加 numbered-choice 菜单（1. 运行测试重试 / 2. 强制覆盖 / 3. 压缩上下文）
- **AC-5.2**：context-guard.sh 增加 numbered-choice 菜单（1. /compact / 2. 新分支 / 3. 强制覆盖）
- **AC-5.3**：manual-acceptance-test.md 中相关测试用例验证通过（O7/O8 更新为匹配实际菜单格式）
- **AC-5.4**：permission-gate.sh 增加 numbered-choice 菜单（1. 写入标记文件继续 / 2. 取消操作）
- **AC-5.5**：pretool-edit-scope.sh 增加 numbered-choice 菜单（1. 强制编辑 / 2. 取消 / 3. 切换到新分支）
- **AC-5.6** [原 AC-9.1]：completion-gate 使用 feature-registry.yaml 作为证据预期来源
- **O9/O10 新增测试**：permission-gate.sh 和 pretool-edit-scope.sh 的 numbered 菜单验收测试
- **回滚：** 恢复原钩子文件
- **Oracle 评估：** 成熟 — 2 轮足够
- **Round 3 裁定：** ❌ NO-GO → 修正后重审（AC 已扩展，需验收确认）
- **依赖：** RPE-004, RPE-000

---

### Phase 1.5：可观测性 (2 Tasks)

> Round 3 裁定：RPE-012 和 RPE-013 从 Phase 4 提前，在 Phase 1 修复后立即执行。
> 理由：Token 趋势面板和 Audit 仪表盘在 Phase 2-5 全程可复用，提前获得开发反馈。

#### RPE-012：lx-status 面板升级 (需求 9, 14)
- **AC-12.1**：增加 Token 消耗趋势（简单 ASCII 图，参考格式见 Round 3 Agentic UI 裁决）；token 源缺失时显示 degraded 状态而非虚假零值
- **AC-12.2**：增加 Error DNA 状态（错误类型分布直方图）；RPE-001 数据未就绪时显示 degraded
- **AC-12.3**：增加 Flywheel P0 事件时间线
- **AC-12.4** [原 AC-9.3]：lx-status 集成 feature-registry.yaml 注册表状态
- **AC-12.5**：所有面板必须处理数据源缺失场景，输出 degraded 状态而非静默显示零值
- **回滚：** 恢复 lx-status 旧版
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-001 (Error DNA), RPE-003 (Token writer), RPE-004 (feature registry)

#### RPE-013：Audit Trail 统一仪表盘 (需求 12 第二阶段)
- **AC-13.1**：统一 carror_dashboard.py + skill_trace_report.py → `.claude/scripts/audit_dashboard.py`（5 源聚合）
- **AC-13.2**：lx-status 集成 audit dashboard 摘要
- **AC-13.3**：添加基本防篡改（快照 SHA256 摘要文件）
- **AC-13.4**：缺失的数据源必须显示为 missing/degraded，不得静默跳过
- **回滚：** 保留原有两个独立脚本，删除新脚本
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-001 (Error DNA), RPE-003 (Token writer), RPE-004 (feature registry)

---

### Phase 2：文档化 (3 Tasks)

#### RPE-006：Lecture 系列创建 (需求 4)
- **AC-6.1**：创建 `lecture/` 目录 + 8 篇按构造顺序文档
- **AC-6.2**：每篇遵循 7 部分模板（Function/Philosophy/Benefits/Implementation/Core Code/Logic Flow/Visual Diagram）
- **AC-6.3**：每篇含 Mermaid 图表（流程图/序列图/状态图）
- **AC-6.4**：前置引用 + 反向链接交叉引用体系
- **AC-6.5**：`lecture/README.md` 含依赖 DAG 进度图
- **AC-6.6**：`lecture_sync_check.py` 自动验证 file:line 引用
- **回滚：** 删除 lecture/ 目录
- **Oracle 评估：** 成熟 — 2 轮足够

#### RPE-007：Docs 重构为 BIMODAL 分类 (需求 1)
- **AC-7.1**：重构 docs/ 为 overview/ + concepts/ + reference/ + guides/ + governance/
- **AC-7.2**：创建 persona-based 入口（quickstart.md / for-beginners.md / for-experts.md）
- **AC-7.3**：保留 marketing/ + tests/ + internal/ 不为重构所动
- **AC-7.4**：创建 `doc-sync-check.sh` — 基于 frontmatter 的文档-代码一致验证
- **回滚：** 恢复 docs/ 原目录结构
- **Oracle 评估：** 成熟 — 2 轮足够

#### RPE-008：Error DNA 共享库提取 (需求 11 增强)
- **AC-8.1**：从 build-validator.sh 提取 `classify_and_suggest()` + `generate_signature()` 到 `.claude/scripts/error_classifier.py`
- **AC-8.2**：build-validator.sh 改为 import 共享库（向后兼容）
- **AC-8.3**：error-dna.sh v2 同样使用共享库签名算法
- **回滚：** build-validator.sh 恢复原内联代码
- **依赖：** 依赖 RPE-001（error-dna.sh 重写完成）
- **Oracle 评估：** 不成熟 — 需 3 轮迭代

#### RPE-009：Feature Probe 增强 (需求 2 第二阶段)
- **Round 3 裁定：** ✅ GO — **AC 已全部分配至其他 Task**
  - AC-9.1 → RPE-005 AC-5.6（completion-gate 使用 registry）
  - AC-9.2 → RPE-004 AC-4.4（feature-probe.sh 是 AC-4.4 的直接产物）
  - AC-9.3 → RPE-012 AC-12.4（lx-status 集成自然属于可视化阶段）
- **RPE-009 取消**：AC 已全部分配至 RPE-004/RPE-005/RPE-012
- **回滚：** 不适用
- **依赖：** 依赖 RPE-004（feature-registry.yaml 完成）
- **Oracle 评估：** 成熟 — 2 轮足够

---

### Phase 3：对外化 (2 Tasks)

#### RPE-010：Marketing 文档重写 (需求 3, 16)
- **AC-10.1**：删除 dual-domain-scoring.md 所有"分析"框内部推演语气
- **AC-10.2**：industry-benchmark.md 改为"基于公开方法论"的客观陈述
- **AC-10.3**：引用 manual-acceptance-test.md 和 auto-feature-test.md 作为评分依据
- **AC-10.4**：8 维度评分对外发布，12 维度评分保留内部
- **AC-10.5**：英文 README 同步更新
- **AC-10.6**：创建 `docs/internal/claim-registry.yaml` — 机器可读事实表，跟踪每个强 claim 的状态（retracted/downgraded/implemented/partial），包含替换表述和 blocker 说明
- **AC-10.7**：创建 `scripts/claim-lint.sh` — 扫描全局营销文档中高风险关键词（"自评分""行业独创""100% 功能完备""完全可见""终极"等），输出命中报告
- **回滚：** 恢复 git 恢复 marketing 文档
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-002 (benchmark 数据), RPE-004 (feature registry), RPE-006 (lecture 证据), RPE-007 (docs 重构)

#### RPE-011：Launch Asset 补全 (需求 3)
- **AC-11.1**：截图/演示视频清单 + 拍摄计划
- **AC-11.2**：dogfooding 日志填充
- **AC-11.3**：外部审查邀请模板
- **AC-11.4**：launch copy 不得包含未经验证的基准数据（19,280/75% 等）
- **回滚：** 无部署变更
- **Oracle 评估：** 成熟 — 2 轮足够

---

### Phase 5：增强 (3 Tasks)

> 注：RPE-012 和 RPE-013 已移至 Phase 1.5 (可观测性)，Phase 4 已删除。

#### RPE-014：OMA Lock 增强 (需求 6)
- **AC-14.1**：修复 TOCTOU 竞争条件（oma_lock_manager.py:50-52）
- **AC-14.2**：添加 heartbeat 过期锁检测机制
- **AC-14.3**：harness_config.sh 集成，使 OMA 在 lx-rpe 步骤中自动触发
- **AC-14.4**：创建 `.omc/state/locks.json` 锁可观测性
- **回滚：** 恢复 oma_lock_manager.py
- **Oracle 评估：** 不成熟 — 3 轮迭代
- **依赖：** RPE-000

#### RPE-016：Race 调度增强 (需求 5)
- **AC-16.1**：4 层 Race 实现 — isolation（.omc/race/{id}/）、dispatch（run_in_background）、coordination（目录隔离 + result.json/owner.json）、collection（result.json polling）
- **AC-16.2**：创建 race 状态机文档（明确非真并发，是任意顺序编排；对外表述为 orchestration pattern 而非 parallel execution engine）
- **回滚：** 删除 .omc/race/ 目录
- **依赖：** 无独立 — Race 与 OMA Lock 是正交功能（Race 使用目录隔离而非锁机制）
- **Round 3 修正：** 删除原 RPE-014 依赖
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-000

#### RPE-017：Flywheel Reports 增强 (需求 15)
- **AC-17.1**：显式空日志防护（`[ -s "$FLYWHEEL" ] || exit 0`）
- **AC-17.2**：创建 `.claude/flywheel-reports/` 持久化报告目录（日期戳文件）
- **AC-17.3**：添加月度趋势比较（/dev/tty 摘要，不注入 AI 上下文）
- **AC-17.4**：持续性 P0 事件桌面通知（osascript 或 notify-send）
- **回滚：** 删除 flywheel-reports/ 目录
- **Oracle 评估：** 成熟 — 2 轮足够
- **依赖：** RPE-000
- **Oracle 评估：** 成熟 — 2 轮足够

---

## 3. AC 汇总矩阵

| RPE-ID | Task | Phase | 成熟度 | 预期迭代 | 依赖 | 状态 |
|--------|------|-------|--------|---------|------|------|
| RPE-000 | Repository Reality Check | 0 | 成熟 | 1 轮 | - | NEW / 必须先执行 |
| RPE-001 | Error DNA 重写 | 1 | 不成熟 | 3 轮 | RPE-000 | ⏳ 部分 |
| RPE-002 | Loading Benchmark | 1 | 不成熟 | 3 轮 | RPE-000 | ⏳ 部分 |
| RPE-003 | Audit Trail 修复 | 1 | 成熟 | 2 轮 | RPE-000 | ✅ GO |
| RPE-004 | 统一特性注册表 | 1 | 成熟 | 2 轮 | RPE-000 | ✅ GO |
| RPE-005 | Agentic UI 菜单 | 1 | 成熟 | 2 轮 | RPE-004, RPE-000 | ❌ NO-GO |
| RPE-012 | lx-status 升级 | 1.5 | 成熟 | 2 轮 | RPE-001, RPE-003, RPE-004 | ✅ GO (依赖就绪后) |
| RPE-013 | Audit 统一仪表盘 | 1.5 | 成熟 | 2 轮 | RPE-001, RPE-003, RPE-004 | ✅ GO (依赖就绪后) |
| RPE-006 | Lecture 系列 | 2 | 成熟 | 2 轮 | RPE-004, RPE-007 (弱) | ✅ GO |
| RPE-007 | Docs 重构 | 2 | 成熟 | 2 轮 | RPE-000, RPE-004 (推荐) | ✅ GO |
| RPE-008 | Error DNA 共享库 | 2 | 不成熟 | 3 轮 | RPE-001 | ⏳ 等 RPE-001 |
| RPE-009 | Feature Probe 增强 | — | 成熟 | — | — | ✅ 已取消/已分配 |
| RPE-010 | Marketing 重写 | 3 | 成熟 | 2 轮 | RPE-002, RPE-004, RPE-006, RPE-007 | ❌ NO-GO (依赖阻塞) |
| RPE-011 | Launch Asset 补全 | 3 | 成熟 | 2 轮 | RPE-010 (推荐), RPE-002 | ❌ NO-GO |
| RPE-014 | OMA Lock 增强 | 5 | 不成熟 | 3 轮 | RPE-000 | ✅ GO |
| RPE-017 | Flywheel 增强 | 5 | 成熟 | 2 轮 | RPE-000 | ✅ GO |

---

## 4. 测试策略

| Task | 验证方式 | 具体命令/检查 |
|------|---------|-------------|
| RPE-000 | 仓库清单 | `find . -type f -size 0` + rg 规范路径 + 产出 repository-reality-check.md |
| RPE-001 | 集成测试 | 手动触发非零退出命令 → 检查 error-dna.jsonl 追加 + error-dna.json 合并 |
| RPE-002 | 脚本执行 | `python3 scripts/loading_benchmark.py` → 输出结构化报告（含 estimate 标注） |
| RPE-003 | 文件+行为 | read-files.log 轮转 + token writer 确认 + proactive-handoff 无静默失效 |
| RPE-004 | Schema 验证 | `python3 -c "import yaml; yaml.safe_load(open('.claude/feature-registry.yaml'))"` |
| RPE-005 | 手工验收 | 触发 4 个钩子 → 检查 numbered-choice 菜单 (O7-O10) |
| RPE-012 | 视觉审查 | lx-status 显示真实或 degraded 面板（Token 源缺失时不显示假零值） |
| RPE-013 | 脚本执行 | `audit_dashboard.py` 输出 5 源聚合报告 + 缺失源显示 degraded |
| RPE-006 | 脚本执行 | `python3 scripts/lecture_sync_check.py` |
| RPE-007 | 脚本执行 | `bash scripts/doc-sync-check.sh` |
| RPE-008 | 单元测试 | error_classifier.py 测试 + build-validator.sh 向后兼容 |
| RPE-009 | — | 已取消，AC 已全部分配 |
| RPE-010 | 脚本执行 | `bash scripts/claim-lint.sh` 零高风险关键词命中 |
| RPE-011 | 清单检查 | 截图/视频/dogfooding/外部审查文件均存在 |
| RPE-014 | 单元测试+集成 | stale lock / heartbeat / 竞争 acquire 测试通过 |
| RPE-016 | 集成测试 | race/ 目录隔离 + result.json 轮询（无 OMA 锁依赖） |
| RPE-017 | 集成测试 | 空日志 `exit 0` + flywheel-reports/ 目录创建 |

---

## 5. Oracle 迭代完成报告

| 轮次 | 状态 | 参与特性 | 产出 |
|------|------|---------|------|
| Round 1 ✅ | 已完成 | 13 项初始需求 | research.md 13 章节 + 优化版 WBS (17 Tasks) |
| Round 2 ✅ | 已完成 | 3 不成熟项 (Error DNA/Loading Benchmark/OMA Lock) | 3 候选方案评估 + 推荐方案确定 |
| Round 3 ✅ | 已完成 (11/13 明确, 2/13 部分) | 全部 17 RPE Task | oracle-round3-synthesis.md — 11 项明确裁决 + 5 项计划修正 |
| GPT5.5 Plan 评审 ✅ | 已完成 | plan.md 结构评审 | v1.2 修正 — Phase 0 / 依赖修正 / 职责拆分 / degraded 处理 |
| GPT5.5 Report Advice ✅ | 已完成 | 10 条建议评估 | research.md 新增评估章节 — 8/10 已覆盖, 2 项记录待讨论 |
| GPT5.5 Report Advice 2 ✅ | 已完成 | 评分表 + 任务清单评估 | 创建 docs/internal/product-comparison-scorecard.md；优化任务清单已覆盖，不创建重复副本 |
| GPT5.5 Release Plan ✅ | 已完成 | 5 月发布作战计划评估 | research.md 新增评估章节 — 定位语采纳, dogfooding/evidence 模板创建 |
| GPT5.5 better-info ✅ | 已完成 | 产品价值 + 8 优化建议评估 | research.md 新增评估章节 — 8 建议覆盖分析, C1-C5 证据层级互补, 创建 docs/guides/first-10-minutes.md |
| GPT5.5 better-info2 ✅ | 已完成 | 29 章 5 月执行策略评估 | research.md 新增评估章节 — 29 章覆盖分析, 创建 docs/reference/known-limitations.md + docs/reference/feedback-questions.md |

**输出文件**: `state/oracle-round3-synthesis.md` (Round 3), `state/evidence/gpt5.5-export-plan.md` (GPT5.5 Plan 评审), `state/evidence/gpt5.5-report-advice.md` (GPT5.5 Report Advice), `state/evidence/gpt5.5-report-advice2.md` (GPT5.5 Report Advice 2), `state/evidence/better-info.md`, `state/evidence/better-info2.md`

---

## 6. 回滚方案

| 范围 | 回滚动作 | 风险 |
|------|---------|------|
| 单个 Task | `git restore <file-list>` | 低 |
| 整个 Phase | `git revert <phase-commit>` | 中 |
| 全量产品化 | `git checkout <pre-rpe-branch>` | 低 |
| error-dna.sh | 恢复原始文件（不工作但无副作用） | 无 |

---

## 7. 影响范围

- 新增文件：`state/repository-reality-check.md`, `feature-registry.yaml`, `error_classifier.py`, `loading_benchmark.py`, `lecture_sync_check.py`, `feature-probe.sh`, `audit_dashboard.py`, `locks.json` 脚本, `flywheel-reports/`, `lecture/`（8 篇）, `claim-registry.yaml`, `claim-lint.sh`, `doc-sync-check.sh`
- 修改文件：`error-dna.sh`（重写）, `build-validator.sh`（抽取共享库）, `harness.yaml`, `harness_config.sh`, `read-tracker.sh`, `carror_dashboard.py`, `skill_trace_report.py`, `completion-gate.sh`, `context-guard.sh`, `oma_lock_manager.py`, `lx-status` SKILL.md, `flywheel-report.sh`
- 删除文件：无（所有变更向前兼容）
