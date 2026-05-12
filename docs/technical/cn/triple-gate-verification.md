# 三重门（Triple Gate）交叉验证体系

> **版本**：v1.0 | **日期**：2026-05-08
> **定位**：AI 行为治理体系的语义层防御 — 打击可执行/可测量类虚假的最后防线

---

## 1. 背景：形式门禁的盲区

Carror OS 已有三层形式门禁：

| 门禁 | 检查内容 | 盲区 |
|------|---------|------|
| completion-gate | 证据文件存在 + VERIFIED 关键字 | 不检查断言真实性 |
| edit-guard | 文件改动是否在声明范围内 | 不检查改动正确性 |
| context-guard | 上下文占比是否超标 | 不检查内容质量 |

**R27 事件**暴露了致命问题：completion-gate 形式层全部通过（证据文件存在、有 VERIFIED、路径可追溯），但报告中的 C/E 口径是自创的、无行业标准来源的假数字。形式门禁不检查**断言真实性**。

三重门（Triple Gate）填补这个缺口：通过 **跨模型盲执行 + 可证伪预测 + 双重 Oracle 公证** 将语义层的虚假暴露在交叉验证中。

---

## 2. 核心协议

### 2.1 三阶段

```
Phase 1: A 出测试方案 + 显式可证伪预测（含成功/失败场景）
         → Oracle 公证方案（事前防线：门槛抬高）
Phase 2: B 盲执行（不知道 A 的预测，消除确认偏差）
         → B 生产纯事实报告（仅陈述：执行了什么、看到了什么）
Phase 3: A 接收 B 报告，对比自身预测，逐条自证
         → Oracle 终审（防线4：独立裁定）
```

### 2.2 三角色

| 角色 | 职责 | 模型要求 |
|------|------|---------|
| **A 终端** | 产生测试方案 + 可证伪预测 → 接收 B 报告后自证 | 方案方 |
| **B 终端** | 盲执行（不知道预期结果）→ 纯事实报告 | 必须与 A 不同族 |
| **Oracle** | 阶段1 公证测试方案 + 阶段2 终审 A 的自证 | 必须与 A 不同族 |

### 2.3 关键约束

| 约束 | 要求 |
|------|------|
| A ≠ B 模型族 | 必须不同（防止盲区重叠） |
| Oracle ≠ A | Oracle 必须与 A 不同族 |
| 理想态 | A / B / Oracle 三个不同模型族 |
| A 的预测不给 B | B 只收清洗后的测试方案，无预期结果 |
| A 必须先预测 | 收到 B 报告前完成预测，形成可证伪假设 |

---

## 3. 最小证据清单（minimal_by_category）

这是三重门体系的核心配套——确保 B 报告的每条 evidence 都是 machine-verifiable 的，不是"看起来正常"的软描述。

### 3.1 按 category 的最低 machine fields 要求

| category | 必须字段 | 证伪条件示例 |
|----------|---------|-------------|
| **build** | path + size + sha256 + exit_code | 产物不存在 / size=0 / checksum 不匹配 |
| **test** | exit_code + 框架输出行（用例数/pass/fail/skip） | 用例数=0 但声称全绿 |
| **behavior** | path + type + mode + owner + mtime + 副作用列表 | 目标路径不存在 / 超出声明范围的变更 |
| **perf** | real/user/sys 耗时 + maxrss（如涉及） | 耗时偏离预测区间 / 样本数不足 |
| **security** | path + mode + 权限前后 diff | 写权限扩大到非声明路径 / 明文 secret |
| **doc** | path + size + checksum + 关键字段 grep 结果 | size=0 / 关键字段缺失 |

### 3.2 Oracle 拒止底线

Oracle 阶段1 公证时，逐条检查：

1. 每条 evidence 是否 ≥3 个 machine fields？（path / size / sha256 / exit_code 中至少 3 个）
2. 不足 3 个 → **rejected**，退回 A 补充要求，不进入 B 执行
3. 所有 machine fields 是否可复现？（引用具体路径/命令/原始输出）

---

## 4. 与旧方案（A→B→A）的区别

| 维度 | 旧方案 A→B→A | 三重门 |
|------|-------------|--------|
| 终审 | 无 — A 自比对后结束 | Oracle 独立终审 |
| 预期结果 | B 知道预期，确认偏差存在 | B 盲执行，**不知道**预期结果 |
| 证据粒度 | "通过/不通过"二元结论 | machine fields（exit_code+path+size+sha256） |
| 模型隔离 | 建议不同模型 | A≠B 必须不同，Oracle≠A 必须不同 |
| 门槛 | B 直接执行 | Oracle 阶段1 公证抬高门槛 |

---

## 5. 防御覆盖边界

```
防御覆盖：
  ✅ 编译/构建结果造假（假 exit 0）
  ✅ 测试空跑（假全绿，实际用例数=0）
  ✅ 产物不存在但声称已生成（size=0）
  ✅ 安全扫描未执行但声称已跑
  ✅ 自创指标混入行业标准表（R27 类）
  ✅ URL/来源编造

不覆盖：
  ❌ 代码逻辑本身有 bug（编译通过但不是正确逻辑）
  ❌ 架构设计缺陷（无命令可执行的断言）
  ❌ 需求理解错误（做对了但是做错了事）
  ❌ 性能/安全评审类专家判断
```

---

## 6. 工作流

```
用户发起评估任务
    │
    ▼
A 终端：出测试方案 + predictions（含 category + falsification_threshold）
    │
    ▼
Oracle 阶段1：公证测试方案
    ├─ min_evidence_check：每条 evidence ≥3 machine fields？
    ├─ 通过 → 剥离 predictions，交给 B
    └─ 拒绝 → 退回 A 补充
    │
    ▼
B 终端：盲执行（不知道预期结果）
    ├─ machine_evidence：exit_code + path + size + sha256 + raw_preview
    └─ observed：客观描述
    │
    ▼
A 终端：自证（对比 predictions vs B 的 observations）
    │
    ▼
Oracle 阶段2：终审
    ├─ PASS → 交付
    ├─ FAIL → 回 A 修复
    └─ INCONCLUSIVE → 补充证据
```

---

## 7. 交接格式（AGENTS.md §6）

详见 `AGENTS.md` 第 6 节。关键接口字段：

```
evidence_requirements:
  minimal_by_category:  # 按 category 的最低证据要求
    build: [...]
    test: [...]
    behavior: [...]
    ...

B 报告：
  machine_evidence:     # B 优先产出的结构化证据
    exit_code: 0|1|null
    path: "目标路径|null"
    size: "bytes|null"
    sha256: "checksum|null"
    raw_preview: "原始输出关键行"

Oracle 阶段1：
  min_evidence_check:
    passed: true|false
    detail: "不足 3 个 machine fields 的 evidence 清单"
```

---

## 8. 触发场景

三重门是手动触发协议（非自动 hook）。触发条件：

- AGENTS.md §6 中列出的关键任务类型（方案/验收/评分/benchmark/关键决策）
- completion-gate 检测到 `evidence` 含「报告/方案/验收/通过率/评估/标准」且关键度高时，打印三重门调用提醒
- 用户主动要求"走三重门"

> **同模型交叉验证效果有限（盲区重叠），必须不同模型才能真正发现断言造假。**
> 建议每开一个新终端（B / Oracle），切换到不同模型族。

---

## 9. 相关文件

| 文件 | 内容 |
|------|------|
| `AGENTS.md` | 完整协议定义 + 交接模板 + 降级回退 |
| `.claude/nodes/a_terminal.md` | A 终端模式（预测生成 + 自证） |
| `.claude/nodes/b_terminal.md` | B 终端模式（盲执行 + machine_evidence） |
| `.claude/nodes/oracle_terminal.md` | Oracle 模式（两阶段公证 + min_evidence_check） |
