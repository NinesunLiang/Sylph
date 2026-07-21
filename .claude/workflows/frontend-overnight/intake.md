# intake — 输入接收与成熟度判定

输入允许分期到达。intake 的产物是 `.omc/night/{date}/night-manifest.yaml` 的 `inputs` 块与每页 `api_contract_status`。

## 1. 成熟度矩阵

| prototype | prd | api_doc | 本期范围 | api_contract_status | 强制动作 |
|---|---|---|---|---|---|
| present | present | present | 全量（UI+交互+业务逻辑） | `real` | — |
| present | present | pending/absent | UI+交互+推断业务逻辑 | `inferred` | assumptions.yaml 逐条登记推断契约 |
| present | absent | * | UI+交互；AC 来自原型+intake 问答 | `inferred`/`none` | AC 推断也入 assumptions.yaml |
| absent | * | * | **不开发** | — | C0 NO-GO（BLOCKED_INPUT） |

规则：
- **prototype 是唯一硬输入**。它是 UI 还原的事实源；没有它，任何"先写业务逻辑"都是凭空捏造。
- `pending` = 你明确说"文档在路上"（本期按 inferred 开发，文档到后 reconcile）；`absent` = 本期不考虑。
- PRD 缺席时，intake 必须向你问清：页面目标、主流程、七态中哪些适用、浮层清单（静态原型时这是浮层唯一来源，FINAL §7.1 R2）。

## 2. intake 操作步骤

1. 输入放入 `inputs/{产品名}/`，核对 `prototype.kind`（interactive/static/mixed——决定浮层发现策略，填错 = 夜跑误判）
2. 复制模板：`cp scripts/carroros-gates/templates/night-manifest.template.yaml .omc/night/{date}/night-manifest.yaml`
3. 填充：`inputs.*.status` 按上表；`pages[0]` 选**输入最全+复杂度最低**的真页（O5）；`api_contract_status` 按上表
4. PRD/API 缺席 → 在 `.omc/night/{date}/assumptions.yaml` 预登记推断契约骨架（夜跑模型只可补充、不可删除）
5. 进 `phase0-checklist.md`

## 3. API 文档滞后到达 → reconcile 流程

文档到了之后（任意白天）：

1. 更新 `inputs/{产品名}/api.md`，intake 重判：`api_doc.status: present`
2. **对照检查**：真实契约 vs assumptions.yaml 里的推断契约，逐条标 `confirmed | conflict`
3. `conflict` 条目 → 生成一个 reconcile 夜任务（改 api 层 + 受影响断言），排进下一夜 manifest 的 pages[]（占当夜页位）
4. `confirmed` 条目 → 仅把页面 `api_contract_status` 翻为 `real`（下次该页有任何变更时生效）
5. manifest 任何变动 → 重跑 `gen_control_plane_lock.py --write` → **重新签署**（signoff 哈希失效）

## 4. BLOCKED_INPUT 规则（夜跑时）

夜跑中发现以下情况，模型**不许自行裁决**，记 BLOCKED_INPUT 后按 J0 继续或停页：
- PRD 与原型冲突（以原型为视觉事实源，冲突点登记）
- 推断契约与原型行为明显矛盾
- 静态原型浮层信息不足且 intake 未登记（FINAL §7.1 R2）
- API 文档标记 present 但文件缺失/不可解析
