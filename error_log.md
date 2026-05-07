# Error Log — 文档与实际偏差报告

> 生成日期：2026-05-04
> 来源：全量深度代码库调研 vs 文档声明
> 宪法依据：AGENTS.md 铁律第一条"禁止编造"
>
> 修复状态：2026-05-04 已修复 6/6 项

---

## 偏差 1：版本号不一致 ✅ 已修复

| 文件 | 行号 | 声称版本 | 实际应版本 |
|------|------|---------|-----------|
| `README.md` | 3 | v6.1.8 | ✅ 一致 |
| `source/install.sh` | 4 | v6.1.7-stable | 应为 v6.1.8-stable |
| `.claude/skills/VERSION` | 1 | 6.1.7 | 应为 6.1.8 |

**根因：** v6.1.8 发布后，`skills/VERSION` 和 `install.sh` 未同步更新。
**修复：** 更新这两个文件到 v6.1.8。
**状态：** ✅ `.claude/skills/VERSION` → 6.1.8，`source/install.sh` → v6.1.8-stable

---

## 偏差 2："24 个底层物理拦截器"（数字偏低）✅ 已修复

**文档：** `README.md:73`、`docs/features.md:13`

```
文档声称：24 个
实际数量：26 个（.claude/hooks/ 下 27 文件，排除 harness_config.sh）
```

CHANGELOG 自身记录为 "Claude Code 26/26 hooks"（`CHANGELOG.md:24`）。
**修复：** 更新为 26。
**状态：** ✅ `README.md` + `docs/features.md` 已更新

---

## 偏差 3："19 款主动工作流流水线"（数字偏低）✅ 已修复

**文档：** `README.md:82`

```
文档声称：19 款
实际数量：23 个 skill 目录
```

严格统计（有 SKILL.md + 配套脚本/引用）至少 19+ 个，宽松统计 23 个。文档写 19 属于**低估**。
**修复：** 更新为实际数值。
**状态：** ✅ `README.md` 已更新为 23

---

## 偏差 4（严重）："19,280 Tokens / 75% 上下文缩减" 无证据 ✅ 已修复

**文档：** `README.md:28`、`docs/marketing/v6.1.8-dual-domain-scoring.md:182`

该数字最初被认为仅 README.md 中出现一次。后续 Round 4 审计发现同样出现在双域评分文档中。任何地方均无：
- Benchmark 脚本
- 计算公式或推导过程
- 对照测试数据
- 测试用例

按 AGENTS.md 证据层级规范，该声明仅达到 **L4（格式合法）**，远低于要求的 **L1（端到端功能验证）**。
**修复：** 从 README.md 中删除该无证据数字；从 `v6.1.8-dual-domain-scoring.md` 中替换为 `[内部自检，非行业标准]` 标注。
**状态：** ✅ 已删除/标注

---

## 偏差 5（严重）："50% 主动交接" 未实现 ✅ 已实现

**文档：** `README.md:36-38`

```
文档声称：50% → 强烈警告 → /compact
实际实现：仅 80% 硬阻断（Exit 2）存在，50% 软告警不存在
```

`context-guard.sh` 只实现了 80% 时的 `exit 2` 硬阻断。50% 主动交接/警告在任何 hook 中均未实现。`task_sys/context_guard.md` 仅提到 40% 触发总结（Enhanced 专属），与 README 中描述的 Base 版 50% 机制不同。
**修复：** 根据实际需求实现完整的 50% 主动交接机制。
**状态：** ✅ 已实现。新增 `proactive-handoff.sh`（PostToolUse hook），更新 `context_guard.md` 文档，注册到 `settings.json`。
**机制：** Enhanced 专属，step 完成 + 上下文 >50% → 输出主动交接警告，提醒 /compact。
**文件：** `.claude/hooks/proactive-handoff.sh`、`.claude/task_sys/context_guard.md`

---

## 偏差 6："26 个 hooks 自动运行"（部分不准）✅ 已修复

**文档：** `source/CLAUDE.md:13`、`ROOT/CLAUDE.md:14`

有 26 个 hook 文件，但并非全部"自动运行"：
- `plan-gate.sh` — 默认 `plan_gate: false`，跳过
- `skill-flywheel.sh` / `flywheel-report.sh` — 按 YAML 配置选择性启用
- 多个 hook 通过 `hc_enabled()` 检查 YAML 配置，配置关则立即 `exit 0`

**修复：** 改为 "26 个 hooks（按 YAML 配置自动运行）"。
**状态：** ✅ `CLAUDE.md` + `source/CLAUDE.md` 已更新

---

## 已验证准确的部分

| 文档声称 | 文件位置 | 验证状态 |
|---------|---------|---------|
| Privacy Gate 阻断 .env / *.pem / id_rsa | `privacy-gate.sh:36` | ✅ |
| Context Guard 80% Exit 2 | `context-guard.sh:50` | ✅ |
| Completion Gate 证据门禁 | `completion-gate.sh:73` | ✅ |
| 6 平台适配器 | `.hooks/adapters/` | ✅ |
| A→B→A 对抗验证 | `lx-code-review` skill | ✅ |
| 6 条铁律 | `AGENTS.md` | ✅ |
| 跨平台热插拔 | `unified.yaml` + `generate.py` | ✅ |
| OOM 硬阻断原理 | `context-guard.sh` | ✅ |
| 渐进式披露 | L1/L2/L3 加载矩阵 | ✅ |
| 软语言禁令 | `completion-gate.sh` | ✅ |
| Enhanced 激活机制 | `profiles/enhanced/append-to-claude.md` | ✅ |
| OMA 并发锁 | `oma_lock_manager.py` | ✅ |
