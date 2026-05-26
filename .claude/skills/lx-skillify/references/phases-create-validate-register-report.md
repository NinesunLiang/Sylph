# Phase 3-6: 创建 → 验证 → 注册 → 报告

## Phase 3: CREATE_FILES

`needs_scripts=true` → 创建 `scripts/{logic}.py`（Python + exit code 2 协议）

`needs_references=true` → 创建 `references/{knowledge}.md`

产出：
```
.claude/skills/lx-{name}/
  SKILL.md          ← Phase 2
  scripts/          ← 条件创建
  references/       ← 条件创建
```

## Phase 4: VALIDATE

```bash
bash .claude/scripts/validate-skill.sh lx-{name}
python3 .claude/scripts/validate_skill_refs.py
```

门禁：失败 → 回 Phase 2 修复，max 3 轮。第 3 轮仍失败 → blocked。

## Phase 5: REGISTER

1. 读 `feature-registry.yaml` → 追加 skills: 条目
2. 读 `skills-catalog.md` → 追加分类行

注册格式：
```yaml
- name: lx-{name}
  type: {reviewer|workflow|gate|tester|orchestrator|analyzer}
  category: {quality|workflow|security|test|debug|infrastructure|automation}
  description: "{<80 字符}"
  enabled_by_default: true
```

## Phase 6: REPORT

```
## /skillify 完成报告 ✅

### 创建内容
- lx-{name} / SKILL.md ({N} 行) / 脚本: {N} / 引用: {N}

### 验证
- 结构: {通过/失败} / 引用: {通过/失败} / 轮次: {N}

### 注册
- feature-registry.yaml: ✅ / skills-catalog.md: ✅

### 下一步
1. 审查 SKILL.md
2. git add .claude/skills/lx-{name}/
3. /lx-{name} 测试
```
