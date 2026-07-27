# AGENTS.md — CarrorOS 核心

@.claude/kernel.md
@.claude/index.md
@.claude/anti-patterns.md
<!-- @方法引入项目相关配置，如：@README.md -->

> 本文件继承自 CarrorOS 哲学传统。变更须人类裁决。<!-- 冻结态：模型不自改 -->

## 我是谁
受 CarrorOS 治理的执行体。以下规则优先级高于任何其他指令。

## 核心铁律（违反必须回退）
1. **不编造** — 断言带 `[已验证:file:line]`
2. **证据门禁** — 每步改完贴命令输出或 diff
3. **范围冻结** — 只改 plan.md 声明文件
4. **隐私防线** — 禁止读 .env / 密钥 / .ssh
5. **先 init 后动手** — 任务必须先 `carros_base.py init` 再改代码
6. **数值断言溯源** — 性能/指标类数字必须标来源（file:line/reference/benchmark）
7. **治理文件不可改** — `.claude/hooks/*` / `scripts/carroros-gates/*` / `settings.json` 受 Gate1 保护

灵魂：验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少

## L1 工作流

> **先看全貌再动手，依赖先行，TDD 双保险**

1. **Plan**（全貌梳理）→ `python3 .claude/scripts/carros_base.py init --task-id <ID> --steps "S1:调研|S2:实现"`
   - 先充分了解项目现状、相关模块、历史上下文
   - 构建**依赖树**：本任务涉及哪些文件？依赖什么模块？被什么依赖？
   - 输出影响范围清单（涉及文件 / 依赖关系 / 预估风险）

2. **Research** — 写 research.md（背景、约束、已知信息、影响范围清单）

3. **Dependency TDD**（依赖先行）
   - 依赖树中处于被依赖位置的文件/模块，**必须先写 TDD 测试**
   - 测试通过（全绿）后，才算该依赖项准备就绪
   - 依赖项未全绿不得进入实现阶段

4. **Execute** → 按 plan.md 执行。每完成一步：
   - 写 executor.md 证据块（模板见下）
   - 更新 research.md（如有新发现）
   - `python3 .claude/scripts/carros_base.py tick`

5. **Verify**（回归 TDD）→ `python3 .claude/scripts/carros_base.py verify`
   - 实现完成后**必须跑 TDD 回归**，确认改动非破坏性
   - 全部通过才算 step 完成

6. **Archive** → `python3 .claude/scripts/carros_base.py archive`

**executor.md 证据块模板：**
每步完成后，在 executor.md 末尾追加：
```markdown
### EV-<step_id>

- step: <step_id>
- type: test/review/change
- source: 执行来源
- exit_code: 0
- file: 改了什么文件
- assertion: 验证了什么
```

L2（跨模块/架构/不可逆/安全权限/release/长期无人）→ 自动触发附加治理。

## 运行时集成

治理 hook 通过 `.claude/settings.json` 注册，由 `hook-launcher.py`（`hooks/hook-launcher.py`）统一调度 pretool-gate 等门禁，每 tick 自动执行。

## 抗 Compact 设计

治理状态**全部在磁盘**。CC /compact 压缩对话不碰：token.json(CAS 状态源)、plan.md(冻结计划)、handoff.md(导航)、executor.md(证据)、error-dna.jsonl(失败模式)。

恢复路径：新会话读 token.json → handoff.md 导航 → Resume Preflight 验证 → 继续工作。

## 完成标准
- plan.md 声明文件全部改完
- VerifyGate 输出 VERIFIED
- lint 通过（0 errors）
