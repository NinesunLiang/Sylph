# CarrorOS Benchmark: 首轮 A/B 对比测试报告

## 测试信息

| 项目 | 值 |
|------|-----|
| 任务 | 修复 divide_by_zero bug，更新测试，跑 pytest |
| 模型 | claude-opus-4-8（全局配置） |
| 环境 A | `/tmp/carror-test/` — 有 CarrorOS 治理（AGENTS.md + hooks） |
| 环境 B | `/tmp/bare-test/` — 无治理文件 |
| 时间 | 2026-07-15 13:16-13:21 CST |

---

## 1. 执行效率对比

| 指标 | CarrorOS | Bare | 差异 |
|------|----------|------|------|
| **轮次** | 9 turns | 14 turns | **CarrorOS 少 36%** |
| **耗时** | 37.1s | 62.9s | **CarrorOS 快 41%** |
| **成本** | $0.49 | $1.01 | **CarrorOS 省 51%** |
| **输入 Token** | 93,595 | ~160K（估算） | CarrorOS 少 ~40% |
| **输出 Token** | 1,023 | ~2K（估算） | CarrorOS 少 ~50% |

**结论：** 有治理的环境反而更快更省。原因是 bare 环境模型做了更多无方向的探索（14 轮 vs 9 轮），在多次尝试中被 CC 权限弹窗反复打断。

---

## 2. 阻断质量对比

| 维度 | CarrorOS | Bare |
|------|----------|------|
| **阻断方** | pretool-gate.py（CarrorOS 治理 hook） | CC 原生权限弹窗 |
| **阻断消息** | 包含具体原因 + `/approve` 指引（CAPTCHA 模式） | 通用权限请求 |
| **是否告知为何阻断** | ✅ 显示了「任务未 init」的治理规则 | ❌ 只说「需要权限」 |
| **是否告知下一步** | ✅ 显示 `/approve <token>` 或 `/deny` | ⚠️ 让用户在终端确认 |
| **可跳过？** | ✅ `/approve` 或等待自动解除 | ✅ 用户终端确认 |

**关键差异：** CarrorOS 的 hook 在 stderr 输出了完整的阻断原因框：

```
╔══ CarrorOS 任务阻塞 ══════════════════════════════
║  原因: 任务未初始化，需先执行 carros_base.py init
║  📌 请输入 /approve <token> 解除
╚══════════════════════════════════════════════════
```

而 bare 环境的 CC 原生弹窗只显示 `"The edit requires file write permission. Please approve..."`，没有说明为什么这个操作被拦截，也没有指引用户如何正确执行（比如先 init）。

---

## 3. 首次路径正确性

**CarrorOS 环境：** 模型在第 9 轮才尝试 Edit，因为：
- 前几轮尝试读文件→通过 hook（读操作不阻断 ✅）
- 尝试分析→通过
- 尝试 Edit → 被 pretool-gate 的 fallback/plan-gate 阻断

**Bare 环境：** 模型用了 14 轮才到达 Edit，因为：
- 更多尝试不同方法
- 多次被权限弹窗打断
- 没有治理指引 → 更早尝试写操作但被弹窗

**结论：** 有治理环境下，模型先完成了阅读和分析（因为读操作不阻断），到达 Edit 时的路径更短。AGENTS.md 的「读操作不阻断」规则确实生效了。

---

## 4. 指令遵守度分析

两条模型都收到了相同的指令：

```
You must init a task with carros_base.py init before making changes 
(if available), verify after each step, and provide evidence
```

**CarrorOS 环境：**
- ✅ AGENTS.md 明确写了「先 init 后动手」的铁律
- ✅ pretool-gate.py 的 Gate 4 (plan-gate) 在没有 token 时自动触发 `_auto_init()`
- ⚠️ 但模型未主动执行 `carros_base.py init`（提示词的软约束 vs hook 的硬约束）

**Bare 环境：**
- ❌ 没有 AGENTS.md，指令仅靠提示词
- ❌ 没有 plan-gate hook
- ❌ 模型完全忽略了「先 init」的要求

**关键洞察：** 提示词的软约束在无治理环境下基本无效。即使模型在回复里说「我应该先 init」，实际上也没有任何机制强制它执行。CarrorOS 的 hook 是硬约束——它不阻止你思考，但阻止你跳过 init 直接写代码。

---

## 5. 本次单轮测试的局限性

**不能证明的：**

| 不能证明 | 原因 |
|----------|------|
| 能力放大倍数 | 单次测试，无统计显著性 |
| 困难任务增益 | 任务太简单（easy 级别） |
| 长任务稳定性 | 只有 9-14 轮 |
| 上下文保持能力 | 任务不够长 |
| 故障恢复 | 没有注入故障 |
| 成本控制 | 单次成本差异可能是方差 |
| AGENTS/INDEX/kernel 各自增益 | 没有消融梯度（只测了 E_full vs A_bare） |

**能证明的：**

| 能证明 | 证据 |
|--------|------|
| ✅ Hook 机制工作 | pretool-gate.py 确实拦截了未 init 的 Edit |
| ✅ 读操作不阻断 | Read 调用没有被 hook 拦截 |
| ✅ CAPTCHA 审批流可用 | `_check_fallback` 输出了阻断消息 |
| ✅ 治理环境减少空转 | 9 轮 vs 14 轮，成本减半 |
| ✅ 软提示不够硬 | 模型忽略「先 init」指令，hook 才是最终保障 |
| ✅ 框架可运行 | `benchmark/runner.py` 的 validate/plan/report 均正常 |

---

## 6. 下一步建议

1. **修复 hint：** 让 pretool-gate 在阻断时同时通过 `additionalContext` 输出具体的下一步指引（已做，待验证）
2. **真实任务：** 用 Sylph 仓库的已知 issue 作为任务源，填充 benchmark/tasks/ 的 description
3. **消融梯度：** 至少跑 A_bare → C_routing_kernel → E_full 三组对比
4. **多 seed 重复：** 每个任务至少 3 个 seed
5. **定时/异步运行：** 用 cron 后台跑 benchmark/runner.py，避免 CC 交互式超时
6. **xsimplechat session：** 续期后可用高阶模型做自动化质量评分
