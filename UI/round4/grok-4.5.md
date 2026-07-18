**Grok-4.5 一致性审查（针对 FINAL.md v3.1）**

结论先说：

> **架构层：三家已一致。**  
> **执行规格：大体定型，但仍有 1 处对我（Grok）原提案的否决未获我显式签字、1 处产品风险裁决未获 Owner 闭口、以及若干“写法像一致、跑起来可能各解各的”执行语义空洞。**  
> 因此现在更准确的状态是：  
> **`v3.1-final (spec frozen candidate)` + `Runtime Conditional GO 未决`**，不是“全部补丁定型、可以默认可执行”。

---

## 一、我明确接受、不再争议的内容

以下我签字，无需再讨论方向：

1. R1 权威链：`final_status = reduce(manifest, gate-results, execution-events)`；`token.json` 只是恢复缓存。  
2. R2 `VISUAL_FIXING` + 证据失效传播（标 `SUPERSEDED`，不删除，C1 全链重跑）。  
3. R3 原型分型 + `overlay_contract.status: declared | confirmed_none | unknown`。  
4. R4 权威链攻击类 smoke（伪造/半写/exit 与结果冲突）。  
5. R6 机器化 `control-plane-scorecard.yaml`。  
6. S2 detached signoff、S3 two-stage delivery、S4 环境指纹。  
7. O3 逐态断言、O4 dry-cost 定预算、O1/O2 首夜不阻断。  
8. 首夜：1 页、Patch A、全 mock、K3=0、仅 DONE 建 Draft PR。  
9. 执行时无高阶模型；需要裁决 → J0。

这些已并入 v3.1，我认。

---

## 二、尚未达成一致的事项（按严重度）

### U1 【唯一明确否决我提案的地方】R5 码表——裁决合理，但缺我的正式签字

FINAL.md 的整合裁决：

```yaml
execution_status: NOT_STARTED | RUNNING | CRASHED | TERMINATED   # 晨报派生
final_status:     DONE | BLOCKED | FAILED | null                 # 三值终局
```

我原先倾向把 `CRASHED / NOT_STARTED` 收进更“可见”的终态表达；整合者否决，取 GPT/Opus 版。

**技术上我现在认可这个裁决**（理由充分：晨报派生态不应污染三值终局，和当初删 `DONE_WITH_ASSUMPTIONS` 是同一戒律）。  
**程序上：这是“整合者裁决”，不是“Grok 已同意”。**

为闭合，请直接记：

> **Grok 接受 R5 正交码表，放弃把 CRASHED/NOT_STARTED 写入 final_status。**

这一条关闭后，R1–R6 对我侧全部闭合。

---

### U2 【唯一实质的产品/风险分歧】S1 信任边界：首夜是否接受“可发现”替代“不可发生”

FINAL.md：

> 首夜 = hook deny + `scripts_digest` + 交叉校验 + 早晨 git 审计（侦探式控制）  
> 完整 supervisor / 独立写权限目录 = v3.2

这降级了我与 GPT 都强调的根问题：同一执行身份下，“模型不能写结论”仍是约定，不是物理保证。

- **侦探式控制**：篡改大概率次日能被发现  
- **预防式隔离**：执行模型写不进 gate-results / 改不了裁判脚本

两者不是同一安全级别。  
**我接受首夜可以走侦探式，但只接受为“限时风险承受”，不接受被写成“S1 已解决”。**

必须同时写死这五条，否则 U2 仍算未一致：

```yaml
trust_boundary:
  first_night_mode: detective_controls      # 非 preventive
  residual_risk_accepted_by: "<Owner>"      # 必须人类签字
  scope: "single_page_single_night"
  auto_renew: false                         # 不得默认续到第二夜
  mandatory_before_v3_2_ga:
    - read_only_policy_dir
    - supervisor_only_gate_results
    - separate_execution_identity
```

没有 Owner 对 `residual_risk_accepted_by` 的显式签署，**首夜应是 NO-GO，不是 Conditional GO**。

---

### U3 【执行语义伪共识】正文像定了，脚本仍可能各解各的

这类不是“三家互殴”，是**不钉死就会重新变成分歧**。首夜前必须进 §16 物件，否则不算真正一致：

| # | 空洞 | 必须钉死的内容 |
|---|---|---|
| 1 | O5 简单页 | 不止 `pages.length==1`，要有选页机判字段（完整输入 / V0–V1 / happy path 可测） |
| 2 | O3 assert 词表 | `skeleton_visible` 等必须是**封闭 assertion catalog**，未知 ID → preflight/C4 FAIL，禁止自由文本 |
| 3 | `scripts_digest` | 覆盖传递依赖（helper、hook、catalog、carros_base 相关），不能只哈希 6 个入口脚本 |
| 4 | gate result 事务 | 临时文件 → schema 校验 → fsync → 原子 rename；envelope 绑定 `manifest_sha256/code_sha/control_plane_digest` |
| 5 | C8a/C8b 状态 | `FINALIZED` 与 `delivery_status` 正交；`DRAFT_PR_FAILED` 不得改写 `DONE` |

上述 5 项若仍停留在散文，我会把状态标为：

> **Spec conceptually agreed, execution objects not yet consensus-complete.**

---

### U4 【版本语态】“最终版 / 补丁定型”与 GA 门自相矛盾

文档同时写：

- 「执行规格全部补丁定型」  
- 「GA 门：§16 落盘 + 五类 smoke 实跑绿 + §17a 无新 P0 + §18 闭合」

若后四项未完成，就不能让团队把 `FINAL.md` 读成“可以 `lx-goal on`”。

建议拆成：

```text
Document:        v3.1-final（可冻结）
Spec consensus:  frozen with recorded residual risk (S1)
Runtime:         RC / NO-GO until evidence
GA:              not declared
```

---

## 三、我对“已决 / 未决”的正式记账

### 已对我闭合（含我刚刚接受的 R5）

- R1, R2, R3, R4, **R5（现接受）**, R6  
- O1–O4 的方向与首夜降级策略  
- S2, S3, S4 的方向  

### 仍未闭合

1. **S1 残余风险的 Owner 承责签署**（实质未决）  
2. **U3 五行执行物件是否落盘且可 smoke**（实现未决）  
3. **O5 选页硬门是否机器化**（轻量但必须）  
4. **版本状态措辞**（文档治理）

---

## 四、签署意见（Grok）

```text
Architecture:                 SIGNED OFF
My R1–R6:                     ALL ACCEPTED（含 R5 正交版）
Spec as written:              ACCEPT with 1 recorded residual risk (S1 detective-mode)
Runtime GA:                   NO
First-night Conditional GO:   only if
                              (a) Owner 签署 S1 残余风险（单页单夜、不可自动续）
                              (b) §16 物件落盘
                              (c) 五类 smoke 含权威链攻击集实跑绿
                              (d) O5 选页机判 + assertion catalog 封闭
```

一句话给整合者和 Owner：

> **从 Grok 视角：技术方案的真实分歧只剩 S1“首夜用发现代替防止”是否被人类正式背书；其余要么我已接受裁决，要么是必须写成 schema/脚本否则会再吵起来的执行空洞。别再用“三家已一致”盖住“Owner 尚未对残余风险签字”这件事。**