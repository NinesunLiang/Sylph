---
name: lx-test-gen
version: v1.0.0
description: "Language-agnostic test code generator. Auto-detects project language (Go/TS/Python/etc.), routes to appropriate test patterns: table-driven, mocks, HTTP handlers, benchmarks, fuzz, property-based."
complexity: intermediate
when_to_use: "Use when user needs test code for functions, interfaces, HTTP handlers, or when user says 'generate tests', 'test this function', '/lx-test-gen'."
argument-hint: "<function/handler/module name> [test type]"
harness_version: ">=6.3.0"
status: stable
role: "Language-agnostic test code generator — pattern-based test scaffolding"
execution_mode: stepwise
triggers:
  - "/lx-test-gen"
---
# lx-test-gen — Universal Test Generator

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析测试目标函数|
|context_collector | `../../nodes/context_collector.md` | 收集项目语言/测试框架/惯例|
|generator | `../../nodes/generator.md` | 测试代码生成|
|verifier | `../../nodes/verifier.md` | 编译与运行验证|
|report_generator | `../../nodes/report_generator.md` | 测试报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 生成阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 测试目标定义|
|context_summary | `../../schemas/atomic/context_summary.yaml` | 测试框架上下文|
|finding | `../../schemas/atomic/finding.yaml` | 测试缺口发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 测试报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 测试修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 测试判定 |

### 状态机
本 skill 使用私有 analyze→generate→verify 流程，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [analyze → generate → verify] → done

### 私有节点
本 skill 无私有节点。

---

## 语言自动检测

Step 0 检测项目技术栈，路由到对应测试框架和模式：

| 检测信号 | 语言 | 默认框架 | 可用模式 |
|---------|------|---------|---------|
| `go.mod` | Go | `testing` (stdlib) | table-driven, mocks, httptest, benchmark, fuzz, race |
| `package.json` + `tsconfig.json` | TypeScript | Vitest / Jest | describe/it, mocks (viest.mock), HTTP (supertest) |
| `package.json` (no tsconfig) | JavaScript | Jest / Vitest | describe/it, mocks, HTTP supertest |
| `requirements.txt` / `setup.py` / `pyproject.toml` | Python | pytest | parametrize, mocks (unittest.mock), fixtures |
| `Cargo.toml` | Rust | cargo test | #[test], #[cfg(test)], property-based (proptest) |
| `Gemfile` / `*.gemspec` | Ruby | RSpec / Minitest | describe/it, let/mocks, subject |
| `pom.xml` / `build.gradle` | Java/Kotlin | JUnit / pytest (Java) | @Test, parameterized, mocks (Mockito) |
| 无信号 → 提示用户确认 | — | — | — |

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。

```bash
ls
```

### Step 1: 解析测试目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：
- 项目语言/框架（从 Step 0 检测）
- 测试框架与配置（tsconfig jest/vitest, go test, pytest.ini 等）
- Mock 策略（gomock / vitest.mock / unittest.mock）
- 现有测试模式（`grep` 现有 test 文件前 10 条）
- 已知测试问题（claude-next.md 中相关记录）
- 覆盖率基线（`go test -cover` / `vitest --coverage` / `pytest --cov`）

### Step 3: 路由到测试模式
根据目标类型路由到对应测试模式，语言无关的泛化分类：

| 目标类型 | 测试策略 | 说明 |
|---------|---------|------|
| **纯函数** | 参数化测试 | table-driven (Go) / `test.each` (Jest/Vitest) / `@pytest.mark.parametrize` |
| **接口/抽象** | Mock 测试 | gomock + EXPECT / viest.mock + mockReturnValue / unittest.mock.patch |
| **HTTP Handler** | 请求-响应测试 | httptest / supertest / pytest httpx / axum test |
| **数据库操作** | 集成测试 | 测试数据库 + 事务回滚 / testcontainers / 内存数据库 |
| **性能** | Benchmark | `go test -bench` / vitest bench / pytest-benchmark |
| **模糊** | Fuzz | `go test -fuzz` / Jest fuzz / hypothesis (Python) |
| **并发** | Race/竞争检测 | `go test -race` / Jest --detectOpenHandles / pytest-timeout |
| **属性/不变式** | Property-based | testing/quick / fast-check / Hypothesis / proptest |

### Step 4: 生成测试代码
加载 `@../../nodes/generator.md`，传入 context_summary + 测试模板规范。

**通用测试生成原则**：
- 参数化测试：每个 case 独立命名、独立断言
- Mock：只 Mock 外部依赖，不 Mock 被测函数
- HTTP Handler：测试完整请求/响应周期（状态码+body+header）
- Benchmark：包含计时器重置和内存分配报告（语言相应 API）
- Fuzz：提供有意义的 seed corpus
- 并发测试：可复现 + 超时保护

### Step 5: 编译与运行验证
加载 `@../../nodes/verifier.md`，传入生成的测试 + 验证策略。

验证序列（按语言路由）：
```bash
# Go
go build ./... && go test -v -count=1 ./target/pkg/...
# TypeScript/JavaScript
npx vitest run --reporter=verbose 2>/dev/null || npx jest --verbose
# Python
python -m pytest target/test_file.py -v --tb=short
# Rust
cargo test -p target_crate
```

### Step 6: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件
- 无法检测项目语言 → 提示用户手动指定
- 用户无法提供测试目标 → 引导式问答收集
- 测试全部通过 → "通过"报告
- 编译失败 → 修复后重试，最多 2 次
- 测试框架缺失 → 建议安装指令，不自动安装

## 降级策略
| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 脚本执行失败 | 框架脚本 | 直接运行语言对应命令，手动判断 |
| 测试超时（>60s）| 等待 | 加超时参数，标注"[超时截断]" |
| 竞争条件触发 | 分析 | 调整并发参数/重试，记录复现条件 |
| 编译失败 | 修复编译 | 报告编译错误，不执行测试 |
| 无测试框架 | 运行测试 | 只生成代码，提示用户手动安装框架后运行 |
