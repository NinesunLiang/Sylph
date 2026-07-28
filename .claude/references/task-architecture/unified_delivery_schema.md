# Unified Delivery Schema [SUPERSEDED]

> 状态: SUPERSEDED — 请参考 `@.claude/references/current-task-architecture.md`
> 最后对齐: 2026-07-28
>
> 此文件为历史设计文档。实际交付格式由 GateKeeper 6 种裁决输出替代：
> - 不存在的状态已移除: spec_review, fallback_exploring
> - 统一输出由 `gatekeeper.py` GateDecision 枚举管理
> - 证据层级保持不变，仍有效

---

## 实际交付形式

### GateKeeper 6 种裁决输出（gatekeeper.py L41-48）

| 输出 | 协议 | 含义 |
|:-----|:-----|:------|
| `ALLOW` | C | AI 自决 — 允许 |
| `ALLOW_WITH_CONSTRAINTS` | C | AI 自决 — 带约束允许 |
| `ASK_USER` | A | 真阻断 — 等待用户决策（危险/不可逆/越权） |
| `REDIRECT` | B | 轻量拦截 — 拦截+引导+auto-retry |
| `BLOCK` | A/铁律 | 阻断 |
| `SKIP` | 无人模式 | 跳过+记录到 skipped-risks |

### 证据层级（沿用，已验证）

| 层级 | 类型 | 可信度 |
|:-----|:-----|:--------|
| L1 | 端到端功能验证 | ✅ 强 |
| L2 | 测试通过 + 输出匹配预期 | 中 |
| L3 | 脚本执行成功 / 编译通过 | 弱 |
| L4 | 格式/语法合法 | ❌ 不可单独作为证据 |

### 置信度标注（沿用）

| 标注 | 含义 |
|:-----|:------|
| `[已验证: file:line]` | 从源码直接确认 |
| `[已测试: 命令+输出]` | 运行验证通过 |
| `[推断, 待确认]` | 基于上下文推理但未直接验证 |
| `[文档来源: URL/doc:line]` | 从文档确认 |

### 证据格式（executor.md schema_version: v2）

```markdown
### EV-S1
- step: S1
- type: test/review/change
- source: 执行来源
- exit_code: 0
- file: 改了什么文件
- assertion: 验证了什么
```
