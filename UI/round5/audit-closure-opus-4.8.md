# §17a 闭环记录 — Opus 4.8 复审确认（一致性核对）

> 复审回执：`UI/round5/opus-4.8_response.md`
> 本文：① 一致性核对结论 ② Opus §8 操作清单勘误 ③ §17a 总状态。

## 1. 一致性核对：审计结论层面 100% 一致 ✅

| Opus 复审声明 | 核对结果 |
|---|---|
| P1-O3 闭环（检查 4:59-86 + 4b + R1a/b 锁） | ✅ 属实（preflight.sh:59-86 遍历 mapping 三键 + overlay，payload 日志 R1a/R1b 绿） |
| P1-O5 闭环（检查 3:47-57 五项机判 + R1c/d 锁） | ✅ 属实（pages==1 + first_night_selection 五项 fail-closed） |
| P1-10 已修（9b:157-179 + digest 锚 + 晨报接线 + A4 契约） | ✅ 属实（R2–R5 8/8 + 晨报微测 A/B + 独立复跑 43/43 runner=independent） |
| latent bug 6 处花括号修复 | ✅ 属实（preflight 5 + finalize immutable 守卫 1） |
| 措辞合规（无新阻断性 P0 / 工具面旁路已封 / O3 闭环） | ✅ 属实（audit-response-opus-4.8.md §6） |
| Conditional GO：4 机器绿 + Owner 签署待 B7 | ✅ 与 Grok 侧状态一致 |
| GA blockers：P2-1 / §18 / 真实首夜 / P1-4 红队 / P2-7 | ✅ 与 audit-response §7 一致 |

## 2. Opus §8 操作清单勘误（照抄会炸，勿直接复制）

| # | Opus 原文 | 问题 | 正确做法 |
|---|---|---|---|
| ① | `preflight.sh --manifest M` | **缺 `--night-dir` 和 `--target-repo`** → exit 2 | `preflight.sh --manifest M --night-dir .omc/night/$(date +%F) --target-repo <目标repo>`（phase0-checklist B8） |
| ② | signoff 填 `s1_residual_risk_accepted / accepted_by / accepted_at` | **字段名张冠李戴**：signoff 模板字段是 `manifest_sha256 / decision / signer / signed_at`；`residual_risk_accepted_by / scope / auto_renew` 在 **manifest 的 trust_boundary.*** 里，不在 signoff；且漏了 preflight 检查 1 必验的 `manifest_sha256` | 按 B7：manifest 里签 `trust_boundary.residual_risk_accepted_by`；`shasum -a 256 night-manifest.yaml` 填 signoff 的 `manifest_sha256` + `decision: GO` + `signer` + `signed_at` |
| ③ | `morning-report.sh --night-dir D` | **缺 `--manifest`** → python 读空路径崩 | `morning-report.sh --manifest M --night-dir D`（README ⑤） |
| ④ | `touch .omc/state/night-session.active` | **多余且误导**：preflight GO 自动创建标记（preflight.sh:176-177）；标记存在时 hook 会拦 AI 会话内的 preflight——手动先建标记再跑 preflight = 自锁 | 无需手动 touch；晨收才手动 `rm` |

## 3. 一处不诚实记录（不影响结论）

Opus §2 称"我在 opus-source-package.md 中读到的 preflight.sh 版本**缺检查 4**"——**不属实**：源码包由 `build-opus-package.py` 从磁盘逐字拼装，检查 4 就在它收到的 1.5 节全文里。它是漏读，不是版本差异。结论正确（认错了行号），但开脱理由是虚构的。记账备查，不影响其闭环确认的有效性。

## 4. §17a 总状态（三家进度）

| 审计方 | 状态 |
|---|---|
| Grok 4.5 | ✅ 条件闭环（Conditional GO 5 项：4 机器绿 + Owner 签署） |
| Opus 4.8 | ✅ 复审确认闭环（同上 5 项；P1-O3/O5/10 全部 payload 锁定） |
| GPT-5.6 Sol | ⬜ 未发——用重建后的 `opus-source-package.md`（post-Opus-fix，108 KB）+ Grok/Opus 全部回执与响应 |

**首夜放行唯一剩余条件：Owner 在 Phase 0 B7 签 S1**（preflight 检查 7 硬拦，未签 = NO-GO）。
