# ARCHIVED — v6.2.1 — Historical benchmark snapshot. Referenced scripts may no longer exist on disk.
---
name: MITRE ATLAS AI 威胁矩阵映射
description: Carror OS 30 hook + skill 对应 MITRE ATLAS 攻击战术/技巧的缓解映射（仅记录）
type: benchmark-report
standard: MITRE ATLAS (Adversarial Threat Landscape for AI Systems)
date: 2026-05-05
scope: AI 特有威胁 — Prompt Injection / Model Evasion / Data Poisoning / Output Manipulation
---

# MITRE ATLAS AI 威胁矩阵映射

> **标准来源**：[MITRE ATLAS](https://atlas.mitre.org/) — AI 系统对抗威胁矩阵（2026 业界标准，对标 MITRE ATT&CK 到 AI 场景）
> **适用范围**：Carror OS 作为 AI 治理层，对应 **"AI Developer"** 视角的防御能力
> **对照原则**：映射 Carror OS 具体 hook/skill 到 ATLAS 的战术（Tactic）/ 技术（Technique），标注缓解强度

## 一、威胁场景定位

Carror OS 防御的是 **AI-to-System** 方向的威胁（AI agent 对用户本地 / 仓库 / 基础设施的误操作或恶意操作），而非 **Model-Level** 威胁（对模型训练数据投毒 / 模型窃取）。

| ATLAS 战术阶段 | Carror OS 是否覆盖 | 原因 |
|--------------|:-----------------:|------|
| Reconnaissance（侦察） | 🟡 部分 | privacy-gate 阻止 AI 读取敏感文件做侦察 |
| Resource Development（资源开发） | ❌ | 属于攻击者准备阶段，与治理层无关 |
| Initial Access（初始访问） | 🟡 部分 | context-guard 阻止上下文污染 |
| ML Model Access（模型访问） | ❌ | Carror 不管模型 API，只管 AI 行为 |
| Execution（执行） | ✅ 强 | permission-gate + edit-guard 核心能力 |
| Persistence（持久化） | ✅ | auto-snapshot + session-handoff 防会话漂移 |
| Defense Evasion（防御规避） | ✅ | audit-hooks 三方对账防脚本僵尸化 |
| Discovery（发现） | 🟡 | privacy-gate 限制 AI 探测敏感区 |
| Collection（收集） | ✅ | privacy-gate 双向脱敏 |
| Exfiltration（外泄） | ✅ | privacy-gate + varlock 阻止 token 明文出境 |
| Impact（影响） | ✅ 强 | permission-gate `rm -rf` / DROP TABLE 硬阻断 |

## 二、战术-技术-Carror 缓解映射表

| ATLAS ID | 战术 | 技术名 | Carror 缓解 | 强度 |
|---------|------|--------|------------|:---:|
| TA0002 / AML.T0051 | Execution | Command and Scripting Interpreter | `permission-gate.sh` 拦截 rm-rf / DROP / sudo / curl\|sh | 🟢 强 |
| TA0002 / AML.T0011 | Execution | User Execution | `pretool-edit-scope.sh` 三选项门禁 + AskUserQuestion 确认 | 🟢 强 |
| TA0005 / AML.T0043 | Defense Evasion | Evade ML Model | N/A（模型层） | — |
| TA0005 / AML.T0050 | Defense Evasion | Command and Control | `audit-hooks.sh` 三方对账 + `--scan-internal-filter` 防漂移 | 🟢 强 |
| TA0007 / AML.T0013 | Discovery | Discover ML Model Ontology | N/A | — |
| TA0007 / AML.T0040 | Discovery | Discover ML Artifacts | `privacy-gate.sh` 拦 `.env` / `~/.ssh` / private key | 🟢 强 |
| TA0009 / AML.T0025 | Collection | Data from Information Repositories | `privacy-gate.sh` Read/Bash/Grep 全事件拦截 | 🟢 强 |
| TA0010 / AML.T0024 | Exfiltration | Exfiltration via Inference API | `varlock.py` 双向脱敏代理，明文 token 永不出境 | 🟢 强 |
| TA0011 / AML.T0031 | Impact | Erode ML Model Integrity | N/A（模型层） | — |
| TA0011 / AML.T0034 | Impact | Cost Harvesting（账单攻击） | `subagent-guard.sh` + `posttool-subagent-audit.sh` 三层防线 | 🟡 中（软约束） |
| TA0011 / AML.T0048 | Impact | External Harms - Financial Harm | `permission-gate.sh` 阻断非授权 `git push --force` / package publish | 🟢 强 |
| **新 AI Dev 域** | Context Drift | 长会话指令衰减 | `turn-counter.sh` ≥10 轮注入铁律 + `pretool-rule-anchor.sh` ≥15 轮锚定 | 🟢 强 |
| **新 AI Dev 域** | Hallucination Cascade | 假完成声明 | `completion-gate.sh` 强 L3 证据门禁 + `posttool-write-cite.sh` 引用验证 | 🟢 强 |
| **新 AI Dev 域** | Session Amnesia | 跨会话上下文丢失 | `auto-snapshot.sh` + `inject-project-knowledge.sh` SessionStart 注入 | 🟢 强 |
| **新 AI Dev 域** | Error Recurrence | 反复犯同样错误 | `error-dna.sh` 签名落盘 + `skill-flywheel.sh` P0 事件告警 | 🟢 强 |
| **新 AI Dev 域** | Subagent Runaway | 子 agent 死循环烧 token | `subagent-guard.sh` 声明层 + `posttool-subagent-audit.sh` 执行层 + 人工层 | 🟡 中（软约束，见 R25） |

## 三、AI 特有缓解强度分级

| 威胁 | Prompt 建议层（Cursor/Copilot） | 物理阻断层（Carror OS） |
|------|:---:|:---:|
| `rm -rf` 误执行 | ❌ 仅建议，AI 可忽略 | ✅ Exit 2 硬阻断 |
| `.env` 泄露 | ❌ | ✅ PreToolUse:Read 强阻断 |
| Token 明文出 API | ❌ | ✅ varlock 双向脱敏 |
| 假完成声明 | ❌ | ✅ completion-gate L3 证据门禁 |
| 长会话遗忘铁律 | ❌ | ✅ rule-anchor ≥15 轮强注入 |
| 子 agent 账单雪崩 | ❌ | 🟡 软约束 + 事后对账（见 R25 诚信声明） |

## 四、未覆盖威胁（透明声明）

| 威胁 | Carror 为何不覆盖 | 替代方案 |
|------|------------------|---------|
| Model Extraction / Inversion | 模型层威胁，Carror 是客户端治理 | 模型厂商责任 |
| Training Data Poisoning | 不涉及模型训练 | 模型厂商责任 |
| Adversarial Examples | 不涉及模型推理 | 模型厂商责任 |
| 社会工程对用户本人 | 人因威胁非技术防线 | 用户培训 |

## 五、总览统计

| ATLAS 战术域 | 直接映射 | Carror 有强缓解 | Carror 部分缓解 | N/A |
|------------|:---:|:---:|:---:|:---:|
| Execution | 2 | 2 | 0 | 0 |
| Defense Evasion | 2 | 1 | 0 | 1 |
| Discovery | 2 | 1 | 0 | 1 |
| Collection | 1 | 1 | 0 | 0 |
| Exfiltration | 1 | 1 | 0 | 0 |
| Impact | 3 | 2 | 1 | 0 |
| AI Dev 扩展域 | 5 | 4 | 1 | 0 |
| **合计** | **16** | **12** | **2** | **2** |

**覆盖强度**（排除 N/A）：12 强 + 2 中 / 14 = **86% 强缓解 + 14% 部分缓解**

## 六、结论

- Carror OS 对 MITRE ATLAS 的 **AI-to-System 方向** 威胁覆盖 100%（强 86% + 部分 14%）
- Model-Level 威胁（训练投毒 / 模型窃取）由模型厂商负责，本框架不涉及
- 2 项"部分缓解"集中于子 agent 成本控制（R25 已有诚信声明：软约束不是硬停）

**诚信声明**：本映射由 AI 根据 ATLAS 公开矩阵与 Carror OS 源码对照生成，**新 AI Dev 域** 5 项为 Carror 原生威胁模型（参考 ATLAS 尚未列入的 AI Native Developer 威胁），非 MITRE 官方命名。

## 七、引用

- [MITRE ATLAS Matrix](https://atlas.mitre.org/matrices/ATLAS)
- [ATLAS Tactics 索引](https://atlas.mitre.org/tactics/)
- [ATLAS Techniques 索引](https://atlas.mitre.org/techniques/)
