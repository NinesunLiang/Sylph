# Carror OS 四维评分框架

> **版本**: v6.1.9 | **更新日期**: 2026-05-13
> **定位**: 本项目官方评分体系 — 所有评估报告以此为基准

---

## 概览

Carror OS 从四个维度、共 28 项子维度评估自身治理与能力水平。总分 345 权重分，转换为 10 分制或 8 分制输出。

| 维度 | 名称 | 子维度数 | 总权重 | 说明 |
|------|------|---------|--------|------|
| **C** | 能力 (Capability) | 9 | 105 | 指令清晰度、上下文完整度、流程结构化等 |
| **E** | 防护 (Error Prevention) | 8 | 110 | 目标漂移、幻觉输出、虚假完成等错误防线 |
| **G** | 治理 (Governance) | 6 | 65 | 抗衰减、自动化、安全门禁等长期治理 |
| **U** | 体验 (User Experience) | 5 | 65 | 心智负担、掌控感、交互质量等人机维度 |

**综合 = C + E + G + U 四维加权均分**，总分权重 345。

---

## C 维度：能力 (Capability)

衡量 Carror OS 作为 AI 治理框架的能力完备性。

| 编号 | 名称 | 权重 | 检查方式 | 成熟度 |
|------|------|------|---------|--------|
| C1 | 指令清晰度 | 15 | Hook 脚本 Role 注释覆盖率 | 0.85 |
| C2 | 上下文完整度 | 15 | index.md 铁律速查/引用/知识覆盖 | 0.85 |
| C3 | 流程结构化 | 15 | completion-gate L3 复杂度门禁 + Oracle 终审 + smoke 回归 | 1.00 |
| C4 | 输出规范化 | 10 | posttool-format-gate 注册与 matcher 范围 | 0.85 |
| C5 | 工具生命周期 | 10 | settings.json 事件类型注册覆盖率（6 种事件） | 0.90 |
| C6 | 知识密度 | 10 | claude-next.md 行数 + R 教训数 + 记忆系统文件 | 0.85 |
| C7 | 关联编排 | 10 | OMA 系列 skill 目录存在性 | 0.85 |
| C8 | 可维护性 | 10 | audit-hooks / smoke-test / hook-production-verify 存在 | 0.90 |
| C9 | 错误恢复 | 10 | error-dna / auto-fix / dna-jsonl 基础设施 | 0.85 |

### 各子维度详解

**C1 指令清晰度**: 检测 `.claude/hooks/*.sh` 中带 `# Role:` 注释的脚本比例。目标：100% 覆盖。

**C2 上下文完整度**: 检测 `index.md` 是否包含铁律速查、hooks reference 指针、anti-patterns/kernel 引用。

**C3 流程结构化**: 检测 completion-gate.sh 是否实现了：
- L3 复杂度关键词检测（架构决策/多文件变更等）
- Oracle 终审记录块检查
- harness-smoke-test E2E-6 用例

**C4 输出规范化**: 检测 posttool-format-gate.sh 是否在 settings.json 中注册，且 matcher 为 `.*`（全覆盖）。

**C5 工具生命周期**: 检测 settings.json 中注册的事件类型：PreToolUse / PostToolUse / PostToolUseFailure / Stop / UserPromptSubmit / SessionStart。

**C6 知识密度**: 复合评分 — 50% 行数 + 30% R 教训数 + 20% 记忆文件存在性。

**C7 关联编排**: 检测 OMA 系列 skill 目录：lx-oma-hier / lx-oma-split / lx-oma-gov / lx-oma-orch。

**C8 可维护性**: 检测关键维护脚本：audit-hooks.sh / harness-smoke-test.sh / hook-production-verify.sh。

**C9 错误恢复**: 检测 error-dna 基础设施：hook 脚本 / auto-fix 脚本 / JSONL 数据文件。

---

## E 维度：防护 (Error Prevention)

衡量 Carror OS 对 AI 常见错误模式的防御能力。

| 编号 | 名称 | 权重 | 检查方式 | 成熟度 |
|------|------|------|---------|--------|
| E1 | 目标漂移 | 20 | pretool-edit-scope + claude-next 教训 + turn-counter 检测 | 0.85 |
| E2 | 幻觉输出 | 20 | posttool-claim-audit 注册 + settings 注册 + claude-next 教训 | 0.90 |
| E3 | 虚假完成 | 15 | completion-gate 证据检测 + anti-patterns A2 条目 | 1.00 |
| E4 | 惯性执行 | 12 | fuzzy-block 存在 + turn-counter 模糊词检测 + ghost 豁免 | 1.00 |
| E5 | 症状混淆 | 10 | error-dna NOISE_PATTERNS 过滤 + JSONL 数据量 | 0.85 |
| E6 | 自我矛盾 | 13 | claude-next R42 + R43 + anti-pattern-detect hook | 0.85 |
| E7 | 过度自信 | 10 | completion-gate 软完成语检测 + anti-patterns A2/F1 + 质量评分 | 1.00 |
| E8 | 上下文遗忘 | 10 | compact-detect 知识注入 + inject-project-knowledge + context-guard | 0.90 |

### 各子维度详解

**E1 目标漂移**: 检测 edit-scope.sh 的范围冻结机制、claude-next.md 中的漂移教训、turn-counter.sh 的漂移检测。

**E2 幻觉输出**: 检测 posttool-claim-audit.sh 的存在与注册、claude-next.md 中相关教训。成熟度 0.90（claim-audit exit 2 硬阻断）。

**E3 虚假完成**: 检测 completion-gate.sh 的证据门禁逻辑、anti-patterns.md 的 A2 条目。成熟度 1.00（硬阻断）。

**E4 惯性执行**: 检测 fuzzy-block.sh 存在、turn-counter.sh 的模糊动词检测、ghost 模式下模糊指令豁免。成熟度 1.00。

**E5 症状混淆**: 检测 error-dna.sh 的 NOISE_PATTERNS 过滤规则、JSONL 数据量 > 10 条。

**E6 自我矛盾**: 检测 claude-next.md 中 R42（hook 规则误用于 skill）和 R43（CAPTCHA 脚本化批准）两项教训是否记录。

**E7 过度自信**: 检测 completion-gate.sh 的软完成语匹配、anti-patterns.md 的 A2/F1 定义、质量评分阈值。成熟度 1.00（A2/F1/H1 均 exit 2 硬阻断）。

**E8 上下文遗忘**: 检测 compact-detect.sh 的知识重新注入、inject-project-knowledge.sh 存在、context-guard.sh 存在。

---

## G 维度：治理 (Governance)

衡量 Carror OS 的长期治理能力和基础设施稳健性。

| 编号 | 名称 | 权重 | 检查方式 | 成熟度 |
|------|------|------|---------|--------|
| G1 | 抗衰减防线 | 10 | audit-hooks + hook-production-verify + smoke test + auto-snapshot | 0.90 |
| G2 | AI 自动化 | 10 | compact-detect + auto-snapshot + error-dna 注册 + auto-fix | 0.85 |
| G3 | 学习笔记 | 10 | claude-next.md > 100 行 + handoff + snapshot + R 教训 > 10 | 0.85 |
| G4 | 功能标志 | 10 | harness.yaml hooks_enabled + audit-hooks + hc_enabled 全覆盖 | 0.90 |
| G5 | 内置安全 | 15 | permission-gate + privacy-gate + sensitive-edit + context-guard 注册 | 1.00 |
| G6 | 评测框架 | 10 | score-self-check 存在 + baseline + report + 权重文档化 | 0.85 |

### 各子维度详解

**G1 抗衰减防线**: 检测四项抗衰退机制：audit-hooks.sh（三方一致性审计）、hook-production-verify.sh（生产验证）、harness-smoke-test.sh（回归测试）、auto-snapshot.sh（会话快照）。

**G2 AI 自动化**: 检测四项自动化机制：compact-detect.sh（压缩检测）、auto-snapshot.sh（快照）、error-dna 在 settings.json 中注册、error-dna-auto-fix.sh（自动修复）。

**G3 学习笔记**: 检测知识积累系统：claude-next.md 行数 > 100、session-handoff.md 存在、session-snapshot.json 存在、R 教训数 > 10。

**G4 功能标志**: 检测特性开关基础设施：harness.yaml 定义了 hooks_enabled、audit-hooks.sh 存在、所有 hook 脚本均实现 hc_enabled 门禁。

**G5 内置安全**: 检测四项安全机制在 settings.json 中的注册：permission-gate（危险命令拦截）、privacy-gate（隐私保护）、pretool-sensitive-edit（治理文件 CAPTCHA）、context-guard（上下文阈值阻断）。成熟度 1.00 — 全部为硬阻断机制。

**G6 评测框架**: 检测评分评估基础设施：score-self-check.sh 存在、score-baseline.json 基线已保存、score-report.json 报告存在、脚本内含权重定义。

---

## U 维度：体验 (User Experience)

衡量用户与 Carror OS 交互时的体验质量和心智负担水平。

| 编号 | 名称 | 权重 | 检查方式 | 成熟度 |
|------|------|------|---------|--------|
| U1 | 心智负担减轻 | 15 | CAPTCHA 清晰提示 + ghost 豁免 + 格式方向感 + 质量评分方向 | 0.90 |
| U2 | 用户掌控感 | 15 | permission-gate + sensitive-edit CAPTCHA + git 门禁 + Oracle 裁决 | 0.90 |
| U3 | 行为可预测 | 10 | index.md 铁律速查 + 范围冻结 + 修复上限 + 置信度格式 | 0.85 |
| U4 | 交互质量 | 10 | format-gate 方向感 + matcher 全覆盖 + anti-pattern 检测 | 0.85 |
| U5 | 人机权限分明 | 15 | permission-gate 范围 + sensitive-edit 文件列表 + git 门禁 + privacy 目标 | 0.90 |

### 各子维度详解

**U1 心智负担减轻**: 检测帮助用户减少认知负担的机制：
- pretool-sensitive-edit.sh 中 CAPTCHA 提示包含"输入框中按 Enter"等方位指引
- turn-counter.sh 中 ghost mode 模糊指令豁免
- posttool-format-gate.sh 提供格式方向感提示
- completion-gate.sh 在证据不通过时输出质量分解和改进方向（R38）

**U2 用户掌控感**: 检测用户对系统行为的控制能力：
- permission-gate 在 settings.json 中注册
- pretool-sensitive-edit.sh 使用验证码批准模式
- index.md 包含 Git 门禁规则
- lx-oma-orch SKILL.md 包含 Oracle 门禁裁决机制

**U3 行为可预测**: 检测系统行为的可预测性：
- index.md 包含铁律速查表
- 含范围冻结规则
- 含修复上限规则
- 含置信度标注格式

**U4 交互质量**: 检测输出质量和交互体验：
- posttool-format-gate.sh 提供方向感/摘要
- matcher 配置为 `.*`（全覆盖）
- posttool-anti-pattern-detect.sh 存在（A2/F1/H1 实时阻断）

**U5 人机权限分明**: 检测人与 AI 的权限边界清晰度：
- permission-gate.sh 含 SCOPE_WRITE_RE / gh_write_regex 等精确权限范围
- pretool-sensitive-edit.sh 含敏感文件匹配列表
- index.md 含 Git 操作门禁描述
- privacy-gate.sh 含 `.env`/私钥检测

---

## 评分公式

### 基础分

每个子维度的基础分由其检查项的存在率决定：

```
base_score = features_present / features_total
```

例如 C1（3 项检查）：全部通过 → base = 1.0；通过 2 项 → base = 0.67。

### 成熟度系数

机制的质量比存在更重要。成熟度系数反映机制的实际执行强度：

| 成熟度 | 值 | 含义 | 示例 |
|--------|---|------|------|
| 硬阻断 | 1.00 | exit 2，可中止执行 | permission-gate 拦截 rm -rf |
| 主动机制 | 0.90 | 产生可操作警告/上下文，不阻断 | claim-audit 输出 additionalContext |
| 建议性 | 0.85 | 作为参考或静态检查 | index.md 铁律速查 |

### 教训惩罚

从 claude-next.md 中解析 R 前缀教训，映射到对应维度：

```
penalty = base_penalty × hits
if 已修复: penalty ×= 0.3
penalty = min(penalty, 0.3)  # 上限 30%
```

### 最终分

```
final = max(0, base × maturity - penalty)
```

### 加权汇总

```
weighted_sum = Σ(final × weight) / total_weight
composite_10 = weighted_sum × 10
composite_8 = weighted_sum × 8
```

---

## 评分解读

| 综合分 | 含义 |
|--------|------|
| 9.0+ | 优秀 — 所有维度强覆盖，主要机制均达硬阻断级别 |
| 8.0-8.9 | 良好 — 核心维度覆盖完整，部分维度受成熟度或教训惩罚限制 |
| 7.0-7.9 | 合格 — 主要维度覆盖，但存在明显薄弱环节 |
| < 7.0 | 需改进 — 多个维度存在缺口，需要补充机制 |

### 当前基线

当前 Carror OS 基线评分保存在 `.omc/state/score-baseline.json`。运行以下命令查看最新评分：

```bash
bash .claude/scripts/score-self-check.sh           # 最新报告
bash .claude/scripts/score-self-check.sh --init    # 更新基线
bash .claude/scripts/score-self-check.sh --diff <baseline>  # 差异比较
```

---

## 与其他评分体系的关系

| 体系 | 维度数 | 关系 |
|------|--------|------|
| 三维度内部评分（Defense/Amplification/Governance） | 3 | C+E 映射到 Defense，G 独立，U 为新增 |
| 双域 12 维度评分 | 12 | Capability 域 ≈ C 维度，Governance 域 ≈ G+E 维度 |
| 产品对标记分卡 | 10 | 功能口径不同，用于对外对标 |

本评分体系是项目**官方维度**，所有评估报告应当以此为基准。
