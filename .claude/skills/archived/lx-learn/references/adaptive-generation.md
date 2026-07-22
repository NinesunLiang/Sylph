# 适应性生成规则

> lx-learn 核心差异能力：根据模型能力自动调整 skill 生成策略。

## 模型能力分级

```yaml
tiers:
  high:
    models: [gpt-5.5, gpt-5.6, gpt-5.7, deepseek-v4-pro, deepseek-v5, gemini-3-flash, gemini-3-pro, sonnet-5, opus-4.8, kimi-k3]
    traits:
      - 理解抽象意图
      - 自动推断缺失细节
      - 一次性输出完整 SKILL.md
      - 适应 DSL/模板化方案
    generation_strategy: direct
  medium:
    models: [deepseek-v4-flash, gpt-5.1, gemini-2.5-flash, sonnet-4]
    traits:
      - 需逐步引导
      - 可理解结构化模板
      - 分步执行可靠
    generation_strategy: stepwise
  low:
    models: [gpt-4o, claude-3-haiku, gemini-2.0-flash]
    traits:
      - 易于填表式生成
      - 需频繁用户确认
      - 复杂状态机不可靠
    generation_strategy: fill_form
```

## DSL/模板化方案（高阶模型）

```yaml
# 生成 DSL 的 YAML 规格
skill_blueprint:
  name: lx-{name}
  category: reviewer | generator | gate | workflow
  summary: "{一句话描述}"
  inputs:
    - name: "{参数名}"
      type: "string | file | dir"
      description: "{描述}"
  triggers:
    - "/{shortcut}"
    - "{natural_language_trigger}"
  nodes:
    mandatory: [scanner, behavior_rules, report_generator]
    optional: [target_resolver, context_collector, auto_fixer, verifier, gate_checker]
  schemas:
    mandatory: [verdict, finding, scan_report, severity]
  steps:
    - step: 0
      name: "入口检查"
      action: "检测项目类型"
    - step: 1
      name: "解析目标"
      node: "target_resolver"
    - step: 2
      name: "收集上下文"
      node: "context_collector"
    - step: 3
      name: "扫描/分析"
      node: "scanner"
      rules:
        - id: A1
          rule: "{规则描述}"
          severity: P0
          check: "{检查方式}"
  boundaries:
    - action: "git commit/push"
      reason: "硬边界"
```

高阶模型传入 DSL -> 直接输出完整 SKILL.md。无需中间询问。

## 降级路径

| 当前策略 | 失败 | 降级到 |
|---------|------|-------|
| direct | 输出质量低 | stepwise（分步生成） |
| stepwise | 某步卡住 2+ 次 | fill_form（用户手动填） |
| fill_form | 用户不耐烦 | 提示使用 /learn create 重新开始 |

## 模型感知优化

1. **自动检测模型版本**：从 `ANTHROPIC_MODEL` 环境变量读取
2. **策略动态切换**：可运行时从 high 降级到 medium
3. **输出后验证始终执行**：无论使用哪种策略，最终 SKILL.md 都执行 validate_skill
