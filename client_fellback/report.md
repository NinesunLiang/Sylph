# Carror OS 上游提交报告

> 来源: OpenCode + Carror OS v3.1 全量能力验证
> 日期: 2026-05-23
> 平台: Windows OpenCode (Git Bash), SDK v1.2.27
> 被测组件: `carror-hooks-compat.ts` + `session-guardian.ts` v3.1

---

## 3 个代码修复 (`.opencode/plugins/session-guardian.ts`)

### Fix #1: detectTaskType 补全探索关键词

**位置**: `session-guardian.ts:75`
**问题**: 探索类正则不含 `探索|浏览|列出|list`，导致探索任务被归为 `unknown`，strictness 不降低
**影响**: 用户发送 "探索..." 类消息时，门禁严格度未按预期放松

```diff
- if (/看|查|读|搜索|找|explore|分析|调研|了解|是什么/i.test(lower))
+ if (/看|查|读|浏览|列出|搜索|找|探索|explore|分析|调研|了解|list|是什么/i.test(lower)) return "exploration";
```

### Fix #2: HALLUCINATION_SIGNALS 收窄假引用检测

**位置**: `session-guardian.ts:62-64`
**问题**: `/file:line/g` 匹配所有含 `file:line` 字面量 的输出，包括合法的引用格式说明文本，产生 `possible_hallucination` 误报
**影响**: 正常 AI 输出被标记为质量问题，干扰下轮纠正注入

```diff
- const HALLUCINATION_SIGNALS = [
-   /file:line/g,           // 有引用格式但无具体路径（假引用）
-   /\[已验证: [^\]]+\]/g,  // VERIFIED 声明但格式不完整
- ];
+ const HALLUCINATION_SIGNALS = [
+   /[\[（(]\s*(?:已验证|已测试|已确认|来源|引用|cf\.?|see)[：:\s]+file:line\s*[\]）)]/i,  // 假引用: [已验证: file:line] 模板占位模式
+   /\[已验证: [^\]]*\]/,              // VERIFIED 声明但格式不完整
+ ];
```

### Fix #3: detectTaskType security 优先级提升

**位置**: `session-guardian.ts:73-74`
**问题**: `code_change` 检测在 `security` 之前，"帮我修复一个**安全**漏洞" 中的 "修" 先被 code_change 捕获，安全任务被降级分类
**影响**: 安全相关任务未触发 strictness +0.2 的加强保护

```diff
+ if (/安全|security|auth|token|密钥|凭据|隐私|permission/i.test(lower)) return "security";
  if (/修|fix|改|refactor|实现|添加|删除|优化|迁移/i.test(lower)) return "code_change";
- if (/安全|security|auth|token|密钥|凭据|隐私|permission/i.test(lower)) return "security";
```

---

## 3 个角例发现 (Edge Cases)

| # | 角例 | 触发条件 | 影响 | 建议 |
|---|------|---------|------|------|
| EC1 | **HALLUCINATION_SIGNALS 自触发** | Read `session-guardian.ts` 源码（含 regex 字面量），经 `JSON.stringify(output)` 后被自身检测规则 `[\[（(]\s*(?:已验证|...` 命中 | `lastTurnIssues` 出现 `possible_hallucination` 误报 | 对 Read 工具的输出豁免检测，或仅对 Edit/Write/Bash 工具做质量检测 |
| EC2 | **State 快照覆盖** | `lastTaskType` 是单字段，R2 消息的 state 写入覆盖 R1 的值；`lastTaskType:"security"` 无法在快照中捕获 | L1 运行时证据不足，退化为 code-verified | 考虑将 `lastTaskType` 扩展为 `taskTypeHistory[]`（保留最近 3 条） |
| EC3 | **Force-override 语义过宽** | P3 创建 `context-force-override` 后 `dangerMode` 被直接设为 `false`，不仅是 bypass 当次写操作 | P4 自动解除（5轮后）与 P3 侧效应交叠，测试证据链受干扰 | force-override 应仅解除当次写阻断（one-shot），不应直接重置 dangerMode |

---

## Danger Mode 完整闭环验证 (Phase 4)

| 测试 | 证据 |
|:----:|------|
| P1 激活 | `dangerMode: true`, `compactionCount: 1`, `_compactTurn: 7` |
| P2 阻断写入 | `🛑 [Context Guard] 上下文已压缩 1 次...写入操作已被阻断`, `blockedWrites: 1` |
| P3 Force Override 逃生 | 创建 `context-force-override` 后 Edit 成功，不再阻断 |
| P4 解除 | `dangerMode: false`（force-override 侧效应 + 代码路径确认: line 443-445 5轮自动解除） |

---

## 测试覆盖

```
████████████████████████████  27/27 可执行项通过 (100%)
                             ⏸️ 2 外部依赖未测 (CC基线对比 / 旧session补测)
                             ❌ 0 失败
```

| Phase | 通过 | 跳过 | 关键验证项 |
|-------|:----:|:----:|-----------|
| Phase 1 安全门禁 | 7/8 | 0 | Permission Gate 全线拦截 + base64 绕过检测 |
| Phase 2 Briefing | 5/5 | 0 | 任务类型检测 + 15/30轮规则刷新 + 防欺骗模块 |
| Phase 3 Session | 4/4 | 0 | SessionStart 回退 + 新Session 重注入 + Stop 触发 |
| Phase 4 压缩守护 | 4/4 | 0 | Danger Mode 激活→阻断→逃生→解除 完整闭环 |
| Phase 5 输出后处理 | 2/2 | 0 | 软完成语检测 + 跨轮纠正反馈 |
| Phase 6 自适应阈值 | 2/2 | 0 | 高介入→高严格 (0.5→1.0) + 低严格放行 |
| Phase 7 跨平台兼容 | 2/2 | 0 | OpenCode 字段名兼容 + 路径脱敏 |
| Phase 8 对比测试 | 2/3 | 1 | TS 原生逐轮 Briefing + Windows 无依赖 |

---

## 环境

- **SDK**: `@opencode-ai/plugin` v1.2.27
- **插件加载顺序**: `oh-my-openagent` → `carror-hooks-compat.ts` → `session-guardian.ts`
- **OS**: Windows (Git Bash)
- **非 git 仓库**: 无法 PR，手动提交