# Carror OS 产品优化任务清单

> 版本：v0.1
> 日期：2026-05-04
> 状态：内部执行计划
> 执行者：本地 LLM / 仓库 Agent
> 目标：将战略产品建议转化为具体的仓库任务

---

## 执行规则

在做出变更前，本地模型必须遵守以下规则：

1. 不要添加未经支持的营销声明。
2. 不要将计划中的功能描述为已实现的功能。
3. 除非有基准测试输出，否则不要使用精确的 token 节省数字。
4. 不要将 Race Mode 描述为真正的并行执行。
5. 在锁生命周期硬化得到验证之前，不要将 OMA 描述为生产就绪。
6. 不要在面向公众的文档中使用"自评分"语言。
7. 所有公开声明必须附带证据级别。
8. 优先使用小补丁和清晰的报告。
9. 每个任务完成后，输出已变更的文件和已变更的声明。
10. 如果实现证据缺失，将声明标记为 `partial`、`planned` 或 `unknown`。

---

# 任务 1 — 建立声明治理

## 优先级

P0

## 目标

创建一个机器可读的声明注册表，使 Carror OS 文档变为证据驱动。

## 待创建文件

```text
docs/internal/claim-registry.yaml
scripts/claim-lint.sh
docs/internal/claim-lint-report.md
```

## 操作

1. 创建 `claim-registry.yaml`。
2. 注册所有高风险声明：
   - token 节省
   - context guard
   - proactive handoff
   - Race Mode
   - OMA 锁
   - Error DNA
   - 脱水
   - 审计追踪
   - 行业基准
3. 添加字段：
   - claim_id
   - claim_text
   - status
   - evidence_level
   - public_allowed
   - source_docs
   - required_validation
   - replacement_text
4. 创建 `claim-lint.sh`。
5. 扫描高风险术语：
   - 自评分
   - 行业独创
   - 100% 功能完备
   - 完全可见
   - 真并发
   - 实测节省
   - 19,280
   - 75%
   - Claude 默认 tokenizer
6. 生成 `claim-lint-report.md`。

## 验收标准

- `claim-registry.yaml` 存在并可解析为有效 YAML。
- `claim-lint.sh` 报告所有高风险声明。
- 在 claim-lint 通过或例外情况被记录之前，任何面向公众的文档不得视为最终版本。

## 建议的 YAML Schema

```yaml
claims:
  token_saving_19280:
    status: retracted
    evidence_level: C0
    public_allowed: false
    replacement_text: "渐进式披露旨在减少不必要的上下文加载。确切节省需经基准测试验证。"
    source_docs: []
    required_validation:
      - scripts/loading_benchmark.py
      - docs/testing/loading-benchmark-report.md

  race_parallel_execution:
    status: downgraded
    evidence_level: C1
    public_allowed: true
    replacement_text: "Race Mode 是一种编排模式，而非确定性的并行执行引擎。"
```

## 需要输出的内容

```text
已变更文件：
已变更声明：
剩余阻塞项：
下一步推荐任务：
```

---

# 任务 2 — 执行仓库现实检查

## 优先级

P0

## 目标

在进行进一步产品化之前，验证知识库与实际仓库是否匹配。

## 待创建文件

```text
state/repository-reality-check.md
docs/internal/canonical-path-map.md
```

## 操作

1. 统计钩子、技能、脚本、文档的数量。
2. 检测空的实现文件。
3. 检测文档内容不匹配。
4. 确定以下项的规范源路径：
   - hooks
   - skills
   - scripts
   - docs
   - marketing docs
5. 检查以下文件是否存在：
   - `context_monitor.py`
   - `token-tracking-index.json`
   - `error-dna.sh`
   - `build-validator.sh`
   - `oma_lock_manager.py`
   - `proactive-handoff.sh`
6. 检查是否有任何代码写入：
   - `.omc/state/token-tracking-index.json`
   - `.omc/state/error-dna.json`
   - `.omc/state/read-files.log`

## 建议的命令

```bash
find . -type f -size 0
rg "token-tracking-index.json"
rg "context_monitor.py"
rg "error-dna"
rg "read-files.log|read-tracker.txt"
rg "19,280|75%|自评分|行业独创|完全可见|真并发"
```

## 验收标准

- `repository-reality-check.md` 存在。
- 所有关键文件分类为：
  - 存在
  - 缺失
  - 空
  - 过时
  - 未知
- 阻塞项清晰列出。

## 需要输出的内容

```text
仓库状态：
关键不匹配：
需要人工审核的文件：
阻塞任务：
下一步推荐任务：
```

---

# 任务 3 — 修复 Token 和审计追踪基础

## 优先级

P0

## 目标

使审计追踪和 proactive handoff 变为非静默且能产生证据。

## 可能需要修改的文件

```text
proactive-handoff.sh
read-tracker.sh
carror_dashboard.py
skill_trace_report.py
.claude/scripts/audit_dashboard.py
```

## 缺失时需创建的文件

```text
.omc/state/token-tracking-index.json
.claude/scripts/token_writer.py
docs/internal/audit-trail-status.md
```

## 操作

1. 验证 token 追踪是否有真正的写入者。
2. 如果缺失，创建最小写入者或将功能标记为降级状态。
3. 修改 proactive handoff，使其在 token 源缺失时不会静默退出。
4. 统一读取追踪器文件名。
5. 为读取追踪器添加日志轮转。
6. 创建审计状态报告。

## 验收标准

- Proactive handoff 产生以下之一输出：
  - active
  - triggered
  - skipped_with_reason
  - degraded
- 缺失的 token 数据可见。
- 读取追踪器文件名一致。
- 轮转机制存在。

## 需要输出的内容

```text
已变更文件：
找到的审计源：
缺失的审计源：
变更前行为：
变更后行为：
剩余阻塞项：
```

---

# 任务 4 — 构建功能注册表

## 优先级

P0

## 目标

为所有钩子和技能创建唯一事实源。

## 待创建文件

```text
.claude/feature-registry.yaml
scripts/feature-probe.sh
docs/reference/feature-registry.md
```

## 待修改文件

```text
harness.yaml
harness_config.sh
features.md
```

## 操作

1. 注册所有钩子。
2. 注册所有技能。
3. 添加字段：
   - feature_id
   - layer
   - edition
   - default_enabled
   - config_key
   - source_files
   - docs
   - status
   - evidence_level
   - probe
4. 在配置中添加 `skills_enabled:`（如适用）。
5. 创建 `feature-probe.sh`。
6. 生成人类可读的功能注册表文档。

## 验收标准

- 注册表可解析为 YAML。
- `features.md` 中的每个公开功能都有注册表条目。
- 每个注册表条目都有状态：
  - implemented
  - partial
  - planned
  - broken
  - unknown
- `feature-probe.sh` 可运行至少三个探针：
  - context_guard
  - completion_gate

## 需要输出的内容

```text
已注册功能：
缺失文档：
缺失实现：
已降级功能：
下一步推荐任务：
```

---

# 任务 5 — 用基准测试替换未经支持的 Token 节省声明

## 优先级

P0

## 目标

移除未经支持的 token 节省数字并创建基准测试路径。

## 待创建文件

```text
scripts/loading_benchmark.py
docs/testing/loading-benchmark-report.md
```

## 待扫描/修改的文件

```text
README.md
features.md
README-draft.md
PRESS-KIT.md
FAQ.md
industry-benchmark.md
CHANGELOG.md
```

## 操作

1. 搜索：
   - `19,280`
   - `75%`
   - `70%`
   - `394`
   - `120`
   - `tokens/session`
2. 将未经验证的精确声明替换为"基准测试待定"的语言。
3. 创建基准测试脚本。
4. 报告 token 计数方法是：
   - 官方 API
   - tiktoken 估计
   - chars/4 回退
5. 生成基准测试报告。

## 验收标准

- 未经支持的精确 token 节省声明已移除或标记为内部历史。
- 基准测试报告存在。
- 任何 token 计数方法都已清晰标注。
- `tiktoken` 未被描述为 Claude 的官方 tokenizer。

## 替换文本

```text
渐进式披露旨在减少不必要的上下文加载。确切 token 节省比例应以基准测试实测报告为准。
```

英文：

```text
Progressive disclosure is designed to reduce unnecessary context loading. Exact token savings should be reported only after benchmark validation.
```

## 需要输出的内容

```text
已移除声明：
已降级声明：
基准测试方法：
基准测试结果：
剩余未知项：
```

---

# 任务 6 — 简化开发者体验

## 优先级

P1

## 目标

降低认知负荷，使 Carror OS 更易于理解和试用。

## 待修改文件

```text
README.md
docs/overview/what-is-carror-os.md
docs/guides/quickstart.md
docs/reference/editions.md
FAQ.md
```

## 操作

1. 重写 README，仅回答：
   - 它是什么？
   - 它为什么存在？
   - 它解决什么问题？
   - 3-4 个核心能力是什么？
   - 如何安装？
   - 如何快速试用？
   - 当前的成熟度边界是什么？
2. 将复杂理论移入文档。
3. 添加基于角色的导航：
   - 个人开发者
   - 团队领导
   - 企业试点
4. 添加"我应该用哪种模式？"指南。
5. 减少首屏术语密度。

## 验收标准

- README 首屏在 60 秒内可理解。
- Quickstart 有一条成功的路径。
- 版本说明清晰。
- 高级概念通过链接访问，而非前置加载。

## 需要输出的内容

```text
旧 README 问题：
新 README 结构：
已移出的概念：
剩余令人困惑的术语：
```

---

# 任务 7 — 重构知识库

## 优先级

P1

## 目标

将当前文档集合转变为结构化知识系统。

## 待创建的文件/目录

```text
docs/overview/
docs/concepts/
docs/reference/
docs/guides/
docs/governance/
docs/testing/
docs/internal/
docs/lecture/
docs/archive/
scripts/doc-sync-check.sh
docs/internal/doc-canonical-map.yaml
```

## 操作

1. 将文档移到清晰的类别中。
2. 单独管理营销文档。
3. 将内部评分文档移入 `docs/internal/`。
4. 归档过时的文档。
5. 添加前言元数据：
   - title
   - owner
   - canonical_source
   - evidence_level
   - public_status
   - last_verified
6. 创建文档同步检查器。

## 验收标准

- 公开文档和内部文档已分离。
- 同一功能没有重复的规范描述。
- `doc-sync-check.sh` 报告断裂的文件引用。
- README 链接到新结构。

## 需要输出的内容

```text
已移动文件：
已归档文件：
规范文档：
发现的重复文档：
断裂的引用：
```

---

# 任务 8 — 将对外营销材料重写为基于证据的内容

## 优先级

P1

## 目标

将面向公众的文档从内部自评分转化为基于可重现方法的信息传达。

## 待修改文件

```text
docs/marketing/industry-benchmark.md
docs/marketing/README-draft.md
docs/marketing/PRESS-KIT.md
docs/marketing/FAQ.md
docs/marketing/manifesto.md
```

## 待移动文件

```text
docs/marketing/v6.1.8-dual-domain-scoring.md
→ docs/internal/v6.1.8-dual-domain-scoring.md
```

## 操作

1. 从公开文档中移除自评分框架。
2. 从公开文档中移除"分析"内部评论框。
3. 仅在包含方法说明的前提下保留 8 维基准测试。
4. 将 12 维评分移至内部。
5. 添加局限性说明章节。
6. 添加以下链接：
   - 手动验收测试
   - 自动化特性测试
   - 加载基准测试
   - 功能注册表
7. 将"行业独创"替换为更温和的定位。

## 验收标准

- 公开文档不包含：
  - 自评分
  - 内部分析
  - 未经支持的精确指标
  - 绝对优越性声明
- 行业基准测试包含方法和局限性说明。
- 内部评分不与公开营销内容混合。

## 需要输出的内容

```text
已移除的营销声明：
已重写的营销声明：
已移动的内部文档：
已添加的证据链接：
剩余的发布阻塞项：
```

---

# 任务 9 — 改进可观测性和 Agentic UI

## 优先级

P1

## 目标

使 Carror OS 治理能力可见且可交互。

## 待修改/创建的文件

```text
lx-status/SKILL.md
.claude/scripts/audit_dashboard.py
completion-gate.sh
context-guard.sh
permission-gate.sh
pretool-edit-scope.sh
manual-acceptance-test.md
```

## 操作

1. 升级 `lx-status`，增加：
   - token 趋势
   - Error DNA 摘要
   - 飞轮时间线
   - 功能注册表状态
   - 审计健康度
2. 为以下钩子添加编号选择菜单：
   - completion-gate
   - context-guard
   - permission-gate
   - pretool-edit-scope
3. 添加 O7-O10 验收测试。
4. 缺失数据应显示降级状态，而非虚假成功。

## 验收标准

- `lx-status` 至少显示 4 个面板。
- 所有 4 个钩子显示编号选择菜单。
- 验收测试已更新。
- 缺失源可见。

## 需要输出的内容

```text
已变更的 UI 界面：
已添加的菜单：
已更新的验收测试：
观察到的降级状态：
```

---

# 任务 10 — 构建证据和发布资产库

## 优先级

P1

## 目标

准备可信的产品化和发布证据。

## 待创建文件

```text
docs/internal/EVIDENCE-BANK.md
docs/internal/DOGFOODING-LOG.md
docs/marketing/screenshots-plan.md
docs/marketing/demo-video-plan.md
docs/marketing/external-review-template.md
docs/marketing/case-study-template.md
docs/internal/RISK-REGISTER.md
```

## 操作

1. 创建证据库。
2. 记录狗粮测试会话。
3. 收集：
   - 终端截图
   - 日志
   - 前后对比
   - 演示片段
   - 基准测试表格
   - 用户引语
4. 添加脱敏检查清单：
   - 仓库名称
   - 用户名
   - 密钥
   - 客户数据
   - 内部路径
5. 创建外部评审邀请模板。
6. 创建案例研究模板。

## 验收标准

- 证据库至少包含 5 个条目。
- 狗粮测试日志至少包含 3 个真实会话。
- 截图计划存在。
- 演示计划存在。
- 外部评审模板存在。
- 风险登记册存在。

## 需要输出的内容

```text
已添加的证据条目：
已记录的狗粮测试会话：
已准备好的公开资产：
需要脱敏的资产：
发布阻塞项：
```

---

# 执行顺序

推荐的执行顺序：

```text
P0:
  任务 1 → 任务 2 → 任务 3 → 任务 4 → 任务 5

P1:
  任务 6 → 任务 7 → 任务 8 → 任务 9 → 任务 10
```

理由：

1. 声明治理防止新的错误信息。
2. 现实检查防止编辑过时或错误的文件。
3. 审计/Token 修复修复断裂的证据源。
4. 功能注册表创建唯一事实源。
5. 基准测试移除未经支持的数字。
6. 用户体验简化提升采纳率。
7. 知识库重构提升可维护性。
8. 营销重写提升可信度。
9. 可观测性提升感知和实际控制力。
10. 证据库支持发布和商业转化。

---

# 本地模型主提示词

在将整个任务链分配给本地模型时使用此提示词：

```text
你是 Carror OS 本地产品化代理。

你的目标是在不添加未经支持声明的前提下改进仓库。

遵循以下执行顺序：

1. 建立声明治理。
2. 执行仓库现实检查。
3. 修复 Token 和审计追踪基础。
4. 构建功能注册表。
5. 用基准测试替换未经支持的 Token 节省声明。
6. 简化开发者体验。
7. 重构知识库。
8. 将对外营销材料重写为基于证据的内容。
9. 改进可观测性和 Agentic UI。
10. 构建证据和发布资产库。

规则：
- 不要将计划中的功能描述为已实现。
- 除非有基准测试输出，否则不要使用精确的 token 节省数字。
- 不要将 Race Mode 描述为真正的并行执行。
- 在锁生命周期测试通过之前，不要将 OMA 描述为生产就绪。
- 不要在公开文档中使用自评分语言。
- 每个公开声明必须附带证据级别。
- 每个任务后，输出已变更文件、已变更声明、证据级别、阻塞项和下一步。
- 优先使用小的、可审查的补丁。
```

---

# 最终交付物检查清单

完成所有 10 个任务后，仓库应包含：

```text
docs/internal/claim-registry.yaml
docs/internal/claim-lint-report.md
state/repository-reality-check.md
docs/internal/canonical-path-map.md
.claude/feature-registry.yaml
scripts/feature-probe.sh
scripts/loading_benchmark.py
docs/testing/loading-benchmark-report.md
scripts/doc-sync-check.sh
docs/internal/EVIDENCE-BANK.md
docs/internal/DOGFOODING-LOG.md
docs/marketing/screenshots-plan.md
docs/marketing/demo-video-plan.md
docs/marketing/external-review-template.md
docs/marketing/case-study-template.md
docs/internal/RISK-REGISTER.md
```

---

# 成功标准

本轮优化成功时：

1. 公开文档不再包含未经支持的强声明。
2. 功能状态是机器可读的。
3. 基准测试取代了历史的 token 节省声明。
4. 审计和 token 追踪不再静默失败。
5. 知识库具有清晰的公开/内部分离。
6. README 变得更易于理解。
7. 营销文档变为基于证据。
8. lx-status 和钩子菜单使治理能力可见。
9. 狗粮测试和发布证据已收集。
10. Carror OS 可以被定位为可信的 AI 编程治理系统。
