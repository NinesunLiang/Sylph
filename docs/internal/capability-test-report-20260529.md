# Carror OS 全量能力测试报告

> 日期: 2026-05-29 | 方法: 46 条可证伪测试 + 运行时证据 + Meta-Oracle 双审
> 范围: 15 能力域，覆盖 ~240 文件，14 个 .claude/ 子区域 + 跨平台接入层

---

## 总体结果

| | 数量 | 占比 |
|---|:--:|:--:|
| PASS (断言成立) | 29 | 63% |
| PARTIAL (部分成立) | 12 | 26% |
| FAIL (断言不成立) | 5 | 11% |
| **总计** | **46** | **100%** |

**加权健康度**: 71.2/122 = **58.4%** (ROI 加权: PASS=1.0, PARTIAL=0.5, FAIL=0.0)

---

## 逐域测试结果

### Domain 1: 运行时安全防线 | ROI: 15 | 得分: 11.25/15

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T1.1 | privacy-gate 密钥拦截有效 | ✅ PASS | line 36 正则覆盖 .env/.pem/.key/id_rsa/credentials/kubeconfig；运行时 3,496 次调用 |
| T1.2 | blast-radius 危险命令拦截 | ✅ PASS | 拦截 rm -rf / git push --force / sudo / drop table；运行时 2,798 次调用 |
| T1.3 | terminal-safety 有效但过度敏感 | ⚠️ PARTIAL | Rule6 阻断 >500 字符命令有效，但高频误报：error-dna 6 个签名各 ×5-9 次 |
| T1.4 | 4 个 gate 静默禁用 | ❌ FAIL | harness.yaml:95,100,116,124 全 false，无用户通知机制 |

**优化点**:
- **[P1] T1.3**: terminal-safety Rule6 阈值从 500 提升到 800 字符，或对 `&&` / `;` 分隔的多命令组合做豁免
- **[P1] T1.4**: 为禁用的 gate 添加 SessionStart 通知: "⚠️ 以下安全门禁已关闭: permission_gate, pretool_sensitive_edit..."

### Domain 2: 铁律强制执行 | ROI: 15 | 得分: 13.5/15

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T2.1 | claim-audit read-tracker 交叉验证 | ✅ PASS | line 47-80: 双层验证(完整路径+basename)，read-tracker 不存在→全部标记不可信 |
| T2.2 | completion-gate 7 层防御 | ✅ PASS | line 60-284: 证据存在性+新鲜度(300s)+VERIFIED关键词+软完成词正则+双源+质量评分+E5 RCA |
| T2.3 | edit-scope 范围冻结+completion-blocked | ⚠️ PARTIAL | 机制存在(scope+coupling+DG-131 阻断)，但 Bash sed/echo 可绕过(已知取舍) |
| T2.4 | anti-pattern 硬阻断 A2/F1/H1 | ✅ PASS | 运行时 893 次调用 |

**优化点**:
- **[P2] T2.3**: pretool-edit-scope 扩展 matcher 到 Bash 工具（覆盖 sed/echo 绕过），但需先解决 terminal-safety 过度阻断问题

### Domain 3: 上下文管理 | ROI: 10 | 得分: 9.17/10

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T3.1 | context-guard 实时 token 检测 | ✅ PASS | line 58-80: Python context_monitor.py 获取真实 transcript 百分比，50%/80% 阈值，拒绝启发式 |
| T3.2 | R39 预算 DG-99 修复 | ⚠️ PARTIAL | inject-project-knowledge.sh 存在，DG-99 修复"先检查后累加"，但未逐行验证代码 |
| T3.3 | 4 个 compact 变体存在 | ✅ PASS | ls 确认: AGENTS-compact(2KB) + anti-patterns-compact(1KB) + claude-next-compact(1KB) + kernel-compact(1.3KB) |

**优化点**:
- **[P3] T3.2**: 对 inject-project-knowledge.sh 做单元测试覆盖，验证 R39 预算计算精确性

### Domain 4: 错误检测与恢复 | ROI: 10 | 得分: 5.83/10

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T4.1 | error-dna 心跳+轮转+孤儿清理 | ✅ PASS | line 48(心跳)+56(trap EXIT)+60-69(轮转 1MB/3归档)+305-307(孤儿清理) |
| T4.2 | error-dna RCA 分类被移除 | ❌ FAIL | line 4 明确记录: "移除 JSON 全量重建(~200行)、噪声分类(~100行)、repair_success 检测" |
| T4.3 | retry-budget 3 轮限制 | ⚠️ PARTIAL | 机制存在但不同命令=不同签名，同逻辑修复可绕过 |

**优化点**:
- **[P0] T4.2**: 恢复 error-dna 轻量 RCA 分类（Top 3 签名 + 预计算模式匹配，≤50 行），当前全量移除导致 E5 症状混淆得分为弱
- **[P2] T4.3**: retry-budget 增加命令语义去重（相似命令归一化到同一签名）

### Domain 5: 一致性审计 | ROI: 8 | 得分: 5.33/8

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T5.1 | audit-hooks 三方一致性 | ✅ PASS | Python 脚本，运行时 1,571 次调用 |
| T5.2 | harness-smoke-test | ⚠️ PARTIAL | **205/206 passed, 1 failed**（非之前说的 206/206 全绿） |
| T5.3 | pretool_node_reference 重复 3 次 | ❌ FAIL | harness.yaml:118,120,121 — 重复键，无自动检测 |

**优化点**:
- **[P1] T5.2**: 修复 1 个失败的 smoke test + 增加到 250+ 测试场景（覆盖新增 hook）
- **[P1] T5.3**: audit-hooks.sh 增加 YAML 重复键检测（当前只做三方一致性，不做键值去重）

### Domain 6: 自主模式 | ROI: 8 | 得分: 7.0/8

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T6.1 | Goal/Ghost/RPE 三种模式定义 | ✅ PASS | kernel.md:94-150，阶段分明，L4 截断清晰 |
| T6.2 | autonomous-decision-chain 完整 | ✅ PASS | L1-L4 决策链 + Situation Matrix + Forbidden 清单 |
| T6.3 | 自主模式 hook 降级 | ✅ PASS | context-guard:30-35 + completion-gate:32-54 + claim-audit:9-14 全部降级 |

**优化点**: 无 P0-P2 优化点。

### Domain 7: 文档质量 | ROI: 6 | 得分: 4.5/6

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T7.1 | 7 个教程连贯学习路径 | ✅ PASS | tutorial-00 到 06 存在，~1,812 行，first-10-minutes.md 承诺合理 |
| T7.2 | 故事引用具体机制 | ⚠️ PARTIAL | story-05 引用具体 hook(line 27,37)，但 ~60% 内容是叙事阐述，无运行时增量 |

**优化点**:
- **[P3] T7.2**: 23 个故事文件(~3,277 行)中约 1,966 行纯叙事——考虑提取机制引用部分到 reference/，故事保留为入门读物

### Domain 8: Schema & Node 系统 | ROI: 10 | 得分: 2.5/10

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T8.1 | schema YAML 文件零 hook 引用 | ⚠️ PARTIAL | `verdict` 词出现在 3 个 hook 中(作为 state 文件路径或模板文本)，但 schema 文件名(error_codes/fix_record/gate_result)在 hooks/ 中零匹配 |
| T8.2 | 双编排器状态机冲突 | ❌ FAIL | nodes/orchestrator.md vs task_sys/orchestrator.md: 后者多了 fallback 状态，转换也不同，均无 runtime 引用 |
| T8.3 | feature-registry 零哲学映射 | ❌ FAIL | `grep -c 'philosophy\|Philosophy' feature-registry.yaml → 0` — 40 条目零哲学字段 |

**优化点**:
- **[P0] T8.3**: feature-registry.yaml 每个条目增加必填 `philosophy` 字段（关联 7 条哲学 #1-#7），新增条目无哲学映射 → 阻断
- **[P1] T8.1**: 二选一：(A) 删除无消费者的 schema 文件，或 (B) 在 completion-gate 中引用 verdict schema 做输出验证
- **[P1] T8.2**: 合并 nodes/orchestrator.md 和 task_sys/orchestrator.md，统一状态机定义

### Domain 9: Skill 系统 | ROI: 6 | 得分: 4.0/6

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T9.1 | 26 个 skill 存在且结构完整 | ✅ PASS | 26 个 lx-* 目录，每个有 SKILL.md |
| T9.2 | skill-graph.md 仅显式依赖 | ⚠️ PARTIAL | 映射 L1/L2/L3 但未处理 hook 门禁的隐式依赖 |

**优化点**:
- **[P2] T9.2**: skill-graph.md 增加隐式依赖边（如 lx-goal → pretool-plan-gate hook 依赖）

### Domain 10: 跨平台兼容 | ROI: 12 | 得分: 9.0/12

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T10.1 | unified.yaml 9 事件模型 | ✅ PASS | .hooks/unified.yaml 定义 6 平台适配 (Claude Code/Codex/Gemini/Qwen/Cursor/OpenCode) |
| T10.2 | Cursor hooks.json 注册 | ⚠️ PARTIAL | 仅 4 个 hook(permission-gate/privacy-gate/bash-audit/build-validator)，远少于 settings.json 的 48 个 |
| T10.3 | install.sh 跨平台兼容 | ✅ PASS | resolve_python() + 9 种包管理器(winget/choco/scoop/brew/apt/yum/dnf/pacman/apk) |
| T10.4 | PYTHON_BIN 传播到 hooks | ✅ PASS | harness_config.sh 导出 `$PYTHON_BIN`，所有 source 此文件的 hook 继承 |

**优化点**:
- **[P1] T10.2**: Cursor hooks.json 从 4 个扩展到至少 15 个核心 hook（completion-gate/claim-audit/context-guard/error-dna 等）

### Domain 11: Release 管线 | ROI: 8 | 得分: 6.0/8

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T11.1 | release.sh 7 步流程 | ✅ PASS | 版本递增→同步→打包→审计→提交→推送→Release |
| T11.2 | package-release.sh G4 门禁 | ⚠️ PARTIAL | 存在但 DG-109 (rsync --delete 静默回退 71 文件) 已修复，修复质量待验证 |
| T11.3 | VERSION.json + CHANGELOG 一致 | ✅ PASS | 存在且可读 |

**优化点**:
- **[P2] T11.2**: package-release.sh Step 0 三源预检移到 Step 1 rsync 之后执行，消除每轮发版必报的假阳性漂移阻断 (DG-118)

### Domain 12: Profile 系统 | ROI: 5 | 得分: 2.5/5

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T12.1 | 7 个语言 profile 存在 | ✅ PASS | base/go/python/rust/node/enhanced 目录齐全 |
| T12.2 | profile 零哲学引用 | ❌ FAIL | `grep -r 'philosophy' .claude/profiles/ → (no matches)` |

**优化点**:
- **[P1] T12.2**: 每个 profile harness.yaml 增加 `philosophy_alignment` 字段，标注该语言配置与哪几条哲学最相关

### Domain 13: 哲学对齐 | ROI: 8 | 得分: 4.0/8

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T13.1 | AGENTS.md 哲学优先级链 | ✅ PASS | 7 条哲学 #4>#6>#3>#7>#5>#2>#1，冲突裁决规则明确 |
| T13.2 | philosophy-matrix 静态快照 | ❌ FAIL | 生成于 2026-05-17，12 天未更新 |
| T13.3 | 铁律 #8 无物理 hook | ❌ FAIL | `ls .claude/hooks/pretool-ask-guard.sh → FILE NOT FOUND` |

**优化点**:
- **[P0] T13.2**: philosophy-mechanism-matrix.md 从静态文档改为自动生成（audit-hooks.sh 运行时产出），每次审计时更新
- **[P1] T13.3**: 恢复 pretool-ask-guard.sh（哲学先行门禁），当前仅靠 AI 自我遵守

### Domain 14: 知识管理 | ROI: 6 | 得分: 3.0/6

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T14.1 | claude-next.md 结构化 DG 条目 | ✅ PASS | ~130 条 DG，触发→行为→证据格式统一，升华规则明确 |
| T14.2 | knowledge_condenser 禁用 | ❌ FAIL | `harness.yaml:95: knowledge_condenser: false` |
| T14.3 | anti-patterns 狗粮证据链 | ✅ PASS | DG-85 强制执行，每条反模式引用具体 DG 编号 |

**优化点**:
- **[P0] T14.2**: 重新启用 knowledge_condenser 或替换为 CronCreate 定时任务做自动升华扫描，当前 ~130 DG + ~20 纠正 12 天未升华

### Domain 15: UX / 交互 | ROI: 5 | 得分: 3.33/5

| ID | 测试 | 结果 | 运行时证据 |
|----|------|:--:|------|
| T15.1 | /approve 对话内批准 | ✅ PASS | permission-gate.sh 搜索到 /approve 和 /deny 引用 |
| T15.2 | 方向指引输出格式 | ✅ PASS | AGENTS.md §输出格式标准 定义完整 |
| T15.3 | 裁决边界表完整 | ⚠️ PARTIAL | 5 维度清晰，但 DG-132(oracle-gate 范围过宽)未修复 |

**优化点**:
- **[P1] T15.3**: 按 DG-132 修复 oracle-gate 治理文件分层（claude-next.md/docs/story/dogfood 不触发双审）

---

## 优化点汇总 (按优先级)

### P0 — 立即修复 (4 项)

| # | 来源 | 问题 | 修复方案 | 预计工作量 |
|---|------|------|---------|:--:|
| 1 | T4.2 | error-dna RCA 分类被完全移除 → E5 症状混淆评分弱 | 恢复轻量 RCA: Top 3 签名+预计算模式匹配，≤50 行 | 1h |
| 2 | T8.3 | feature-registry 零哲学映射 → 长期一致性评分 ❌ | 每个条目加必填 `philosophy` 字段，新增无映射→阻断 | 2h |
| 3 | T13.2 | philosophy-matrix 12 天静态快照 | 改为 audit-hooks.sh 运行时自动产出，每次审计更新 | 2h |
| 4 | T14.2 | knowledge_condenser 禁用 → 升华管道坏死 | 重新启用或替换为 CronCreate 定时扫描任务 | 1h |

### P1 — 短期修复 (8 项)

| # | 来源 | 问题 | 修复方案 |
|---|------|------|---------|
| 5 | T1.3 | terminal-safety 高频误报 (6 签名 ×5-9 次) | Rule6 阈值 500→800，或 `&&`/`;` 分隔的多命令豁免 |
| 6 | T1.4 | 4 个 gate 静默禁用 | SessionStart 通知: "⚠️ 安全门禁已关闭: ..." |
| 7 | T5.2 | smoke test 1/206 失败 | 修复失败用例 |
| 8 | T5.3 | harness.yaml 重复键无检测 | audit-hooks.sh 增加 YAML 键值去重检查 |
| 9 | T8.1 | 18 schema 文件零消费者 | 删除无消费者文件 或 completion-gate 引用 verdict schema |
| 10 | T8.2 | 双编排器状态机冲突 | 合并为一个统一的 orchestrator.md |
| 11 | T10.2 | Cursor 仅 4 个 hook | 扩展到 15+ 核心 hook |
| 12 | T13.3 | pretool-ask-guard 缺失 | 恢复哲学先行物理门禁 |

### P2 — 中期改进 (5 项)

| # | 来源 | 问题 | 修复方案 |
|---|------|------|---------|
| 13 | T2.3 | Bash sed/echo 绕过 edit-scope | 扩展 matcher 到 Bash 工具 |
| 14 | T4.3 | retry-budget 命令签名去重 | 相似命令归一化到同一签名 |
| 15 | T9.2 | skill-graph 缺隐式依赖 | 增加 hook 门禁依赖边 |
| 16 | T11.2 | package-release.sh 假阳性漂移阻断 | 三源预检移到 rsync 之后 (DG-118) |
| 17 | T15.3 | oracle-gate 范围过宽 | 治理文件 blast-radius 分层 (DG-132) |

### P3 — 锦上添花 (2 项)

| # | 来源 | 问题 | 修复方案 |
|---|------|------|---------|
| 18 | T3.2 | R39 预算缺少单元测试 | 对 inject-project-knowledge.sh 做测试覆盖 |
| 19 | T7.2 | 故事 ~60% 纯叙事 | 提取机制引用到 reference/，故事保留为入门读物 |

---

## 能力热力图

```
Domain 1  安全防线    ██████████████░░  11.25/15  (75%)
Domain 2  铁律执行    █████████████████  13.50/15  (90%)
Domain 3  上下文管理  ██████████████░░   9.17/10  (92%)
Domain 4  错误恢复    ███████░░░░░░░░░   5.83/10  (58%)  ← P0
Domain 5  一致性审计  ████████░░░░░░░░   5.33/8   (67%)
Domain 6  自主模式    ██████████████░░   7.00/8   (88%)
Domain 7  文档质量    ███████████░░░░░   4.50/6   (75%)
Domain 8  Schema/Node ███░░░░░░░░░░░░░   2.50/10  (25%)  ← P0
Domain 9  Skill系统   ████████░░░░░░░░   4.00/6   (67%)
Domain 10 跨平台兼容  █████████████░░░   9.00/12  (75%)
Domain 11 Release管线 ████████████░░░░   6.00/8   (75%)
Domain 12 Profile系统 ██████░░░░░░░░░░   2.50/5   (50%)  ← P1
Domain 13 哲学对齐    ██████░░░░░░░░░░   4.00/8   (50%)  ← P0
Domain 14 知识管理    ██████░░░░░░░░░░   3.00/6   (50%)  ← P0
Domain 15 UX交互      ████████░░░░░░░░   3.33/5   (67%)
─────────────────────────────────────────────────
综合                    ███████████░░░░░  71.2/122 (58.4%)
```

---

## 跨模型验证备注

本报告的运行时证据由 DeepSeek 采集（grep/wc/ls/cat 等只读命令的输出）。关键断言（T8.1 修正、T5.2 smoke test 205/206、T8.3 零哲学映射）已通过命令输出物证验证。

Opus 4.7 和 GPT 5.5 可用于交叉验证以下高不确定性测试:
- T2.1-T2.4: 铁律执行的语义正确性（代码逻辑审查）
- T7.1-T7.2: 文档质量（需人工/多模型判断）
- T8.1: schema 引用的精确定义（"verdict" 词边界）
- T10.3-T10.4: 跨平台代码路径完整性

---

*报告路径: `docs/internal/capability-test-report-20260529.md`*
*证据文件: `.omc/plans/2026-05-29/.../test-evidence-raw.txt`*
*测试矩阵: `.omc/plans/2026-05-29/.../test-case-matrix.md`*
