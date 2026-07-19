# PKG-B 补充材料（round3 补缺）

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | 生成: 2026-07-19 | 密钥已脱敏
> 起因：gpt round2 方案 3 处 hunk context 失配 + validate_skill.py 替换命令目标函数不存在——此三份文件此前从未交付。


## 1. `.claude/skills/lx-validate-skill/scripts/validate_skill.py`（全文 96 行）

> 真相：全文件只有一个 `check()` 函数（:21）+ `main()`（:71）；所谓 R6 实现在 :51-57，语义是"scripts/*.py 缺 sys.exit 则 WARN"，与 SKILL.md:66 文档规则"scripts/ 仅 .py"**两者皆不同**——文档、实现、你假设的 check_r6 三方漂移。

```python
     1	#!/usr/bin/env python3
     2	
     3	"""
     4	
     5	validate_skill.py — 验证 skill 目录结构是否符合三层规范（v6.0.1）
     6	
     7	用法：python3 validate_skill.py --skill lx-{name} [--skills-dir .claude/skills]
     8	
     9	exit: 0=通过, 2=有违规
    10	
    11	"""
    12	
    13	import argparse, sys, json
    14	
    15	from pathlib import Path
    16	
    17	
    18	REQUIRED_FIELDS = ["name", "version", "description", "when_to_use", "harness_version"]
    19	
    20	
    21	def check(skill_dir: Path):
    22	    violations = []
    23	    warnings = []
    24	
    25	    # 1. SKILL.md 存在
    26	    skill_md = skill_dir / "SKILL.md"
    27	    if not skill_md.exists():
    28	        violations.append("SKILL.md 不存在")
    29	        return violations, warnings
    30	
    31	    content = skill_md.read_text(encoding="utf-8")
    32	
    33	    # 2. frontmatter 字段
    34	    for field in REQUIRED_FIELDS:
    35	        if f"{field}:" not in content:
    36	            violations.append(f"缺少 frontmatter 字段: {field}")
    37	
    38	    # 3. 原子化声明
    39	    if "## 原子化声明" not in content and "原子化声明" not in content:
    40	        violations.append("缺少「原子化声明」区块")
    41	
    42	    # 4. 降级策略
    43	    if "## 降级策略" not in content:
    44	        violations.append("缺少「降级策略」章节")
    45	
    46	    # 5. 不含私有 nodes/ schemas/
    47	    for bad in ["nodes/", "schemas/"]:
    48	        if (skill_dir / bad).exists():
    49	            violations.append(f"包含私有 {bad} 目录（违反 R1/R2）")
    50	
    51	    # 6. scripts/*.py 如存在，必须有 exit code 处理
    52	    scripts_dir = skill_dir / "scripts"
    53	    if scripts_dir.exists():
    54	        for py in scripts_dir.glob("*.py"):
    55	            code = py.read_text(encoding="utf-8")
    56	            if "sys.exit" not in code:
    57	                warnings.append(f"scripts/{py.name} 缺少 sys.exit（建议加退出码）")
    58	
    59	    # 7. docs/ 不应存在（应改为 references/）
    60	    if (skill_dir / "docs").exists():
    61	        violations.append("存在 docs/ 目录，应迁移到 references/（违反规范）")
    62	
    63	    # 8. SKILL.md 行数警告（超过 300 行提示精简）
    64	    lines = len(content.split('\n'))
    65	    if lines > 300:
    66	        warnings.append(f"SKILL.md 共 {lines} 行，建议精简到 300 行以内")
    67	
    68	    return violations, warnings
    69	
    70	
    71	def main():
    72	    p = argparse.ArgumentParser()
    73	    p.add_argument("--skill", required=True)
    74	    p.add_argument("--skills-dir", default=".claude/skills")
    75	    args = p.parse_args()
    76	
    77	    skill_dir = Path(args.skills_dir) / args.skill
    78	    if not skill_dir.exists():
    79	        print(json.dumps({"error": f"skill 目录不存在: {skill_dir}"}))
    80	        sys.exit(1)
    81	
    82	    violations, warnings = check(skill_dir)
    83	    passed = len(violations) == 0
    84	
    85	    print(json.dumps({
    86	        "skill": args.skill,
    87	        "passed": passed,
    88	        "violations": violations,
    89	        "warnings": warnings,
    90	    }, ensure_ascii=False, indent=2))
    91	
    92	    sys.exit(0 if passed else 2)
    93	
    94	
    95	if __name__ == "__main__":
    96	    main()
```

## 2. `.claude/skills/lx-validate-skill/references/report-templates.md`（全文）

> 你的 hunk 失配原因：R6 在 :41，位于"警告列表"小节，上文不是 R3/R4/R5 行。

```
     1	# lx-validate-skill 报告模板
     2	
     3	> 校验报告和链路追踪的输出格式模板。按需加载。
     4	
     5	## 校验报告
     6	
     7	### 全部通过
     8	
     9	```
    10	## Skill 原子化校验报告 ✅
    11	
    12	### 校验范围
    13	- Skill: {name}
    14	- 规则数：11
    15	
    16	### 结果：通过
    17	- 错误：0
    18	- 警告：0
    19	```
    20	
    21	### 有错误/警告
    22	
    23	```
    24	## Skill 原子化校验报告 ⚠️
    25	
    26	### 校验范围
    27	- Skill: {name}
    28	- 规则数：11
    29	
    30	### 结果：{N} 错误, {M} 警告
    31	
    32	#### 错误列表
    33	| 规则 | 问题 | 修复建议 |
    34	|------|------|---------|
    35	| R3 | 缺少原子化声明 | 添加 ## 原子化声明 区块 |
    36	| ... | ... | ... |
    37	
    38	#### 警告列表
    39	| 规则 | 问题 | 建议 |
    40	|------|------|------|
    41	| R6 | 缺少状态机声明 | 添加 ### 状态机 声明 |
    42	| ... | ... | ... |
    43	```
    44	
    45	## 链路追踪
    46	
    47	```bash
    48	# 完整执行路径 + 错误路径 + Token 节省画像
    49	python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py
    50	
    51	# 仅 Token 节省分析（JSON 输出）
    52	python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only
    53	
    54	# 过滤指定特性
    55	python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --feature {feature_name}
    56	```
    57	
    58	读取三个数据源：
    59	- `.omc/state/skill-trace.jsonl` ← update_progress.py 写入
    60	- `.omc/state/error-dna.json` ← error-dna.sh 写入
    61	- `.omc/state/read-tracker.txt` ← read-tracker.sh 写入
    62	
    63	## 渐进式披露检查
    64	
    65	```bash
    66	python3 .claude/skills/lx-validate-skill/scripts/check_progressive_disclosure.py \
    67	  --all --skills-dir .claude/skills
    68	```
    69	
    70	读取 JSON：`total_violations=0` → 合规；有 violations → 报告并建议修复。
```

## 3. `.claude/skills/references/oma/skill-chaining.md`（全文）

> 你的 hunk 失配原因：真实行有 2 空格缩进、无 `<pipeline>` 实参，且链式列表共 5 行（含 lx-code-review/lx-test-gen），非你假设的 3 行。命令风格 `/lx-oma-hier`（连字符）与 SKILL.md 的 `/lx-oma hier`（子命令）并存——统一为哪种风格是你的设计裁决，请在真实内容上重做。

```
     1	# Skill 链式承接 (Skill Chaining)
     2	
     3	> 所有 OMA skill 的链式组合模式。引用：`@reference/oma/skill-chaining.md`
     4	
     5	## 链式组合哲学
     6	
     7	单个 skill = 原子操作。链式组合 = 原子 skill 按契约串联成完整流水线。
     8	
     9	```
    10	原子 skill A ──契约──→ 原子 skill B ──契约──→ 原子 skill C
    11	```
    12	
    13	每个 skill 只关心自己的输入/输出契约，不感知上下游实现。
    14	
    15	## 主链：PRD 全生命周期
    16	
    17	```
    18	lx-oma-hier ──→ lx-oma-split ──→ lx-rpe ──→ lx-code-review ──→ lx-test-gen
    19	 (主PRD→Sub)    (Sub→Feature)    (开发)      (审查)            (测试)
    20	      │               │              │            │                │
    21	      └── 输出: Sub PRD ──┘             │            │                │
    22	               └── 输出: Feature RPE ───┘            │                │
    23	                         └── 输出: 代码 ─────────────┘                │
    24	                                   └── 输出: 审查报告 ────────────────┘
    25	
    26	链式调用:
    27	  1. /lx-oma-hier docs/master-prd.md --pipeline
    28	  2. /lx-oma-split sub-prds/domain-auth.md --pipeline
    29	  3. /lx-rpe prd/auth/feat-login --pipeline
    30	  4. /lx-code-review
    31	  5. /lx-test-gen
    32	```
    33	
    34	## 治理链：变更检测 & 传播
    35	
    36	```
    37	lx-oma-gov ──→ lx-oma-split ──→ lx-rpe
    38	 (检测变更)     (重拆)          (重开发)
    39	
    40	链式调用:
    41	  1. /lx-oma-gov reconcile          # 检测主 PRD 变更
    42	  2. /lx-oma-gov propagate --execute # 传播到 feature
    43	  3. /lx-oma-split <changed>        # 重拆受影响的 feature
    44	  4. /lx-rpe <feature>              # 重新开发
    45	```
    46	
    47	## 编排链：自动推进
    48	
    49	```
    50	lx-oma-orch auto
    51	   ↓ 读 pipeline.yaml
    52	   ├── hier_done? → 触发 split
    53	   ├── oma_ready? → 触发 rpe
    54	   ├── dev_done?  → 触发 code-review
    55	   └── review_done? → 触发 test-gen
    56	
    57	每个阶段有 Oracle gate，orch 自动推进。
    58	```
    59	
    60	## 审判链：双法官审核
    61	
    62	```
    63	Oracle Agent ──→ Meta-Oracle ──→ 人类
    64	 (静态分析)       (运行时+对抗)    (最终裁决)
    65	
    66	嵌入任意链式流程：
    67	  hier → [Oracle → Meta-Oracle] → split → [Oracle] → rpe → [Oracle → Meta-Oracle] → 交付
    68	```
    69	
    70	## 组合规则
    71	
    72	### 契约传递
    73	
    74	上游输出 → 下游输入必须是结构化契约：
    75	
    76	```
    77	上游 SKILL.md:
    78	  输出: `sub-prds/domain-{name}.md`
    79	
    80	下游 SKILL.md:
    81	  输入: `<sub_prd_path>`（Sub PRD markdown 文件）
    82	```
    83	
    84	### 独立可执行
    85	
    86	链中任意 skill 可以独立调用，不依赖链上历史：
    87	
    88	```
    89	✅ /lx-oma-split sub-prds/domain-auth.md     # 独立执行
    90	✅ /lx-rpe prd/auth/feat-login               # 独立执行
    91	```
    92	
    93	### 去重
    94	
    95	如果两个 skill 的公共能力相同 → 提取到 `references/oma/`：
    96	
    97	| 公共能力 | 引用路径 |
    98	|---------|---------|
    99	| 裁决链 | `decision-chain.md` |
   100	| 执行工作流 | `execution-workflow.md` |
   101	| 降级升级 | `degradation-escalation.md` |
   102	| Pipeline 契约 | `pipeline-contract.md` |
   103	| 可观测性 | `observability.md` |
   104	| 错误码 | `error-codes.md` |
   105	| 方向指引 | `direction-guide.md` |
   106	
   107	## 并发链：Race 模式
   108	
   109	```
   110	lx-race
   111	  ├── Task A: lx-rpe feat-A        (并行)
   112	  ├── Task B: lx-rpe feat-B        (并行)
   113	  └── Task C: lx-rpe feat-C        (并行)
   114	       ↓
   115	  聚合报告 → lx-oma-orch 更新 pipeline
   116	```
   117	
   118	独立子任务（互不依赖）→ Race 并发。有依赖 → Stepwise 串行。
```

## 4. 现状变更：oracle_gate.py 已是符号链接（在途改动，未提交）

```
-rwxr-xr-x@ 1 lucas.liang  staff  3773 Jul  9 23:26 .claude/scripts/oracle_gate.py
lrwxr-xr-x@ 1 lucas.liang  staff    36 Jul 19 01:22 .omc/scripts/oracle_gate.py -> ../../.claude/scripts/oracle_gate.py
```

> `.omc/scripts/oracle_gate.py` → `../../.claude/scripts/oracle_gate.py`（2026-07-19 01:22 工作区改动）。你的"逐字重复双副本"表述需更新为"已符号链接的单副本 + 悬挂入口"；删除两处路径的裁决不变，`git rm` 对符号链接适用。

## 5. `.claude/skills/` 目录清单（佐证命令风格裁决）

```
SKILLS.md
TEMPLATE.md
archived
lx-code-review
lx-dogfood
lx-ghost
lx-git-check
lx-goal
lx-learner
lx-oma
lx-oracle
lx-root-cause-analysis
lx-rpe
lx-skillify
lx-task-spec
lx-validate-skill
lx-varlock
references
skill-dependencies.yaml
```
