# R7 提分计划 — Mate-Oracle 评测反馈闭环

> 由 Mate-Oracle 运行时冒烟评测驱动（2026-07-24）
> 门禁缺口：24 项总加权 7.67 → 目标 ≥8.6（需 +0.93）
> 状态：**计划就绪，待人类启动**
> 前置依赖：R6-B（token 轮换 + 脱敏回执）已通过 owner 裁决临时视为通过

---

## 一、当前评分 vs 目标

| 维度 | 运行时(7/24) | 目标 | 缺口 |
|------|------------|------|------|
| C1-C9 加权 | 7.71 | ≥9.0 | -1.29 |
| E1-E8 加权 | 7.68 | ≥9.0 | -1.32 |
| **24 项总加权** | **7.67** | **≥8.6** | **-0.93** |
| 最低单项 | **6 (C6/E5)** | **≥8.0** | **-2.0** |

## 二、哪些已经好了（不花功夫）

基于 14 项运行时冒烟测试的硬证据，以下维度已提分，R7 不需要再碰：

| 维度 | 原外评 | 运行时 | 证据 |
|------|--------|--------|------|
| C5 工具生命周期 | 6 | **8** | on→done→off 完整走通 + compact 恢复 + 跨会话 + lifecycle 互斥 17/17 |
| C9 错误恢复 | 6 | **8** | fallback engine 正确决策 + null crash 修复 + watermark 准确 + 中文 slug 修复 |
| E7 过度自信 | 6 | **7** | oracle_agent 闭包 bug 修复 + 31/31 对抗测试绿 |

## 三、哪些是 bug 修复已覆盖的（基础设施缝补，状态调整为已解决）

| 发现 | 修复 commit | 状态 |
|------|------------|------|
| fallback_engine token=None crash | `4e002f5` | ✅ 已合入 |
| lx-goal 中文 slug → `-` | `4e002f5` | ✅ 已合入 |
| oracle_agent task_id NameError | `4dbf020` | ✅ 已合入 |
| 回归套件 6→12 恢复 + 4 路径漂移 | `48a715b` + `50d384a` | ✅ 已合入 |
| posttool-claim-audit 冷启动误阻断 | `50d384a` | ✅ 已合入 |
| meta_oracle 缺 _latest_task_id() | `50d384a` | ✅ 已合入 |

## 四、真正需要 R7 施工的（不是修 bug，是加功能）

### PKG-A: 知识密度提升（C6: 6→9）

**当前状态**: 知识升华管线有文件（error-dna.jsonl, stop-flywheel.py, sublimation-log.jsonl）但未注册到 settings.json，从不被执行。

**需要做的事**:

1. **注册 error-dna PostToolUse hook** — 在 `.claude/settings.json` 中添加一行
   ```json
   {"type": "command", "command": "python3 .claude/hooks/hook-launcher.py error-dna", "timeout": 5000}
   ```
   - 影响: E5 症状混淆（有了数据底座才能治理）
   - 影响: C6 知识密度（有了采集才有升华）

2. **端到端升华管线验证** — 触发 error → error-dna → stop-flywheel → anti-patterns.md 新增一条目

3. **自动对账仪表盘** — scorecard 中的 Δ 计算自动化，不在需要人工追

**预估提分**: C6 6→7, E5 6→7（+0.08 加权）

### PKG-B: 38 个零测试机制补齐（治理·评测框架 7→9）

**当前状态**: 50+ 机制仅 12 个有测试覆盖。这是外评 C4/E5 低分的根因之一。

**需要做的事**（按性价比排序）：

1. **P0: test-fallback-engine.py** — 15 种失败类型 × 4 种决策，回归一次全跑（~80 行）
   - 前置: 无（脚本已修复）
   - 预估工时: 15min

2. **P1: test-posttool-claim-audit.py** — COLD_START/G1/E6 三种违规 + 自主模式降级（~100 行）
   - 前置: 已修复冷启动误阻断逻辑
   - 预估工时: 20min

3. **P2: test-privacy-gate.py** — Token 拦截(3种)/敏感路径(5种)/良性文件放行（~80 行）
   - 前置: 无
   - 预估工时: 15min

4. **P3: test-completion-gate.py** — 证据校验/过期/降级/L3 复杂性检测（~120 行）
   - 前置: 无
   - 预估工时: 25min

**预估提分**: C4 7→8, 治理·评测框架 9→9（0.25 加权，因为测试覆盖本身不是分数维度，但通过 C4 间接）

### PKG-C: AI 赋能全流程自动化（治理 7→8）

**当前状态**: `scripts/run-regression.sh` 已恢复且 12/12 全绿，但未接入 CI/pre-commit。

**需要做的事**:

1. **验收 Gate 化** — `lx-goal done` 前强制跑回归，失败则不允许 done
2. **pre-commit hook** — 人类装一次 hook，提交前自动跑回归
3. **单测覆盖率报告** — hooks 层 38 个 py 文件的 pytest 覆盖率基线

**预估提分**: 治理·自动化 7→8（+0.15 加权）

### PKG-D: 输出规范化机检（C4: 7→9）

**当前状态**: 外评 C4=7 因为输出格式反复漂移（audit 日期双存、verify 事件双格式等）。

**需要做的事**:

1. **PostToolUse schema 校验硬化** — `posttool-output-schema.py` 从 warn-only 升级到与已知 schemas 严格对比
2. **cmd_lint 入口** — 新增 CLI 入口对所有已知输出格式做机器检查

**预估提分**: C4 7→9（+0.19 加权）

## 五、人类独占项（AI 不可代劳）

| # | 事项 | 原因 | 处理 |
|---|------|------|------|
| 1 | **R6-B 轮换收口** | token 轮换需 Moonshot 控制台操作，AI 无法执行 | 见 R6-B receipt |
| 2 | **error-dna hook 注册** | `.claude/settings.json` 治理门禁，AI 需 goal mode 或人工编辑 | 人工 1 行配置 |
| 3 | **pre-commit hook 安装** | `git hooks` 是 git 写操作（硬边界） | `git config core.hooksPath .claude/hooks` |
| 4 | **coverage baseline 选型** | pytest / coverage.py / 第三方 CI 选型需要用户决定 | 决策后 AI 可自动化 |

## 六、R7 启动检查清单

- [ ] R6-B token 轮换 → 脱敏回执已入库（owner 认领）
- [ ] `bash scripts/run-regression.sh` → 12/12 ALL PASS（当前已验证 ✅）
- [ ] 24 项评分已更新到最新（当前已更新 ✅）
- [ ] 已确认 R7 不开新的 Grok 模型调用（遵守 Grok 禁令）
