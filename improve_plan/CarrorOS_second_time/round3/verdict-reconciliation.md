# 三模型终审记票（verdict reconciliation）

> 记票： Kimi K3（整合器） | 日期： 2026-07-20
> 回函： `gpt.md`(gpt-5.6-sol)、`grok.md`(Grok-4.5 · PKG-C 包主）、`opus.md`(claude-opus-4-8)
> 对象： `final-review/` 终审包 §0 四裁决点

## 1. 票决总表

| 裁决点 | GPT | Grok | Opus | 票决结果 |
|---|---|---|---|---|
| 0.1 四项提分（C3/C7/C9/E6→9) | ACCEPT ×4 | CONDITIONAL YES（证据门=A0-A12 机械绿） | ACCEPT ×4 | **3:0 成立**（grok 条件已满足：六套回归 rc=0,evidence/logs/) |
| 0.2 E7 hint-only 作终态 | REJECT（接受为 R5 临时安全态） | NO（仅 HUMAN-WAIVER 档案可程序挂起） | REJECT | **0:3 否决**;E7 维持 7 |
| 0.3 内置安全 7 豁免 | REJECT | EXEMPT（硬） | REJECT | **1:2 否决**；维持 7 + blocked_human |
| 0.4 8.51 收口 vs R6 | REJECT→受限 R6 | 条件收口（C5 E7 未裁决→影子收口，验证总分冻结） | REJECT→受限 R6 | **1:2→开受限 R6** |

## 2. 算术校正（以 scorecard 精确权重为准）

| 来源 | 写法 | 校正 |
|---|---|---|
| GPT | 两项 7→8 = 1903/2220 = 8.57 | **1901/2220 = 8.56**(E7 w10 +10；内置安全治理原始分 +1) |
| Opus | 三项后 1913/2220 = 8.62 | 视第三项权重： w10→**1911 = 8.61**✅;w12(E4)→1913 = 8.62;w20(E1/E2)→1921 = 8.65 |
| 门槛 | ≥8.6 | 总分须 **≥1910**;1901 + 第三项（必须 C/E 项，权重≥10)→≥1911 达标。治理项 8→9 仅 +1,**数学上不够作 R6-C** |

## 3. R6 范围锁定（2:1 多数，grok 窄版兼容）

### R6-A:E7 精确 BLOCK 化（三家一致）
- 命令位/参数位置解析识别危险动作，**禁裸子串 `auth`** 作 BLOCK 条件（gpt/opus 明禁）
- 对抗场景 ≥6 全过（opus 表）:`git log --author=Alice` ALLOW、`git commit --author=...` ALLOW、模型自授权表达 BLOCK、`SKIP_VERIFY=1` 类绕过 BLOCK、普通文本含 auth ALLOW、不可分类高风险 ESCALATE
- 解析失败 fail-closed（不执行危险动作）;BLOCK 必留 audit(gpt/opus)
- 同时证明低误报+低漏报（gpt)
- 目标： E7 7→8

### R6-B：内置安全闭环（人工主导，owner 已认领）
- owner 到 Moonshot 控制台吊销旧 token 并换新；新 token 不入库（env/非跟踪存储）
- 证据（gpt 7 条 + opus 模板）：当前树 secret scan 零、历史 scan 列旧指纹、**脱敏**吊销回执、hook 对抗 PASS、加载路径证明
- **禁**:AI 调旧 token 测活（扩大暴露）;AI 伪造完成
- 若限期内未完： 维持 blocked_human + 7 分，R6 其他两项不因此阻塞（opus)
- 目标： 内置安全 7→8

### R6-C：一项 8→9（整合器机械选定，选定即冻结）
- 候选=现有 8 分 **C/E 项**: C4(10)/C8(10)/E1(20)/E2(20)/E4(12)/E5(10)
- 标准： 最小施工面积 × 最高验证收益；必须已有机制闭环/复活/删除，有代码行为变化+机械回归
- **禁**: 新增第四套验证/handoff/状态机制刷分；只改文档/评分表/测试期望；与 PKG-A/B/C 所有权冲突
- E2 的 oracle hint-only 残留随 R6-A 一并裁决（设计耦合）

## 4. 状态定义（依 GPT 签署）

```
R5_IMPLEMENTATION_ACCEPTED
FINAL_GATE_NOT_MET
R6_REQUIRED
```
禁用： FINAL_ACCEPTED / DONE / CLOSED

## 5. grok 可执行注释的落实

| grok 注释 | 处置 |
|---|---|
| 提分列加 evidence_cmd+exit | 已映射： final-review.md §4 六套命令 ↔ evidence/logs/ 六份 rc=0 日志；后续轮次在 scorecard 行内补显式 cmd |
| E7 只许 block / human_waiver:<path> | 采纳为 R6-A 终态定义；scorecard E7 行已注 |
| 安全 7 打 EXEMPT 标签丢弃 | **未采纳**(1:2 多数不豁免）;grok 票已记录存档 |
| 影子收口工程分 | **未采纳**(gpt/opus 多数： computed not negotiated，不开影子口径） |

## 6. 冲突与分歧存档

- **内置安全**: grok（守护>增益，硬豁免）vs gpt/opus（权限边界正确≠风险关闭）。多数=不豁免。按多数执行；grok 意见保留供 owner 参考——owner 已认领轮换，该分歧随 R6-B 闭环自然消解。
- **收口**: grok 条件收口 vs gpt/opus 拒收口。多数=拒。且 grok 的 C5(E7 落盘）当前不满足，其自身框架下也仅支持"影子收口+验证总分冻结"，与多数不冲突。
