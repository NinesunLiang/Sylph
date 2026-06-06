# harness-smoke-test.sh 全面分析报告

> 分析日期: 2026-06-07
> 文件: .claude/scripts/harness-smoke-test.sh (2179行)
> 总测试项: ~212 项（TOTAL 计数器在不同条件路径下最终值 200-220）

---

## 一、测试分组归类

### 1. Hook 语法检查（bash -n）— ⚠️ 弱断言组
共 **11 项**，仅检查 `bash -n` 不报错，不验证运行时行为：

| # | 测试名 | 风险 |
|---|--------|------|
| R36 | knowledge-condenser 语法检查 | 弱 — bash -n 只能发现语法错误，逻辑错误漏不掉 |
| R37 | posttool-handoff-writer 语法检查 | 弱 |
| R38 | auto-scope 语法检查 | 弱 |
| R37 | pretool-plan-gate 语法检查 | 弱 |
| R38 | build-validator 语法检查 | 弱 |
| R39 | error-dna-auto-fix 语法检查 | 弱 |

**结论**: 这 6 项是**最水的测试**。bash -n 无法发现变量拼写错误、退出码错误、逻辑短路等。但保留少量有价值（至少确保 shell parse 正常）。建议合并为 1 个通用语法检查块。

### 2. Hook 注册/配置检查（settings.json / harness.yaml grep）
共 **9 项**，仅 grep 配置文件是否存在某行：

| 测试 | 检查项 |
|------|--------|
| R38 posttool-claim-audit settings.json 注册 | 弱 |
| R38 posttool-claim-audit harness.yaml 开关 | 弱 |
| R32 intent-tracker settings.json 注册 | 弱 |
| R32 intent-tracker harness.yaml 开关 | 弱 |
| R36 knowledge-condenser settings.json 注册 | 弱 |
| R36 knowledge-condenser harness.yaml 开关 | 弱 |
| R37 posttool-handoff-writer settings.json 注册 | 弱 |
| R37 posttool-handoff-writer harness.yaml 开关 | 弱 |
| R39 completion-gate quality harness.yaml 配置 | 弱 |
| R32 intent-tracker 非 Edit 静默退出 | 中 — 至少验证了 exit code |

**结论**: 这些仅确认配置存在，不验证 hook 的功能正确性。**建议合并**为一个 `audit-hooks.sh --check-registry` 调用（此脚本尾部已调用）。

### 3. hook 真实行为测试（有输入→断言输出/exit code）
共 **~70 项**，这是最有价值的组。

#### 3a. context-guard（上下文门禁）
- 7 项：95% heuristic warn-only、25% 正常放行、Read/Grep/Bash 诊断通道放行、ghost mode 降级
- **质量**: 高 — 覆盖了 R29 关键路径

#### 3b. privacy-gate（隐私门禁）
- 5 项：.env 阻断、ssh key 阻断、sk-ant Token 阻断、ghp_ Token 阻断、正常 Read 放行
- **质量**: 高 — 覆盖 main sensitive patterns

#### 3c. permission-gate（权限门禁）
- 3 项：rm -rf 阻断、git commit 阻断、ls 放行 + E2E CAPTCHA 流
- **质量**: 中高

#### 3d. edit-guard（编辑门禁）
- 2 项：未 Read 就 Edit 阻断、非 .go 放行
- **质量**: 中

#### 3e. pre-edit-lsp-check（LSP 检查）
- 3 项：LSP 不可用放行、.txt 跳过、.py 提醒
- **质量**: 中

#### 3f. error-dna（错误 DNA 捕获）
- 6 项（含 R22 PostToolUseFailure + stop-drain transcript 补录）
- **质量**: 高 — 有输出内容断言

#### 3g. write-lock（写锁）
- 2 项：加锁+解锁
- **质量**: 中

#### 3h. posttool-edit-quality（编辑质量自查）
- 1 项：检查 additionalContext 含自查内容
- **质量**: 中

#### 3i. lsp-suggest（LSP 建议）
- 4 项：首次导出符号警告、第二次放行、正则放行、会话标记检查
- **质量**: 中

#### 3j. subagent-guard（子 agent 门禁）
- 4 项：无 max_turns 放行、含 max_turns 放行、安全 agent 放行、dangerous agent 检查
- **质量**: 中高

#### 3k. completion-gate（完成门禁）
- 2 项：无证据硬阻断、in_progress 放行
- **质量**: 高

#### 3l. posttool-claim-audit（断言审计）
- 5 项：无 claim 放行、未读 claim 阻断、软完成语检测、settings 注册、yaml 开关
- **质量**: 中高

#### 3m. posttool-anti-pattern-detect（反模式检测）
- 4 项：A2 虚假完成阻断、F1 假设驱动阻断、H1 语义编造阻断、正常放行
- **质量**: 高 — 有明确的 exit code 和内容断言

#### 3n. pretool-blast-radius（爆炸半径）
- 3 项 + 4 项 R42-R45：git checkout . 阻断、git checkout -- file 放行、分号绕过阻断等
- **质量**: 高

#### 3o. pretool-terminal-safety（终端安全）
- 2 项：危险命令放行告警、正常命令放行
- **质量**: 低 — 只检查 exit 0，没检查告警内容

### 4. E2E 联动场景
共 **13 项**：

| 场景 | 断言质量 |
|------|---------|
| E2E-1: CAPTCHA 流 | 高 |
| E2E-2: 知识注射循环 | 中 |
| E2E-3: 错误 DNA 捕获 | 高 |
| E2E-4: 格式化门禁 | 高 |
| E2E-5: Stop 持久化链 | 高 |
| E2E-6: C3 Oracle 终审 | 高 |
| 场景A: 危险命令拦截 | 中 |
| 场景B: 治理文件编辑 | 中 |
| 场景C: 虚假完成双重门禁 | 中 |
| 场景D: Token 泄露 | 中 |
| 场景E: SessionStart 知识注入 | 中 |
| 场景F: 用户纠正 | 中 |

### 5. ED-R (Error-DNA Escape Detection)
共 **7 项**：
- ED-R-1~7: 覆盖 governance_bypass (sed/tee/echo redirect)、captcha_forgery (sensitive-approved/permission-approved)、evidence fabrication、normal command not recorded
- **质量**: 高 — 每个都有明确的 jsonl 内容断言

### 6. Anti-Pattern Detection（R44）
共 **3 项**：
- A2 虚假完成、F1 假设驱动、H1 语义编造 → 都要求 exit 2 + 内容匹配
- **质量**: 高

### 7. Cross-Platform 测试
共 **14 项**：

| 测试 | 评价 |
|------|------|
| bash 可用 | ❌ 无意义 — smoke test 已经在用 bash 跑 |
| python3 可用 | ❌ 无意义 — 多个测试已经依赖 python3 |
| jq 可用 | ⚠️ 弱 — 只是 info |
| 平台检测 | ❌ 无意义 — uname 总有输出 |
| sed -i '' (BSD) | ⚠️ 只在 macOS 触发，价值低 |
| COPYFILE_DISABLE | ❌ 无意义 — 环境变量检查 |
| Codex CLI | ❌ 无意义 — 工具安装检查 |
| OpenCode config | ❌ 无意义 |
| VS Code CLI | ❌ 无意义 |
| Python 核心模块 | ⚠️ 弱 — smoke test 已经依赖这些模块 |
| Python secrets | ❌ 无意义 |
| git 可用 | ❌ 无意义 — 项目已经依赖 git |
| .git 目录 | ❌ 无意义 |
| 无残留信号文件 | ⚠️ 弱 — 但可保留 |

**结论**: 14 项 cross-platform 测试中，**至少 10 项可删除**。只有"无残留信号文件"有微弱价值。

### 8. 飞轮数据真实性验证
共 **6 项**：
- flywheel.log 存在且有记录、格式合规
- session-turns.json count>0
- error-dna.jsonl signature
- session-snapshot.json 字段完整
- context-cache.md 非空
- token-tracking-index.json 格式

**结论**: 这些是运行时产物检查。如果 CI 环境没有真实运行过 Claude Code，全是空的/不存在，会误报。**建议标记为 `--full` 模式**，默认跳过。

### 9. OpenCode sylph-hooks 路由验证
共 **5 项**：
- 文件存在、beforeHooks 安全门禁、afterHooks 检测、promptHooks 认知注入、script 路径对应磁盘文件、blocking 约束

**结论**: 如果项目不使用 OpenCode，这些测试相当于死代码。当前目录存在 `.opencode/plugins/sylph-hooks.ts`，所以有效。但检查较浅（仅 grep 存在性）。

---

## 二、可删除 / 可合并项清单

### 🔴 可直接删除的测试（12 项）

| 行号 | 测试 | 原因 |
|------|------|------|
| ~382 | pretool-edit-scope hook 已移除 | 注释明确写 "hook 已移除" |
| ~656-658 | DG-124 pretool-edit-scope(锚定) hook 已移除 | 注释明确写 "hook 已移除" |
| ~731 | build-validator REMOVED | ROI zero, Oracle approved |
| ~775-776 | compact-detect REMOVED | ROI zero, Oracle approved, skip 占位 |
| ~910-911 | error-dna-auto-fix REMOVED | ROI zero, Oracle approved |
| ~1883 | "跨平台: bash 可用" | 脚本本身就是 bash，100% 存在 |
| ~1886 | "跨平台: python3 可用" | 脚本已依赖 python3 |
| ~1892 | "跨平台: 平台检测" | uname 永远不会失败 |
| ~1907 | "跨平台: COPYFILE_DISABLE" | 环境变量检查，无行为断言 |
| ~1913 | "跨平台: Codex CLI" | 工具安装检查，不在 smoke test scope |
| ~1916 | "跨平台: OpenCode config" | 目录存在检查 |
| ~1919 | "跨平台: VS Code CLI" | 工具安装检查 |
| ~1922 | "跨平台: Python 核心模块" | 脚本已依赖 |
| ~1930 | "跨平台: Python secrets" | 脚本已依赖 |
| ~1934 | "跨平台: git 可用" | git 是项目基础依赖 |
| ~1937 | "跨平台: .git 目录" | 项目结构前提 |

### 🟡 推荐合并的测试（15+ 项）

| 测试 | 合并建议 |
|------|---------|
| 6 个 bash -n 语法检查 | 合并为 1 个 `for hook in ...; do bash -n; done` 循环 |
| 8 个 settings.json/harness.yaml 注册检查 | 合并为 `audit-hooks.sh --check-registry` 调用（脚本尾部已做） |
| pretool-oracle-gate + meta-oracle-trigger | 两者关联性高，建议合并流程测试 |
| 3 个 anti-pattern 测试 | 已比较紧凑，可保留 |
| ED-R 7 个测试 | 可保留，但其中 ED-R-4 和 ED-R-7 几乎一样（都是 governance_bypass）|

### 🟠 与 capability-matrix-test.sh 重复的检查

| 检查项 | cap-matrix 中的位置 | 建议 |
|--------|-------------------|------|
| settings.json/harness.yaml 注册 grep | D1/D2 dimension | 保留 smoke test 的注册检查但使用 audit-hooks 统一入口 |
| hook 语法检查 (bash -n) | D5 | 两处重复，建议 smoke test 取消，交 cap-matrix |
| source mirror 同步 | D8 | 两处都做了，建议统一 |
| validate_skill_refs | D9 | cap-matrix 也检查，可保留任一 |
| .git 目录存在 | env check | 两处都有，建议 smoke test 删除 |

---

## 三、死测试（引用已移除/不存在的 hook 或脚本）

| 行号 | 原测试 | 状态 |
|------|--------|------|
| 382 | pretool-edit-scope 测试 | hook 已移除，仅留下 log 占位 |
| 656-658 | DG-124 pretool-edit-scope(锚定) | hook 已移除 |
| 731 | build-validator | REMOVED, Oracle approved |
| 775-776 | compact-detect | REMOVED, skip 占位 |
| 910-911 | error-dna-auto-fix | REMOVED, Oracle approved |

这些已正确标记为 skip/removed，但占用了 TOTAL 计数器位置（合计约 6 个空占位）。

---

## 四、弱断言组（只检查 exit 0 但不检查输出）

| 测试 | 断言 | 评价 |
|------|------|------|
| pretool-terminal-safety 危险命令放行告警 | 只 check exit 0，不 grep stderr 内容 | 弱 — 应该检查是否有 "告警\|warn" |
| 大部分 run_case 调用（第二个参数 expected_stderr_regex=""） | 只比较 exit code | 中等 — 如果 hook 有逻辑错误，exit code 能发现 |
| posttool-handoff-writer 非 completed 静默退出 | 只 check exit 0 | 弱 |
| posttool-completion-audit 无崩溃 | 只 check exit != 127 | 极弱 |
| posttool-format-gate 不阻断 | 只 check exit != 2 | 极弱 |
| intent-tracker 无崩溃 | 只 check exit 0 | 极弱 |
| ecosystem-probe 无崩溃 | 只 check exit != 127 | 极弱 |
| agentic-ui source 无崩溃 | 只 check 不崩溃 | 极弱 — source 命令本身会执行脚本 |
| pretool-sensitive-edit 编辑普通文件 | 只 check exit 0, stderr 被框架拦截 | 弱 |

**特别差的**:
- line 1633: `(source .claude/hooks/agentic-ui.sh 2>/dev/null && pass ...) || fail ...` — source 一个 hook 脚本会在当前 shell 执行所有代码，相当于在 smoke test 进程中运行 hook，有副作用风险。
- line 1665: `ecosystem-probe.sh` 只检查不是 127（command not found）

---

## 五、pretool-oracle-gate 测试合理性

已有修复（line 1530-1555）：
- 检查 `oracle_gate: true` 是否在 harness.yaml 启用
- 如果禁用则跳过阻断测试（仅检查有上下文注入）
- 有 ACCEPT 裁决时检查二审交互提示

**评估**: 当前实现合理，但有两个问题：
1. oracle-gate.sh 在 hooks 目录存在但测试中未直接调用（用的是 pretool-oracle-gate.sh）
2. "有 ACCEPT 应交互提示" 测试（line 1544）依赖创建 oracle-verdicts.md，该文件路径与实际路径可能有漂移

---

## 六、assertion-collector 测试有效性

line 1575-1584:
- 仅检查 "运行不崩溃"（exit 0）
- 没有检查是否真的记录了 assertion-log.jsonl
- line 1582 执行 `pass` 但没有写文件断言
- 实际 `rm -f .omc/state/assertion-log.jsonl` 在 pass 之后，意味着从未断言文件内容

**结论**: assertion-collector 测试**基本无效** — 只验证脚本不报错退出，没验证核心功能（记录软完成语）。

---

## 七、knowledge-condenser 测试有效性

line 915-983 + 2112-2140:
- 文件存在性检查后执行 5 个测试
- 双格式解析验证（line 942-959）是唯一有价值的 — 检查实际解析
- harness.yaml 开关检查已被尾部 R36 扩展重复（line 2112-2121）
- "语法检查" (bash -n) 是弱断言

**结论**: knowledge-condenser 已在 DG-105 标记为废弃（harness.yaml false）。如果文件被清理，所有测试自动跳过。目前有 ~4 项冗余。

---

## 八、cross-platform 测试完整评估

共 14 项测试（line 1880-1945）：

| 价值 | 测试 | 建议 |
|------|------|------|
| ❌ 0 | bash 可用、python3 可用、git 可用、.git 目录、platform 检测 | 脚本运行前提，无信息量 |
| ❌ 0 | Codex CLI、OpenCode config、VS Code CLI | 工具安装检查，不是功能测试 |
| ❌ 0 | Python 核心模块、secrets | 脚本已依赖 |
| ⚠️ 低 | sed -i '' (BSD) | 只在 macOS 触发，测试 sed 兼容性有一定价值 |
| ⚠️ 低 | COPYFILE_DISABLE | 环境变量检查 |
| ⚠️ 低 | jq 可用 | info 级别 |
| ✅ 中 | 无残留信号文件 | 防止跨会话干扰 |

**建议**: 保留 `sed -i ''` 和 `无残留信号文件`，其余 12 项删除或移到独立的 `scripts/env-check.sh`。

---

## 九、总体统计

| 类别 | 数量 | 占比 |
|------|------|------|
| 总测试计数 | ~212 | 100% |
| ✅ 高质量测试（有内容断言） | ~85 | 40% |
| ⚠️ 中等质量测试（exit code + 基础输出） | ~60 | 28% |
| 🔴 弱断言（仅 exit 0 或 bash -n） | ~25 | 12% |
| ❌ 可删除测试 | ~30 | 14% |
| 💀 死测试（已移除 hook） | ~6 | 3% |
| 🔄 与 cap-matrix 重复 | ~8 | 4% |

### 建议删除汇总（30 项）

#### 立即删除（死代码，16 项）：
1. ❌ `pretool-edit-scope` 占位（line 382）
2. ❌ `DG-124 pretool-edit-scope(锚定)` 占位（line 656-658）
3. ❌ `build-validator` REMOVED（line 731）
4. ❌ `compact-detect` REMOVED（line 775-776）
5. ❌ `error-dna-auto-fix` REMOVED（line 910-911）
6-14. ❌ 9 项无意义 cross-platform （bash/python3/git/.git/Codex/VS Code/OpenCore config/Python modules/secrets）
15. ❌ `agentic-ui source` 测试（line 1633 — `source` 在当前 shell 执行 hook 有风险）
16. ❌ COPYFILE_DISABLE 环境变量检查

#### 建议合并（减少噪声，~14 项→2 项）：
1. 6 个 `bash -n` 语法检查 → 1 个 for 循环
2. 8 个 settings.json/harness.yaml grep → 1 个 `audit-hooks.sh --check-registry` 调用（尾部已有）

#### 需要加强（弱断言变强，8 项）：
1. `pretool-terminal-safety` 应检查 stderr 含告警内容
2. `assertion-collector` 应检查 assertion-log.jsonl 内容
3. `posttool-completion-audit / format-gate / handoff-writer` 应检查 JSON 输出内容
4. `ecosystem-probe` 应提供有效输入而非仅检查不崩溃
5. `agentic-ui` 应以子进程方式测试而非 source

---

## 十、各 R 区块实际测试项总结

| 区块 | 实际测试项 | 质量 |
|------|-----------|------|
| R23 | 8 个新注册 hook 业务验收（lsp-suggest, subagent-guard, posttool-edit-quality, flywheel-report, skill-flywheel, audit-hooks 等） | 中高 |
| R24 | auto-snapshot, completion-gate, inject-project-knowledge, posttool-bash-audit, posttool-write-cite, read-tracker, turn-counter, pretool-user-correction, posttool-edit-quality, flywheel-report, skill-flywheel 等 | 高 |
| R25 | subagent-guard, posttool-subagent-audit | 中高 |
| R26 | audit-hooks --scan-internal-filter | 中 |
| R27 | pretool-rules-inject（L1 注入、空输入安全） | 中 |
| R27b | pretool-rules-inject 空输入 | 中 |
| R29 | context-guard heuristic、token_writer --reset/--increment | 高 |
| R30 | source mirror 关键文件同步 | 中 |
| R31 | session-dump 结构完整性 | 中 |
| R32 | intent-tracker 注册+功能 | 低—中 |
| R33 | validate_skill_refs | 高 |
| R34 | source mirror 扩展（settings+harness） | 低（已废弃）|
| R35 | error-dna-auto-fix REMOVED | 死代码 |
| R36 | knowledge-condenser, AGENTS.md distribution | 低（废弃 hook）|
| R37 | posttool-handoff-writer, pretool-plan-gate | 低—中 |
| R38 | auto-scope, posttool-claim-audit, build-validator | 低—中 |
| R39 | completion-gate quality, error-dna-auto-fix | 低 |
| R40 | ghost/goal mode 降级 | 高 |
| R42-R45 | blast-radius hook（git checkout . 等） | 高 |
| R44 | anti-pattern detection（A2/F1/H1） | 高 |
| ED-R | escape detection（E1/E2/E4） | 高 |
| UX-1.3 | lsp-suggest | 中 |

---

## 关键结论

1. **约 85 项高质量测试**（40%）— 有内容断言、多路径覆盖 — 需保留
2. **可删除约 30 项**（14%）— 死代码或无意义检查 — 建议立即清理
3. **约 25 项弱断言**（12%）— 只有 exit 0 检查 — 建议加强
4. **与 capability-matrix-test.sh 重复约 8 项** — 建议 smoke test 专注运行时行为，cap-matrix 专注静态注册完整性
5. **cross-platform 部分膨胀严重** — 14 项中只 2 项有微弱价值
6. **assertion-collector 测试基本无效** — 从未断言核心功能
7. **knowledge-condenser 测试复杂但 hook 已废弃** — 清理后可大幅简化
