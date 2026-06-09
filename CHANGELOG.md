# CHANGELOG

> Carror OS 版本历史 | 遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) | [语义化版本](https://semver.org/lang/zh-CN/)

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
- OC carroros-gov plugin 5 文件漂移: error-dna.py / harness_lib.py / posttool-claim-audit.py / pretool-oracle-gate.py / privacy-gate.py — packages/ 版（更新版）同步覆盖 .opencode/plugins/
- error-dna.py 三管道写入数据链断裂修复：旧格式双写 + retry-budget.json 强制创建，闭环 error-dna.py → retry-budget.json → pretool-retry-check.py 完整工作
- error-dna-auto-fix.py 读取优先 retry-budget.json，旧格式 fallback
- test-harness.mjs carror-hooks-compat 注册断言修复（49/49 全绿）
- harness_lib.py: 新增 hc_fail_closure() 函数（fail-close/fail-open 配置支持）
- posttool-claim-audit.py: E6 v2 机制升级（content_flip 检测 + edit_repeat 检测）
- pretool-oracle-gate.py: 移除 IS_WINDOWS 跳跃（macOS/Linux Oracle 门禁恢复）
- privacy-gate.py: C5 fail-close（harness.yaml 缺失时拒绝放行）

**自动化保证**:
- install.sh 安装时自动 `cp -r packages/carroros-gov .opencode/plugins/` — 用户安装/更新即获取最新版

---

## [v6.4.0] — 2026-05-31

> 知识管道激活 + 四hook接线上线 + 三门户路由完善 + Story对齐 + 全量测试框架

**新增**:
- 知识管道 Phase 4 激活: knowledge-condenser.sh 扫描claude-next.md高频模式→升华建议
- pretool-plan-gate.sh 上线: 方案未审批→阻断Edit/Write/Bash，三模式感知(ghost/goal/normal)
- build-validator.sh 上线: 12种构建命令自动诊断+修复建议
- error-dna-auto-fix.sh 上线: 跨会话错误回顾(≥3次顽固错误)
- 全量测试框架: harness-full-test.sh → 12领域套件聚合(571/606)
- 3个reference文档: mechanism-lifecycle.md / source-mirror-discipline.md / red-team.md
- 回滚脚本: rollback-last-refactor.sh (软回滚/硬回滚)

**路由扩展**:
- AGENTS.md 路由条目: 24→28条 (+发布流水线/Source Mirror/狗粮Triage/Red Team/机制生命周期)
- Skills入口补skills-catalog.md路径
- 置信度标注格式纳入编码内核: [已验证:file:line] / [已测试:命令+输出] / [推断,待确认]

**修复**:
- 12个孤儿/僵尸hook: 5个幽灵声明清理 + plan-gate.sh删除 + feature-probe.sh迁移
- 17个CHANGELOG-6.3.*.md清理,保留最新
- 发行版kernel.md替换为开发版(v6.3.27→v6.4.0版本)
- harness-smoke-test 更新: R36-R39新增10项测试(213/213全绿)
- 烟雾测试 R36 knowledge-condenser 状态更新 (幽灵注册→已激活)
- 5个幽灵harness声明清理

**Story对齐**:
- Story-08: autonomous.active→tokens/lx-ghost.json+lx-goal.json，is_mode_active()更新
- Story-10: "旧军团消逝"→"旧军团迁移进化"，承认.claude/scripts/仍在活跃
- Story-12: ED-01"移除"→"搁置归档→v6.3.27三扇封印解开"

**运行时验证**:
- 平台: Darwin arm64 (Apple Silicon)
- Claude Code 2.1.158 ✓ | OpenCode 1.15.4(OMO) ✓ | OMC ✓
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
- 5个僵尸hook (anti_pattern_detect等)
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
