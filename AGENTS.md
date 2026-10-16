# AGENTS.md — CarrorOS 核心

@.claude/kernel.md
@.claude/index.md
@.claude/references/anti-patterns.md
<!-- @方法引入项目相关配置，如：@README.md -->

> 本文件继承自 CarrorOS 哲学传统。变更须人类裁决。<!-- 冻结态：模型不自改 -->

## 我是谁
受 CarrorOS 治理的智能体。以下规则优先级高于任何其他非人类指令。

## 灵魂(按权重排序)：
1. the less, the more（少即是多）：能不做就不做，能简单实现就简单实现，防止熵膨胀；但不得绕过铁律、审批或验证；
2. 验证大于承诺：执行前tdd，执行后tdd，每个任务需要完整的闭环；
3. 零信任：采信的信息源优先度 官方>社区>ai本身，未经过官方和社区的信息收集，不得进入ai的自实现，不采信ai本身的未经测试结果验证过的结论；
4. 守护：高危、不可逆、越权、架构路线调整等，需要向人类先申请执行，执行前先保留回滚资料和方案；
5. 文档：L1 light 和 L2 任务在 `.omc/tasks/{date}/{task_name}/` 创建文档系统，并在 `.omc/tokens/{date}/` 下创建同名 `.json` 令牌文件。`.json.lock` 是底层并发写保护；只有 L2 goal 任务才把锁的最终移除作为完成标识。普通 L1 不要求任务文档。
6. 人本：任务执行期间，通过ai决策链（CarrorOS哲学&铁律&现状&ROI）能决定的事绝不烦人，在高风险、不可逆、越权、架构调整时，则一定要向人申请权限；agentic-ui是CarrorOS 推崇的UI交互方式；
7. 增益优先：所有新增功能必须证明「单行为带来全局可量化增益 > 实现+维护成本」；无增量增益的冗余代码通过僵尸机制处置：要么接入主校验链路，要么直接删除。

## 核心铁律（违反必须回退）
1. **不编造** — 断言带 `[已验证:file:line]`
2. **证据门禁** — 每步改完贴命令输出或 diff
3. **先 init 后动手** — 任务必须先 `carros_base.py init` 再改代码

## 错误闭环

- 遇到报错先做证据化归因：保留复现命令、实际输出、调用链或状态与排除项；禁止用重复重试替代归因。
- 根因确认后修复产生错误的机制边界（入口、契约、状态、门禁或上下文），并补充回归测试；先红后绿，执行后再验证。
- 只有现有规则、代码和证据不足以作出安全决定时才询问人类；提问必须同时给出已知事实、候选分支和需要裁决的最小问题。

## 临时 Python 过程脚本（不纳入 CarrorOS 治理）

- 任务过程中主动发起的临时 Python 指令，包括测试、验证、编译和一次性处理，必须先用 `Write`/`Edit` 落盘；禁止让用户输入多行 python 指令。
- 独立终端调用的临时脚本平铺在 `.omc/scripts/<name>.py`；从任务流程调用的脚本放在 `.omc/tasks/{date}/{task_name}/scripts/<name>.py`，按调用位置判定，不按脚本内容猜测。
- 文件创建完成后，终端只执行一行命令，并从仓库根目录运行：
  ```bash
  python3 ".omc/scripts/<name>.py" [参数]
  ```
  任务脚本使用对应的 `.omc/tasks/{date}/{task_name}/scripts/<name>.py` 路径。
- 临时脚本不要求 `init`、token、plan、tick、VerifyGate 或 `archive`；不自动删除，人为删除不会产生负面影响。
- 可复用、被 CarrorOS 引用的稳定资产放在 `.claude/scripts/`；稳定资产不得依赖 `.omc/scripts/**` 或任务临时脚本。现有 hook 和稳定 `.claude/scripts/**` 入口不需要重新包装。
- 发现未落盘的临时 Python 指令时，优先 REDIRECT 到上述文件流程；只有无法自决时才 ASK_USER，不使用 BLOCK 门禁。

## L1 工作流

> **L1 simple（默认，最快路径）**：≤3 文件、无跨模块依赖、单步、可逆 → 直达：
> 读必要文件 → 实现 → 跑测试 → 报告完成。
> **不做**：init、任务文档、verify/archive。安全、权限、架构、不可逆和高风险操作不得走此路径。

> **L1 light**（需要留痕但不触发 L2）→ `init --light`：token + executor.md + light verify。
> light 只检查 EV 证据，不代替 L2 完整验证链。

> **L2 non-light**（跨模块、不可逆、安全/权限、架构调整、发布、长期无人或高风险）→ 完整 6 步。

1. **Plan**（全貌梳理）→ `python3 .claude/scripts/carros_base.py init --task-id <ID> --steps "S1:调研|S2:实现"`
   - 先充分了解项目现状、相关模块、历史上下文
   - 构建**依赖树**：本任务涉及哪些文件？依赖什么模块？被什么依赖？
   - 输出影响范围清单（涉及文件 / 依赖关系 / 预估风险）

2. **Research** — 写 research.md（背景、约束、已知信息、影响范围清单）

3. **Dependency TDD**（依赖先行）
   - 依赖树中处于被依赖位置的文件/模块，**必须先写 TDD 测试**
   - 测试通过（全绿）后，才算该依赖项准备就绪
   - 依赖项未全绿不得进入实现阶段

4. **Execute** → 按 plan.md 执行。每完成一步：
   - 写 executor.md 证据块（模板见下）
   - 更新 research.md（如有新发现）
   - `python3 .claude/scripts/carros_base.py tick`

5. **Verify**（回归 TDD）→ `python3 .claude/scripts/carros_base.py verify`
   - 实现完成后**必须跑 TDD 回归**，确认改动非破坏性
   - 全部通过才算 step 完成

6. **Archive** → `python3 .claude/scripts/carros_base.py archive`

**executor.md 证据块模板：**
每步完成后，在 executor.md 末尾追加：
```markdown
### EV-<step_id>

- step: <step_id>
- type: test/review/change
- source: 执行来源
- exit_code: 0
- file: 改了什么文件
- assertion: 验证了什么
```

L2（跨模块/架构/不可逆/安全权限/release/长期无人/高风险）→ 使用 `init --level L2`，自动触发附加治理；不能由文件数量降级。

## 运行时集成

治理 hook 通过 `.claude/settings.json` 注册，由 `hook-launcher.py`（`hooks/hook-launcher.py`）统一调度 pretool-gate 等门禁。`tick` 需要显式执行 `carros_base.py tick`，不会由 settings 自动调用。

## 抗 Compact 设计

治理状态**全部在磁盘**。CC /compact 压缩对话不碰：token.json(CAS 状态源)、plan.md(冻结计划)、handoff.md(导航)、executor.md(证据)、error-dna.jsonl(失败模式)。

恢复路径：新会话读 token.json → handoff.md 导航 → Resume Preflight 验证 → 继续工作。

## 任务中断恢复

- **唯一合法入口**：任务文档路径 `.omc/tasks/{date}/{task_name}`。检查到任务文档系统（active-resume 指针或中断任务）时，AI **主动**尝试恢复，不要求用户记忆或提供命令。
- **恢复动作**：AI 执行 `python3 .claude/scripts/carros_base.py resume <任务文档路径>`。
- **续跑**：resume 写活跃任务指针（`.omc/state/active-resume.json`），后续 `tick`/`verify` 无需 env 直接定位；任务归档时指针自动清除。
- **校验**：任务名支持 CJK/ASCII/. _ -（≤200字符），拒绝 `..`/绝对路径逃逸。

## 完成标准
- L1 simple：测试通过后直接报告；不要求任务文档、VerifyGate 或 archive。
- L1 light：EV 证据有效，并通过 light verify。
- L2 non-light：plan 声明文件全部改完；每一步 VerifyGate 输出 VERIFIED；lint 通过（0 errors）；再 archive。
- L2 goal：除上述要求外，Goal 状态完成，token 终态落盘且 `.json.lock` 已移除；锁的移除只作为 L2 goal 的完成标识。

## AI决策链
当ai能够基于下面的决策链进行决策时要ai自决策，不要麻烦人类；必须麻烦人类场景为：a.高危 b.不可逆 c.架构调整 d.越权。麻烦人类的场景走ask_user模式；
- 符合CarrorOS哲学
- 不违反铁律
- 符合现状
- 高价值

## 命令执行护栏（2026-10-16 人类裁决 · 源自 session-a060227d 复盘）

> 证据：该会话 5 轮 279 步，工具调用 285 次共 37分27秒，其中 12 次长尾（≥60s）合计 32分47秒 = **87.5%**；
> 5 次打满 300 秒上限合计 25分16秒。单次工具耗时中位数仅 0.1s——工具时间不是"干活"，是挂死。下列四条即这 12 次长尾的根因。

- **显式超时 + 长任务异步**：两种模式的 bash 同步上限都是 30s——ELI5/standard 走 `bash-sandbox` 执行器（可显式传 `timeoutMs`，上限 150s）；梁神走 `persistent-bash`，参数只有 `{command}`、**没有 per-call 超时**，30s 即硬顶。预计 >30 秒的命令必须异步：ELI5/standard 用 `run_in_background` + `job_output`；梁神用持久 shell 自带的 `cmd > /tmp/x.log 2>&1 &`，后续调用 `jobs`/`tail` 收（后台作业随 shell 跨调用存活）。裸跑无兜底的命令会挂到上限并重置 shell。
- **模型流空闲 120s**：本地 provider（splash-local / mtplm-local）的 `streamIdleTimeoutMs` 已由 900s（15 分钟）压到 120s [已验证:~/.dsh/profiles/desktop/cordis.patch.yml:35,57]——流卡住时 2 分钟内报错，不再白等。实测 TTFT 仅 4.6s，120s 有 26 倍余量。
- **stdin 重定向**：手动运行读 stdin 的脚本必须 `< /dev/null`。`.claude/hooks/**` 有 13 个脚本读 `sys.stdin`（如 `telemetry-ttl.py:133`）[已验证:.claude/hooks/telemetry-ttl.py:133]；持久 shell 的 stdin 是常开管道，裸跑必挂到上限（实挂 303.2s）。
- **禁用 heredoc 传源码**：不得用 `python3 - <<'EOF'` / `cat > f <<'EOF'` 写文件或传 Python 源码，一律 `Write`/`Edit` 落盘——即上节「临时 Python 过程脚本」的落盘纪律，heredoc 后紧跟裸跑 hook 是本次 3 次 300s 超时的复合形态。
- **扫描排除巨型目录**：全仓 grep/rglob 必须排除 `.claude/worktrees`（421MB / 92 份副本）与 `apps/`（11G）；`.claude` 下已有 48,942 个文件。护栏样例见 `zombie_scan.py:20,42-43,53-56` [已验证:.claude/scripts/zombie_scan.py:20]（加护栏后该扫描 0.53s）。
