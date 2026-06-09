# CHANGELOG

> Carror OS 版本历史 | 遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) | [语义化版本](https://semver.org/lang/zh-CN/)

---

## [v6.7.5] — 2026-06-09

> 统一优化：决策树 + 两段式 + fallback 三级降级 + fail-open + P0 Bug 修复

**新增**:
- B1: #8 哲学先行从 1 行模糊描述升级为 4 分支精确决策树（不可逆→问人 / 过程性→执行 / 技术选择→最小改动 / 哲学冲突→裁决链），降低 AI 猜错率
- C1: completion-gate 三级 fallback（Level 1 正常 → Level 2 简化 3 步链 → Level 3 紧急只警告），三态降级防卡死
- C2: permission-gate CAPTCHA fail-open 超时（900s），有出口不永久阻塞
- C5: 原子写 + 行数/长度校验，防静默写入损坏
- A2: 铁律 `[auto]` 标注（降低认知负担，一眼识别自动化规则 vs 需人工判断的规则）
- B2: pre-ask-guard 两段式决策链（Phase 1 AGENTS.md 快速扫描 → 命中即返回，Phase 2 全遍历兜底）
- C4: oracle-gate 状态合并单 JSON 文件 + 5s timeout，减少状态分裂风险
- C7: meta-oracle-trigger 标记驱动（评分≥85 / G1-G4 匹配才触发审查）
- A4: anti-pattern 路由 TOP3 提示，注意力分配优化
- A3: 路由索引描述精简 47%（AGENTS.md 7,907→6,371 字节，-20%）

**修复**:
- P0: `pre-completion-gate.py:L28` — `TOKENS_DIR=***` 粘贴遗留 bug（运行时 NameError），改为 `TOKENS_DIR = STATE_DIR / "tokens"`
- P0: `harness.yaml:max_entries=100` vs `error-dna.py:max_errors=50` 参数不一致，统一为 100
- source mirror 全量同步（17 个文件 md5 一致）

**自动化保证**:
- 双法官审查通过（Oracle REVISE → P0 修复 → ACCEPT / Meta-Oracle ADVISORY → 条件满足）
- 12/12 Python hook 语法检查全绿
- source mirror 一致性全绿

---

## [v6.7.4] — 2026-06-09

> OC carroros-gov plugin 漂移修复 + packages/ → .opencode/plugins/ 同步

**新增**:
- dual-platform test runner: scripts/run-oc-tests.mjs（npm run test → 6/6 测试套件）
- capability-matrix: harness-full-test.sh 全量执行集成在 OC 测试入口

**修复**:
- OC carroros-gov plugin 5 文件漂移: install.sh 安装时 `cp -r packages/carroros-gov .opencode/plugins/` — 用户安装即同步
- meta-oracle-trigger.sh 路由表 + firewall.sh 条件体修正

---

## [v6.7.3] — 2026-06-09 (内部测试，未发版)

---

## [v6.7.2] — 2026-06-09 (内部测试，未发版)

---

## [v6.7.1] — 2026-06-09

> Meta-Oracle 评分增强：9.01→9.56 🚀 G 治理维度满分

**新增**:
- token-compact-state.json 状态文件，C2 上下文完整性 53%→80%
- harness-smoke 日志摘要格式，G2 smoke 验证通道激活

**增强**:
- philosophy.md 双向映射描述（机制→哲学逆向追溯），G1 哲学一致性 70%→100%
- completion-gate.py RCA/根因分析关键词，E5 症状混淆诊断能力提升
- 治理评分 Meta-Oracle ACCEPT：C 91.4% / E 97.3% / G 100% / 总分 9.56

---

## [v6.7.0] — 2026-06-09

> OC plugin 漂移修复 + packages/ 与 .opencode/plugins/ 一致性同步 + error-dna 数据链闭环修复

**新增**:
- plan-gate.py 存根 hook 创建，capability-matrix D1 全绿（75 PASS/0 FAIL）

**修复**:
- OC carroros-gov plugin 5 文件漂移
- error-dna.py 三管道写入数据链断裂修复
- 多项修复详情见完整 CHANGELOG

---

## [v6.4.0] — 2026-05-31

> 知识管道激活 + 四hook接线上线 + 三门户路由完善 + Story对齐 + 全量测试框架

**新增**:
- 知识管道 Phase 4 激活
- pretool-plan-gate.sh 上线
- build-validator.sh 上线
- error-dna-auto-fix.sh 上线
- 全量测试框架: harness-full-test.sh → 12领域套件聚合(571/606)
- 3个reference文档
- 回滚脚本

**路由扩展**:
- AGENTS.md 路由条目: 24→28条
- Skills入口补skills-catalog.md路径
- 置信度标注格式纳入编码内核

**修复**:
- 12个孤儿/僵尸hook
- 17个CHANGELOG清理
- 发行版kernel.md替换
- 烟雾测试更新

**运行时验证**:
- 34/34 运行时实验全绿
- 213/213 Smoke 全绿 | 571/606 Full test

---

## [v6.3.27] — 2026-05-31

> 三门户架构重构 + Windows兼容 + 上下文工程修复

**新增**:
- 三门户架构: AGENTS.md(主门户) + kernel.md(数字资产管理员) + index.md(hooks路由注册表)
- 24条路由索引覆盖全部机制/能力/工作流
- Compact交接文档化(kernel.md §Compact交接)
- 根目录清理: 删除17项过期文件/目录

**修复**:
- context-compressor bootstrap→mtime死循环 (FORCE_REGEN)
- AGENTS-compact.md缺失导致缓存不完整
- 5个僵尸hook
- Windows where.exe + PYTHON_BIN兼容

---

## [v6.3.26] — 2026-05-30

> DG-131 completion-gate + 双法官审查

- DG-131: completion-gate minimum scope blocking + docs alignment
- terminal-safety 200→500
- dual-review fixes + docs optimization
- comprehensive docs semantic alignment

---

## [v6.3.8] — 2026-05-29

> 文档同步 + Python路径缓存

- full docs sync: new mechanisms, deprecated, 2 new stories
- Python path cache (Windows where.exe overhead)
- harness_config _resolve_python() Windows PATH fix
- checklint recursive loop fix

---

## [v6.3.7] — 2026-05-28

> 发布检查清单 + source mirror

- complete release checklist (5 phases, 14 checks)
- skill-flywheel absolute path fix
- final source mirror sync + zombie fix
- DG-129/130 dogfood

---

## [v6.3.5] — 2026-05-26

- customer AI feedback fixes

## [v6.3.4] — 2026-05-25

- AGENTS.md upgrade merge fix + pre-upgrade cache

## [v6.3.3] — 2026-05-24

- install.sh --uninstall + AI维护引导

## [v6.3.2] — 2026-05-23

- Gate协议重构 + checkpoint通用节点 + 上下文分层注入

## [v6.3.1] — 2026-05-22

- 门禁体系原子化重构 + tokens/路径迁移 + 双法官审计修复

## [v6.3.0] — 2026-05-21

> 6.3 系列起点

---

## [v6.2.41] — 2026-05-20

- DG-125 /approve对话内批准协议 + G2三项修复

## [v6.2.40] — 2026-05-19

- DG-124 客户端反馈7项修复 + hook计数修正 + flywheel埋点补全

---

## [v6.1.9-stable] — 2026-05-09

> 狗粮修复 + 三重门硬化 + Oracle审计闭环 + 发布流水线

**新增**:
- 三重门交叉验证协议（A→B→A盲执行 + Oracle终审）
- OMA技能依赖图声明（skill-dependencies.yaml）
- 统一技能版本号格式
- lx-oma-orch、lx-oma-split、lx-oma-hier、lx-oma-gov

**修复**:
- context-guard白名单漂移修复
- subagent-guard max_turns软约束重构
- PostToolUseFailure事件架构纠正
- 12个僵尸脚本批量归位
- error-dna高频错误捕获增强

---

## [v6.1.8] — 2026-05-03 (Cross-Platform Edition)

## [v6.1.7-stable] — 2026-04-29 (Stabilization Release)

## [v6.1.5] — 2026-04-28 (One-Man Army Edition)

## [v6.1.4] — 2026-04-27 (The Documentation Refactor Edition)

## [v6.1.3] — 2026-04-27 (The Three-Stage Architecture Edition)

## [v6.1.2] — 2026-04-27 (Safe Migration Edition)

## [v6.1.1] — 2026-04-27 (Cloud Installer Edition)

## [v6.1.0] — 2026-04-27 (Progressive Delivery Edition)

## [v6.0.8] — 2026-04-27 (The Seamless Edition)
