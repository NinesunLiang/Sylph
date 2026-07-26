# CarrorOS — AI 编程代理治理内核

> *"DeepSeek V4 Flash + CarrorOS 用出了以前 Opus-4.6 的感觉。而 Opus-4.6 贵到没法日常用。"*
> — CarrorOS 用户

## 它解决了什么

低成本模型（DeepSeek V4 Flash）原本只能做简单短任务。长了就偏、偏了就丢、丢了就得人从头来。

CarrorOS 用三件事改变了这一点：

### 1. 任务磁盘化 + Token 磁盘化

模型有上下文窗口限制，但 CarrorOS 没有。

任务文档、计划、证据全部写磁盘。compact 不丢。新会话能续接。DeepSeek 的上下文只装当前这一步——前后文都在磁盘上。

之前只能做短任务 → 现在能做完整的、需要多轮迭代的长任务。

### 2. 工作流让每个任务完整闭环

DeepSeek 本身容易"做着做着偏了"或者"说做完了其实没做"。

CarrorOS 通过 gate 强制执行闭环：**init → tick → execute → verify → archive**。每步有证据、有验证、有审计。偏了会被拦回来，没做完的不会被放过去。

不是靠模型的自觉，是工作流在执行层面做保证。

### 3. AI 自决策

不需要用户每一步都确认为什么这么做。

一句话下去，AI 自己规划、自己执行、自己验证、自己闭环。CarrorOS 提供护栏——在护栏内模型自由发挥，不傻等人工审批，不每一步都停下来问人。

## 核心机制

| 机制 | 作用 |
|------|------|
| **运行时 hook**（16+ 门禁） | 每次工具调用前后物理执行，模型绕不过 |
| **证据强制验证** | 完成声明必须有 file:line / 测试证据 / VERIFIED 标记 |
| **错误记忆（error-dna）** | 94 条真实错误签名，同一错犯 3 次升级阻断 |
| **飞轮升华** | 发现新模式 → 自动生成规则 → 下次自动命中 |
| **双模型 Oracle** | 59 场对抗场景全覆盖，6 类判决统一 |
| **生命周期** | compact 不丢状态，跨会话续接无缝 |

## 评分

Opus-4.8 + GPT-5.6Sol 独立外评 31 维度：**9.0 / 10**（Δ=0 双模型一致）

151 场对抗全绿 · 42/42 回归全绿 · 3 条生产 trace 闭环 · 59 文件 SHA256 可追溯

## 哲学

验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少

每个 hook 都要回答"没有它会出什么事"——答不出来的，不装。

## 快速开始

```bash
status       python3 .claude/scripts/carros_base.py status
init         python3 .claude/scripts/carros_base.py init --task-id <name>
tick         python3 .claude/scripts/carros_base.py tick
verify       python3 .claude/scripts/carros_base.py verify
archive      python3 .claude/scripts/carros_base.py archive
regression   bash scripts/run-regression.sh
```
