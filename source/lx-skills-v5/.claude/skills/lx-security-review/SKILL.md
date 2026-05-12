---

name: lx-security-review

version: v4.0.0

description: "Scan staged Go code + dependencies for vulnerabilities, auto-fix, re-scan, and give commit verdict."

when_to_use: "Use after 'git add' before commit, or when user says 'security review', 'security scan', 'pre-commit check'."

model: sonnet

argument-hint: "[file path or git ref]"

paths:

 - "*.go"

 - "go.mod"

harness_version: ">=1.1.0"
role: "Security vulnerability scanner for Go code and dependencies"
execution_mode: stepwise

triggers:
  - "/lx-security-review"
  - "security scan"
---

# Pre-commit Security Gate (Go)

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析扫描目标|
|context_collector | `../../nodes/context_collector.md` | 收集依赖/配置/已知漏洞|
|scanner | `../../nodes/scanner.md` | 按 15 条安全规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | 🔴🟠🟡 问题自动修复|
|verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证|
|gate_checker | `../../nodes/gate_checker.md` | 安全门禁判定|
|report_generator | `../../nodes/report_generator.md` | 安全审查报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 扫描阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 扫描目标定义|
|severity | `../../schemas/atomic/severity.yaml` | 🔴🟠🟡🟢 严重度分级|
|finding | `../../schemas/atomic/finding.yaml` | 安全漏洞发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 扫描报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|gate_result | `../../schemas/atomic/gate_result.yaml` | 安全 Gate 判定|
|verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长扫描会话的上下文总结 |

### 状态机
本 skill 是**门禁型**，使用 scan→fix→re-scan→gate 线性链，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [scan → fix → re-scan → gate] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用扫描阶段行为约束。

```bash
l
s
go.mod # 缺失 → "不适用"
```

### Step 1: 解析扫描目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 过滤：保留 `*.go`、`go.mod`。排除：`vendor/`、`*_test.go`

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：Go 版本、依赖列表（`go.mod`）、已知安全组件（加密库、认证中间件）、已知漏洞（claude-next.md）。

### Step 3: 安全扫描
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的安全规则集：
**🔴 Critical（阻塞 + 自动修复）**| # | 规则 | 检查方式 ||---|------|---------|| SEC-01 | 硬编码密钥/密码 | `grep -rn "password\|secret\|api_key\|token" --include="*.go"` + 排除 `os.Getenv()` || SEC-02 | SQL 注入 | ast-grep 搜索字符串拼接 SQL 模式 || SEC-03 | 命令注入 | grep `exec.Command` 含用户输入 |
**🟠 High（阻塞 + 自动修复）**| # | 规则 | 检查方式 ||---|------|---------|| SEC-04 | 认证绕过 | grep 认证中间件 bypass 路径 || SEC-05 | 敏感数据日志 | grep `log.*password\|log.*token\|log.*secret` || SEC-06 | 路径穿越 | grep `filepath.Join` 含用户输入无清洗 |
**🟡 Medium（阻塞 + 自动修复）**| # | 规则 | 检查方式 ||---|------|---------|| SEC-07 | 缺失输入校验 | 检查 HTTP handler 无 Validate/长度检查 || SEC-08 | 错误信息泄漏 | grep `Error.*%v.*err` 暴露内部细节 || SEC-09 | 缺失鉴权 | grep 写操作无 auth 检查 || SEC-10 | SSRF | grep `http.Get/Post` 含用户输入 URL |
**🟢 Low（仅警告）**| # | 规则 | 检查方式 ||---|------|---------|| SEC-11 | 敏感注释 | grep `TODO.*security\|FIXME.*auth` || SEC-12 | 默认 HTTP Client | grep `http.Get/Post` 无自定义 Timeout || SEC-13 | goroutine 泄漏风险 | grep `go func` 无 context/done channel || SEC-14 | 弱加密算法 | grep `md5\|sha1\|des\|rc4` || SEC-15 | 依赖漏洞 | `govulncheck ./...` |
**深度扫描强制要求**：- 🔴 硬编码密钥：排除 `os.Getenv()` 调用- 🔴 SQL 注入：用 ast-grep 搜索字符串拼接，不可仅搜 `fmt.Sprintf.*SELECT`- 🟡 缺失校验：对每个 HTTP handler 检查 request body 校验- 🟢 goroutine 泄漏：搜索 `go func` 后检查 context/done channel/WaitGroup

### Step 4: 误报排除
**误报场景**：在注释/字符串中、测试文件中的泄漏、有参数化查询、使用现有安全 helper、占位符常量值、有 `//nolint:gosec` 且理由合理。

### Step 5: Auto-Fix（🔴🟠🟡）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略：
| 规则 | 修复模板|
|------|---------|
|SEC-01 硬编码密钥 | 替换为 `os.Getenv("KEY_NAME")`|
|SEC-02 SQL 注入 | 替换为参数化查询（`db.Query("...?", arg)`）|
|SEC-03 命令注入 | 替换为 `exec.Command` 参数数组|
|SEC-05 敏感数据日志 | 脱敏或移除敏感字段|
|SEC-06 路径穿越 | 添加 `filepath.Clean()` + 白名单校验|
|SEC-07 缺失输入校验 | 添加 `Validate()` 方法|
|SEC-12 默认 Client | 添加 `\&http.Client{Timeout: 30 * time.Second}` |

### Step 6: Re-scan 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。重新执行 Step 3 的全部 15 条规则 + `govulncheck ./...`。

### Step 7: 门禁判定
加载 `@../../nodes/gate_checker.md`，传入扫描结果 + 门禁规则（🔴🟠🟡 必须修复，🟢 可警告通过）。

### Step 8: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件- 无 `go.mod` → "不适用"- scan-rules.md 缺失 → 使用内置 15 条规则摘要执行扫描- 全部命中为误报 → "通过"报告- 2 次修复失败 → 输出 blocked 报告

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|skill 不可用 | Invoke lx-security-review | govulncheck（Go）或 npm audit（前端），标注 [降级扫描]|
|govulncheck 未安装 | govulncheck | references/scan-rules.md 静态模式扫描，标注 [静态扫描-无工具]|
|🔴 阻断2次仍未修复 | 修复 | BLOCKED + 漏洞清单，等待用户决策|
|外部依赖漏洞 | 修复 | 记录 tech-debt + CVE，不阻断 |


