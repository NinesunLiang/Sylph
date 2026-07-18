我重新按 **FINAL.md v3.1 与三家最后一轮意见逐项对账**。结论是：

> **核心架构已经一致；还剩 1 个明确的保留分歧、2 个尚未取得显式确认的裁决，以及若干“文字已纳入但执行语义尚需钉死”的问题。**  
> 这些不要求推翻 v3.1，但“执行规格全部补丁定型”这句话略早。更准确应写成：  
> **“架构定型；首夜策略接受有残余风险的 Conditional GO；执行物件待 smoke 证明。”**

---

# 一、已经达成一致的内容

下面这些可以视为三家共同结论，不必再讨论方案方向：

1. `night-manifest.yaml` 是唯一、不可变的 desired-state 契约；
2. detached signoff，避免 manifest digest 自引用；
3. 首夜只做 1 页；
4. Patch A、自定义组件体系；
5. 执行时无高阶模型；
6. J0 结构化阻塞，不允许夜间模型自行裁决；
7. `final_status` 保持 `DONE | BLOCKED | FAILED`；
8. `execution_status` 独立表达 `NOT_STARTED / RUNNING / CRASHED / TERMINATED`；
9. 结论由 `manifest + gate-results + execution-events` 重算；
10. `token.json` 仅为恢复缓存，不是结论权威源；
11. 证据绑定 `code_sha`；
12. C6 失败进入 `VISUAL_FIXING`，修改后使旧证据失效并全链重跑；
13. `verification-summary` 与 `delivery-receipt` 两阶段分离；
14. GitHub 交付失败不推翻页面验证结果；
15. 晨报遍历 manifest `pages[]`，不得遗漏崩溃或未启动页面；
16. `control-plane-scorecard.yaml` 机器生成；
17. fail-open smoke 必须包含权威链攻击用例；
18. 静态/交互/混合原型分型；
19. `required_states` 使用逐态断言契约；
20. O1/O2 首夜只作为警告和晨报指标；
21. 预算由 Phase 0 dry-cost 实测校准；
22. 只有 `DONE` 创建 Draft PR；
23. 首夜 K3=0、全 mock、不接真实后端。

这些已经形成完整共识主干。

---

# 二、唯一明确存在的实质分歧：S1 信任边界是否足以放行首夜

FINAL.md 选择的是：

> 首夜采用 hook deny、`scripts_digest`、交叉校验、早晨 Git 审计等“五层最小隔离”；完整 supervisor 权限隔离放到 v3.2。

而我的原始 S1 意见是：

> 只要实现模型和裁判仍拥有同一写权限，“模型不能自行宣布成功”就不是物理保证；至少要有只读策略目录或独立写权限的结果目录。

这不是纯措辞差异，而是**风险接受标准不同**：

- FINAL.md 的方案保证的是：篡改大概率能被发现；
- S1 完整方案保证的是：执行模型不能完成篡改；
- “可发现”不等于“不可发生”。

因此，FINAL.md 目前把 S1 从**首夜阻断项**降成了**已知残余风险**。这属于整合者的产品/风险裁决，并不等于技术上已经一致。

## 建议如何正式收口

不要写成三家技术结论完全一致，而应在签署区明确：

```yaml
trust_boundary:
  first_night_mode: detective_controls
  preventive_isolation_complete: false
  residual_risk_accepted_by: "<用户/Owner>"
  expires_after: "first_trial_night"
  mandatory_v3_2:
    - read_only_policy_dir
    - supervisor_owned_gate_results
    - separate_execution_identity
```

并把首夜决策限定为：

> **Conditional GO for one supervised-recovery trial night**  
> 不是 `GO`，更不是 v3.1-GA。

如果用户明确接受该风险，S1 就不再是“悬而未决”，而是“已裁决的残余风险”。但不能描述成已经获得预防性隔离。

---

# 三、两处“整合者已裁决，但未看到原提案方显式签字”

## 1. R5：Grok 原方案被否决，但缺 Grok 明确确认

FINAL.md 采用 GPT/Opus 方案：

```yaml
execution_status:
  NOT_STARTED | RUNNING | CRASHED | TERMINATED

final_status:
  DONE | BLOCKED | FAILED | null
```

这在建模上是正确的，我支持。它保持了：

- 运行态与终局正交；
- `CRASHED/NOT_STARTED` 不伪装成业务终局；
- `final_status` 三值稳定。

但 Grok 原提议把 `CRASHED / NOT_STARTED` 放入 `final_status`。FINAL.md 现在是**裁决了该分歧**，而不是证明 Grok 已同意。

如果目标是“三家一致签署”，需要 Grok 明确回复：

> 接受 `execution_status` 与 `final_status` 正交，不再坚持 CRASHED/NOT_STARTED 进入 final_status。

技术上无需再改文档，只差签字。

## 2. S1：需要我方明确接受“首夜风险降级”

如上所述，FINAL.md 选择的不是我原始完整方案。若保持现方案，需要把它视为：

- 用户接受风险；
- 限首夜；
- 限 1 页；
- Draft PR only；
- 早晨必须做独立审计；
- 首夜后不得无限续期。

这同样属于**裁决待签字**，而不是实现细节。

---

# 四、文字已纳入，但执行定义仍需钉死的 5 项

这几项不是三家方向分歧，而是“伪共识风险”：正文看起来一致，脚本实现时可能各自理解不同。

## 1. O5 是否真正成为首夜选页门禁

目前明确看到的是：

```text
首夜 pages.length == 1
```

但 O5 不只是“1 页”，而是：

```text
输入最完整 + 复杂度最低 + 能跑通真实 happy path 的简单真页
```

如果 §17 只是建议、没有机器化选择依据，O5 尚未真正落地。

建议在 manifest 增加：

```yaml
first_night_selection:
  input_completeness: complete
  complexity: V0_or_V1
  prototype_accessible: true
  acceptance_contract_complete: true
  happy_path_testable: true
```

preflight 对这些字段 fail-closed。否则“首夜一页”仍可能选到最难页。

## 2. `required_states` 的断言词汇是否封闭

例如：

```yaml
loading:
  assert: skeleton_visible
```

必须明确 `skeleton_visible` 不是任意字符串，而是受支持的 assertion ID。至少要有：

```yaml
assertion_catalog_version: "1.0"
```

并建立映射：

```text
assertion ID
→ Playwright helper
→ 参数 schema
→ pass/fail 规则
→ evidence type
```

未知 assertion ID 必须在 preflight 或 C4/C5 失败，不能忽略，也不能退化成 Markdown 说明。

建议：

```yaml
required_states:
  loading:
    assertions:
      - id: skeleton_visible
      - id: no_layout_shift_on_resolve
        params:
          max_cls: 0.1
```

目前 `{assert, not, and}` 这种自然语言式字段不利于机器验证，也不利于未来组合。

## 3. `scripts_digest` 的覆盖对象需要规范

`sha256:...` 对“六脚本”求哈希还不够明确。需要定义：

- 六个脚本的确定文件列表；
- 路径排序；
- 原始字节还是拼接内容；
- 是否包括 `carros_base.py`；
- 是否包括 assertion catalog；
- 是否包括 hook 配置；
- 是否包括调用的辅助模块；
- 符号链接如何处理。

否则攻击者不改六个入口脚本，只改它们 import/source 的 helper，就可绕过摘要。

更合理的是生成控制面物料清单：

```yaml
control_plane_lock:
  algorithm: sha256
  entries:
    - path: scripts/finalize-page.sh
      sha256: ...
    - path: scripts/lib/gate-reducer.py
      sha256: ...
    - path: .carros/assertion-catalog.yaml
      sha256: ...
```

摘要必须覆盖**传递依赖**，不能只覆盖入口文件。

## 4. gate result 的事务写入规则

权威链攻击测试里已经提到“写一半”“exit code 与结果文件冲突”，但执行协议必须写死：

1. 结果先写临时文件；
2. 完成 schema 校验；
3. `fsync`；
4. 原子 rename；
5. 记录 gate run ID；
6. 绑定 `manifest_sha256`、`code_sha`、`script_digest`；
7. 同一 gate 多次执行保留历史，只有合法最新结果参与 reducer。

建议最小 envelope：

```yaml
gate_run_id: "uuid"
gate_id: "C4"
status: PASS | FAIL | ERROR | SUPERSEDED
manifest_sha256: "..."
code_sha: "..."
control_plane_digest: "..."
started_at: "..."
finished_at: "..."
process_exit_code: 0
evidence: []
```

缺任意权威字段，reducer 必须 fail-closed。

## 5. `FINALIZED → DELIVERED` 与交付失败状态语义

文档说 GitHub 故障不改变 `DONE`，这是对的。但状态机仍画成：

```text
FINALIZED → DELIVERED
```

如果 `gh pr create` 失败，页面显然没有进入 `DELIVERED`。因此需要明确：

```text
FINALIZED
  ├─ C8b success → DELIVERED
  └─ C8b failure → DELIVERY_FAILED
```

或者将 delivery 从页面验证状态机中彻底正交出去：

```yaml
verification_state: FINALIZED
final_status: DONE

delivery_status:
  NOT_ATTEMPTED | IN_PROGRESS |
  DRAFT_PR_CREATED | DRAFT_PR_FAILED
```

我更推荐后者。这样不会为了 GitHub 故障污染验证状态机。

---

# 五、还有一个文档级矛盾：`v3.1-GA` 与 GA 门尚未满足

文件标题写“最终版 v3.1”，正文状态写：

> 执行规格全部补丁定型

同时又写：

> GA 门：§16 落盘 + smoke 实跑绿证 + §17a 审计 + §18 闭合。

如果这些门尚未实际完成，那么当前版本不能同时被理解为“v3.1-GA”。

建议版本状态明确拆开：

```text
Document/specification version: v3.1-final
Runtime readiness: RC / NO-GO
GA status: pending evidence
```

也就是：

- **文档可以 final**；
- **执行规格可以 frozen**；
- **系统不能叫 GA**；
- **首夜仍取决于落盘证据，而不是文档写完。**

这能避免后续团队把“FINAL.md”误读成“已经允许 `lx-goal on`”。

---

# 六、最终对账结论

## 真正未一致

| 项目 | 当前状态 | 如何闭合 |
|---|---|---|
| S1 首夜是否必须物理权限隔离 | **仍有实质分歧** | 用户明确接受单夜 detective-control 残余风险，或首夜前完成 supervisor 隔离 |
| R5 状态码方案 | 技术上已裁决，缺 Grok 显式签字 | Grok 确认接受 GPT/Opus 正交方案 |
| S1 风险降级 | 已由整合者裁决，缺原提案方显式签字 | 明确“限单页单夜、不可自动续期” |

## 方向一致但实现需钉死

1. O5 简单页选页规则；
2. assertion catalog 封闭词表；
3. scripts digest 的传递覆盖范围；
4. gate result 原子写入与 envelope；
5. delivery status 与 verification state 正交。

## 我的最终签署意见

> **Architecture：Sign-off**  
> **Specification：Accept with one recorded dissent（S1）**  
> **Document：可冻结为 v3.1-final**  
> **Runtime GA：尚未成立**  
> **首夜：只有在 §16、smoke、§17a、§18 全闭合，并由 Owner 显式接受 S1 残余风险后，才是单页 Conditional GO。**

一句话：

> **三家在“系统应该怎么设计”上已经一致；尚未完全一致的是“首夜能否用可发现的防篡改措施代替真正不可篡改的权限隔离”。其余问题不是架构争议，而是必须在脚本和 schema 里写死的执行语义。**