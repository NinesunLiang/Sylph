# lx-code-review — Go 代码质量审查

## 原子化声明

| 节点 | 路径 |
|------|------|
| target_resolver / context_collector / scanner / auto_fixer / verifier / report_generator / behavior_rules | `../../nodes/` |

Schema: scan_target / severity / finding / scan_report / fix_record / verdict → `../../schemas/atomic/`

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/auto-fix-templates.md` | auto fix templates 阶段 |
| `references/rules-catalog.md` | rules catalog 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
collect_context → scan → fix → re-scan → done
```

## 执行流程

### Step 0: 入口
规范文件自检（kernel.md / go-style-guide.md）→ 缺失不阻塞，用内置规则 fallback。无参数 → 引导式问答。

### Step 1-2: 解析 + 收集
解析审查目标（过滤 `*_test.go`/`vendor/`/`*.pb.go`）→ 收集 Go 版本/框架类型/项目规范/已知问题。

### Step 3: 8 类并行扫描 → `@references/rules-catalog.md`
39 条规则（A-H），每条必须执行实际 grep/ast-grep，引用原始输出。强证据协议，不可用描述替代。

### Step 4: 误报排除
FP 标记：注释/字符串/`//nolint`/go-zero 生成代码/内部函数/只读不分支。

### Step 5-6: Auto-Fix → `@references/auto-fix-templates.md`
P0+P1 自动修复 → re-scan 验证 → before/after 对比表。

### Step 6.5: 经验沉淀
成功修复 P0/P1 → 反哺 claude-next.md（去重，同规则 ≥3 条跳过）。

### Step 7: 输出报告
✅ 通过 / ⚠️ 需改进，含 blocked 项 + P2/P3 建议。

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| skill 不可用 | 调用 lx-code-review | 用 references/ 规则自行审查 [降级审查] |
| >50 文件 | 全量 | 只审查高风险文件 |
| auto-fix 后仍有 P0 | 修复+重审 | 2 次后 BLOCKED |
| git 不可用 | git diff | 文件列表扫描 |
| go-style-guide 缺失 | 项目规范 | 内置规范 [降级] |
