# 拆解质量校验 & 门禁

## 物理门禁（自动化）

```bash
# MECE 正交性 + 实体Own + 依赖闭合 + 接口孤儿
python3 .claude/scripts/verify_oma_mece.py {output_dir}/
```
exit 0 = 校验通过。exit 1 = 修复后重新校验（最多3轮）。

## AI 语义校验

物理脚本无法判断的：
- 模板字段完整性：每个 Sub PRD 包含8个必填字段
- 非功能契约一致性：各域约束之和 ≤ 全局约束
- 父需求全覆盖：追溯条目覆盖主 PRD 各章节

## 校验报告格式

```markdown
## 拆解质量报告
- verify_oma_mece.py：{exit_code} → ✅/❌
- 模板字段（8 项）：✅/❌
- 非功能契约一致性：✅/❌
- 父需求全覆盖：✅/❌
```

## 人工审核门禁

hier → oma 阶段转换前，**必须**输出审核清单：

```
[ ] Sub PRD 边界正交？→ 引用 MECE 摘要
[ ] 接口契约可落地？→ 引用接口检查
[ ] 数据实体唯一性？→ 引用 Entity Own 表
[ ] 无循环依赖？→ 引用依赖分析
[ ] INDEX.md 文件齐全？→ 引用文件清单
[ ] MECE 冲突项已裁决？→ 逐项说明
```

待裁决项清零后，执行 `/lx-oma-orch gate og-NNN approve`。

## Meta-Oracle G1 架构决策终审

> **G1 触发条件**（详见 `AGENTS.md §Meta-Oracle G1`）：hier 拆解涉及 ≥2 子系统（功能域）+ 不可逆的架构变更。

### 触发判定

以下场景满足 G1（任一项即可）：
1. 功能域 ≥2 个，域间存在不可逆的接口契约依赖
2. 架构决策涉及核心数据模型重组（跨多域实体归属）
3. 拆解方案影响下游 lx-oma-split 的 feature 拆分方式

> 常规 1 域拆解或可逆调整不需要 Meta-Oracle。判定模糊时默认不触发。

### 执行方式

1. **时机**：人工审核门禁通过 + Oracle gate approved 后
2. **命令**：`bash .claude/scripts/meta-oracle-review.sh G1`
3. **执行**：spawn opus critic agent（独立上下文）
4. **门禁**：软门禁 — ACCEPT/ADVISORY/REJECT
5. **留痕**：`.omc/state/meta-oracle-verdicts.md`

### G1 专项审查

- [ ] 跨子系统影响分析完整性
- [ ] 不可逆性评估（回滚成本）
- [ ] 接口契约与下游 feature 一致性
- [ ] 与现有哲学/铁律冲突检查
- [ ] 数据实体跨域冲突检查（DG-01 类问题）
