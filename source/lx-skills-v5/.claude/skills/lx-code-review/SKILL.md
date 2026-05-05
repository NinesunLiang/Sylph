---

name: lx-code-review

version: v4.0.0

description: "Review & fix Go code: 8 categories, 39 rules covering error handling, go-zero patterns, concurrency, interface design, performance, robustness, observability."

when_to_use: "Use after writing Go code, before tests/commit. Trigger: 'review code', 'code review', 'check quality', 'review my changes'."

model: sonnet

argument-hint: "[file path, git ref, or function name]"

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"

---

# Go 代码质量审查

## 原子化声明

> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点

| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 从参数/git diff 解析审查目标|
|context_collector | `../../nodes/context_collector.md` | 收集框架/版本/项目惯例|
|scanner | `../../nodes/scanner.md` | 按语言专项规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | P0/P1 问题自动修复|
|verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证|
|report_generator | `../../nodes/report_generator.md` | 审查报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 审查阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema

| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 审查目标定义|
|severity | `../../schemas/atomic/severity.yaml` | P0-P3 严重度分级|
|finding | `../../schemas/atomic/finding.yaml` | 审查发现的问题项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 审查报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 审查判定 |

### 引用的 task_sys 组件

| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一 |

### 状态机

本 skill 使用**私有 scan→fix→re-scan 循环**，不引用 `orchestrator.md`。原因：代码审查是扫描+修复+验证的迭代流程。
**核心状态映射**: need_clarification → executing → [collect_context → scan → fix → re-scan] → done

### 私有节点

本 skill 无私有节点。

---

## 执行流程

### Step 0: 规范文件自检

无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用审查阶段行为约束。

```
bashtest
-f .claude/kernel.md && echo "kernel=yes" || echo "kernel=no"test -f .claude/go-style-guide.md && echo "styleguide=yes" || echo "styleguide=no"
```

缺失 → 输出引导信息，**不阻塞**（AI 使用内置通用规则 fallback）。

### Step 1: 解析审查目标

加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。
- 过滤：保留 `*.go`，排除 `*_test.go`、`vendor/`、`*.pb.go`、`mock_*.go`、`*_gen.go`、`testdata/`

### Step 2: 收集项目上下文

加载 `@../../nodes/context_collector.md`，收集：Go 版本、框架类型（go-zero/标准库）、error 处理风格、日志框架、项目规范（go-style-guide.md §4.17-§4.20）、已知问题模式（claude-next.md）。

### Step 3: 八类别并行扫描

加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的规则集（见下方）。
**强证据执行协议**：每条规则必须执行实际 grep/ast-grep 命令，引用原始输出，不可用描述替代。

#### 扫描规则集（本 skill 私有领域知识）

**类别 A — Error Handling（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| A1 | error 被吞 | P0 | AST grep: `$_ = $FN($$$)` || A2 | error 未 wrap | P1 | grep `fmt.Errorf` / `errors.Wrap` || A3 | error 消息格式 | P2 | grep `errors.New("` |
**类别 B — Concurrency Safety（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| B1 | goroutine 无生命周期控制 | P0 | AST grep: `go $FN($$$)` || B2 | mutex 无 defer Unlock | P1 | AST grep: `.Lock()` → 检查 defer || B3 | 共享变量无保护 | P1 | 分析 goroutine 闭包变量捕获 |
**类别 C — go-zero 架构（6 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| C1 | handler 含业务逻辑 | P0 | 检查 handler 文件 DB 操作 || C2 | logic 直接操作 DB | P1 | 检查 logic 文件 SQL/ORM || C3 | svc 未通过 ServiceContext 注入 | P1 | 检查全局变量或直接 new || C4 | middleware 链顺序不当 | P1 | 检查路由注册顺序 || C5 | goctl 代码不同步 | P0 | 比对 .api/.proto 与 types.go || C6 | yaml 缺安全配置 | P1 | 检查 Timeout:0 / MaxConns:0 |
**类别 D — Go 惯用法 + 接口设计（5 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| D1 | 导出函数缺 doc comment | P2 | AST: 导出函数前一行注释 || D2 | 接口过大（>5 方法） | P1 | AST grep: `type $NAME interface` || D3 | 包名与目录名不一致 | P2 | 比较 package 声明与目录名 || D4 | 接口有空实现 | P1 | AST grep: `return nil` 空方法 || D5 | 接口方法跨抽象层级 | P2 | 判断方法是否属同一业务域 |
**类别 E — 性能反模式（7 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| E1 | 循环内字符串拼接 | P1 | AST grep: 循环内 `$S += $V` string || E2 | slice append 无预分配 | P2 | 检查 `for` + `append` 模式 || E3 | 不必要的 fmt.Sprintf | P3 | grep 简单拼接模式 || E4 | map 未预分配 | P2 | 检查 `map[K]V{}` + 循环赋值 || E5 | 大 struct 值接收器 | P2 | AST grep: 值类型方法接收器 || E6 | 循环内 MustCompile | P1 | grep 循环体内 regexp.MustCompile || E7 | 热路径中 defer | P2 | 检查 for 循环体内 defer |
**类别 F — 代码结构（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| F1 | 函数超过 80 行 | P1 | 计算函数体行数 || F2 | 嵌套深度超过 4 层 | P2 | 分析缩进层次 || F3 | 重复代码块（≥10 行） | P2 | AST 结构比对 |
**类别 G — 可观测性（6 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| G1 | 错误路径无日志 | P1 | AST grep: `if err != nil` 块内无 log || G2 | 日志缺上下文 | P2 | grep 日志调用检查结构化字段 || G3 | context 未传递到日志 | P2 | AST grep: `logx.Error` 无 WithContext || G4 | 关键操作无日志 | P1 | 检查 DB/HTTP/状态机附近日志 || G5 | 日志级别不当 | P3 | 分析代码路径与级别匹配 || G6 | 缺 metric 埋点 | P2 | 检查 handler 入口 metric 调用 |
**类别 H — 鲁棒性（6 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| H1 | 公开函数指针参数无 nil 检查 | P1 | AST grep: 公开函数指针参数 || H2 | map 取值未用 comma-ok | P1 | AST grep: 单返回值 map 访问 || H3 | 类型断言无 comma-ok | P0 | AST grep: `$VAR.($TYPE)` || H4 | slice 首元素无 len 检查 | P0 | grep `\\[0\]` 检查守卫 || H5 | 资源获取后无 defer 释放 | P1 | grep FindOne/sql.Open/http.Get 检查 defer || H6 | 外部调用无超时 | P1 | grep http.Get/client.Do 检查 WithTimeout |

### Step 4: 误报排除

**误报场景**（标记为 FP，不报告）：
- 在注释或字符串中
- 有显式 `//nolint` 且理由合理
- error 已通过其他路径处理
- go-zero 生成的模板代码（goctl 产出）
- H1 中的内部函数（非公开）→ 降级为 P3
- H2 中仅读取不做分支判断 → 标记 "待确认"
不确定 → 标记 "待确认: [reason]"。

### Step 5: 生成改进建议

对每个真阳性问题：位置（file:line）+ 问题本质 + 修改建议（含代码示例）+ 是否可自动修复。排序：P0 → P1 → P2 → P3。

### Step 6: Auto-Fix（P0 + P1）

加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 以下修复策略：
| 规则 | 修复模板|
|------|---------|
|A1 error 被吞 | 添加 `if err != nil { return ..., err }`|
|B1 goroutine 无控制 | 添加 `context.WithCancel` + `select { case <-ctx.Done() }`|
|B2 mutex 无 defer | `Lock()` 后添加 `defer Unlock()`|
|D2 接口过大 | 按职责域拆分为 ≤5 方法的子接口|
|E1 循环拼接 | 替换为 `strings.Builder`|
|E6 循环内正则 | 提升到包级变量|
|H1 无 nil 检查 | 函数入口添加 `if param == nil`|
|H2 map 无 comma-ok | 改为 `val, ok := m[key]`|
|H3 类型断言无 comma-ok | 改为 `v, ok := i.(Type)`|
|H4 slice 无边界检查 | 添加 `if len(items) == 0`|
|H5 资源未释放 | 添加 `defer resource.Close(ctx)`|
|H6 无超时 | 添加 `context.WithTimeout` |
**修复规则**：优先复用现有组件；匹配项目风格；每个问题最多 2 次修复尝试。

### Step 6.5: Re-scan 验证

加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。重新执行 Step 3 的全部规则，输出 before/after 对比表。

### Step 6.7: 经验沉淀

成功修复 P0/P1 后，自动追加到 `.claude/claude-next.md`：

```
markdown##
[Code Review 反哺] {规则号} {问题简述}
- **文件**: `{file:line}`
- **问题**: {问题描述}
- **改进**: {修复方式}
- **来源**: lx-code-review auto-fix
- **严重度**: {P0 🔴 / P1 🟠}

```

**跳过条件**：通用 Go 规范 / 同一规则号已有 ≥3 个条目。

### Step 6.8: 飞轮日志

| 触发条件 | 执行命令|
|---------|---------|
|P0 问题存在 | `echo "$(date +%Y-%m-%d),code_quality_p0,P0,$(basename $(pwd))" >> ~/.claude/flywheel-buffer.jsonl`|
|P1 问题存在 | `echo "$(date +%Y-%m-%d),code_quality_p1,P1,$(basename $(pwd))" >> ~/.claude/flywheel-buffer.jsonl` |

### Step 7: 输出报告

加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。
**✅ 通过** / **⚠️ 需改进**：按需输出对应报告（含 before/after 对比表、blocked 项、P2/P3 建议）。

## 跨 Skill 联动

| 方向 | Skill | 触发条件 | 数据契约|
|------|-------|---------|---------|
|下游传至 | `/lx-golang-test` | P0/P1 中发现的未测试路径 | 传递：未覆盖函数名 + 问题场景|
|下游传至 | `/lx-security-review` | 审查通过后 → 安全扫描 | 传递：审查通过的文件列表|
|下游传至 | `/lx-debug-spec` | Auto-fix 失败（blocked） | 传递：规则号 + 问题描述 + 失败尝试 + 代码位置|
|上游来自 | `/lx-tdd-spec` | 规格完成 → 实现完成 → 代码审查 | 接收：实现文件列表|
|关联 | `/lx-perf-analysis` | E 类别发现严重性能问题 | 传递：性能问题位置 + 初步诊断 |

## 错误恢复与升级路径

| 场景 | 恢复动作|
|------|---------|
|re-scan 发现修复引入新问题 | 回退本次修复 → 标记原始问题 + 新问题为 blocked|
|git 不可用 | 回退到 `$ARGUMENTS` 指定的文件列表扫描|
|review-rules.md 缺失 | AI 使用通用规则执行扫描|
|go-style-guide.md 缺失 | 使用本 Skill 内置规范，降级通知用户|
|2 次修复失败 + 根因不明 | 升级至 `/lx-debug-spec` |

## 中止条件

- 过滤后无 Go 文件 → "无变更"报告
- 非 Go 项目（无 go.mod）→ "不适用"
- 全部命中为误报 → "通过"报告
- 待确认项超过 5 个 → 暂停，请求用户输入

## 降级策略

| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|skill 不可用 | Invoke lx-code-review | AI 用 references/knowledge/ 规则自行审查，标注 [降级审查]|
|变更文件 >50 个 | 全量审查 | 只审查高风险文件（main/handler/auth）|
|auto-fix 后仍有 P0 | 修复+重审 | 最多重试2次，第3次 BLOCKED + 修复建议 |
