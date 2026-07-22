# lx-code-review → 9+ 迭代方案

> 当前 v4.1.0，Sonnet-5 重审 73/100
> 目标：三模型评分均 ≥90/100

## 残留 P0（Sonnet-5 判定）

### P0-1: autofix 边界形式化
现状：文字描述 safe/review/suggest 的 allowed/forbidden
目标：YAML schema 形式化，代码可直接校验

```yaml
# 新增到 references/autofix-policy.yaml
autofix_policy:
  safe:
    allowed:
      patterns:
        - "formatting-only"     # 缩进/空格/换行
        - "typo-in-comments"    # 注释拼写
        - "import-cleanup"      # 仅当 verifier 通过
    forbidden:
      patterns:
        - "public-api-change"   # 导出函数签名变更
        - "behavior-change"     # 语义等价不可保证
        - "dependency-change"   # 增删依赖
        - "schema-change"       # 数据模型变更
    constraints:
      max_files: 1
      max_lines_changed: 50
      requires_verifier_pass: true
  review:
    requires:
      - show_diff
      - user_confirmation
      - verifier_pass_or_override
    constraints:
      max_files: 5
      max_lines_changed: 200
      requires_diff_display: true
  suggest:
    action: report_only
    constraints:
      no_file_modification: true
```

### P0-2: verifier 降级触发条件形式化
现状：文字描述"视验证项而定"
目标：条件矩阵，明确定义每级 verifier 的降级条件

```yaml
# 新增到 references/verifier-rules.yaml
verifier_degradation:
  build:
    degradable: false
    on_failure: "partial_report + review_inconclusive"
  schema:
    degradable: false
    on_failure: "partial_report + review_inconclusive"
  typecheck:
    degradable: true
    conditions:
      - mode == "fast"
      - mode == "fix-safe"
    on_degrade: "confidence caps at medium"
  test:
    degradable: true
    conditions:
      - mode == "fast"
    on_degrade: "confidence caps at medium"
  formatter:
    degradable: true
    conditions: ["*"]
    on_degrade: "warn, no confidence impact"
  lint:
    degradable: true
    conditions: ["*"]
    on_degrade: "warn, no confidence impact"
```

### P0-3: 模式冲突合并算法
现状：文字描述互斥规则
目标：优先级数值算法

```yaml
# 新增到 references/mode-rules.yaml
mode_priorities:
  report-only: 100  # 最高优先级
  strict: 80
  fix-with-confirmation: 60
  fix-safe: 40
  full: 20
  fast: 10

resolution_rules:
  - when: [report-only, fix-safe]
    action: reject ("report-only 禁止写文件")
  - when: [report-only, fix-with-confirmation]
    action: reject ("report-only 禁止写文件")
  - when: [strict, fast]
    action: strict wins, warn "fast skipped checks bypassed by strict"
  - when: [full, fast]
    action: full wins, suppress fast
  - default: higher_priority_wins
```

## 修复影响

| 文件 | 变更 | 行数 |
|------|------|------|
| references/autofix-policy.yaml | 新建 | ~30 |
| references/verifier-rules.yaml | 新建 | ~25 |
| references/mode-rules.yaml | 新建 | ~20 |
| SKILL.md | 引新文件路径 | ~3 |
| tests/ | 补充3个YAML schema校验测试 | ~40 |

## 预期收益

- P0-1: safe 边界可编程校验，防止 autofix 越界
- P0-2: verifier 降级行为可预测，无语义冲突
- P0-3: 模式组合行为确定，无歧义

## 非目标

- 不修改 auto-review.py 代码（仅文档+测试）
- 不修改 finding.yaml schema
- 不修改规则元数据格式
