# GPT 终审裁决：CarrorOS 二期优化 R5

> 终审对象：`final-review.md` 及其证据日志  
> 审查口径：**验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少**  
> 结论：**R5 有效但未达到既定终验门槛；不接受 8.51 作为正式收口，裁决开启受限 R6。**

## 一、四项提分裁决

| 项目 | 申请调整 | GPT 裁决 | 结论 |
|---|---:|---|---|
| C3 | 8 → 9 | 接受 | 成立 |
| C7 | 8 → 9 | 接受 | 成立 |
| C9 | 8 → 9 | 接受 | 成立 |
| E6 | 8 → 9 | 接受 | 成立 |

### 裁决理由

四项提分均有施工事实、回归日志和机械验收支撑，不只是文档自评：

- PKG-A 三层对抗测试达到 `20/20 PASS, rc=0`，覆盖 U11、C3、E6；证据为 `final-review.md:§4`、`pkg-a-20x20.log`。
- PKG-A 验收 A-A1 至 A-A5 全绿；证据为 `final-review.md:§4`、`pkg-a-acceptance.log`。
- PKG-B 验收 A-B2 至 A-B12 全绿；证据为 `final-review.md:§4`、`pkg-b-acceptance.log`。
- PKG-C 验收覆盖单测、实时触发、幂等、fail-closed、互斥和 scope guard，并输出 `ALL_PKG_C_ACCEPTANCE_PASSED`；证据为 `final-review.md:§4`、`pkg-c-acceptance.log`。
- R4 验收 A-R4-1 至 A-R4-8 全部通过；证据为 `final-review.md:§4`、`r4-acceptance.log`。
- launcher 的 fail-open、fail-closed 和返回值透传测试达到 `3/3 PASS`；证据为 `final-review.md:§4`、`launcher.log`。
- E6 的提分包含双源脚本清零、六处验证漂移修复、registry 与运行时真相源分离、handoff 转为 JSON SSOT 并检测 `md_vs_json_mismatch`，不是单纯改文案；证据为 `final-review.md:§3 E6`。
- 证据包提供从基线到终验 HEAD 的提交记录、哈希漂移归因及 SHA256 清单；证据为 `final-review.md:§8`、`commits-since-baseline.txt`、`hash-drift-r5.json`、`SHA256SUMS`。

### 限定

该接受仅确认这四项达到 **9 分口径**，不等于整个项目通过终验。单项提分与总门禁必须分开裁决，不能用局部成功覆盖剩余 7 分项。

**裁决：四项提分全部成立。**

---

## 二、E7 hint-only 终态裁决

### 裁决：不接受作为终态

接受它作为 **R5 临时安全态**，但不接受它作为 CarrorOS 的正式终态。

`final-review.md:§3 E7` 已明确：

- E7 当前仍为 7 分；
- FORCE 关键词从 `aut` 修成 `auth` 只完成了误报面的局部修复；
- Oracle 仍是 hint-only；
- BLOCK 化因 `git --author` 中包含 `auth` 可能误伤而被主动推迟。

这说明现状不是“hint-only 已被证明是正确终态”，而是“BLOCK 化尚未满足误锁安全前件”。两者不能混同。

CarrorOS 的核心承诺是 hooks 机械强制。对于只提示、不阻断的高风险命中：

1. AI 可以忽略提示继续执行；
2. 提示不能形成强制状态转换；
3. 提示不能证明危险动作已停止；
4. 因而不满足“零信任”和“守护”。

但是，不能把现有宽泛关键词直接改成 BLOCK。`auth` 对 `git --author` 的子串误伤已经是明确反例；在误报面未机械消除前直接 BLOCK，也违反“守护”和“人本”。

### R6 必须采用的终态

E7 应收敛为：

```text
结构化危险动作匹配 → BLOCK
模糊自然语言关键词 → hint + audit
普通安全命令 → PASS
```

也就是说，**接受 hint-only 作为模糊检测层的终态，不接受整个 E7 门禁维持 hint-only**。

R6 必须先建立精确命令分类：

- 按命令及参数位置识别危险动作；
- 不得使用裸子串 `auth` 作为 BLOCK 条件；
- `git --author` 必须有负向对抗测试；
- 命中真实不可逆动作时必须 BLOCK 或进入人类独占裁决；
- 解析失败必须采用不执行危险动作的 fail-closed 状态；
- 测试必须同时证明低误报和低漏报。

**裁决：E7 维持 7 分，开启 R6；hint-only 不接受为整体终态。**

---

## 三、内置安全 7 分豁免裁决

### 裁决：不豁免，维持 7 分

`final-review.md:§0.3` 与 `§7` 已确认：

- 明文 `sk-` token 存在于 Git 历史；
- secret-scan 门已经落地；
- token 吊销和轮换已正确登记为 `blocked_human`；
- 实际吊销与换新仍未完成。

secret-scan 解决的是“防止再次提交”，不能追溯性证明已泄露凭证失效。只要历史中的 token 是否仍有效没有机械证据，风险就仍然存在。

“轮换只能由人工完成”是正确的权限边界，但不是评分豁免理由。CarrorOS 明确坚持人类独占不可逆裁决；因此：

- AI 不应自行轮换密钥；
- 系统应准确阻断并交给人；
- 但在人完成之前，安全项仍应反映未闭环风险。

### 提分所需机械证据

内置安全从 7 提至 8，至少必须同时具备：

1. 人类在 Moonshot 控制台吊销旧 token；
2. 新 token 不写入受版本控制文件；
3. 仓库当前树 secret scan 为零；
4. Git 历史扫描明确列出旧 secret 指纹；
5. 提供旧 token 已失效的验证回执，回执不得包含完整 token；
6. hook 对新增同类 secret 的对抗测试为 PASS；
7. `.gitignore` 与配置加载路径证明凭证只来自非跟踪存储或环境变量。

不得为了提高分数由 AI 调用旧 token 测试其有效性；这可能扩大秘密暴露。失效证据应来自人类控制台的吊销回执或脱敏 API 状态回执。

**裁决：内置安全不豁免，维持 7 分，继续保持 `blocked_human`。**

---

## 四、8.51 收口或开启 R6

### 裁决：不接受正式收口，开启受限 R6

既定终验门槛是：

```text
24 项全部 ≥ 8.0
加权总分 ≥ 8.6
```

当前状态是：

```text
E7 = 7
内置安全 = 7
加权总分 = 8.51
```

两项门禁均未达到。根据 `final-review.md:§0.4` 的算术：

```text
两项 7 → 8：
1903 / 2220 = 8.57
```

即使把两个 7 分项都修到 8，仍低于 8.60；还必须有至少一项真实的 `8 → 9` 提升，才能达到约 8.61。

因此，直接接受 8.51 收口会产生三个问题：

1. 把预先定义的门槛改成事后协商；
2. 奖励“接近门槛”而不是“满足门槛”；
3. 与 CarrorOS 的 `computed, not negotiated` 原则直接冲突。

### 状态定义

R5 可以标记为：

```text
R5_IMPLEMENTATION_ACCEPTED
FINAL_GATE_NOT_MET
R6_REQUIRED
```

不得标记为：

```text
FINAL_ACCEPTED
DONE
CLOSED
```

### R6 范围锁定

R6 只能包含三项，不得借机扩大工程范围：

1. **E7：7 → 8**
   - 精确危险命令分类；
   - 高置信危险动作 BLOCK；
   - 模糊关键词保留 hint + audit；
   - `git --author` 等误报对抗测试；
   - 机械验收通过。

2. **内置安全：7 → 8**
   - 人类吊销并轮换旧 token；
   - 补充脱敏吊销回执；
   - 当前树和历史 secret scan 对账；
   - 新凭证不落 Git。

3. **再选择一个当前 8 分项真实提升至 9**
   - 必须是已有机制的闭环、复活或删除；
   - 不得新增一层机制刷分；
   - 必须有代码行为变化和机械回归证据；
   - 不能只改文档、评分表或测试期望。

第三项由整合器从现有 8 分项中按“最小施工面积且最高验证收益”机械选定；选定后冻结，不得施工中换项。

---

# 最终签署意见

```yaml
reviewer: gpt-5.6-sol
decision:
  score_increases:
    C3_8_to_9: ACCEPT
    C7_8_to_9: ACCEPT
    C9_8_to_9: ACCEPT
    E6_8_to_9: ACCEPT

  E7_hint_only_as_final_state: REJECT
  E7_hint_only_as_temporary_state: ACCEPT
  E7_score: 7
  E7_r6_required: true

  builtin_security_exception: REJECT
  builtin_security_score: 7
  token_rotation_blocked_human: VALID

  close_at_8_51: REJECT
  open_r6: REQUIRED

final_status: R5_IMPLEMENTATION_ACCEPTED_FINAL_GATE_NOT_MET
```

## 一句话终裁

**四项提分成立；E7 不接受整体 hint-only 终态；内置安全不予豁免；8.51 不得收口，必须开启范围锁定的 R6，完成“两项 7→8 + 一项 8→9”后再终验。**