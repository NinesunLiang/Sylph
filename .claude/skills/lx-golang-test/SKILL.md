---

name: lx-golang-test

version: v4.0.0

description: "DEPRECATED (Oracle 审计 2026-05-15): Generate Go test code via pattern routing: table-driven, mocks, HTTP handlers, benchmarks, fuzz, race detection."

complexity: intermediate
when_to_use: "Use when user needs Go test code for functions, interfaces, HTTP handlers, benchmarks, or fuzz tests."

model: sonnet

argument-hint: "<function/handler name> [test type]"

paths:

 - "*.go"

 - "go.mod"

 - "*_test.go"

harness_version: ">=1.1.0"
status: deprecated
role: "Go test code generator — pattern-based test scaffolding"
execution_mode: stepwise

triggers:
  - "/lx-golang-test"
---

# Go Testing: Pattern Router + Code Generator

## 原子化声明

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机|
|------|------|----------|
|`scripts/run_go_tests.py` | Go 编译+测试+覆盖率执行 | Step 执行阶段 |

> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析测试目标函数|
|context_collector | `../../nodes/context_collector.md` | 收集测试框架/项目惯例|
|generator | `../../nodes/generator.md` | 测试代码生成|
|verifier | `../../nodes/verifier.md` | 编译与运行验证|
|report_generator | `../../nodes/report_generator.md` | 测试报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 生成阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答|

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 测试目标定义|
|context_summary | `../../schemas/atomic/context_summary.yaml` | 测试框架上下文|
|finding | `../../schemas/atomic/finding.yaml` | 测试缺口发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 测试报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 测试修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 测试判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长测试会话的上下文总结 |

### 状态机
本 skill 使用**私有 parse→generate→verify 流程**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [analyze → generate → verify] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查

```bash
ls go.mod 2>/dev/null || echo "不适用: 非 Go 项目"
```

### Step 1: 解析测试目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：Go 版本、测试框架（标准库/testify）、Mock 策略（gomock/mockgen）、现有测试模式（`grep -r "func Test" --include="*_test.go" | head -10`）、已知测试问题（claude-next.md）。

### Step 3: 路由到测试模式
根据目标类型路由到对应测试模式：
| 目标类型 | 测试模式 | 关键特征|
|---------|---------|---------|
|纯函数 | Table-Driven Tests | `[]struct{ name, input, want }`|
|接口 | Mock-based Tests | gomock/mockgen + `EXPECT()`|
|HTTP Handler | httptest | `httptest.NewRecorder()` + `httptest.NewRequest()`|
|DB 操作 | Integration Tests | 测试数据库 + 清理|
|Benchmark | Benchmark Tests | `func BenchmarkXxx(b *testing.B)`|
|Fuzz | Fuzz Tests | `func FuzzXxx(f *testing.F)`|
|Race | Race Detection | `go test -race` |\|

### Step 4: 生成测试代码
加载 `@../../nodes/generator.md`，传入 context_summary + 测试模板规范。
**测试生成原则**：- Table-Driven Tests：每个 case 独立命名、独立断言- Mock-based Tests：只 Mock 外部依赖，不 Mock 被测函数- HTTP Handler：测试完整请求/响应周期- Benchmark：包含 `b.ResetTimer()` 和 `b.ReportAllocs()`- Fuzz：提供有意义的 seed corpus

### Step 5: 编译与运行验证
路由命中 Step 5 时，执行脚本：

```bash
n
3 .claude/skills/lx-golang-test/scripts/run_go_tests.py \ --pkg {target_pkg} --race --cover
bashpython3 .claude/skills/lx-golang-test/scripts/run_go_tests.py \ --pkg {target_pkg} --race --cover

```
读取 JSON 输出：`passed=true` → Step 6；`passed=false` → 报告失败+修复建议。
加载 `@../../nodes/verifier.md`，传入生成的测试 + 验证策略。
验证序列：1. 编译：`go build ./...`2. 测试：`go test ./target/pkg/... -v -count=1`3. Race 检测：`go test -race ./target/pkg/...`4. 覆盖率：`go test -cover ./target/pkg/...`

### Step 6: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件- 无 `go.mod` → "不适用"- 用户无法提供测试目标 → 提问- 测试全部通过 → "通过"报告- 编译失败 → 修复后重试，最多 2 次

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|run_go_tests.py 失败 | 脚本执行 | 直接运行 go test ./... -v，手动判断|
|测试超时（>60s）| 等待 | 加 -timeout 30s，标注"[超时截断]"|
|race 检测触发 | 分析 | go test -race -count=10 缩小范围，记录复现条件|
|go build 失败 | 修复编译 | 报告编译错误，不执行测试 |


