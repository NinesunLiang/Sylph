**不完美，而且目前不建议把 Grok-4.5 或 Opus-4.8 版本直接作为“可无人值守上线”的最终版。**

更准确地说：它们已经是**高质量治理提案/补丁方案**，但还不是经过真实工程验证的稳定发行版。

## 我的判断

| 版本 | 主要优势 | 主要问题 | 结论 |
|---|---|---|---|
| **Grok-4.5** | 保守、务实；强调输入治理、失败分类、C7 机器门和结构化阻塞 | 偏评审与风险纠偏，完整落地脚本和实际运行证据仍不足 | 很适合作为**安全审计层** |
| **Opus-4.8** | 治理覆盖更完整；契约、预算、熔断、共享缺口管理较细 | 体系偏重，复杂度可能超过首夜任务需要；文档存在不等于脚本真正可靠 | 很适合作为**治理设计层** |
| **整合后的 CarrorOS 方案** | 吸收两者长处，并加入真实命令映射、J0、Phase 0 路由预生成 | 仍需补丁和真实运行验证 | 当前应当**有条件 Go**，而非宣称完美 |

## 目前尚未闭环的关键问题

### 1. 规则写出来了，不代表机器真的执行得对

必须真实验证：

- `c7-check` 能否稳定识别超行数、裸色值、魔法像素和过大功能块；
- C1 是否能真正阻止越过 `files_allowed`；
- C2 的 typecheck、lint、build 是否与项目实际命令一致；
- Playwright 是否覆盖正常、空、加载、失败、防重复提交和关闭行为；
- 截图、验收结果和 commit SHA 是否可靠绑定；
- `verify → archive → Draft PR` 能否断点恢复。

任何一个只是文档描述、没有可执行测试，都不能算闭环。

### 2. J0“判断真空”还需要彻底机器化

J0 是方案中非常关键的设计：夜间没有高阶模型裁决时，系统不能猜测。但还要进一步明确：

1. 哪些情况允许选择最小风险路径；
2. 哪些情况必须降级；
3. 哪些情况只能产出占位结构；
4. 哪些情况必须标记 `BLOCKED`；
5. 哪些情况立即熔断整个任务。

这些规则必须转成确定性的优先级、错误码和状态迁移，不能停留在自然语言原则。

### 3. Mock 降低了后端风险，但没有消除前端风险

Mock 能避免误操作真实后端、资金和权限数据，却无法避免：

- 状态机实现错误；
- 交互表面可点、实际链路不成立；
- loading/error/empty 状态缺失；
- 乐观更新和回滚逻辑错误；
- 公共组件被局部需求污染；
- 用截图“伪装”功能完成；
- Mock 契约与未来真实 API 偏离。

因此不能因为“全程使用 Mock”就将任务统一视为低风险。

### 4. Ant Design 策略仍需唯一化

需要在 Phase 0 形成机器可读裁决，例如：

```yaml
ui_policy:
  mode: custom # custom | antd6 | hybrid
  antd_major: 6
  public_component_changes: deny
  token_source: src/styles/tokens.css
```

尤其要避免 Agent 在页面开发过程中临时决定：

- 一部分使用自定义组件；
- 一部分使用 Ant Design；
- 再通过局部 CSS 强行覆盖；
- 最终出现两套间距、圆角、颜色和交互语义。

### 5. 还缺少真实基准数据

不能只凭方案完整度判断效果，至少要进行小规模试运行并记录：

- 错误完成声明数；
- 越界改动数；
- 未授权公共组件改动数；
- 同指纹无效重试次数；
- D2 正确阻塞率；
- 有证据的 AC 通过率；
- Draft PR 可审率；
- 断点恢复成功率；
- 视觉回归误报与漏报率；
- 单页平均 token、时间和修复轮数。

没有这些数据，“完美”只能是文档层面的主观评价。

## 当前 Go / No-Go 结论

### 无补丁直接大规模无人值守：**No-Go**

不适合直接：

- 多页面大规模并行；
- 自动合并；
- 修改公共组件；
- 接触真实写接口；
- 处理需求或设计输入不完整的页面；
- 执行高视觉复杂度 V3 任务；
- 依靠模型自行解释冲突规则。

### 小规模首夜试运行：**有条件 Go**

建议约束为：

- 页面不超过 3 个；
- 仅 V0–V2；
- 不包含 B3 风险；
- PRD、API、关键状态截图齐全；
- 路由空壳提前提交；
- C1–C4 门禁已真实跑通；
- 默认只生成 Draft PR；
- 全局关闭自动合并；
- 公共组件和共享基础设施默认只读；
- K3 可关闭，不作为首夜成功的必要依赖；
- 无法判断时结构化阻塞，绝不自行补需求。

## 最终评价

我不会给任何一个版本打“完美”。更合理的定位是：

- **Grok-4.5：优秀的风险审计与保守主义补丁**
- **Opus-4.8：优秀的治理完整性与契约设计版本**
- **二者整合后：具备试运行价值，但尚未达到无条件无人值守**

真正的“稳定版”不应该由文档自称，而应该由连续若干轮真实任务证明：**零越界、零虚假完成、可恢复、可复核，并且 Draft PR 持续可审。**



我的方案会定义为：

# **CarrorOS Frontend Autopilot v2.0**

它不是继续增加提示词，而是把 Grok-4.5 的风险控制、Opus-4.8 的治理契约和 CarrorOS 的执行体系，收敛成一个**确定性状态机 + 可执行门禁 + 证据链**。

核心目标不是让 AI “尽量完成”，而是保证它只产生三种可信结果：

1. **DONE**：需求已完成，证据完整，可进入 Draft PR。
2. **BLOCKED**：缺少输入或需要人工裁决，明确说明阻塞点。
3. **FAILED**：工程执行失败，保留日志、现场和恢复入口。

绝不允许“看起来完成”。

## 一、整体架构

```text
需求/设计稿/API/仓库
        ↓
Input Compiler（输入编译）
        ↓
Task Contract（任务契约）
        ↓
Planner（研究、AC、实施计划）
        ↓
Policy Engine（权限、风险、J0 裁决）
        ↓
Executor（编码与测试）
        ↓
Verifier（功能、视觉、架构验证）
        ↓
Evidence Binder（证据绑定 commit SHA）
        ↓
Draft PR / BLOCKED / FAILED
```

AI 负责理解与实现；状态迁移、权限检查、验收和终止条件由程序控制。模型不能自行宣布完成，也不能绕过门禁。

## 二、任务先编译成契约

任何编码开始前，先生成机器可读的 `task.yaml`：

```yaml
id: FE-20260718-001
risk: B1
visual_level: V2
route: /orders/detail

scope:
  files_allowed:
    - src/pages/orders/detail/**
    - tests/e2e/orders-detail.spec.ts
  files_denied:
    - src/shared/**
    - src/router/**
    - src/store/**

ui_policy:
  mode: antd6
  token_source: src/styles/tokens.css
  allow_global_override: false

inputs:
  prd: docs/orders-detail.md
  api_contract: docs/api/orders.yaml
  references:
    - prototype/orders-detail.png

acceptance_criteria:
  - id: AC-01
    type: functional
    assertion: 页面可以正确展示订单详情
  - id: AC-02
    type: interaction
    assertion: 重复点击提交只产生一次请求
  - id: AC-03
    type: visual
    assertion: 三个目标视口通过视觉验收

required_states:
  - loading
  - success
  - empty
  - business_error
  - network_error
  - submitting
```

输入不完整时不直接编码。系统先判断缺失内容是可以依据仓库模式确定，还是必须转为 `BLOCKED`。

## 三、确定性执行状态机

```text
INTAKE
  → RESEARCHED
  → CONTRACT_FROZEN
  → PLANNED
  → IMPLEMENTING
  → STATIC_VERIFIED
  → BEHAVIOR_VERIFIED
  → VISUAL_VERIFIED
  → ARCHITECTURE_VERIFIED
  → EVIDENCE_BOUND
  → DRAFT_PR
```

每次状态迁移都必须满足：

- 上一阶段产物存在；
- 对应命令退出码为 0；
- 证据文件能够解析；
- 产物绑定当前 commit SHA；
- 工作区没有未登记的越界修改。

失败不会从头盲目重试，而是依据失败指纹路由到对应修复阶段。同一指纹连续出现两次就熔断，防止 AI 无效循环。

## 四、门禁体系

我会把 C0-C8 收敛成下面九道真正可执行的门：

| 门禁 | 检查内容 |
|---|---|
| C0 输入门 | PRD、设计、API 和路由信息是否足够 |
| C1 范围门 | 修改文件是否全部位于 `files_allowed` |
| C2 静态门 | TypeScript、ESLint、构建、依赖完整性 |
| C3 架构门 | 目录、组件边界、状态归属、公共模块污染 |
| C4 功能门 | 每条功能 AC 是否有自动化断言 |
| C5 交互门 | loading、empty、error、重复提交、关闭与回退 |
| C6 视觉门 | 三视口截图、布局差异和溢出检测 |
| C7 治理门 | 裸色值、魔法尺寸、超大组件、违规覆盖等 |
| C8 交付门 | 证据是否完整并绑定当前 SHA |

其中 C4-C6 分开执行。功能通过不代表视觉通过，截图相似也不能证明交互正确。

## 五、J0 无人裁决规则

夜间没有人工时，AI 不能凭主观偏好决定。固定优先级为：

1. 复用仓库已有模式；
2. 不修改 `shared`、`tokens`、`router`、`auth`；
3. 不增加依赖；
4. 保持单页可回滚；
5. 不改变全局交互语义；
6. 不创建未在计划中声明的跨页状态。

触发 J0 时必须生成 `assumptions.yaml`，记录候选方案、选择依据、回滚方法和晨间复核要求。

以下情况直接 `BLOCKED`：

- 不同输入之间存在关键冲突；
- 涉及权限、资金、真实写操作或安全语义；
- 必须修改公共组件或全局架构才能继续；
- 无法从 PRD、设计稿和仓库模式确定核心行为；
- 需要新增依赖但没有预授权。

## 六、前端专项治理

我的版本会比现有方案更强调 UI 一致性，并增加四类机器检查。

### 1. UI 模式只能三选一

- `custom`：完全使用项目自定义组件；
- `antd6`：使用 Ant Design v6 和项目 token；
- `hybrid`：必须预先列出允许使用 Ant Design 的组件。

执行阶段不能临时切换模式。

### 2. 组件先复用后新增

生成组件前，必须建立 `reuse-map.json`，记录：

- 已搜索的现有组件；
- 可以直接复用的组件；
- 需要组合封装的组件；
- 新建组件的必要理由。

### 3. 视觉验证不只做截图差异

同时检查：

- 目标视口下的元素边界；
- 文本截断和溢出；
- sticky/fixed 元素遮挡；
- 弹窗和下拉层级；
- 加载前后的布局抖动；
- 真实图片、字体和图标是否加载；
- 页面是否存在空白画布或不可点击区域。

### 4. 强制交互状态矩阵

每个异步操作至少验证：

```text
idle → submitting → success
idle → submitting → business_error
idle → submitting → network_error
```

并验证重复提交、取消、关闭、刷新和返回后的状态行为。

## 七、失败恢复

每一步都写入 `executor.jsonl`，包含：

- 当前状态；
- 执行命令；
- 输入和输出摘要；
- commit SHA；
- 失败类型和指纹；
- 下一恢复节点。

进程中断后从最后一个已通过门禁恢复，而不是重新规划全部任务。失败分为输入、代码、环境、测试、视觉、治理和基础设施七类，各自拥有固定修复路由和重试预算。

## 八、最终交付物

```text
.omc/tasks/<task-id>/
├── task.yaml
├── research.md
├── plan.md
├── assumptions.yaml
├── reuse-map.json
├── executor.jsonl
├── gate-results.json
├── ac-results.json
├── test-results/
├── screenshots/
├── evidence-manifest.json
└── final-report.md
```

`evidence-manifest.json` 中每项证据都包含文件哈希、测试结果和 commit SHA。修改代码后旧证据自动失效，必须重新验证。

## 九、落地策略

我不会一开始就开放全自动。版本成熟度分四级：

- **L0 影子执行**：只分析和生成计划，不改代码；
- **L1 受限执行**：单页面、Mock、禁止修改共享模块，只生成 Draft PR；
- **L2 标准执行**：允许多个低风险页面和已有 API 接入；
- **L3 扩展执行**：经过授权后才允许共享组件、路由和全局状态修改。

升级依据不是运行次数，而是量化指标：零越界率、AC 有证据通过率、Draft PR 可审率、恢复成功率、视觉误报率和人工返工量。

## 与 Grok-4.5、Opus-4.8 的核心区别

Grok-4.5 更像风险审计补丁，Opus-4.8 更像完整治理设计。我的版本会把两者进一步工程化：

- 把自然语言原则编译成 `task.yaml`；
- 把执行过程变成不可跳步的状态机；
- 把模型裁决改成策略引擎和 J0 优先级；
- 把“完成”改成证据绑定后的系统状态；
- 把失败重试改成分类路由、预算和熔断；
- 把前端视觉验收扩展为布局、资源、交互和多视口联合验证。

一句话概括：

> **我的方案不是追求 AI 无论如何都完成任务，而是让 AI 在授权范围内自主完成，并让每一个“完成”都可以由机器复验、由证据追溯、由提交回滚。**

这才是我认为可以逐步走向真正无人值守的版本。
