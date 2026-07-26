# CarrorOS — AI 编程代理治理内核

> *"DeepSeek V4 Flash + CarrorOS 用出了以前 Opus-4.6 的感觉。而 Opus-4.6 贵到没法日常用。"*
> — CarrorOS 用户

CarrorOS 是一个**运行时治理层**，架在 AI 编码代理（Claude Code、OpenCode 等）和代码仓库之间。

不是规则文件（AGENTS.md），不是提示词工程——是**物理执行的 hook**，在每次工具调用前和调用后运行。模型绕不过去，因为门禁在操作系统层面执行。

## 一句话

让你用中低阶模型（DeepSeek V4 Flash），得到高阶模型（Opus-4.6）级别的可靠输出。成本是前者的，质量是后者的。

## 核心能力

| 能力 | 实现 |
|------|------|
| **运行时强制** | 16+ Python hook 通过 settings.json 注册，PreTool/PostTool 执行 |
| **虚假完成拦截** | completion-gate 5 维证据评分 + 双源验证 + 软完成语检测 |
| **目标漂移防御** | E4 惯性升级链：NARROW → REDIRECT → BLOCK（同一错误 3 次即升级）|
| **幻觉审计** | posttool-claim-audit file:line 溯源 + G1 数值断言 |
| **知识引擎** | error-dna → retry-budget → claude-next → 飞轮升华闭环 |
| **安全门禁** | 敏感文件保护、危险命令拦截、输出脱敏、不可逆操作人工审批 |
| **生命周期管理** | precompact 快照 + handoff 一致性 + session 恢复 |
| **双模型 Oracle** | 59 场对抗场景全覆盖 + 6 类判决统一 verify_contract |

## 评分

Opus-4.8 + GPT-5.6Sol 独立外评 31 维度：**9.0 / 10**（Δ=0 双模型一致）

- 151 场对抗测试全绿
- 42/42 回归套件全绿
- 3 条端到端生产 trace 闭环
- 59 文件 SHA256 证据链可追溯

## 架构

```
AI Agent (CC/OC)
    │  PreToolUse → hook-launcher → pretool-gate (14 门合一)
    │                → pretool-scorecard-gate
    │                → pre-completion-gate (TaskUpdate)
    ▼
  [工具执行]
    │  PostToolUse → posttool-claim-audit
    │                → posttool-bash-audit
    │                → completion-gate
    │                → posttool-sensitive-filter
    │                → error-dna
    ▼
  治理日志 (error-dna / flywheel / handoff)
```

## 快速开始

```bash
# 看当前状态
python3 .claude/scripts/carros_base.py status

# 跑全量回归
bash scripts/run-regression.sh

# 初始化任务
python3 .claude/scripts/carros_base.py init --task-id my-task

# 查看当前任务状态
python3 .claude/scripts/carros_base.py tick

# 验证完成证据
python3 .claude/scripts/carros_base.py verify

# 归档任务
python3 .claude/scripts/carros_base.py archive
```

## 哲学

验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少

治理不是越多越好。CarrorOS 的每个 hook 都要回答"没有它会出什么事"——答不出来的，不装。
