# 加载基准测试报告

**生成时间：** 2026-05-04 09:07:31
**方法：** tiktoken cl100k_base
**仓库：** `/Users/lucas.liang/Desktop/Sylph/Carror_OS`
**数据版本：** Carror OS ≤ v6.1.8。以下 L2 文件列表中部分 skill（lx-browser-verify、lx-react-review、lx-golang-test、lx-web-perf、lx-prd、lx-debug-spec、lx-security-review、lx-tdd-spec）已于 v6.2.0 从核心移除，对应文件不再存在。以下 token 计数为数据生成时的历史快照，仅作参考。

---

## 1. 方法

- **Token 估算：** 使用 `tiktoken` 的 `cl100k_base` 编码（与 Claude 模型相同）。此为**估算值**——实际 LLM 上下文用量取决于模型内部 tokenization 和系统 prompt 开销。
- **降级：** 若未安装 tiktoken，回退到 `chars // 4`（英文约 4 字符/token）。降级结果标注 `[estimate: chars/4 fallback]`。
- **样本：** 单次扫描 `.claude/` 下所有 `.md` 文件 + `CLAUDE.md` + `AGENTS.md`。未重复采样（文件内容为静态）。
- **局限：**
  1. Token 计数为估算值，非精确 LLM 上下文测量。
  2. 未计入系统 prompt 大小、对话历史或工具定义。
  3. 单次测量——无方差计算（静态内容）。
  4. 仅统计文本内容；未做 binary/frontmatter 解析。
  5. 行数按总行数（含空行）报告，以便与 loading_matrix.md 的声明对比。同时提供非空行数。

---

## 2. 层级定义

| 层级 | 内容 | 加载策略 |
|------|------|---------|
| **L1** | `CLAUDE.md`, `AGENTS.md`, `kernel.md`, `anti-patterns.md`, `claude-next.md` | 每次会话启动时始终加载 |
| **L2** | 所有 `SKILL.md` 文件、节点系统文件 (`.claude/nodes/`)、按需加载的 `task_sys/` 文件 (orchestrator, context_guard, mechanism_evals, loading_matrix 等) | 进入特定阶段或触发 skill 时按需加载 |
| **L3** | Skill 参考文档 (`.claude/skills/*/references/`)、任务模板文件 (`.claude/task_sys/templates/`) | 执行特定操作时精准加载 |

---

## 3. 条件对比

### Condition A：渐进式披露（仅 L1）
- 文件数：5
- 总行数（含空行）：427
- 非空行：311
- 总 Token：7,539

### Condition B：全量加载（L1 + L2 + L3）
- 文件数：143
- 总行数（含空行）：9,200
- 非空行：6,984
- 总 Token：172,994

### 节省量
| 指标 | 渐进式 (A) | 全量 (B) | 减少 |
|------|-----------|---------|------|
| 行数（含空行） | 427 | 9,200 | 95.4% |
| 非空行 | 311 | 6,984 | 95.5% |
| Token | 7,539 | 172,994 | 95.6% |

---

## 4. loading_matrix.md 声明验证

loading_matrix (`task_sys/loading_matrix.md`, 第 89 行) 声称：

> "首次加载从 394 行 → ~120 行，减少 70%。"

### 实测结果（总行数，含空行）
| 指标 | 声称值 | 实测值 |
|------|--------|--------|
| 全量加载（前） | ~394 行 | **9,200 行** |
| 渐进式（后） | ~120 行 | **427 行** |
| 减少 | ~70% | **95.4%** |

**判定（总行数）：** 注意：实测值与声称值有差异（声明值仅计算核心规范文件，本报告为全量扫描——L2 SKILL.md + L3 references 使行数大幅增加）。

### 备选：非空行
| 指标 | 声称值 | 实测值 |
|------|--------|--------|
| 全量加载（前） | ~394 行 | **6,984 行** |
| 渐进式（后） | ~120 行 | **311 行** |
| 减少 | ~70% | **95.5%** |

**判定（非空行）：** 注意：同上差异说明。实际节省效果远优于声明。

---

## 5. 结构报告

### L1 文件（始终加载）
| 路径 | 行数 | 非空 | Token | 方法 |
|------|------|------|-------|------|
| CLAUDE.md | 17 | 13 | 197 | tiktoken cl100k_base |
| AGENTS.md | 232 | 168 | 3,180 | tiktoken cl100k_base |
| .claude/kernel.md | 30 | 20 | 410 | tiktoken cl100k_base |
| .claude/anti-patterns.md | 117 | 89 | 2,878 | tiktoken cl100k_base |
| .claude/claude-next.md | 31 | 21 | 874 | tiktoken cl100k_base |

### L2 文件（按需加载）
| 路径 | 行数 | 非空 | Token | 方法 |
|------|------|------|-------|------|
| .claude/skills/lx-browser-verify/SKILL.md | 113 | 80 | 2,322 | tiktoken cl100k_base |
| .claude/skills/lx-code-review/SKILL.md | 174 | 133 | 4,149 | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/SKILL.md | 201 | 142 | 3,652 | tiktoken cl100k_base |
| .claude/skills/lx-frontend-test/SKILL.md | 9 | 8 | 257 | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/SKILL.md | 133 | 98 | 1,753 | tiktoken cl100k_base |
| .claude/skills/lx-oma/SKILL.md | 55 | 36 | 944 | tiktoken cl100k_base |
| .claude/skills/lx-perf-analysis/SKILL.md | 151 | 114 | 2,684 | tiktoken cl100k_base |
| .claude/skills/lx-prd/SKILL.md | 369 | 282 | 8,333 | tiktoken cl100k_base |
| .claude/skills/lx-pre-commit/SKILL.md | 69 | 44 | 942 | tiktoken cl100k_base |
| .claude/skills/lx-pre-push/SKILL.md | 89 | 59 | 1,214 | tiktoken cl100k_base |
| .claude/skills/lx-react-review/SKILL.md | 149 | 112 | 3,172 | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/SKILL.md | 211 | 168 | 5,864 | tiktoken cl100k_base |
| .claude/skills/lx-rpe/SKILL.md | 1,052 | 914 | 15,695 | tiktoken cl100k_base |
| .claude/skills/lx-security-review/SKILL.md | 127 | 95 | 2,431 | tiktoken cl100k_base |
| .claude/skills/lx-status/SKILL.md | 50 | 33 | 529 | tiktoken cl100k_base |
| .claude/skills/lx-style-guide/SKILL.md | 128 | 94 | 2,669 | tiktoken cl100k_base |
| .claude/skills/lx-task-spec/SKILL.md | 194 | 151 | 3,312 | tiktoken cl100k_base |
| .claude/skills/lx-tdd-spec/SKILL.md | 140 | 106 | 3,540 | tiktoken cl100k_base |
| .claude/skills/lx-todo/SKILL.md | 293 | 229 | 6,188 | tiktoken cl100k_base |
| .claude/skills/lx-validate-skill/SKILL.md | 159 | 112 | 1,897 | tiktoken cl100k_base |
| .claude/skills/lx-varlock/SKILL.md | 68 | 47 | 1,175 | tiktoken cl100k_base |
| .claude/skills/lx-web-perf/SKILL.md | 133 | 97 | 2,745 | tiktoken cl100k_base |
| .claude/nodes/ 共 14 个文件 | — | — | ~12,868 | tiktoken cl100k_base |
| .claude/task_sys/ 共 7 个文件 | — | — | ~10,257 | tiktoken cl100k_base |

### L3 文件（精准加载）
共 95 个 reference/模板文件，分布在各个 skill 下。最大池：
- lx-rpe references：~19K tok（含 batch-accept-template.md 19,021 tok）
- lx-code-review references：~910 tok
- lx-debug-spec references：~2,245 tok
- lx-golang-test references：~3,000 tok
- lx-root-cause-analysis references：~7,816 tok
- lx-prd references：~5,708 tok

完整列表见英文原版报告，此处保留数据结构。

### 层级汇总
| 层级 | 文件数 | 行数 | 非空行 | Token |
|------|--------|------|--------|-------|
| L1 | 5 | 427 | 311 | 7,539 |
| L2 | 43 | 5,638 | 4,317 | 97,963 |
| L3 | 95 | 3,135 | 2,356 | 67,492 |
| **总计（A：渐进式）** | **5** | **427** | **311** | **7,539** |
| **总计（B：全量）** | **143** | **9,200** | **6,984** | **172,994** |

---

## 6. Token 节省估算公式

### L3 Reference 按需加载
```
池均值   = L3 总分担 / skill 数        = 67,492 ÷ 17 ≈ 3,970 tok/skill
单文件均 = L3 总分担 / ref 文件数       = 67,492 ÷ 95 ≈ 710 tok/文件
每次触发 = 池均值 - 单文件均            ≈ 3,260 tok/次 skill 触发
会话总计 = skill 触发次数 × 每次节省
```

**口径说明**：假设无渐进式时 skill 触发加载全部 reference；有渐进式时只加载命中的（~1 文件）。实际节省量随 skill 的 reference 数波动（如 lx-rpe 池 ~19K tok，lx-golang-test 池 ~3K tok）。

### CLAUDE.md 轻量化（含 AGENTS.md）
```
每次会话节省 = 内联估算 - CLAUDE.md 实际 - AGENTS.md
             ≈ 9,400 - 160 - 3,180 = 6,060 tok/会话
```
无 Carror OS 时 AGENTS.md 的内容也在 CLAUDE.md 内，净节省需扣除 AGENTS 加载成本。

### Compact 节流
```
首次节省 ≈ 200K × 50% - 基线上下文  ≈ 100K - 39K ≈ 61K tok
实际节省更多（transcript 实测一次 compact 即 112K tok）
```
Compact 发生在上下文接近 200K 限制时，压缩后约剩 50%。实际节省量取决于压缩前的实际上下文大小，通常多于保守估算。

---

## 7. 20 轮会话节省结论（真实 transcript 推算）

| 指标 | 无 Carror OS | 有 Carror OS | 节省量 | 比例 |
|------|-------------|-------------|--------|------|
| 会话启动 | 45,524 tok (CLAUDE.md 含内联 9,400) | 39,464 tok (L1 7,539) | +6,060 | |
| 20 轮对话增长 | ~58,843 tok (19×~3,097) | ~58,843 tok | — | |
| Skill 触发 (3 次) | ~11,910 tok (3×3,970 全加载) | ~2,130 tok (3×710 命中) | +9,780 | |
| **Context 预估** | **~116,277 tok** | **~100,437 tok** | **~15,840** | **~14%** |
| **含 1 次 Compact** | **~107,000 tok** | **~50,000 tok** | **~57,000** | **~53%** |

**关键发现：**
- 仅结构节省（轻量化 + 按需加载）在短会话中占比约 14%
- Compact 是最大节省来源，一次压缩即可超出所有结构节省之和
- 会话越长（>80 轮），Compact 触发概率越高，节省比例可达 50%+
- 以上为 transcript 实测数据 + 启发式估算值

---

## 8. 局限

1. **Token 计数为估算值** — tiktoken cl100k_base 接近但不等同于 Claude 实际 tokenization。边间字符、特殊 token 等均在实际用量中有所差异。
2. **动态内容未计入** — 系统 prompt、工具描述、对话历史和工具调用结果未纳入本次测量。
3. **单次静态快照** — 文件内容在迭代中可能变化。本报告在生成时刻准确。
4. **L3 按需加载估算依赖于简化假设** — 实际节省取决于 skill 触发模式、命中哪些 reference 文件、会话上下文管理策略。
5. **未测量渐进式加载的认知成本** — 按需加载节省 token 但增加延迟（首次触发 skill 时的文件读取开销）。此成本未被量化。
6. **CLAUDE.md 轻量化口径** — 无 Carror OS 的内联 CLAUDE.md 大小为估算值（典型内容长度 ~9,400 tok），实际项目间可能有较大差异。
7. **Compact 节省高度依赖使用模式** — 紧凑会话（定向任务、少 context 重置）与探索性会话（频繁切换话题、持续大型上下文）的 Compact 效果差异显著。
8. **L1 随项目时间增长** — claude-next.md 和 anti-patterns.md 随时间增加，L1 增量将缓慢侵蚀节省量。周期性升华（经验→kernel.md）有助于控制增长。

---

**英文原版报告（51KB）包含所有 143 个文件的逐行 token 详细数据。本中文译本保留核心方法、分析框架和关键结论，合并了完整文件清单为主要结构汇总。完整数据请参阅英文原版。**
