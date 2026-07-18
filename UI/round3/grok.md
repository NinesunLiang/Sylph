**Grok-4.5 审核意见（第三轮独立审计）**

与 GPT / Opus 的共识很大，**但我不签“架构已 Sign-off”**。  
我的结论更硬：

> **v2.0-rc1：架构 Conditional Accept，执行物件 No-Go，首夜默认 No-Go。**  
> 仅当控制面荣誉条件全部满足时，才给 **1 页 / 串行 / Patch A / K3=0 / Draft PR only** 的 Conditional GO。

---

## 0. 和另外两家哪里不一样

| 议题 | GPT | Opus | **我（Grok）** |
|---|---|---|---|
| 总体定级 | 架构 Sign-off，脚本 No-Go | 同左，并加 E11/E12 | **架构只给 Conditional Accept**。骨架可用，但“串行页隔离 / 失败开闸 / 控制面先于产量”还没硬到可签 |
| 首夜页数 | 建议先 1 页 | 建议先 1 页 | **硬规则：首夜永远 1 页**。不是建议。第 2、3 页要等早晨控制面 8 问全绿后再签 |
| 脚本质量路线 | 推结构化 / AST / digest | 同左 + 禁写 src | **首夜优先 fail-closed 粗门，而不是半吊子聪明门**。宁可少判一点 PASS，也不能解析失败还 exit 0 |
| 最大危险 | machine_summary 可伪造、SHA 自引用 | 晨报蒸发崩溃页、假证据 | **系统能在“控制面全绿”的假象下交出假产量**。E10/E11/P0-4 是同一类病：撒谎型通过 |
| J0 | 基本够用 | 已到理论极限 | **还不够**。缺“页间污染 / 工作区中毒后是否允许继续下一页”的硬裁决 |
| 接受 L0 可选 | 同意 | 同意 | 同意，但 **Draft PR only ≠ 控制面已证明**。没有故意失败的 smoke，就没有 GO |
| 修完就能跑 3 页？ | 偏谨慎开放 | 偏谨慎开放 | **否**。修完只够 1 页试毒 |

我与两家最关键的分歧只有一句：

> 他们在修“会不会炸”。  
> 我在审“炸了会不会还看起来像成功，以及成功了会不会腐蚀第二天”。

---

## 1. 全面接受的部分（不再争）

以下与 GPT / Opus 对齐，直接收编进我的 Go 条件：

1. **P0-1**：废除 Markdown 内嵌 machine_summary；结论文件必须独立且结构化。  
2. **P0-2**：证据绑 `code_sha`，禁止“binding_sha == HEAD”的自引用。  
3. **P0-3**：删掉 `DONE_WITH_ASSUMPTIONS` 作为顶级状态；硬 AC / 七态缺失只能 `BLOCKED`。  
4. **P0-4**：模型不得书写终局结论；`final_status/ac_*` 只能由门禁脚本聚合生成。  
5. **E11**：晨报必须按 manifest `pages[]` 遍历；缺 summary 只能是 `CRASHED/NOT_STARTED`，不可消失。  
6. **E12**：取证前清 artifacts；截图名绑定 `code_sha`。  
7. **spec 选址**：保留 `tests/e2e/`，不进 `src/**`。  
8. **签署**：`human_signoff` 必须绑定 `manifest_digest`。  
9. **单一契约**：`night-manifest.yaml` 作为唯一 desired state；运行态不得回写。

这些不是我的新增贡献，是底线。

---

## 2. 我多抓的 6 个不一样风险（G1–G6）

### G1. 最大风险不是“脚本报错”，是“失败开闸（fail-open）”

GPT/Opus 修的是逻辑反了、字段对不上、哈希绕圈。  
我要求额外做一个**失败开闸审计**，每个脚本必须证明：

| 场景 | 必须结果 |
|---|---|
| manifest 解析失败 | FAIL，不能当“无违规” |
| 允许列表为空 | FAIL |
| git 命令失败 | FAIL |
| 证据目录不可读 | FAIL |
| YAML 缺字段 | FAIL |
| 应检查 0 个文件却声称 PASS | FAIL |

首夜最怕的不是 `c7-check` 误伤 `1px`，而是：

```bash
# 伪码：解析失败后 items=0，循环不执行，最后 echo PASS
```

**任意门禁在输入腐烂时还能 PASS，这比漏写一个正则致命一个数量级。**

验收标准：

```bash
./scripts/*-check.sh --smoke-fail-open
# 以上场景必须非 0；preflight 不通过则禁止 lx-goal on
```

### G2. 串行 ≠ 页间隔离；J0 缺“工作区中毒”出口

Kimi 认为首夜串行就够安全。不够。

真实夜间风险：

- 第 1 页改坏了 `tsconfig`、eslint cache、playwright 快照目录、本地 mock 数据；
- 或者留下未清理的 node 进程 / port 占用 / 半成品 untracked；
- 第 2 页在毒化基线上“绿”。

所以要新增硬规则：

```text
PAGE_BOUNDARY_RESET（每页开始前）
1. 工作树相对 page baseline 干净
2. 仅允许当前页 files_allowed 出现 diff
3. 测试产物目录重置
4. 失败页执行 quarantine：
   - 恢复到 page_start_sha
   - 或把毒化文件移出并标记 BLOCKED_ENV/FAILED
5. 未完成 reset，禁止进入下一页
```

若 reset 本身失败：

- 不是“跳过本页继续”；
- 而是 **`NIGHT_FUSE: WORKSPACE_POISONED`**，整晚停。

这是我对 J0 的补刀：  
**不是所有阻塞都能“记一笔然后继续下页”。工作区一旦可能污染后页，就必须整晚熔断。**

### G3. shared 腐蚀熔断还只是 YAML，不是门

我的 v1.1 补丁里有：

```yaml
shared_gap_policy:
  max_local_workarounds_per_gap: 2
  on_exceed: BLOCKED_SCOPE
```

现在的 rc1 仍停留在登记层。  
首夜若不做 shared 修改，不代表没有：

- 页面内复制公共组件；
- 同构 hack 连写 3 页；
- “先绕开，早上再统一”变成三套分支实现。

要求：

1. `shared-gap-registry.yaml` 必须机器读写；  
2. 新增同指纹 workaround 前先查计数；  
3. 超过阈值直接 `BLOCKED_SCOPE`，不能再局部绕开；  
4. 晨报单独一节“公共面腐蚀候选”，按 gap_id 聚合，不要散落在 assumptions 里。

否则第一周最常见的结果不是写不出来，而是：

> 每页都能 Draft PR，shared 被绕成三份。

### G4. 视觉门 N/A 不能算过；工具失败不得变相 PASS

K3 关闭我同意。  
但 chrome-devtools / Playwright 视觉链路一旦 flaky，系统很容易写成：

```text
C6: N/A (tool unavailable)
final_status: DONE
```

这是假完成的温床。

硬规则：

- 首夜所需视觉子集（溢出 / 三视口截图 / 关键区块可见性）任一项因工具失败没做成：最多 `BLOCKED_ENV` 或 `FAILED`，**绝不能 DONE**；
- `N/A` 只允许给“本页声明不适用”的 AC，不允许给“工具没跑成”的 AC；
- 环境失败连续 2 次：夜级熔断，而不是带着环境疤痕继续刷页。

### G5. Draft PR 只对 `final_status=DONE` 创建

GPT 拆了 `delivery_status`，正确。  
我再收紧一层：

| final_status | 是否建 Draft PR |
|---|---|
| DONE | 可以 |
| BLOCKED | 默认不建；最多建 `draft/blocked-...` 并且标题强制 `[BLOCKED]`，且 CI 说明“不可审功能” |
| FAILED / CRASHED | 不建 PR，只留 branch + 现场包 |

首夜更严：

**只允许 DONE 建 Draft PR。**  
BLOCKED/FAILED 一律不建 PR，避免早晨评审队列被半成品污染，也避免“有 PR ≈ 差不多做完”的组织幻觉。

### G6. 控制面通过率是首夜唯一主指标，产量不是

这是我和两家语气差异最大的地方。

早晨顺序必须锁死：

1. 门禁是否会故意失败？  
2. 晨报是否漏页？  
3. 是否出现无证据 DONE？  
4. 是否出现越界/untracked 漏检？  
5. 是否出现同指纹死循环？  
6. 崩溃是否可恢复？  
7. **以上全绿后，才准看页面还原度。**

如果控制面挂了，即使页面“看起来好看”，首夜也算失败。  
**Autopilot 的第一晚交的是控制系统，不是业务页面。**

---

## 3. 对 Kimi 两处裁决的再审

### 3.1 L0 可选 —— 接受，但不接受“可直接 3 页真跑”

Draft PR only 可以代替影子周。  
可代替的是“写码链路验证”，代替不了“控制面抗撒谎验证”。

因此：

- L0 可选；  
- 但 **rc2 后的首夜 = 1 页试毒夜**，不是 3 页交付夜。

### 3.2 单一契约 —— 接受，并加不可变约束

manifest 单一 source of truth 是对的。  
补两条：

1. Phase 0 签署后 manifest **只读**；  
2. 任何运行态回写 manifest → 直接 `FAILED_INVARIANT`。

运行只能写：

```text
token.json
executor.jsonl
gate-results.json
machine-summary.yaml
artifacts/**
```

---

## 4. 对 Opus E1 方案的裁决

我明确站 GPT + Opus 后者立场：

- **拒绝** `src/pages/**/__e2e__`  
- **接受** `tests/e2e/**` + 结构化路径许可

原因不是品味，是风险：

把测试塞进生产源码树，是用长期架构债务换短期正则省事。  
这违背我一贯的 B 保守原则：**范围门应该变聪明，代码布局不该为烂脚本让路。**

---

## 5. 我和 Opus 的细差异

Opus 的 E11/E12 我全收。  
但对 P0-2 我比他更强调**操作顺序**：

```text
code freeze
  → 记录 code_sha
  → 清 artifacts
  → 跑行为/视觉
  → 生成 machine-summary（脚本）
  → evidence commit（可选）
  → Draft PR
```

并且：

- `VISUAL_VERIFIED` 后禁写 `src/`：接受；  
- 但 **`STATIC_VERIFIED` 之后若再改 src，必须自动作废所有行为/视觉证据**，不能靠人记。

一句话：  
Opus 防的是“截图假文件”；  
我防的是“证据时间线被后续步骤改写后仍显示通过”。

---

## 6. 首夜 Go / No-Go（Grok 版）

### 仍然 No-Go 的状态

当前 rc1，只要下面任一条成立，就 **No-Go**：

1. 结论字段仍可能由模型填写；  
2. 晨报仍以磁盘目录而非 pages[] 为源；  
3. 门禁存在解析失败却 PASS 的路径；  
4. 页间无 baseline reset / poison fuse；  
5. 视觉工具失败可被记成 N/A 并通过；  
6. `required_states` 缺失仍可能进入 DONE 家族；  
7. 未修 E1–E10 + P0-1~P0-4 + E11/E12；  
8. 想首夜直接跑 >1 页。

### Conditional GO 的最小集

只在同时满足时给 Semi-GO：

1. 五脚本 + morning-report 完成  
   **正向 / 反向 / 篡改 / 崩溃 / fail-open** 五类 smoke；  
2. `machine-summary.yaml` 100% 门禁生成；  
3. 证据使用 `code_sha`，取证前清场；  
4. 晨报按 pages[] 全量现身；  
5. manifest 签收绑 digest；  
6. 页边界 reset + 工作区中毒整晚熔断已落地；  
7. shared-gap 计数熔断已是可执行门，不只是文档；  
8. 三 Owner 具名：Design System / 门禁脚本 / 早晨控制面审查；  
9. **任务清单只有 1 个页面**；  
10. 全局：无自动合并、无真实后端、无 B3、K3=0、Patch A、Draft PR only。

---

## 7. 我对第三轮的直接裁决

### 接受

- 单一 `night-manifest.yaml`  
- L0 可选  
- C3 在 C4 前  
- 不做首夜全量 sha256  
- 关闭 K3  
- Draft PR only  
- 集中式 e2e

### 拒绝

- “架构已完美/已 Sign-off”这种表述  
- 首夜 ≤3 页真跑  
- Markdown 真相源  
- DONE 家族膨胀  
- 测试搬进 `src/`  
- 视觉 N/A 当通过  
- 失败页污染后继续连跑  
- 有 PR 就当昨夜成功

### 新增必须进 rc2 的条目

1. **fail-open 冒烟**  
2. **page boundary reset + night poison fuse**  
3. **shared-gap 可执行熔断**  
4. **工具失败 ≠ N/A PASS**  
5. **仅 DONE 建 Draft PR**  
6. **首夜固定 1 页**

---

## 8. 一句话差异总结

GPT 靠工程正确性把 rc1 从“能写”打回“能验”。  
Opus 靠作者视角补了晨报撒谎和假截图。  
**我靠无人值守保守主义再收一层：

不是问“模型能不能做完页”，  
而是问“当它做不完、做一半、做坏工作区、工具挂掉、自己给自己填 DONE 时，系统会不会仍然微笑着交付”。**

在那套微笑被扑灭之前，Grok 的票是：

**No-Go。**  
修完控制面后：

**Only 1-page Conditional GO。**