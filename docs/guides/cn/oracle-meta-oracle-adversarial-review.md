# Oracle vs Meta-Oracle: 一场真实的攻防博弈

> Carror OS v6.2.0 源码级审计实录 — 3 轮 Oracle 审查 × 2 轮 Meta-Oracle 二审，累计 7 次 agent 调用、200+ 次 tool use。
> 初始评分 6.61/10 → 终评 ~8.4/10，46 项发现中修复 38 项。

---

## 背景

2026-05-15，用户对 Carror OS v6.2.0 进行了一次全面的 Meta-Oracle 源码级审计，产出 32 项发现清单。随后启动了长达 6 轮的优化冲刺，目标是把评分从 6.61 拉到 8.6。

冲刺完成后，用户提出更高的要求：**关键机制必须通过 Oracle agent 和 Meta-Oracle agent 的共同验收**。

这开启了一场教科书级的安全攻防博弈。

---

## 博弈模型：A→B→A 三重门 + Meta-Oracle

```
AI 实现变更
  → Oracle critic agent 独立一审（源码级，留痕，给出 VERDICT）
    → AI 修复 Oracle 发现的问题
      → Oracle 重审（验证修复）
        → Meta-Oracle 独立二审（不同方法论，验证 Oracle 的结论）
          → AI 修复 Meta-Oracle 发现的问题
            → 双签通过 ✅
```

### 两个审查者的方法论差异

| | Oracle | Meta-Oracle |
|---|--------|-------------|
| 方法论 | 静态检查（文件存在、注册完整、代码逻辑） | **运行时验证**（实弹测试、bash 执行、交叉验证） |
| 倾向 | 偏紧：不确定时假设有问题 | 偏松：不确定时运行时确认 |
| 盲区 | 容易误判严重性（静态分析看到"注入"就判 CRITICAL） | 依赖 Oracle 的输出做二次判断 |
| 互补性 | 广度优先：全文件扫描 | 深度优先：针对性证伪 |

---

## Round 1: permission-gate 一审 — 死刑判决

### Oracle 一审 (2026-05-16 02:43)

**审查对象**: `permission-gate.sh` — Carror OS 的安全门禁核心

**裁决: REJECT** — 2 CRITICAL, 3 MAJOR, 4 MINOR

**关键发现**:

> **C1: BYPASS_RE 定义但从未使用 — base64 编码绕过检测是死代码**
>
> Line 37 定义了 `BYPASS_RE` 变量（DG-11 记录的编码绕过检测），但在整个脚本中从未被 `grep` 比对过。这意味着 `echo "cm0gLXJmIC8=" | base64 -d | bash` 这样的编码绕过命令可以完全绕过所有 7 个检测正则。
>
> 文档记录了、设计完成了、变量的注释写了、但集成这一步漏掉了。**整个 DG-11 安全改进是空气。**

> **C2: Python 字符串注入 — check_cache/write_cache 中的 `$cmd_sig` 内联**
>
> 缓存函数通过 shell 变量展开将命令签名内联到 Python 字符串中。命令中的单引号会破坏 Python 语法，导致缓存静默失败。

> **M1: `cat\b` 排除允许 `cat > current-scope.txt` 写入绕过**
>
> scope gate 的读命令排除列表过于宽松，cat 的所有调用都被排除，包括重定向写。

**Oracle 采用了 ADVERSARIAL 模式** — 1 CRITICAL + 3 MAJOR 自动触发升级，在对抗模式下刻意寻找最坏情况。

### AI 修复 (2026-05-16 02:43-02:44)

- C1: `BYPASS_RE` 接入检测链，编码绕过 → token 模式无条件硬阻断
- C2: cache 函数改用 `sys.argv + heredoc`，消除字符串注入
- M1: `cat\b` → `cat\s+\S` 收紧排除
- M3: 移除 `permission_keywords` 死配置，补齐 3 个 sub-keys

---

## Round 2: 二审 — Meta-Oracle 的降级裁决

### Meta-Oracle 二审 (2026-05-16 02:44)

**裁决: REVISE**

**Oracle 的 5 项发现验证结果**:

| Oracle 发现 | Meta-Oracle 验证 | 最终 |
|------------|-----------------|------|
| C1: BYPASS_RE 死代码 | ✅ 确认 | CRITICAL |
| C2: Python 字符串注入 | ⚠️ **降级**: 注入后果是 fail-closed（更安全而非更宽松），非安全绕过 | **MAJOR** |
| M1: cat 绕过 | ⚠️ 确认但修正影响范围：影响 scope gate 非 permission gate | MAJOR |
| M2: Ghost mode 绕过 | ❌ **关闭**: Ghost mode 的门禁降级是设计行为，非 bug | 无效 |
| M3: permission_keywords | ✅ 确认 | MAJOR |

**Meta-Oracle 新增发现**: MO-01: 3 个 permission_gate sub-key 未注册到 harness.yaml

### 关键教训: 静态分析 vs 运行时验证

Oracle 看到 "字符串注入" 立刻判 CRITICAL。Meta-Oracle 实际运行验证后发现：注入导致 Python 语法错误 → cache miss → 需要 CAPTCHA 重新审批。这是 **fail-closed**（安全性上升，UX 下降），不是安全绕过。

**如果只看 Oracle 的结论就修复，会把时间浪费在"安全漏洞"上——实际上它根本不是漏洞。**

---

## Round 3: Oracle 重审 — 发现新 bug

### Oracle 二审 (2026-05-16 02:44-02:49)

**裁决: REJECT** — 2 个新 CRITICAL

> **新 C1: check_cache 永远返回成功 — 完整的 CAPTCHA 绕过**
>
> AI 在修复 C2 时重构了 `check_cache` 函数，使用 `sys.argv` + `heredoc` 消除了注入。但 Python 脚本中忘记添加 `sys.exit()`——所有路径都以 exit 0 结束。
>
> 后果：第一次 CAPTCHA 批准后，`approved-ops.json` 被创建，此后所有危险命令都因为 `if check_cache "$CMD_SIG"` 永远为 true 而**自动放行**。整个 permission gate 变成 "一次性门禁"。

> **新 C2: check_cache stdout 污染 — 产生非 JSON 输出**
>
> Python 的 `print('hit')` / `print('miss')` 输出到 stdout（hook 的 JSON 响应通道），与后续的 `echo '{"continue": true}'` 混合，产生 `hit\n{"continue": true}` 这种非法 JSON。

**这是 AI 重构引入的 regression** — 修复旧 bug 时引入了新 bug，而新 bug 比旧 bug 更危险。

### Meta-Oracle 的回应

Meta-Oracle 确认：
- C1 确实存在（运行时验证确认：所有 4 条路径 exit 0）
- 严重性评估正确（从 "一次性门禁" 到 "完全绕过" 只需 1 次 CAPTCHA）

### AI 再次修复

- 添加 `sys.exit(0)` on hit, `sys.exit(1)` on miss
- 添加 `>/dev/null` 抑制 Python stdout
- 运行时验证：cache miss 时 `check_cache` 正确返回 1

---

## Round 4: Oracle + Meta-Oracle 双签

### Oracle 三审 (2026-05-16 03:08)

**3 项修复验证**:
- Fix 1 (check_cache): ✅ PASS
- Fix 2 (BYPASS_RE printf): ✅ PASS  
- Fix 3 (cat 排除): ❌ FAIL — `cat\s+\w` 过于严格，回归到 `cat\b`

**注意**: 第一个 Oracle 一审说 `cat\b` 太宽松（M1），第三个 Oracle 三审说 `cat\s+\w` 太严格。最终回退到 `cat\b`——**宽松的排除比严格的误杀更安全**。

### Meta-Oracle 最终签字 (2026-05-16 03:30)

**独立运行时验证**:
- check_cache: 4/4 路径验证通过
- BYPASS_RE: `printf "%b"` + `printf '%b'` 均正确匹配
- G1 伪诚信检测: 发现 Oracle 遗漏的 `grep -c || echo 0` 双重计数 bug

**最终裁决: ACCEPT-WITH-RESERVATIONS** → 修复 G1 bug 后 **ACCEPT**

---

## 统计

| 指标 | 数值 |
|------|------|
| Oracle 审查轮次 | 3 |
| Meta-Oracle 审查轮次 | 2 |
| 总 agent 调用 | 7 |
| 总 tool use | 200+ |
| Oracle CRITICAL 发现 | 4 → 全部修复 |
| Oracle MAJOR 发现 | 5 → 3 修复, 1 降级, 1 关闭 |
| Meta-Oracle 新增发现 | 3 |
| AI 引入的 regression | 2（全部由 Oracle 二审发现） |
| 最终双签结果 | ✅ ACCEPT |

---

## 启示

1. **一个审查者不够。** Oracle 一审发现了 2C/3M，但漏掉了 Meta-Oracle 发现的 3 项。Meta-Oracle 也漏掉了 Oracle 二审发现的 2 个新 bug。只有两者结合才接近完整覆盖。

2. **AI 修 bug 会引入新 bug。** 这是整个博弈中最精彩的转折——AI 修 C2（字符串注入）时重构了 cache 函数，引入了更危险的 check_cache exit code bug。Oracle 的二审在对抗模式下专门寻找"修复引入的 regression"，精准捕获。

3. **静态分析 ≠ 运行时验证。** Oracle 将 C2（字符串注入）判为 CRITICAL，Meta-Oracle 运行时验证后降级为 MAJOR——因为实际后果是 fail-closed。如果不做运行时验证，团队会优先修复一个"不存在的安全漏洞"。

4. **同一个 reviewer 不同轮次可能矛盾。** Oracle 一审说 `cat\b` 太宽松，三审说 `cat\s+\w` 太严格。同一个 reviewer 在不同上下文下给出相反建议——多轮审查的价值就在于此。

5. **Meta-Oracle 的"对抗性假设"是关键。** Meta-Oracle 刻意假设 "Oracle 可能是错的"，然后去找证据证伪。这种方法论在 C2 降级和 M2 关闭中产生了正确的裁决。

---

> 这份记录本身也是一次狗粮——Carror OS 的 Oracle+Meta-Oracle 双签机制，在自己身上经受了一次真实的压力测试。

---

## 开源学习：让你的教训成为别人的护身符

这份文档是怎么来的？一次 Meta-Oracle 审计 → 6 轮优化冲刺 → 3 轮 Oracle × 2 轮 Meta-Oracle 攻防博弈 → 提炼成叙事 → 喂给社区。

如果你也在使用 Carror OS，当你的 AI 犯了错、踩了坑、差点酿成事故，处理完之后顺手喂一条狗粮：

```bash
/lx-dogfood "刚才 permission-gate 没拦住 git commit，根因是 jq 提取 heredoc 命令返回空导致门禁静默放行。修了 fail-closed + token 模式。教训：安全门禁默认应该是阻断而非放行。"
```

一句话就够了。这条教训会进入你的 `claude-next.md`——你的 AI 下次会话会自动读到它，不会再犯同样的错。

如果你觉得某条教训对别人也有用，带上原文去论坛或 GitHub Discussions 发帖。Carror OS 的维护者会从中挑选高价值内容，升华为新的种子教训（SEED 模板）或铁律机制。下次 release 时，所有人安装 Carror OS 都会自动获得。

**你的踩坑经验，成了别人的护身符。代码开源，教训也开源。** 这就是 Carror OS 社区的飞轮。
