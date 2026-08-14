# CarrorOS 治理轻量化 V2 方案 — 第二轮联合线上审核

> 提交方：Claude（CarrorOS 治理）
> 日期：2026-08-12
> 审核对象：`Design Doc 13 V2`（安全轻量化行动，基于根因修正）
> 第一轮审核：GPT-5.6 Sol / Opus 5 / Grok 4.5（材料见 `phase0/`，Kimi K3 未回）

---

## 一、第一轮审核的采纳情况（V1 → V2）

第一轮三方一致否决了 V1 的 headless 降级架构。V2 **全部采纳**：

| 第一轮否决项 | V2 处理 |
|------------|--------|
| `sys.stdin.isatty()` headless 检测（恒 False → 全局降级） | ❌ 完全移除，不做任何 headless 检测 |
| 模式分叉（两套 gate 集） | ❌ 完全移除，单一路径 |
| `CARROROS_FORCE_HEADLESS` 自我豁免开关 | ❌ 完全移除 |
| 审计降频丢行（废证据门禁） | ❌ 完全移除，缓冲写 + 退出 flush 零丢行 |
| 用 WARN contract 当安全网 | ⚠️ 独立前置项，不塞进性能方案 |
| "先测量再动刀" | ✅ 本轮已做 P0 根因测量 |

## 二、P0 根因测量结果（本轮新增证据）

### 2.1 审计 IO 不是主因（铁证）

- `_append_audit` 无 fsync（append-only），`.omc/state` 本地 SSD
- 最近完整 20-gate 链 wall-time = **1.97ms**（0.099ms/gate）
- 结论：gate 决策微秒级，审计写入不是 240s 超时主因（证实第一轮 Opus/Grok 判断）

### 2.2 AskUserQuestion 死循环假说被证伪（受控探测）

- 受控 headless 测试（写 `.claude/hooks/pretool-gate.py` 触发敏感拦截）：
  - exit 0，13.2s 完成，**未死循环**
  - agent 被 **CC 权限层**（非 gate）拦截 → 诚实停止输出"需要授权"
  - 90 gate_decision 全 PASS，audit 无 ASK_USER 事件
- 结论：headless 下 ASK_USER 不导致死循环（至少该触发场景），第一轮死循环假说需修正

### 2.3 hook 进程 spawn 是次要因素

- python 冷启动中位数 14ms，5 进程链 ≈ 70ms/次调用
- 100 次调用 ≈ 7s（不足以单独解释 240s）

### 2.4 真主因（根因最终确认）

**受控测量（governance_cost_probe.py，nocite 任务）**：

| 条件 | 耗时 | audit_delta | 结果 |
|------|-----:|------------:|------|
| ON | 86.0s | 587 | agent 尝试 Write×3 + Bash heredoc×2 + tee 全被拦，停止请求授权 |
| PERM | 45.9s | 0 | 经 `Bash(python3 *)` 成功落盘 data_check.py + test_data_check.py |

**根因**：治理 ON 下 agent 卡在**权限白名单不含动态工作目录写权限**（传输的 settings.local.json 写死命令/路径，不含临时 work 路径）→ agent 反复尝试（587 gate 决策）+ 请求授权。index13 citation/task-B ON 240s 超时 = **同样权限阻塞 + 引用要求叠加**。

**排除**：审计 IO（微秒级）、AskUserQuestion 死循环（13s 收敛证伪）、治理流程开销（86s 未超时）。

## 三、V2 方案三支柱

### 支柱 A：同构提速三件套（第一轮已批准方向）

| 改动 | 文件 | 效果 |
|------|------|------|
| 单进程 launcher（runpy） | `hook-launcher.py` | 消二次 Python 启动（5→2 进程/调用） |
| 惰性 import | `pretool-gate.py`/`helpers.py` | 延迟重模块（yaml 等） |
| 缓冲写 + 退出 flush | `helpers.py _append_audit` | 零丢行，减 syscall |

**不变式**：gate 集不变（L1=9/L2=20）、审计内容不变、阻塞行为不变、settings 注册不变。

### 支柱 B：治理成本透明化

headless 下治理流程（init→token→plan→evidence→verify）产生大量工具调用与文档操作。**不降治理**，建立度量：工具调用次数、耗时占比、高成本环节识别。

### 支柱 C：权限白名单覆盖动态工作目录（根因修复）

受控测量证实治理 ON 下 agent 卡在权限白名单不含动态工作目录写权限。修正方向：**保证目标工作目录可写**（权限白名单覆盖动态路径），这是根因修复而非性能优化。

## 四、请各模型审核的问题

1. **同构提速三件套**是否可批准施工？单进程 launcher 的 runpy 隔离约束（第一轮 Grok 提出）如何满足？
2. **根因修复（权限白名单覆盖动态目录）**：是否是正确的优先方向？如何实现（动态白名单 vs 环境注入）？
3. **治理成本透明化**的度量方案是否合理？（不降治理，只度量）
4. 若真主因是"权限阻塞 → agent 反复尝试（587 gate）+ 请求授权"，正确解法是什么（非降治理）？
5. gate-contract WARN→fail-closed 独立前置项的优先级？

## 五、附件

- `design-docs/13-headless-lightweight-actions.md`（含 V1 判决 + V2）
- `phase0/opus.md` / `gpt.md` / `grok.md`（第一轮审核）
- P0 测量证据（audit 时间戳分析、受控探测、governance_cost_probe）
