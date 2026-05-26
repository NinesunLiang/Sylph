---
name: lx-purify
description: "思想纯度审计 — 哲学→铁律→现状三层全量审计，逐对象双法官审核，改完即验。"
version: v1.0.1
harness_version: ">=6.3.0"
status: stable
argument-hint: "[region|object]"
triggers: ["/lx-purify", "思想纯度审计", "大清洗"]
when_to_use: "Use for self-auditing Carror OS governance purity: philosophy→iron-rules→status-quo three-pass audit across 8 regions. Trigger: '/lx-purify', '思想纯度审计', '大清洗'."
role: "self-auditor — philosophy-first, per-object, verify-immediately"
execution_mode: stepwise
---

## 原子化声明

> 本 skill 无私有 references，共享能力引用 @../references/oma/。


# lx-purify — 思想纯度审计

## 审计架构

```
一等公民: 哲学 (天道 — 解决"怎么做")
  #4(没验证=没做) > #6(0信任) > #3(先守护) > #7(文档优先) > #5(以人为本) > #2(少量大增益) > #1(渐进披露)
  ↓ 划定方向

二等公民: 铁律 (法律 — 解决"不可做什么")
  #1禁止编造 #2用户裁定 #3证据门禁 #4Git门禁 #5范围冻结 #6隐私防线 #7断言真实 #8哲学先行
  ↓ 划定边界

三等公民: 现状 (基础设施 — 解决"怎么合群")
  已有机制、文件约定、命名风格、脚本体系
  ↓ 在此之上构建
```

## 执行流程

### 1. 扫描目标

```
Region 1: skills/     Region 3: hooks/      Region 5: source/
Region 2: nodes/      Region 4: scripts/    Region 6: schemas/
          Region 7: references/   Region 8: 版本系统
```

### 2. 逐对象，三 Pass 全量过

#### Pass 1: 思想层 — 7条哲学逐一对照

| # | 哲学 | 检查项 | 问题信号 |
|---|------|--------|---------|
| #4 | 没验证=没做 | 声明有物理门禁/脚本验证？还是纯文档？ | 纸面无物化、completion-gate 可绕过 |
| #6 | 0信任 | AI 输出经可证伪验证？Oracle 独立审查？ | AI 自证无第三方、评审链缺失 |
| #3 | 先守护 | 危险操作有前置门禁？context-guard 覆盖？ | 无权限检查、rm/write 无拦截 |
| #7 | 文档优先 | 方案→执行→证据链完整？ | 无文档直接改、无证据说"完成" |
| #5 | 以人为本 | 输出有方向指引？选项有重量？裁决交人？ | 替人决策、选项无说明、无"自定义"出口 |
| #2 | 少量大增益 | 有过度设计？虚假求圆满？ | >200行 SKILL.md、功能重复、未激活的 Enhanced |
| #1 | 渐进披露 | 按需加载？还是一把梭？ | 一次倾泻全部、@ 引用未用 |

#### Pass 2: 行为层 — 8条铁律逐一对照

| # | 铁律 | 检查项 | 问题信号 |
|---|------|--------|---------|
| #1 | 禁止编造 | 引用文件存在？路径有效？ | 幻影引用(file:line 指向不存在) |
| #2 | 用户裁定 | 关键决策交人？ | AI 自行裁决架构/安全/冲突 |
| #3 | 证据门禁 | 软完成语检测 | "应该没问题""基本完成""理论上" |
| #4 | Git门禁 | git 仓库内？commit 经批准？ | 未 commit、未 git diff 验证 |
| #5 | 范围冻结 | 引用不越界？ | 引用其他 skill 私有内容、跨 Region 改动 |
| #6 | 隐私防线 | 无 .env/密钥引用？ | 明文 token、.env 路径 |
| #7 | 断言真实 | 评分/百分比有来源？ | 无 file:line 或行业标准 URL |
| #8 | 哲学先行 | 跳过哲学直接问人？ | 哲学可裁决却打断用户 |

#### Pass 3: 组织层 — 与同类逐项对比

对当前对象，找 2-3 个最相近的同类对比：

| 维度 | 检查项 |
|------|--------|
| 命名 | frontmatter name 风格、文件命名、section 标题 |
| 目录 | 在正确 Region？同级文件数量一致？ |
| 引用 | `../../nodes/` 约定？`@../references/` 模式？ |
| frontmatter | 字段完整（version/harness_version/status/role）？ |
| 版本 | harness_version 一致？version 合理？ |
| 重复 | 与同类有重复段落？可提取到 references/？ |
| 验证 | 用了已有脚本而非新建？ |

### 3. 双法官审核链

每个问题提交双法官（两个独立个体，各自走完整链）：

```
Step 1: 哲学审查 — 符合7条哲学？
  #2→最小改动  #4→验收全覆盖  #1→渐进披露
  → 不符合则 REVISE

Step 2: 铁律审查 — 触碰法律红线？
  断言有 file:line？(#1) Git write 已申请？(#4) 改动在范围内？(#5)
  → 违反则 REJECT（不可继续）

Step 3: 现状审查 — 合群？
  路径遵循 ../../nodes/？references 跟 rpe 一致？复用已有脚本？命名趋同？
  → 不一致则 REVISE
```

### 4. 双法官 sub-agent 执行协议

> ⚠️ 教训：展开框架=150K token→sub-agent 死。必须脱水。

1. 生成 purify-compact.md（~800 字节脱水版，见本 skill 目录）
2. 读被审文件→嵌入 content 到 prompt（不让 sub-agent 自己读）
3. prompt ≤3K token：compact框架 + 文件内容 + 判决指令
4. toolsets=`[]`（内容已嵌入，不需要文件读取）
5. 同时 spawn Oracle + Meta-Oracle（并行）
6. sub-agent 连续失败 2 次→fallback：主 agent 自行做认知隔离审查

### 5. 各区审计速查

#### skills/
```bash
# frontmatter 完整性
for f in skills/*/SKILL.md; do
  n=$(grep -c '^name:' "$f"); s=$(grep -c '^status:' "$f"); r=$(grep -c '^role:' "$f")
  [ $n -eq 0 ] || [ $s -eq 0 ] || [ $r -eq 0 ] && echo "⚠️ $f"
done
# 重复段检测
grep -c '错误码与超时规范\|可观测性\|降级策略' skills/*/SKILL.md
```

#### hooks/ — 三重验证（不改脚本）
```bash
# ① harness.yaml 声明 vs settings.json 注册一致性
python3 -c "import json; ..."  # 提取注册列表
grep -E '^\s+[a-z_]+:' harness.yaml  # 提取声明
# ② 文件孤立检测
for f in hooks/*.sh; do
  refs=$(grep -l "$f" hooks/*.sh | grep -v "$f")
  [ -z "$refs" ] && echo "⚠️ $f — 孤立"
done
# ③ harness 布尔 vs settings 注册矛盾
# 例：harness.yaml skill_flywheel:false 但 settings.json 注册→矛盾
```

#### source/ — 同步检查
```bash
diff -rq .claude/ source/harness-kit/.claude/ | grep -v 'Only in' | grep -v scheduled_tasks
```
排除 `scheduled_tasks.json`（运行时数据）。

#### nodes/ — 分层判定
有 frontmatter = 角色节点（注入 prompt），无 = 工具模板。不是 bug。

### 6. 逐对象改验

1. 声明：改什么 + 为什么(标注触发的哲学#和铁律#) + 影响范围
2. 执行
3. 验证：skill→`validate_skill_refs.py`，hook→`harness-smoke-test.sh`
4. 失败→回滚，通过→下一对象

## 红线

- 不碰 `hooks/` 工作的脚本（只改 `harness.yaml` 声明）
- 不新增节点/机制（只提取重复到 `references/`）
- 不动 `AGENTS.md`
- 不删除文件（标记废弃或移 `archive/`）

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 双法官 sub-agent 连续失败 2 次 | 主 agent 自行做认知隔离审查 |
| purify-compact.md 生成失败 | 手动构造脱水版框架 |

