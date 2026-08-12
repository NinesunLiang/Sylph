# 0016. 治理架构降噪：前置引导定路径 + 途中轻量 + 末端校验

**日期**: 2026-08-13
**来源**: 独立评估-index16-新机制效能验证盲评（降噪三面改造）

## 上下文

index15 盲评（C8.81/E8.78/长期8.29/UX7.57）后量化发现治理重心严重偏斜：

- 每次工具调用触发 **6+ 道途中防错 gate**（audit 实测 sensitive-edit/fallback/action/secret-scan/plan/edit-scope 各 3836+ 次/日），绝大多数是重复防错；
- **前置引导形同虚设**：scorecard-gate 仅触发 7 次，working-set 路径契约存在但未显式注入 AI 上下文；
- 防编造（E2/E3）防线虽强，但治理精力 99% 花在"途中频繁拦截"而非"前置定路径"。

用户裁决方向（"从放错，到只做正确的事情"）：**前置引导（schema）是路径唯一和正确的关键 → 实施途中不再防错（防不过来）→ 实施结束前（TDD）做必要门禁**。

## 决策

治理架构改为三段式：**前置引导定路径 → 途中轻量 → 末端校验**。

1. **前置引导强化（schema 定路径）**：
   - `working-set.yaml` 的 `allowed_paths`/`denied_paths` 作为路径契约真源；
   - `pretool-scorecard-gate.py` v2 升级为**全写工具路径预检**：写越界 → REDIRECT 引导，治理区（.omc/.claude）豁免；
   - `carros_base.py init` 激活时**打印路径契约**（allowed/denied），AI 一开始就规划在 schema 内。

2. **途中砍防错（防不过来）**：
   - `pretool-gate.py` L1 从 9 道砍为 **5 道真安全门**（sensitive-edit/governance-bypass/action/secret-scan/stall）；
   - L2 从 20 道砍为 **15 道**（保留 verify/oracle/g6-budget 等真校验，砍 source-marker/fallback/plan/edit-scope/claim-source）；
   - 删除死代码 hook ×4（posttool-bash-audit/session-resume/token_writer/turn-counter）；
   - 删除失效描述 `skill-dependencies.yaml`（引用不存在的 lx-oma 管线）。

3. **中间轻量化（进程合并）**：
   - `hook-launcher.py` 支持单次 spawn 串行执行多 hook（空格分隔）；settings.json 合并后 Write 调用 8→5 spawn、Bash 6→4。

4. **末端校验保留（必要门禁）**：
   - `verify_gate.py` / `completion-gate.py` 原样保留——防编造（断言匹配）、防虚假完成（软完成检测）、plan 完成度检查是最后防线。

## 替代方案

- **温和砍**：只砍 fallback/plan/edit-scope 三道，保留 secret-scan/action → 途中仍有 4 道 gate，开销未充分下降；
- **只强前置**：不砍途中 gate，只升级 scorecard-gate → 3836+ 次/日途中开销仍在，仅治标；
- **全砍**：pretool-gate 完全移除 → 安全边界归零，敏感路径/密钥/危险命令无拦截，风险过高。

## 理由

选"激进砍 + 强前置"而非替代方案：

- **防不过来**：途中 gate 每工具调用跑 6+ 道，99% 是重复放行（audit 实证），边际收益趋零；
- **前置更有效**：路径契约（allowed/denied）在任务开始时定路径，比途中事后拦截更强——AI 一开始就走对，而非走错被拦；
- **防线不归零**：真安全 gate（敏感/危险/密钥/治理绕过/卡死）保留，末端 verify_gate/completion-gate 兜底 E2/E3；
- **index16 实证**：真实 L2 任务验证 4 机制点生效 + E1/E2/E3 防线无泄漏，C/E 回 9.00、长期治理 +0.57、UX +0.86。

## 后果

- **正向**：每工具调用 spawn 从 8 降至 5；路径越界前置拦截；AI 更少被途中门禁打断；
- **约束**：scorecard-gate v2 仅在活跃任务 working-set 时生效，需真实任务积累验证稳定性；
- **风险**：E1/E2 依赖前置+末端补位，若 scorecard-gate v2 失效则目标漂移防线退化——需监控；
- **兼容**：settings.json 是本机配置（gitignore），团队共享需单独分发；
- **防线迁移**：防编造从"途中频繁提醒"移到"末端严格校验"，强度未降但位置变化，需保持末端 gate 不被砍。
