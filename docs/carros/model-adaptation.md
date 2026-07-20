# 模型适配指南 — 高阶模型

> 适配 gpt-5.5+ / sonnet-4.6+ / opus-4.6+ / grok-4.5+ / glm-5.4+ 高阶模型
> 支持平台：Claude Code + OpenCode
> 本文基于 settings.json + settings_ds.json + settings_k3.json 的实践经验沉淀

---

## 目标

高阶模型（200K+ 上下文、多 step reasoning、复杂 tool calling）与当前 deepseek-v4-flash 在以下方面存在差异，需要针对性适配：

| 维度 | deepseek-v4-flash（当前默认） | 高阶模型 |
|:----|:----------------------------|:---------|
| 上下文窗口 | 64K | 200K~1M |
| 工具调用 | 基础，单轮 tool use | 多轮 tool use，并行 tool call |
| subagent 路由 | 仅 flash | opus/sonnet/haiku 三级路由 |
| compact 策略 | 激进 compact 为主 | 大窗口下可延迟 compact |
| 模型切换成本 | 无（始终同模型） | 需考虑 cost/quality 平衡 |
| fallback 策略 | 不降级即失败 | 支持 fine-grained fallback |

## 支持的模型版本

| 模型 | 系列 | 供应商 | 最小版本 | 推荐版本 | 上下文 | 特点 |
|:----|:-----|:-------|:--------|:--------|:------|:-----|
| GPT | GPT-5.5+ | OpenAI | gpt-5.5 | gpt-5.5 | 256K | 综合最强，tool use 稳定 |
| Sonnet | sonnet-4.6+ | Anthropic | sonnet-4.6 | sonnet-5 | 200K | 编程/代码推理最优 |
| Opus | opus-4.6+ | Anthropic | opus-4.6 | opus-4.8 | 200K | 架构/设计最佳 |
| Grok | grok-4.5+ | xAI | grok-4.5 | grok-4.5 | 256K | 长上下文，分析推理强 |
| GLM | glm-5.4+ | 智谱 AI | glm-5.4 | glm-5.4 | 256K | 国内合规，中文任务优 |

## 配置方式

### 方式 A：通过代理转发

当前架构使用 port 8765 代理（已在 settings.local.json 中验证），统一转发到各模型 API：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8765",
    "ANTHROPIC_AUTH_TOKEN": "<proxy-token>",
    "ANTHROPIC_MODEL": "<model-name>"
  },
  "model": "<model-name>"
}
```

已验证的模型映射（通过代理）：

| settings.json `model` | 代理转发的实际模型 | 备注 |
|:---------------------|:-----------------|:-----|
| `gpt-5.5` | gpt-5.5 | 已验证 Messages API + Tool Use |
| `sonnet-5` | sonnet-5 | 已验证 Messages API + Streaming |
| `gemini-3.5-flash` | gemini-3.5-flash | 已验证兼容 |
| `deepseek-v4-flash` | deepseek-v4-flash | 当前默认 |

### 方式 B：Claude Code 原生（仅适配制/Official API）

如果直接使用 Anthropic/OpenAI Official API，配置方式不同：

**Anthropic Official（sonnet/opus）：**
```json
{
  "model": "sonnet-5",
  "apiUrl": "https://api.anthropic.com",
  "authToken": "sk-ant-..."
}
```

**OpenAI Official（gpt-5.5）：**
需要额外 OpenAI 兼容层（如 cc-switch 或 openai-to-anthropic-proxy），因为 Claude Code 原生要求 Anthropic Messages API 格式。

### 方式 C：OpenCode

OpenCode 原生支持多种模型供应商，无需 Anthropic 兼容层：

**opencode/carroros.json 中的模型配置示例：**
```json
{
  "model": "gpt-5.5",
  "provider": "openai",
  "apiKey": "sk-..."
}
```

更多 OpenCode 模型配置参考其官方文档。

## 推荐的模型用法矩阵

按任务等级推荐：

| 任务类型 | 推荐模型 | 原因 |
|:--------|:--------|:-----|
| 日常开发 / 单文件修复 | gpt-5.5 / sonnet-5 | 性价比最高，编程强 |
| 架构设计 / 跨模块重构 | opus-4.8 | 复杂推理需要 deep thinking |
| 代码审查 / Audit | opus-4.8 / gpt-5.5 | 审查精度要求高 |
| 长文档总结 / 长上下文 | grok-4.5 / glm-5.4 | 大窗口 + 长程分析 |
| Oracle 复核 | opus-4.8 / grok-4.5 | 需要独立高精度判断 |
| 中文任务 / 国内部署 | glm-5.4 | 中文协议兼容性最好 |

## 约束与注意事项

### 1. settings.json 的 model 字段约定

```json
{
  "model": "gpt-5.5",
  "env": {
    "ANTHROPIC_MODEL": "gpt-5.5"
  }
}
```

- Claude Code 的 `model` 字段 = 主模型
- `ANTHROPIC_MODEL` env = 传递给 CC proxy 的模型名，必须与 `model` 一致（否则 CC 内部使用 `model` 而 API 使用 `ANTHROPIC_MODEL`，导致不一致）
- `CLAUDE_CODE_SUBAGENT_MODEL` = subagent 模型（支持 opus/sonnet/haiku 三级）

### 2. 高阶模型的 SubAgent 配置

高阶模型支持 Claude Code 原生的三级 SubAgent 路由：

```json
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet-5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "opus-4.8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "sonnet-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.5"
  }
}
```

### 3. 高阶模型的 Compact 策略

大上下文模型（200K+）不需要高频 compact：

| 上下文水位 | 建议动作 |
|:-----------|:---------|
| < 60% | 不处理（高阶模型可容纳更大窗口） |
| 60-75% | 选择性 compact（压缩 less relevant 部分） |
| 75-85% | 主动 compact |
| > 85% | 写 handoff + 强制 compact |

修改 `.claude/harness.yaml` 中的 compact_interval：

```yaml
hooks:
  pretool-compact-writer:
    enabled: true
    compact_interval: 30  # 高阶模型从 15 提升到 30
```

### 4. 高阶模型的 fallback 策略

高阶模型成本高、响应慢，fallback 阈值需调整：

```yaml
fallbacks:
  - trigger: "oracle_slow_3x"
    condition: "oracle_rtt_3x_avg > 60000"  # 从 30s 放宽到 60s
  - trigger: "parse_error_3x"
    condition: "consecutive_parse_errors >= 5"  # 从 3 放宽到 5
```

### 5. 防止误使用 Opus/Sonnet 的 guard

高阶模型 token 成本高，需要明确的 cost guard：

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "524288"  // 高阶模型可用更大窗口
  }
}
```

## 迁移指南：从 deepseek-v4-flash 切换到高阶模型

### Step 1：备份当前 settings.json

```bash
cp .claude/settings.json .claude/settings.bak.deepseek.json
```

### Step 2：更换 settings.json 中的 model

从：
```json
{
  "model": "deepseek-v4-flash",
  "apiUrl": "http://127.0.0.1:9998",
  "authToken": "test"
}
```

改为：
```json
{
  "model": "sonnet-5",
  "apiUrl": "http://127.0.0.1:8765",
  "authToken": "<proxy-8765-token>"
}
```

### Step 3：验证连接

```bash
curl -s -X POST http://127.0.0.1:8765/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{"model":"sonnet-5","max_tokens":50,"messages":[{"role":"user","content":"say hi in 3 words"}]}'
```

### Step 4：更新 subagent 路由（可选）

```json
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet-5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "opus-4.8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "sonnet-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.5"
  }
}
```

### Step 5：更新 harness.yaml 配置（可选但推荐）

- `compact_interval`: 15 → 30（高阶模型可承载更大上下文）
- fallback timeout: 30s → 60s（高阶模型响应时间较长）

## 遗留配置参考

以下配置保留为历史参考，不做功能性修改：

| 文件 | 原用途 | 适配状态 |
|:----|:------|:---------|
| `settings_ds.json` | deepseek-v4-flash 备用配置 | 与 settings.json 一致，保留参考 |
| `settings_k3.json` | kimi-k3 备选配置（通过 moonshot 代理） | 保留参考，不适配高阶模型 |

### settings_ds.json

与 settings.json 配置一致（deepseek-v4-flash + port 9998），用于低成本执行任务、L1 日常开发。如需切换回 deepseek，将其内容复制到 settings.json。

### settings_k3.json

kimi-k3 备选（通过 `api.moonshot.cn/anthropic` 兼容层），模型名设为 `opus` 但实际走 kimi-k3。因 kimi-k3 不支持复杂 tool use 和多轮 subagent 路由，仅保留参考。

## 验证清单

切换到高阶模型后，逐项验证：

- [ ] `curl -s http://127.0.0.1:8765/v1/models` 返回所选模型
- [ ] `curl -s -X POST http://127.0.0.1:8765/v1/messages` 正常返回（Messages API 兼容性）
- [ ] Tool Use 正常（调用带 `tools` 参数的消息）
- [ ] SubAgent 路由正常（检查 `CLAUDE_CODE_SUBAGENT_MODEL`）
- [ ] CarrorOS 所有 hooks 正常工作
- [ ] compact 水位管理正常（compact_interval 调整后无异常）
- [ ] fallback 降级正常触发（模拟 oracle 超时、parse error 等）

## 附录：模型版本对照表

| settings.json model 值 | 供应商 | Claude Code 内置路由 | 代理兼容 |
|:-----------------------|:-------|:--------------------|:---------|
| `gpt-5.5` | OpenAI | 不原生支持（需代理） | 已验证 |
| `sonnet-5` | Anthropic | 原生支持 | 已验证 |
| `opus-4.8` | Anthropic | 原生支持 | — |
| `grok-4.5` | xAI | 不原生支持（需代理） | 理论可行 |
| `glm-5.4` | 智谱 | 不原生支持（需代理） | 理论可行 |
| `deepseek-v4-flash` | DeepSeek | 不原生支持（需代理） | 已验证（当前默认） |
| `kimi-k3` | Moonshot | 不原生支持（需代理） | settings_k3.json 参考 |
| `gemini-3.5-flash` | Google | 不原生支持（需代理） | 已验证 |
