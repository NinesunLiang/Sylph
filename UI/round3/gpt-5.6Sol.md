**审核结论：Conditional Sign-off，暂不允许直接落盘首夜运行。**

整体架构已经收敛，以下裁决我同意：

- 执行时无高阶模型，J0 只负责选择出口并留证；
- 首夜串行、最多 3 页、Patch A、Draft PR only；
- 使用单一 `night-manifest.yaml` 作为声明式契约；
- C3 放在 C4/C5 前，便宜门禁优先；
- L0 可选，不要求影子周；
- 不为首夜另建一套状态机。

但 E1–E10 修复方案中仍有 **4 个阻断级问题、6 个重要问题**。这些问题修完并通过集成 smoke 后，我才会签署首夜 `GO`。

**阻断级发现**

### P0-1：E9 提议的 `sed` 仍然提取不到 YAML

你给出的命令：

```bash
sed -n '/## 11\. machine_summary/,/```/p'
```

会从标题开始，在遇到**第一个开围栏** `` ```yaml `` 时立即结束，输出大致只有：

```markdown
## 11. machine_summary（脚本专用，禁止手改）
```yaml
```

真正字段全部被排除。因此 E9 目前仍未修复，晨报仍会得到空值。

应使用结构化 YAML 文件，或者正确提取两个围栏之间的内容。例如：

```bash
awk '
  /^## 11\. machine_summary/ { section=1; next }
  section && /^```yaml$/ { yaml=1; next }
  yaml && /^```$/ { exit }
  yaml { print }
' "$REPORT"
```

但我更建议不要从 Markdown 中反向解析。机器真相应直接写入：

```text
.omc/tasks/<id>/machine-summary.yaml
```

`acceptance_report.md` 只负责展示，由 `machine-summary.yaml` 渲染生成。否则所谓“单一真相源”在报告层又变回 Markdown 和 YAML 块两份表达。

### P0-2：证据绑定 `HEAD` 存在提交循环，E6 方案不可稳定成立

流程中截图发生在代码提交之后，随后至少还会产生：

- `acceptance_report.md`；
- `machine-summary.yaml`；
- screenshots 或 trace；
- `token.json` / `executor.md`；
- 证据清单或 archive commit。

一旦证据被提交，`HEAD` 就从代码提交 A 变成证据提交 B。若报告绑定 A，检查 `binding_sha == HEAD` 会失败；若先写 B，再把 B 填进报告，则修改报告又产生 C。这是经典的自引用提交问题。

需要拆成两个 SHA：

```yaml
code_sha: <最后一次影响运行行为的提交>
evidence_commit_sha: <可选，证据提交完成后由交付层记录>
```

证据新鲜度应验证：

```bash
git diff --quiet "$code_sha"..HEAD -- \
  src/ package.json pnpm-lock.yaml vite.config.* playwright.config.*
```

含义是：从取证时的 `code_sha` 到当前交付 HEAD，所有会影响实现和测试环境的路径不得变化。不要要求 `code_sha == HEAD`。

首夜可以暂不加证据文件 `sha256`，但必须至少记录：

- `code_sha`；
- 证据相对路径；
- 文件存在性；
- 文件非空；
- 生成时间；
- 对应 AC；
- Playwright run ID 或测试结果路径。

### P0-3：结果枚举发生硬冲突

文档先规定只有：

```text
DONE / BLOCKED / FAILED
```

后面又规定：

```text
DONE_WITH_ASSUMPTIONS
```

这会导致状态机、晨报聚合和晋升指标对同一结果产生不同解释。尤其“七态缺任一最多 DONE_WITH_ASSUMPTIONS”会让未满足硬 AC 的任务以完成态出现，违反证据完成制。

建议保持三种顶级结果不变：

```yaml
final_status: DONE | BLOCKED | FAILED
completion:
  qualified: true | false
  assumptions_present: true | false
```

规则应明确：

- 假设不影响硬 AC：允许 `DONE + assumptions_present: true`；
- 缺少任何 required state 或硬 AC：只能 `BLOCKED`；
- 工程、环境或执行异常：`FAILED`。

不能用 `DONE_WITH_ASSUMPTIONS` 吸收未通过的七态验收。

### P0-4：`machine_summary` 仍可由执行模型自行宣称，证据链不可信

模板写“禁止手改”不能构成控制。夜间执行模型本身就在修改工作区，它完全可以填写：

```yaml
final_status: DONE
ac_passed: 14
```

而 morning-report 只负责聚合，不会发现这些值是否来自真实门禁。

`machine-summary.yaml` 必须由控制脚本生成，字段来源固定：

- `final_status`：由状态机终态推导；
- `ac_total/ac_passed`：由 evidence-check 结果推导；
- `branch`：来自 `git branch --show-current`；
- `code_sha`：来自取证节点；
- `model_calls_total`：来自执行日志聚合；
- `draft_pr_url`：来自 `gh pr create` 返回值；
- `blocked_code`：来自合法阻塞事件；
- `wall_clock_min`：由时间戳计算。

报告模板不能成为这些字段的输入源。

**重要发现**

### P1-1：我反对将 Playwright spec 放进 `src/pages/**/__e2e__`

这不是合理的 C1 修复，而是为了适配脚本限制而改变代码组织。风险包括：

- 测试文件进入 TypeScript 应用扫描范围；
- 被 ESLint、coverage、构建工具或 IDE 项目错误纳入；
- Playwright 的 Node 类型与浏览器源码类型冲突；
- `import.meta.glob` 等宽匹配可能把测试纳入生产图；
- 页面删除、移动时测试发现规则容易漂移；
- 集中测试报告与 CI shard 配置更复杂。

保留：

```text
tests/e2e/<domain>.spec.ts
```

让 C1 从 manifest 的 `paths.spec` 读取许可路径。引入 YAML 解析器不是缺点，系统本来就在消费 YAML；持续用 `grep/sed` 解析嵌套 YAML 才是风险。

推荐使用仓库已有 YAML 解析能力，或者由 `carros_base.py` 统一读取并输出规范化 JSON，Shell 脚本只消费 JSON。

### P1-2：E2 的 untracked 检查范围不完整且会误伤基线

只检查：

```bash
git ls-files --others --exclude-standard -- src/
```

会漏掉：

- `tests/e2e/`；
- 根目录配置；
- 新增脚本；
- 未授权的 `.omc` 契约修改；
- `package.json` 之外的新依赖配置。

同时，它可能把任务开始前用户已有的未跟踪文件算成本任务违规。

正确做法是：

1. Phase 0 明确要求干净工作树，或记录 baseline；
2. C1 检查全仓库新增文件；
3. 仅对明确证据目录、测试产物目录做白名单；
4. 路径判断使用 NUL 分隔，兼容空格和特殊字符。

```bash
git ls-files --others --exclude-standard -z
git diff --name-only -z "$BASE_SHA"
```

### P1-3：UI policy 的 grep 实现可绕过，也会误报

下面的扫描不足以承担 C3 硬门：

```bash
grep -rn "from ['\"]antd"
```

它会漏掉：

```ts
import Button from 'antd/es/button';
const antd = await import('antd');
const Button = require('antd').Button;
export { Button } from 'antd';
```

也可能命中注释和字符串。应使用 ESLint 的 `no-restricted-imports` 或 AST 棄查，并覆盖 `antd` 与 `antd/*`。

同理，`:global` / `!important` 应只扫描 **diff 新增行** 和受控样式文件，不能扫描整个目录或包含删除行的普通 diff，否则历史代码会阻塞新任务。

### P1-4：E3/E5 的正则修复仍不可靠

魔法 px 正则仍可能：

- 命中字符串、注释、媒体查询；
- 漏掉 `.5px`、`2.0px`；
- 对合法图标尺寸、阴影和设计要求一刀切。

裸色正则仍会漏掉：

```css
color /* reason */: #fff;
--local-color: #fff;
background: linear-gradient(#fff, #000);
```

也会误判 JS 条件或普通字符串。首夜可暂用正则，但必须定义为“启发式治理门”，提供结构化 allowlist，而不是宣称精确检查。长期应使用 Stylelint/PostCSS AST 与 ESLint AST。

### P1-5：E7 的签署检查不能继续使用宽泛 grep

```bash
grep -E 'go_nogo:\s*"?(GO|CONDITIONAL_GO)"?'
```

可能匹配注释、示例、其他页面字段，且没有确认：

- 字段确实位于 `human_signoff` 下；
- signer 非空；
- signed_at 合法；
- manifest 签署后未被修改。

签署至少应绑定 manifest 内容摘要：

```yaml
human_signoff:
  decision: GO
  signer: "..."
  signed_at: "..."
  manifest_digest: "sha256:..."
```

`lx-goal on` 前重新计算 digest。否则签署后 pages、risk、scope 被改动仍可运行。

### P1-6：状态映射遗漏 C1，且终态命名混合“阶段”和“结果”

表中从 `IMPLEMENTING` 直接进入 `STATIC_VERIFIED`，没有显式表示 C1 已通过。恢复时系统无法区分：

- 实现已提交但未检查范围；
- 范围已通过，可以进入 C2。

至少增加 `SCOPE_VERIFIED`，或者在 token 中记录正交 gate 状态：

```yaml
state: IMPLEMENTING
gates:
  C1: PASS
  C2: PENDING
```

另外 `DRAFT_PR` 是交付产物，不应替代完成状态。建议：

```yaml
final_status: DONE
delivery_status: DRAFT_PR_CREATED | DRAFT_PR_FAILED | NOT_ATTEMPTED
```

否则页面实现与证据全部通过，但 GitHub 暂时故障时，会被误判为实现失败。

**对六个靶子的明确答复**

1. E1–E10 之外，当前最危险的是 E9 围栏提取仍错误、证据 SHA 自引用、机器摘要可伪造、签署未绑定 manifest 内容。

2. 选择集中式 `tests/e2e/`。C1 应理解 manifest 中的多个允许路径，不应通过把测试塞进生产源码树来规避解析。

3. 同意单一声明契约 `night-manifest.yaml`。但运行态不能回写 manifest。manifest 是 immutable desired state；`token.json`、gate results 是 observed state，不构成第二契约。

4. 同意 C3 在 C4/C5 前。我的原方案表格顺序不是必须保留的执行顺序。静态架构检查成本更低，提前执行更合理。

5. 同意 L0 可选。Draft PR 能验证真实编码链路，信息密度高于纯规划影子。但首夜建议只跑 1 页，成功后同夜是否继续由预签署策略决定，不能由夜间模型自行扩容。

6. 首夜可以不做证据文件 `sha256`，但只绑 `HEAD` 不成立。必须改为 `code_sha + 受控路径无变化`。反例包括 archive 更新报告、PR URL 回填、trace 重试覆盖、截图同名覆盖、格式化或自动修复在视觉验收后修改源码。

**最终裁决**

当前版本不是“第三轮可直接落盘定稿”，应标记为：

> **v2.0-rc1：架构 Sign-off，执行物件 No-Go**

完成以下事项后可升为 `v2.0-rc2` 并开始首夜：

1. 修复 machine summary 提取，最好改为独立机器文件；
2. 解决证据 SHA 自引用，采用 `code_sha` 新鲜度模型；
3. 删除 `DONE_WITH_ASSUMPTIONS` 顶级状态冲突；
4. 机器摘要改为门禁脚本生成；
5. 保留集中式 E2E，由结构化 manifest 解析扩展 C1；
6. 签署绑定 manifest digest；
7. 增加 C1 可恢复状态；
8. 对五个脚本做正向、反向、篡改、崩溃恢复四类集成测试。

这些通过后，我支持 **单页、串行、Patch A、K3 关闭、Draft PR only 的首夜 Conditional GO**。首夜不要直接跑满 3 页，先证明控制面不会漏报、误报或接受伪造证据。