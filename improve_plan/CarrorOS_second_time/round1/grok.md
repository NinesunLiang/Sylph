**PKG-C 就位。**  
依据评分靶心，本包只吃 **生命周期 / handoff** 账本，不越界碰 verify 链（PKG-A）与验证契约统一（PKG-B）。

---

## 0. 评分 → PKG-C 责任映射（只动本包）

| 评分洞 | 证据浓缩 | PKG-C 处置方向 | 哲学环 |
|--------|----------|----------------|--------|
| C5 / E8 / 抗衰减 | 抗 compact 是旗舰却 **无 PreCompact hook**；compact-write 静默失败 | **新 hook 或复活僵尸**：PreCompact 强制落盘 + 失败不可静默 | 验证 > 零信任 > 守护 |
| C2 / E8 | handoff 计数失真 `0/0` vs 实际 `0/3`；读侧门禁全死 | **计数对账**：单一真相源 + 写/读对称 + 失真阻断 | 验证 > 零信任 |
| E6 / UX | **三份 handoff**；registry 宣传 20+ vs 实际 6 hook | 生命周期域内：**接线或删除**，消灭多源，不做新叠层 | 零信任 > 少 |
| goal / ghost（包定义） | goal 与 ghost 可并存未互斥 | **互斥态机**：磁盘状态机械裁决 | 验证 > 守护 |
| C5 | SessionEnd / SubagentStop 缺失或不完整 | 补全生命周期闭合：资源/计数/handoff flush | 守护 > 验证 |
| C7（边缘） | 幽灵 skill 仅当涉及 lifecycle handoff 路由时才进本包 | **只清 handoff 路径上的幽灵引用**；编排全量归档归 Kimi/他包 | 少；不新增机制 |

**明确不进 PKG-C（防交差）**  
- `verify_gate` / `cmd_verify` / `_check_verified` / 假完成 E3 → **PKG-A**  
- 6 处重复验证、`oracle_gate` 孤儿、R6/pipeline/.sh → **PKG-B**  
- 明文 token、VERSION、双源脚本全库、anti-patterns 垃圾 → 由整合器另开包，本包不碰

---

## 1. 本包目标不变式（草案，待文件证实后冻结）

产出方案前，不变式预锁定为：

1. **磁盘唯一真相源**：session 生命周期态（goal | ghost | idle）、handoff 计数、compact 快照路径 **仅一处可写、处处只读同一路径**。  
2. **PreCompact 不可静默失败**：hook 失败 exit ≠ 0 或证据未写入 → 上层须感知（fail-closed 于 lifecycle 域）。  
3. **计数对账**：`written == claimed == readable`；失真 → 非 0 exit（机械，不许 WARN-only 完结）。  
4. **goal ⊕ ghost**：同一 session 任意时刻至多一个为 active；并存 = 非法态，hook/门禁拒绝。  
5. **闭环**：SessionEnd / SubagentStop 必须 flush handoff + 计数落盘 + 互斥态复位为可审计终态。  
6. **僵尸二选一**：已登记未接线的 lifecycle hook → **接线** 或 **从 registry/文档删除**，禁止登记幽灵。

哲学自检：全部服务 **验证 > 零信任 > 守护**；与更高环冲突的「增益/少」优化自动作废。

---

## 2. 施工零设计空间前 **必须补充的材料**

没有下列内容，方案只能停在诊断层，**不能**写精确 diff（约束 2、5）。请按块粘贴或给仓库可读路径/归档。

### 块 A · Hooks 注册与现网实现（生命周期）
1. hooks 注册表全文（如 `.claude/settings.json` / `hooks.json` / CarrorOS registry）——含「宣传的 20+ 特性」原文  
2. 实际在跑的 hook 脚本目录列表 + 每个入口文件头 ~80 行  
3. 任何 `*compact*` / `*PreCompact*` / `*SessionEnd*` / `*SubagentStop*` / `*handoff*` 文件（含 `.bak`、归档、注释掉的注册）

### 块 B · Handoff 多源与计数
4. 所有 handoff 写入点（三份 handoff 各自路径 + 写入函数）  
5. 计数读写：谁写 `0/0`、谁读、schema（JSON 字段名）  
6. 一次真实失败样例：磁盘上 `0/0` 与「实际 0/3」的两次 `cat`/`jq` 输出

### 块 C · goal / ghost 状态
7. goal、ghost 状态文件路径与 schema  
8. 创建/切换/清除 goal、ghost 的 skill 或脚本  
9. 是否已有互斥检查（有则贴代码；无则明确说「无」）

### 块 D · 启动/结束链路
10. launcher / session 启动脚本（尤其 fail-open 点）  
11. compact-write 失败静默的代码位置（函数名 + 文件）  
12. Subagent 启停若存在：入口与 stop 回调

### 块 E · 边界与整合器约束
13. PKG-A / PKG-B 是否已占文件列表（Kimi 若有 merged 文件集白名单请贴）  
14. 仓库根相对路径约定与测试入口（`pytest` / `test-*.py` / hook harness）

**最低可开工子集**（先给这些即可出 v0.1 精确方案）：  
**A1+A2+A3 + B4+B5 + C7+C8**。其余后续补丁迭代。

---

## 3. 收到材料后我将交付的形态（六段式，PKG-C only）

```
① 目标与不变式          ← 冻结上表 + 哲学环声明
② 文件清单              ← path → edit|new|delete → 精确 diff / 全文（文件集零交叉）
③ 精确命令序列          ← 无「视情况」
④ 逐条机械验收          ← cmd + 期望 exit/stdout（含 hook 触发 + jq 比对）
⑤ 回滚命令
⑥ 禁止事项              ← 施工者不可即兴边界
```

预期改造骨架（**待证据确认后再定 diff，不提前编造路径**）：

| 优先级 | 动作 | 僵尸策略 |
|--------|------|----------|
| P0 | PreCompact hook：强落盘 handoff/goal 快照；失败非 0 | 无则 **new**；有 `.bak` 则 **接线或删除** |
| P0 | handoff 计数单一真相源 + 对账门禁 | 三源 → 一源，其余 delete 或改只读 redirect |
| P1 | goal ⊕ ghost 互斥（写路径 + Session 钩子） | 复活已有检查，否则最小新检查挂现有 hook |
| P1 | SessionEnd / SubagentStop flush + 终态 | 无则 new；登记与实现对齐 |
| P2 | registry 生命周期条目与真实 hook **对齐**（删虚增或接线） | 二选一，完成登记账 |
| P2 | compact-write 去静默（lifecycle 相关分支） | 修现有，不新层 |

验收锚（包定义硬性）：

- hook 触发测试 exit 0  
- `jq` 比对：计数、goal/ghost 互斥、PreCompact 产物 hash/字段  
- `git apply --check` 干净  
- **无**「人工确认」唯一验收

---

## 4. 给整合器 Kimi K3 的边界声明

- **PKG-C 文件集候选域**（材料到齐后最终收敛）：  
  `hooks/*compact*`、`hooks/*session*`、`hooks/*subagent*`、`hooks/*handoff*`、  
  lifecycle registry 片段、goal/ghost state 路径、计数 schema 单源文件。  
- **绝不进入**：`verify_gate*`、`oracle_gate*`、`cmd_verify*`、验证规则模板主力（A/B 包）。  
- 若与 A/B 冲突：按哲学链 **验证 > 零信任 > 守护** 申诉，由 Kimi 裁决。

---

## 5. 请你现在做的事

**按「块 A → B → C」顺序贴文件**（可分多条消息）。  
每条消息标注：`块X-文件名` + 完整内容或 `path + 关键函数全文`。

收到 **最低可开工子集** 后，我下一响应直接出 **PKG-C v0.1 六段式方案**（精确 diff，面向 DeepSeek-V4-Flash 零设计空间），并抄送边界给与 opus / gpt-5.6Sol 对齐。

**材料越原样越好**——不要摘要；评分已够诊断，现在要的是 **文件:行号** 级真相源。