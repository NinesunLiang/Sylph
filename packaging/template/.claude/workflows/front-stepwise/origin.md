明白。你要的不是一次性灌入一份超长 Prompt，而是一个**状态机式“抽卡工作流”**：

- 每次只展示、执行一张卡；
- Agent 能自行检查的信息优先自行检查；
- 只有无法从代码、Git、配置、测试中确认时才询问用户；
- 卡片完成后生成结构化记录；
- 满足退出条件后，才能抽下一张；
- 如果发现风险，则进入“异常卡”，不能带病推进；
- 最终通过验证卡和交付卡形成闭环。

下面给你一套可以直接使用的 **前端需求治理卡组**。

---

# 一、卡片工作流总览

```text
C00 启动卡
  ↓
C01 工作区基线卡
  ↓
C02 需求澄清卡
  ↓
C03 模块定位卡
  ↓
C04 依赖与数据流卡
  ↓
C05 影响面卡
  ↓
C06 方案选择卡
  ↓
C07 变更契约卡
  ↓
C08 实施卡（可循环）
  ↓
C09 机械验证卡
  ↓
C10 独立审查卡
  ↓
C11 影响回归卡
  ↓
C12 仓库清洁卡
  ↓
C13 用户验收卡
  ↓
C14 交付闭环卡
```

异常分支：

```text
任意卡片
  ├─ 信息不足 → Q01 用户问询卡
  ├─ 发现越界 → X01 范围升级卡
  ├─ 基线失败 → X02 基线异常卡
  ├─ 公共契约变化 → X03 兼容性决策卡
  ├─ 验证失败 → X04 修复决策卡
  └─ 用户改动冲突 → X05 工作区冲突卡
```

这里最重要的规则是：

> **Agent 不应该因为“可能要问用户”就立即提问。先检查仓库中是否存在答案；只有无法可靠确定、存在多种产品语义，或者需要扩大修改范围时，才抽用户问询卡。**

---

# 二、统一卡片结构

每张卡都使用相同的数据结构，便于 Claude Code、OpenCode 或自研工作流执行。

```yaml
card:
  id: C00
  title: 启动卡
  status: pending # pending | active | blocked | passed | failed
  objective: 本卡要解决的唯一问题

  inputs:
    required: []
    inherited: []

  auto_checks:
    - Agent 可以自行执行的检查

  user_questions:
    policy: only_if_unresolved
    questions: []

  outputs:
    required: []

  evidence:
    - file_path
    - symbol
    - command_result
    - user_decision

  exit_criteria:
    - 本卡通过条件

  failure_routes:
    unresolved: Q01
    scope_violation: X01

  next_card: C01
```

## 信息来源优先级

每张卡必须按下面的顺序找答案：

```text
1. 当前用户已经明确提供的信息
2. 项目治理文档：CLAUDE.md / AGENTS.md / README
3. package.json、配置文件、源码和测试
4. Git diff、Git history、语言服务和引用搜索
5. 自动化命令的实际结果
6. 合理推断，但必须标记为“待确认”
7. 最后才询问用户
```

不能用推断替代产品决策。例如：

- “项目用 pnpm”通常可自行检查；
- “这个按钮点击后是否关闭弹窗”属于产品语义，代码与需求冲突时应询问用户；
- “能不能修改公共 hook”属于范围决策，必须获得批准。

---

# 三、运行时只展示一张卡

每轮回复建议固定采用以下界面：

```md
## 当前卡片：C03 模块定位卡

### 本卡目标
定位需求对应的页面入口、模块边界和现有实现。

### 已继承信息
- 需求：……
- 目标页面：……
- 基线状态：……

### 我可以自行检查
- 搜索页面文案和路由入口
- 查找目标组件引用
- 阅读相邻模块和测试

### 需要用户回答
当前不需要，我会先自行检查。

### 执行结果
- 页面入口：`src/...`
- 主组件：`FooPage`
- 证据：……

### 本卡结论
PASS

### 下一张
C04 依赖与数据流卡
```

如果真的需要用户回答，就停在当前卡：

```md
## 当前卡片：Q01 用户问询卡

我已检查：
- `src/...`
- `src/...`
- 现有测试……

仍无法确定以下产品行为：

**问题 1：保存成功后应该怎么处理？**

A. 保持弹窗打开，并显示成功状态  
B. 关闭弹窗并刷新列表  
C. 关闭弹窗，但不自动刷新  
D. 其他：请说明

建议：B  
原因：相邻模块均采用 B，但当前需求没有明确说明。

请回复选项。确认前我不会修改代码。
```

---

# 四、主卡组

## C00：启动卡

### 目标

建立任务容器，只收集任务最小入口信息，不分析、不改代码。

### Agent 自行检查

- 当前目录是否为 Git 仓库；
- 是否存在 `CLAUDE.md`、`AGENTS.md`、`README.md`；
- 是否存在 `package.json`；
- 当前分支；
- 当前工作区状态。

### 只有以下情况才问用户

- 用户没有提供任何需求；
- 不知道目标项目或目标目录；
- 同时存在多个独立前端项目，无法判断目标；
- 用户要求与仓库内容明显不一致。

### 输出

```yaml
task:
  summary: ""
  repository: ""
  target_area: unknown
  user_constraints: []
  initial_risks: []
```

### 退出条件

```text
[ ] 已获得一句话需求
[ ] 已确定目标仓库
[ ] 已记录用户明确禁区
```

下一张：`C01 工作区基线卡`

---

## C01：工作区基线卡

### 目标

确定“修改前”的仓库状态，防止覆盖用户改动或把旧问题误认为新回归。

### Agent 自行检查

```bash
git status --short
git branch --show-current
git diff --stat
git diff --name-only
```

并读取：

```text
package.json
package manager lockfile
TypeScript 配置
lint 配置
test 配置
build 配置
```

如果成本可接受，执行现有项目脚本，但不能使用自动修复参数。

### 需要询问用户的条件

- 目标文件已经有用户未提交修改；
- 工作区存在大量未知修改，无法区分归属；
- 基线验证失败且会妨碍本任务判断；
- 当前处于受保护分支，而流程要求新建分支。

### 输出

```yaml
baseline:
  branch: ""
  package_manager: ""
  dirty_files: []
  user_owned_changes: []
  commands:
    typecheck: ""
    lint: ""
    test: ""
    build: ""
  existing_failures: []
```

### 退出条件

```text
[ ] 已记录修改前 Git 状态
[ ] 已识别包管理器
[ ] 已识别验证命令
[ ] 已区分用户已有改动
[ ] 没有覆盖风险
```

若发现冲突：进入 `X05 工作区冲突卡`。  
否则下一张：`C02 需求澄清卡`。

---

## C02：需求澄清卡

### 目标

把自然语言需求转成可验证的行为，不讨论实现方案。

### Agent 自行检查

- 搜索需求提到的文案、页面、组件名称；
- 查看当前 UI 行为；
- 查看相邻功能的交互模式；
- 查看已有测试表达的业务规则；
- 查看类型、接口和 mock 数据。

### 应确认的信息

```yaml
requirement:
  actor: 谁使用
  trigger: 通过什么操作触发
  expected_behavior: 预期发生什么
  visible_result: 用户看到什么
  failure_behavior: 失败时看到什么
  loading_behavior: 加载时看到什么
  empty_behavior: 无数据时看到什么
  out_of_scope: 明确不做什么
```

### 何时询问用户

只有存在以下“产品决策”时询问：

- 两种实现都符合现有代码，无法确定预期；
- 需求与现有行为冲突；
- 成功、失败、空状态未定义且会直接影响用户；
- 是否保持向后兼容无法从代码确定；
- 验收标准无法客观判断。

### 输出示例

```yaml
requirement:
  actor: 管理员
  trigger: 点击编辑弹窗中的保存按钮
  expected_behavior:
    - 提交修改后的表单
    - 成功后关闭弹窗
    - 刷新当前列表
  failure_behavior:
    - 保持弹窗和用户输入
    - 显示现有错误提示
  out_of_scope:
    - 不修改权限
    - 不修改路由
    - 不新增批量编辑
  unresolved: []
```

下一张：`C03 模块定位卡`。

---

## C03：模块定位卡

### 目标

准确定位页面入口、功能模块和模块边界。

### Agent 自行检查

- 搜索路由；
- 搜索页面文案；
- 搜索组件引用；
- 查找入口组件；
- 查找相邻测试和 Storybook；
- 使用语言服务查找 definition/references。

### 输出

```yaml
module:
  route_entry: ""
  page_entry: ""
  primary_component: ""
  private_components: []
  shared_components: []
  related_tests: []
  related_stories: []
  ownership_boundary: ""
```

每项都必须附证据：

```text
`UserEditDialog`
- 定义：src/features/users/UserEditDialog.tsx:28
- 引用：src/features/users/UserPage.tsx:114
- 范围：users 模块私有
```

### 退出条件

```text
[ ] 找到页面或功能入口
[ ] 找到主要组件
[ ] 区分模块私有资源和共享资源
[ ] 找到相关测试，或确认不存在
```

下一张：`C04 依赖与数据流卡`。

---

## C04：依赖与数据流卡

### 目标

回答数据从哪里来、如何渲染、如何修改、如何回到 server。

### Agent 自行检查

沿调用链跟踪：

```text
页面入口
→ 组件
→ 事件处理器
→ hook / store action
→ mapper / serializer
→ API client
→ server
→ response parser
→ cache / store
→ UI 重渲染
```

同时检查：

- loading/error/empty/success；
- 缓存 key；
- optimistic update；
- query invalidation；
- URL 状态；
- 表单默认值；
- API 类型和 UI 类型之间的转换。

### 输出

```yaml
data_flow:
  reads:
    - source: ""
      path: []
      destination: ""
  writes:
    - trigger: ""
      path: []
      server_endpoint: ""
      post_success: ""
      post_failure: ""
  state:
    readers: []
    writers: []
    defaults: []
```

### 压缩属性

本卡产生的依赖树属于事实制品，应外置保存：

- 原始代码和 Git 可恢复：**无损、可回滚**；
- 将完整调查压成摘要：**有损**；
- 摘要不得作为公共接口判断的唯一依据。

下一张：`C05 影响面卡`。

---

## C05：影响面卡

### 目标

在写代码前找出所有可能被波及的调用方。

### Agent 自行检查

针对计划可能修改的每个符号：

- 查找全部引用；
- 检查是否 export；
- 检查是否跨模块；
- 检查 props、参数、返回值；
- 检查默认值；
- 检查测试覆盖；
- 检查公共状态的读写者。

### 输出

| 符号 | 定义位置 | 调用方 | 范围 | 可否修改 | 风险 |
|---|---|---|---|---|---|
| `useUpdateUser` | `...` | A、B | 共享 | 保持契约 | 高 |
| `EditForm` | `...` | 当前页面 | 私有 | 可修改 | 低 |

将文件分成三组：

```yaml
change_boundary:
  safe_to_change: []
  compatibility_required: []
  forbidden_without_approval: []
```

### 触发异常卡

如果满足任一条件，不能直接继续：

- 需求必然要求修改公共 hook；
- 必须修改全局状态；
- 必须修改公共类型；
- 必须修改路由、权限或 API 契约；
- 必须新增依赖。

进入：`X01 范围升级卡` 或 `X03 兼容性决策卡`。

否则下一张：`C06 方案选择卡`。

---

## C06：方案选择卡

### 目标

提出最小可行方案，在修改代码前确定实现路径。

### Agent 应提供最多三个方案

```text
方案 A：模块内局部实现
方案 B：复用现有公共能力
方案 C：扩展公共抽象
```

默认优先级：

```text
现有能力直接复用
> 模块内局部组合
> 向后兼容地扩展公共能力
> 修改公共契约
> 新增依赖
```

### 每个方案必须包含

```yaml
solution:
  files_to_change: []
  files_to_add: []
  public_contract_changes: []
  benefits: []
  risks: []
  verification: []
```

### 是否需要用户确认

可以自动选择方案的条件：

- 只有一个明显符合现有 pattern 的方案；
- 不修改公共资源；
- 不引入依赖；
- 不改变用户未说明的行为；
- 修改范围局部且可逆。

必须询问用户的条件：

- 不同方案会产生不同用户行为；
- 需要改变公共契约；
- 需要新增依赖；
- 需要修改受保护文件；
- 需要在技术债务和局部重复之间做产品级取舍。

下一张：`C07 变更契约卡`。

---

## C07：变更契约卡

### 目标

冻结本次允许修改的内容。这是实施前的硬门禁。

### 自动生成契约

```yaml
change_contract:
  task: ""
  allowed_files: []
  allowed_new_files: []
  protected_files:
    - package.json
    - lockfiles
    - routing
    - permissions
    - global_state
    - build_config

  contracts_to_preserve:
    props: []
    hook_returns: []
    function_signatures: []
    api_payloads: []
    api_responses: []
    defaults: []
    cache_keys: []

  acceptance_criteria: []
  verification_commands: []

  stop_conditions:
    - 需要修改 allowed_files 以外的文件
    - 需要改变公共接口
    - 需要新增依赖
    - 发现需求与现有行为冲突
```

### 给用户展示的简化版本

```md
## 计划修改

- `src/features/users/UserEditDialog.tsx`
  - 增加需求要求的交互
- `src/features/users/UserEditDialog.test.tsx`
  - 覆盖成功和失败场景

## 明确不修改

- 路由
- 权限
- 全局状态
- 公共 hook 的返回结构
- API payload
- package.json 和 lockfile

## 验收标准

- [ ] 保存成功后关闭弹窗并刷新列表
- [ ] 保存失败后保留输入
- [ ] 不影响其他调用方
- [ ] 相关验证通过
```

如果前面所有信息都明确、没有公共风险，可自行冻结并继续；否则等待用户确认。

下一张：`C08 实施卡`。

---

## C08：实施卡

### 目标

一次只实现一个逻辑单元，而不是一口气改完整个需求。

这张卡可以循环抽取：

```text
C08.1 UI 结构
C08.2 状态和事件
C08.3 请求与回写
C08.4 错误和边界状态
C08.5 测试
```

### 每次实施卡规则

```yaml
implementation_unit:
  objective: ""
  files: []
  expected_diff: ""
  local_verification: ""
```

执行前：

```text
[ ] 当前文件在 allowed_files 中
[ ] 文件没有未处理的用户修改冲突
[ ] 不需要扩大公共契约
```

执行后：

```text
[ ] 检查本逻辑单元 diff
[ ] 运行最小相关验证
[ ] 未出现越界文件
[ ] 未出现自动格式化扩散
```

### 立即停止条件

- 实际代码结构与调查结论不同；
- 需要修改契约外文件；
- 需要改变公共默认值；
- 需要新增依赖；
- 需要用 `any`、`ts-ignore` 等规避错误；
- 出现无法解释的测试失败。

所有实施单元完成后进入 `C09`。

---

## C09：机械验证卡

### 目标

用工具证明改动没有引入基础质量问题。

### 验证顺序

```text
1. git diff --check
2. changed-files lint
3. targeted test
4. typecheck
5. project lint
6. broader test
7. build
```

只运行项目已有命令，不猜测、不中途自动修复。

### 输出

| 检查项 | 修改前 | 修改后 | 新增回归 | 结果 |
|---|---|---|---|---|
| Typecheck | PASS | PASS | 否 | PASS |
| Target test | PASS | PASS | 否 | PASS |
| Build | PASS | PASS | 否 | PASS |

### 失败处理

验证失败时不能默默修复，先分类：

```yaml
failure:
  category:
    - pre_existing
    - caused_by_change
    - environmental
    - unknown
  evidence: []
  proposed_action: ""
```

- 明确由本次改动造成且修复在契约内：抽新的 `C08 修复卡`；
- 需要扩大范围：进入 `X04 修复决策卡`；
- 属于基线问题：记录，不把它伪装成通过。

下一张：`C10 独立审查卡`。

---

## C10：独立审查卡

### 目标

由没有参与实现上下文的 Reviewer 审查实际 diff。

### 检查范围

```text
1. 是否偏离相邻模块写法
2. 是否出现无关重构
3. 是否修改公共资源
4. 是否重复造轮子
5. 是否改变默认值或错误行为
6. 是否有 stale state、竞态或重复提交
7. 是否破坏 a11y、responsive、dark mode
8. 测试是否只覆盖实现细节
```

### 输出严重度

```text
BLOCKER：会造成错误、安全问题或公共契约破坏
HIGH：较大概率导致回归
MEDIUM：维护性或边界场景问题
LOW：非阻塞建议
```

每项都必须带：

- 文件和行号；
- 证据；
- 影响；
- 最小修复建议。

不能为了“显得认真”强行找问题。如果没有问题，明确输出：

```text
未发现阻塞问题。
剩余验证盲区：……
```

下一张：`C11 影响回归卡`。

---

## C11：影响回归卡

### 目标

从实际 diff 反向枚举所有变更符号，确认没有影响其他地方。

### 自动检查

对每个变更符号检查：

```text
定义位置
全部调用方
export 变化
props 变化
参数变化
返回类型变化
默认值变化
null/undefined 行为变化
请求结构变化
缓存 key 变化
副作用时序变化
现有测试覆盖
```

### 输出

| 变更符号 | 调用方 | 契约改变 | 测试覆盖 | 风险 |
|---|---|---|---|---|

注意：

> 类型兼容不等于行为兼容。默认值、请求时机、错误处理和副作用顺序都必须单独检查。

下一张：`C12 仓库清洁卡`。

---

## C12：仓库清洁卡

### 目标

保证项目没有被分析产物、生成文件或无关改动污染。

### 自动检查

```bash
git status --short
git diff --stat
git diff --check
git diff --name-only
```

检查：

- `package.json`；
- lockfile；
- 临时 HTML；
- coverage；
- dist/build；
- 日志；
- 截图；
- snapshot；
- `console.log`；
- `debugger`；
- `TODO/FIXME`；
- `ts-ignore`；
- `eslint-disable`；
- 大范围格式化。

### 输出分类

```yaml
repository_cleanliness:
  intended_changes: []
  unintended_changes: []
  generated_files: []
  user_owned_files: []
  dependency_changes: []
  cleanup_required: []
```

注意：不能自行删除无法确认归属的用户文件。

下一张：`C13 用户验收卡`。

---

## C13：用户验收卡

### 目标

将技术完成转换成用户可操作的验收步骤。

### 如果可以自行验证

Agent 应先自行完成：

- 浏览器自动化；
- 组件测试；
- Storybook；
- 截图对比；
- dev server 页面检查。

### 只有以下情况才交给用户

- 需要用户账户、私有环境或 MFA；
- 需要主观视觉判断；
- 需要真实外部服务；
- 产品行为必须由用户确认；
- Agent 无法访问浏览器环境。

### 用户验收格式

```md
## 请验收以下行为

前置条件：
1. 启动项目：`pnpm dev`
2. 打开：`/users`

操作：
1. 打开任意用户的编辑弹窗
2. 修改名称
3. 点击保存

预期：
- 保存期间按钮禁用
- 成功后弹窗关闭
- 列表显示新名称
- 失败时弹窗保持打开，输入不丢失

请回复：
- `通过`
- 或描述不符合预期的步骤
```

下一张：`C14 交付闭环卡`。

---

## C14：交付闭环卡

### 目标

输出最终可审计交付记录。

### 最终输出

```yaml
delivery:
  requirement: ""
  changed_files: []
  behavior_changes: []
  preserved_contracts: []
  tests_added_or_updated: []
  validation_results: []
  user_acceptance: ""
  known_limitations: []
  rollback_boundary: ""
  final_status:
    - READY
    - READY_WITH_KNOWN_LIMITATIONS
    - NOT_READY
```

最终必须回答四个问题：

1. 改了什么？
2. 为什么这些文件必须改？
3. 如何证明没有影响其他地方？
4. 还有什么没有被验证？

---

# 五、异常卡组

## Q01：用户问询卡

一次只问**一个决策主题**，避免把十个问题一起丢给用户。

```md
## 需要你决定

### 已确认事实
- ……
- ……

### 无法自行确定
保存成功后是否关闭弹窗。

### 可选项
A. 关闭并刷新列表  
B. 保持打开并显示成功提示  
C. 关闭但不刷新

### 我的建议
A

### 原因
同模块另外两个编辑弹窗均采用 A。

确认前不会继续实施。
```

用户回答后，将结论写回对应主卡，而不是只留在聊天记录里。

---

## X01：范围升级卡

触发条件：实际实现必须修改契约外文件。

```md
## 发现需要扩大修改范围

原允许范围：
- `A.tsx`
- `A.test.tsx`

新发现：
- 现有能力由共享 hook `useFoo` 固定控制
- 不修改该 hook 无法满足需求

选择：
A. 批准向后兼容地扩展共享 hook  
B. 采用模块内局部实现，接受少量重复  
C. 暂停任务重新设计

建议：B  
原因：当前共享 hook 有 6 个外部调用方，扩展会扩大回归面。
```

---

## X02：基线异常卡

当修改前就有失败：

```text
[ ] 失败是否与目标模块相关
[ ] 是否阻止验证本次需求
[ ] 是否可以通过 targeted test 绕开
[ ] 是否需要用户先处理基线
```

不得顺手修复无关基线问题。

---

## X03：兼容性决策卡

适用于：

- 公共 props；
- hook 返回值；
- API payload；
- 默认值；
- 公共状态；
- 缓存 key。

必须对比：

```text
旧契约
新契约
调用方数量
迁移成本
兼容方案
测试覆盖
```

---

## X04：修复决策卡

验证失败时，先决定：

```text
A. 契约内最小修复
B. 扩大范围修复
C. 回滚当前实现并换方案
D. 记录为环境/基线限制
```

未经确认不得用配置关闭错误。

---

## X05：工作区冲突卡

发现用户未提交改动与目标文件重叠时：

```text
[ ] 不 reset
[ ] 不 checkout 覆盖
[ ] 不 stash 用户改动，除非用户授权
[ ] 展示重叠文件
[ ] 说明可安全继续还是需要隔离 worktree
```

---

# 六、卡片控制器 Prompt

下面这段可以作为整个工作流的总 Prompt。它不会把所有任务同时执行，而是控制“每轮只抽一张”。

```xml
<role>
你是前端变更治理 Agent。你通过顺序抽取卡片完成需求调查、实施、验证和交付。

你的首要目标：
1. 满足明确需求；
2. 保持项目干净；
3. 不引入新增坏点；
4. 不覆盖用户已有修改；
5. 所有重要结论都可由代码、Git、命令或用户决定追溯。
</role>

<card-engine>
主卡顺序：

C00 启动
C01 工作区基线
C02 需求澄清
C03 模块定位
C04 依赖与数据流
C05 影响面
C06 方案选择
C07 变更契约
C08 实施
C09 机械验证
C10 独立审查
C11 影响回归
C12 仓库清洁
C13 用户验收
C14 交付闭环

异常卡：
Q01 用户问询
X01 范围升级
X02 基线异常
X03 兼容性决策
X04 修复决策
X05 工作区冲突
</card-engine>

<execution-rules>
- 每轮只激活一张卡。
- 不得跳过尚未通过的硬门禁卡。
- 优先自行检查仓库，再询问用户。
- 能从代码、配置、测试、Git 或命令确定的信息，不询问用户。
- 涉及产品语义、公共契约、范围扩大、依赖变化或用户文件冲突时，必须询问用户。
- 每张卡只解决一个阶段问题。
- 卡片完成后必须输出证据、结论和下一张卡。
- 如果卡片未满足退出条件，状态必须是 BLOCKED，不能假装通过。
- 调查、Review 卡只读。
- 未通过 C07 变更契约卡，不得修改业务代码。
- 未通过 C09 机械验证卡，不得宣称任务完成。
- 未通过 C12 仓库清洁卡，不得进入最终交付。
</execution-rules>

<change-safety>
- 不新增依赖，除非用户明确批准。
- 不修改 package.json 或 lockfile，除非需求明确要求且用户批准。
- 不修改路由、权限、全局状态、公共 hook 或公共类型，除非通过范围升级卡。
- 不运行全仓库自动格式化。
- 不使用 any、ts-ignore、eslint-disable、跳过测试等方式隐藏问题。
- 不删除、reset、checkout 或覆盖用户已有改动。
- 临时架构图、日志和分析制品默认写到仓库外。
</change-safety>

<response-format>
## 当前卡片：<ID> <标题>

### 本卡目标
<唯一目标>

### 已继承信息
<前序卡片已经确认的信息>

### 自动检查
<本轮自行检查了什么>

### 证据
<文件、符号、命令结果或用户决定>

### 仍未确定
<无则写“无”>

### 本卡结论
PASS | BLOCKED | FAILED

### 下一步
<下一张卡；如果需要用户回答，只提出本卡必要问题>
</response-format>

<start>
从 C00 启动卡开始。
如果用户已经提供了足够的启动信息，可以自行完成 C00，但本轮仍然只处理 C00，不得同时执行后续卡片。
</start>
```

---

# 七、Claude Code 路径

Claude Code 推荐采用：

```text
主会话：卡片控制器和用户决策
Subagent 1：C03-C05 调查
Subagent 2：C10 独立审查
Subagent 3：C11 影响分析
```

规则：

- C03–C05 的大量工具结果先落盘，只把结论返回主会话：**无损可回滚**；
- Subagent 使用 fresh context，避免调查内容污染实施上下文；
- C07 变更契约必须写入任务制品或 `CLAUDE.md` 邻近任务记录；
- L5 AutoCompact 是 **有损不可逆**，不能仅依赖它保存卡片状态；
- 同一工具结果预览必须稳定复用，避免破坏 prompt cache。

推荐卡片状态文件放在仓库外：

```text
~/.local/state/ai-workflows/<repo>/<task-id>/state.yaml
```

如果确实需要入库，应放项目已有治理目录，并经过用户批准。

---

# 八、OpenCode 路径

OpenCode 推荐三会话：

```text
session: governance-controller
session: implementation
session: independent-review
```

- `governance-controller`：运行 C00–C07、C12–C14；
- `implementation`：只执行 C08 和 C09；
- `independent-review`：执行 C10 和 C11。

同一 working tree 下：

- 只能有一个写会话；
- 调查和 Review 会话保持只读；
- 需要并行写时使用 Git worktree，不能让多个会话抢同一文件。

OpenCode Prune 是**非物理删除、可审计回溯**，可以保留完整卡片执行历史；但 LLM 摘要仍是**有损压缩**。以下内容必须结构化外置：

```yaml
current_card: C08
passed_cards: [C00, C01, C02, C03, C04, C05, C06, C07]
allowed_files: []
protected_files: []
baseline_failures: []
user_decisions: []
validation_results: []
unresolved_risks: []
```

---

# 九、建议的可观测指标

卡片工作流应该记录：

| 指标 | 目标 |
|---|---:|
| 平均每张卡用户提问数 | 越低越好，但不能牺牲决策准确性 |
| 可自行检查的问题占比 | ≥80% |
| 卡片跳过率 | 0% |
| 越界修改次数 | 0 |
| 工作区冲突未提前发现次数 | 0 |
| 新增 lint/type/test 回归 | 0 |
| 公共契约未声明变化 | 0 |
| 验证失败后越界修复次数 | 0 |
| 临时产物进入 Git 次数 | 0 |
| 独立 Review 覆盖率 | 高风险任务 100% |
| prompt cache hit rate | 持续监控 |
| compaction 次数/session | 越低越好 |
| 有损 compaction 占比 | 尽量低 |
| Claude Code L5 占比 | 接近 0 |
| token $/task | 按卡片、模型分别统计 |

---

# 十、最小可用版本

如果你觉得 15 张主卡过多，可以先落地成 8 张：

```text
1. 启动与基线卡
2. 需求澄清卡
3. 模块调查卡
4. 影响面与方案卡
5. 变更契约卡
6. 实施卡
7. 验证与审查卡
8. 清洁与交付卡
```

但我更推荐完整卡组，因为你要实现的是“逐张抽取、每步闭环”，而不是简单的 Prompt 分段。完整版本能明确区分：

```text
事实调查
≠ 产品决策
≠ 技术设计
≠ 范围授权
≠ 实施
≠ 自动验证
≠ 独立审查
≠ 用户验收
```

其核心运行原则可以压缩成一句话：

> **一次只抽一张卡；能检查就不问，不能决定才问；当前卡未闭环，绝不进入下一张。**