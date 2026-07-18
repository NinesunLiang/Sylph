# §17a 闭环记录 — GPT-5.6 Sol 复审（有条件闭环 → 补件完成，待终验）

> 复审回执：GPT-5.6 Sol 对 `audit-response-gpt-5.6Sol.md` 的复审结论（用户转贴）
> 本文：① 复审裁决 ② 两项未决条件的处置 ③ 与 Opus/Grok 不同的新东西 ④ §17a 三家总状态

## 1. GPT 复审裁决（原文要点）

```yaml
review_verdict:
  design_consensus: ACCEPTED        # 修复方向/定性/R-SOL 设计 全部认同
  p0_sol_1_claim: CONDITIONALLY_CLOSED
  artifact_verification: PENDING    # 仅凭回执文本不能独立核验实物
  first_night_go: BLOCKED           # 仍缺 S1 签署 + Phase 0 五项输入
  ga_go: BLOCKED                    # P2-SOL-1 等 GA blockers 不动
```

两项未决条件：①源码—日志—digest—independent bag 四向一致性核验；②`NIGHT_DENY_ROOT` 生产不可操纵性确认。
GPT 明示：四向比对完成 + 源码包逐字核验后，可更新为 `p0_sol_1: CLOSED / artifact_verification: PASSED / first_night_go: CONDITIONAL`。

## 2. 两项条件的处置（全部落地，机械验证）

### ① 四向一致性核验 → `UI/round5/sol-artifact-verify.py`（全 PASS）

| 核验 | 结果 |
|---|---|
| hook/launcher sha256 == control_plane_lock 条目 | ✅ `c5b8fbd7…` 一致（锁覆盖信任边界自身） |
| 真仓当前 digest == 独立袋 == self 袋 | ✅ `1a356692…` 三向 MATCH |
| 旧独立袋 `d1255cd2…` ≠ 当前（9b 过期拒收物理基础） | ✅ |
| R-SOL-A 端到端：exit 2 **且 marker 字节不变**（GPT 点名"证命令未执行"） | ✅ |
| 钉版哈希（hook/launcher/独立袋/源码包/digest 全量 64hex） | ✅ 日志 `sol-artifact-verify-20260718.log` |

GPT §4 点名的其他细节一并补证：`_mask_quotes` 转义边界（`"a\"$(id)"` 拦 / `'$(id)'` 放）、白名单过宽分支（gh 必须 `--draft` 禁 `--repo`；git 禁 `--amend/--no-verify/--force/-f`）、run-gate 参数穿透（类 6 继续绿）、independent 独立性（rsync /tmp 独立树）。

### ② NIGHT_DENY_ROOT 生产不可操纵 → 双层代码锁（非文档约定）

1. `hook-launcher.sh` 生产路径显式 `unset NIGHT_DENY_ROOT`；
2. hook 内锚定优先：锚定根处于夜间时 env override 一律忽略（拐根攻击端到端 BLOCK；测试覆写在锚定根白天时正常）。

### 复审后回归（hook/launcher 变更 → digest 再滚动，R-SOL-I 重跑全绿）

smoke self **80/80** + independent **80/80**（新 digest `1a356692` 入袋）+ Grok-A/B 7/7 + Opus P1 13/13 + Sol verify 24 攻击 BLOCK（逐例 marker-intact）/21 合法 ALLOW + 四向核验全 PASS。

## 3. GPT 带来的新东西（记账）

1. **唯一一家打穿"hook 前提"的审计**：Grok/Opus 证明的是"hook 拦住控制面写入 ⇒ 权威链闭合"；GPT 证明的是前提本身不成立（动态路径删 marker 关灯）。三家是纵深互补，不是重复。
2. **拒收"只差 Owner 签署"的表述**：`owner_signoff_sufficient: false`——S1 承接理论残余，不承接一行可复现 payload。此措辞已并入放行口径。
3. **证据分级**：设计认同 ≠ 实物核验。本轮起所有 fresh payload 日志配钉版哈希（§9.3 #6），后续审计可直接复跑比对。
4. **无虚构开脱**：GPT 复审对不确定项（实物未亲验）明确挂 PENDING 而非采信文本——与 Opus 轮"漏读推给版本差异"形成对照，无需勘误。

## 4. §17a 三家总状态

| 审计方 | 状态 |
|---|---|
| Grok-4.5 | ✅ 闭环（3 P0 修复 + 复审确认） |
| Opus 4.8 | ✅ 闭环（3 P1：2 误报锁证 + 1 真洞修复，复审确认） |
| GPT-5.6 Sol | ✅ **有条件闭环**（P0-SOL-1 修复+fresh payload 锁定；两项补件已落地并机械验证，待 GPT 对 §9 补件+源码包终验盖章——其自身条件已全部满足，无遗留技术项） |

**首夜放行剩余条件（与审计无关的两项）**：
- Owner S1 签署（Phase 0 B7；承接 GPT §5 残余清单六条）
- Phase 0 五项输入（目标 repo 位置 / 首夜页面 / 原型路径 / PRD 路径 / API 文档路径）

**GA blockers**：P2-1+P2-SOL-1（supervisor 独立写身份）/ §18 / 真实首夜 / P1-4 红队 / P2-7。

## 5. 给 GPT 终验的物料清单

1. `UI/round5/audit-response-gpt-5.6Sol.md` §9（复审补件：锁紧 + 四向核验 + 回归表）
2. `UI/round5/opus-source-package.md`（post-Sol-复审重建，135 KB / 2791 行，含 hook v3.1、smoke 80 例驱动、全部日志逐字）
3. 可复跑验证：`python3 UI/round5/sol-artifact-verify.py`（四向）、`python3 UI/round5/sol-p0-verify.py`（55 项 payload）
