<!-- PROJECT: Carror OS -->

<!-- DATE: 2026-05-17 -->

# 代码执行内核（kernel.md）

> 本文件是 AI 执行内核 — 写代码前必读，冻结后不可随意扩展

## ⚖️ 宪法冻结声明
本文件作为 **AI 执行内核（Kernel）**：
- ✅ 不再新增行为铁律、Gate 类型
- ✅ 所有新经验默认进入 `.claude/claude-next.md`，验证稳定后可升华到此文件

---

## 架构铁律
<!-- 由 R17 审计填充 @2026-05-07 -->
- **双域架构**：harness-kit（内核层/治理） + lx-skills-v5（能力层/工程），严格按 domain 划分职责
- **Hook 不可失败**：所有 `hooks/*.sh` 禁止 `set -e`，必须 `exit 0` 或 `echo '{"continue": true}'` 结尾
- **hc_enabled 门禁**：每个 Hook 脚本必须通过 `hc_enabled "feature_name" || exit 0` 读取 yaml 开关
- **最大修复上限**：同一问题最多修 3 轮，超过则 BLOCKED 升级用户
- **harness.yaml 整数类型**：涉及 bash 整数比较（`[ "$VAL" -lt "$THRESHOLD" ]`）的配置值必须用整数。0-100 百分比刻度用 `60` 而非 `0.6`。浮点数导致 bash `[` 静默失败。（升华自 DG-54）
- **发行包路径脱敏**：开发机绝对路径（`/Users/xxx/...`）禁止进入 `packages/`。`package-release.sh` 打包前替换为 `__PROJECT_ROOT__` 占位符，`install.sh` 安装时替换为用户实际路径。（升华自 DG-31）

## 命名强制规则
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Hook 脚本**：snake-case（`context-guard.sh`、`completion-gate.sh`），与 harness.yaml key 保持连字符一致
- **Python 脚本**：snake_case（`context_monitor.py`、`oma_lock_manager.py`）
- **Skill 目录**：`lx-` 前缀（`lx-oma-split`、`lx-code-review`），SKILL.md 主文件
- **YAML key**：snake_case（`hooks_enabled.completion_gate`），与脚本调用一致
- **版本号**：始终 `6.3.0` 格式，唯一真相源 `VERSION.json`

## 错误处理铁律
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Hook 永不阻塞**：任何失败必须 `exit 0` 或 `echo '{"continue": true}'` + `exit 0`
- **证据门禁优先**：错误修复后必须提供 VERIFIED 证据再标 completed
- **Error DNA 捕获**：Bash 错误自动记录至 `error-dna.jsonl`，使用 `error_classifier.py` 分类
- **修复 3 轮上限**：每轮记录根因假设，第 3 轮仍失败 → BLOCKED 升级
- **禁止绕过门禁**：permission-gate/sensitive-edit 阻断时必须等待用户明确授权。AI 不得代用户批准或自行写入批准标记（R42 安全漏洞修复）
- **对话内批准（DG-125）**：permission-gate 阻断时 AI 不要求用户切终端。在对话中输出以下格式：

  ```
  ⚠️ Dangerous command requires approval:
  <被阻断的命令>
  Reason: <危险类型，如 destructive/git push/sudo/gh write>
  Reply /approve <token> to execute, /deny to cancel.
  ```

  用户回复后 AI 行为：
  - `/approve <token>` → `pretool-approve-detect.sh` 自动写入 `permission-approved` → 重试原命令（5分钟缓存）
  - `/deny` → 放弃，报告用户
  - 禁止要求用户去终端粘贴 token
- **原生批准优先**：敏感文件编辑优先使用 `permissionDecision: ask` 原生对话框，/approve 对话内机制作为回退
- **关键脚本修改前备份**：修改 permission-gate.sh / settings.json 等关键治理文件前必须 `cp file file.bak`，修改后必须 `bash -n file` 语法检查。这些文件损坏 = 全 Bash 被封 = 无法自救。（升华自 DG-13, DF-04）

## 测试要求
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Harness Smoke**：修改 hook 后必须通过 `harness-smoke-test.sh`（动态计数，全绿为 pass）
- **Hook 生产验证**：`hook-production-verify.sh`（动态计数，全绿为 pass）覆盖所有 gate 场景
- **OMA Lock 测试**：修改锁逻辑后必须运行 `test_oma_lock.py`
- **版本审计**：修改版本号后必须运行 `audit-hooks.sh` 确认三方对齐
- **安全正则格式覆盖**：涉及安全门禁的正则表达式必须测试 ≥4 种路径格式：裸文件名(`AGENTS.md:42`)、相对路径(`./src/main.go:15`)、绝对路径(`/Users/x/project/file.go:42`)、点路径(`.claude/hooks/foo.sh:15`)。（升华自 DG-29）

## 禁止行为
<!-- 由 R17 审计填充 @2026-05-07 -->
- 禁止在 Hook 脚本中设置 `set -e`（会阻断工具调用）
- 禁止 `eval`（当前 0 处，保持零容忍）
- 禁止未引用 `file:line` 的技术断言（铁律 #1）
- 禁止在报告中混合自创指标与行业标准（铁律 #7）
- 禁止在 `for x in $VAR` 中使用未加引号变量（R24 教训）
- 禁止 `json.load → str.replace → json.dump` 管道修改含转义字符的治理文件。JSON dump 会损坏嵌套引号。用 sed 纯文本替换。（升华自 DF-04, DG-12）
- 禁止 `$(grep -c pattern || echo 0)` 模式 — `grep -c` 输出 "0" 并 exit 1，`|| echo 0` 追加第二个 "0"，产生双输出 `"0\n0"` 导致整数比较失败。正确做法：`VAR=$(grep -c pattern 2>/dev/null); VAR="${VAR:-0}"`。（升华自 DG-36）
- 禁止 `sed -i` 使用未验证非空的变量作为行号 — `LINE=$(grep -n 'pattern' file | head -1 | cut -d: -f1)` 返回空 → `sed -i '' "${LINE}i\\..."` 空行号插入导致文件全毁。任何 sed -i 行号操作前必须 `[ -n "$LINE" ] || { echo "FATAL"; exit 1; }`。（升华自 DG-68）
- 禁止在 macOS sed 中使用 `\\+` 量词（POSIX BRE 不兼容）— `\\+` 在 macOS 被解释为字面加号而非量词。跨平台脚本必须用 `sed -E` 启用 ERE，或改用 `[0-9][0-9]*` / `\\{1,\\}` 等 POSIX 兼容写法。（升华自 DG-77）

## 三模式文档路径

> 三种无人巡航模式各自有独立的文档路径约定，不可混用。

| 模式 | 根路径 | 信号文件 |
|------|--------|---------|
| **goal/ghost** | `.omc/state/{plan\|task\|test\|token}/{date}/{feature}/` | `.omc/state/tokens/lx-goal.json` |
| **rpe** | `rpe/{feature}/` | 无独立信号文件 |
| **oma** | `main_prd/{sub_prd}/{feature}/` | `.omc/state/tokens/autonomous.active` |

- **goal/ghost 模式**：每个 feature 在 `{plan|task|test|token}` 四类子目录下各自存储
- **rpe 模式**：直接位于 `rpe/{feature}/`，无日期层级
- **oma 模式**：`main_prd`（单数），不是 `main_prds`
- **信号文件**：统一存放在 `.omc/state/tokens/` 子目录下，不在 `.omc/state/` 根目录

> ⚠️ **违禁路径**：`prd/`、`sub-prds/`、`rpe/feat-*`（已废弃）

## 无人值守模式：正式阶段

> 三种无人巡航模式各有固定阶段结构。AI 在进入对应模式后必须按阶段执行，不可跳阶段。
>
> **核心规则**：无人值守模式下，决策链 L4（权限/风险/路线/资源）截断为「记录↷跳过」，不穿透到人。

### Goal 模式（目标驱动，有明确终点）

```
Phase 0: 澄清窗口
  → 人确认目标，plan/prd 起草
  → 用户可在这个窗口提问/纠偏
  → lx-goal phase0-done → 方案通过门禁（pretool-plan-gate）
  → 代码变更解锁，进入自主执行

Phase 1-∞: 自主执行
  → 决策链 L1→L2→L3 逐层消化
  → L4（权限/风险/路线/资源）截断为记录↷跳过
  → 子命令: task-done / skip-risk / hard-boundary-hit / blocked-human
  → 3 轮修复上限，超过则 BLOCKED

Phase ∞∞: 退出
  → lx-goal report → 生成汇总报告
  → lx-goal off → 清理信号文件，恢复 hook 正常阻断
```

### Ghost 模式（方向驱动，开放式探索）

```
Phase 0: 澄清窗口
  → 人确认探索方向
  → 不限定时限，方向感驱动

Phase 1-∞: 持续探索
  → 阅读→记录→发现→深入（无固定任务清单）
  → 不追求"完成"，追求"发现"
  → 中断时自动生成探索笔记（posttool-handoff-writer）
```

### RPE 模式（任务驱动，有 Executor）

```
Executor 阶段:
  → 读 rpe/{feature}/executor.md（任务清单）
  → 串行逐任务执行：读→改→验收→标记 [x]
  → 每步独立验收，失败不阻塞其他任务
  → 全部完成后关闭 RPE
```

### 口头进入无人模式

> 用户口述"自己搞定 / 不用问我 / 全自动做完 / 你看着办"等表达 → 等同于激活 Goal 模式。

```
用户口述 → AI 提取目标 → lx-goal on "{目标}" → 进入 Phase 0
```

> ⚠️ 口头进入的 Phase 0 窗口极短——AI 应快速确认目标后直接 phase0-done，不给用户造成"还需要确认"的感觉。

---

## 有人值守模式

> 与无人值守相反——决策链 L4 **必须穿透到人**。人实时在场，升级即打断。

| 模式 | 任务规模 | L4 行为 | 文档路径 |
|------|---------|---------|---------|
| **ToDo** | 小型（单步/明确修复） | 穿透打断 | `.omc/state/todo-queue.md` |
| **Task-spec** | 中型（多步/需规划） | 穿透打断 | `.omc/state/tokens/lx-goal.json`（Phase 0 后人介入） |
| **标准交互** | 默认 | 按需打断 | — |

```
ToDo（小型）:
  用户说"修一下 X" / "加上 Y" → 单步执行 → L4 穿透到人确认

Task-spec（中型）:
  Phase 0: 方案起草 → 人审阅批准
  Phase 1-∞: 逐步执行 → 每步 L4 穿透
  Phase ∞∞: 人验收
```

### 无人 vs 有人：决策链 L4 行为差异

| | 无人值守 | 有人值守 |
|---|---------|---------|
| L1 AI判断 | 执行 | 执行 |
| L2 静态分析 | 执行/warn-only | 执行/BLOCKED |
| L3 运行时 | Oracle 审核 | Oracle 审核 |
| **L4 权限/风险/路线/资源** | **记录↷跳过** | **穿透打断 → 人裁决** |
