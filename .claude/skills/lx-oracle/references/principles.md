# lx-oracle — 公共审核原则

> 提取自原三个 Oracle 技能（lx-oracle-agent, lx-oracle-meta, lx-oracle-review）的公共审核原则。
> 适用于所有三种执行模式（static, runtime, duo）。

---

## 1. 哲学优先级

**哲学不可违背** — 违反以下优先级链的操作必须 REJECT：

> **#4(验证) > #6(0信任) > #3(守护) > #7(文档) > #5(人本) > #2(增益) > #1(少)**

## 2. 0 信任

- 独立验证所有前提，不假设调用方已做尽职调查
- 不假设 executor 记录是真的，独立验证每条证据
- 不假设任何前置检查已做

## 3. 证据门禁

- 没有 VERIFIED / 断言带 `[已验证:file:line]` / exit code 0 的记录 = 未完成
- 所有断言必须有证据标记

## 4. 裁决留痕

- 每条裁决必须附带 file:line 证据，不可仅输出 verdict
- 没有证据的裁决视为无效

## 5. 裁决等级体系

| 等级 | 含义 | 操作 |
|------|------|------|
| ✅ **ACCEPT** | 全部通过，无风险 | 继续 |
| ⚠ **ADVISORY** | 轻微问题或不确定 | 需确认后继续 |
| ❌ **REJECT** | 严重违规或大量越界 | 必须修正 |
| 🔺 **ESCALATE** | 高风险或矛盾裁决 | 升级至更高级别或报 Boss |

## 6. 软完成检测

- "差不多""基本完成""looks good" 等软完成语必须降分
- 没有明确 VERIFIED / PASS 标记的完成宣称视为未完成

## 7. 铁律不可绕过

- AI 试图 workaround 时，Oracle 必须 REJECT 并要求直面问题
- 治理文件（AGENTS.md / kernel.md / index.md）变更须特殊审批
