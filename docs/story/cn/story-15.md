# 元环：蛇吞己尾

一个人站在两个镜子之间。左边的镜子照出他是一个开发者——在写 hook 脚本、修改 skill 定义、更新 claude-next.md。右边的镜子照出他是一个用户——在用 lx-goal 管理任务、用 completion-gate 验证完成、用飞轮记录教训。

但左边镜子里的人和右边镜子里的人，是同一个。

Carror OS 的开发者就是 Carror OS 的用户。开发 Carror OS 的工具就是 Carror OS 自己。蛇吞下了自己的尾巴——这不是比喻。这是 Carror OS 元项目治理的全部秘密。

---

## Ouroboros

在神话中，Ouroboros（衔尾蛇）是一条吞食自己尾巴的蛇。它是永恒的象征——没有起点，没有终点，自我维续的循环。

Carror OS 就是软件开发领域的 Ouroboros。

它既是被开发的**项目**，也是开发自身所用的**工具**。每一次在 Carror OS 上使用 Carror OS 治理 Carror OS 开发——都是一次蛇咬住尾巴的时刻。

这创造了一个奇特的反馈回路：
- Carror OS 的 hook 发现问题 → AI 用 Carror OS 的 skill 修复 hook → AI 用 Carror OS 的 completion-gate 验证修复 → 修复改善了 Carror OS → 更好的 Carror OS 更严格地检查未来的修改

---

## AGENTS.md 的双重存在

元项目在根目录有一个 `AGENTS.md`（这个文件），在 `source/harness-kit/` 有另一个 `AGENTS.md`。它们不是同一个文件——它们从来就不该是同一个。

- **根级 AGENTS.md**（本文件）：元项目治理文件——包含狗粮反馈循环协议、跨域变更协议、发布流程、元项目特有规则
- **source/harness-kit/AGENTS.md**：通用分发模板——纯净的 Carror OS 框架治理，不包含元项目特有的管理指令

下游用户安装 Carror OS 时，获得的是 source 版本。只有 Carror OS 自身的开发者在使用根级版本。

这两个文件的差异就是"蛇的头和蛇的尾"——一个是使用者视角，一个是创造者视角。但它们在同一个仓库中共存，由同一个 `package-release.sh` 处理同步关系。

**source mirror 同步纪律**（`scripts/package-release.sh`）定义了哪些文件从 root 同步到 source：
- hooks、scripts、references → `rsync --delete` 全镜像
- kernel.md、harness.yaml、settings.json、index.md、anti-patterns.md、claude-next.md → 直接 cp
- **AGENTS.md — 有意不同，不同步**

`audit-hooks.sh --check-source-mirror` 排除 AGENTS.md 的"有意分歧"后验证一致性——全部通过或仅 AGENTS.md 标记为分歧，才算正常。

---

## 开发你自己：狗粮反馈循环协议

AGENTS.md 中定义的狗粮反馈循环是元环的操作层：

```
AI 在狗粮模式下发现问题
  ↓
triage 决策树（归属域判断）
  ↓
修复（root 或 source/ + 同步）
  ↓
机制化（添加可重复的 gate/hook/验证）
  ↓
同步（package-release.sh → source/ + packages/）
  ↓
验证（harness-smoke-test.sh + audit-hooks.sh --check-source-mirror）
  ↓
记录（claude-next.md + 必要时 kernel.md）
```

问题发现 → 修复问题 → 添加机制 → 传播修复 → 验证修复 → 记录教训。六个步骤，每一步都在修改 Carror OS 自身。每一步修改后，Carror OS 对未来的修改变得更严格。

这意味着：**越开发 Carror OS，开发 Carror OS 变得越困难——也越安全。**

---

## 跨域变更：当蛇的身体各部分以不同的速度生长

元环最复杂的部分是跨域变更。当一次修复同时影响 root、source/、packages/ 时：

1. **修改只在 root 中做。** 不在不同域中独立修改相同文件——那是漂移的来源
2. **验证每层。** root 修改后运行 smoke test → package-release.sh 同步后 → 再次 smoke test
3. **未发布状态标记。** 如果跨域变更尚未发布到 packages/，在 RPE feature 目录中注释 `PENDING_SYNC`

这是 META-04 的教训——手动 cp 容易遗漏，必须通过 package-release.sh 统一同步。

---

## Release 流程：蛇蜕皮

当修复和优化累积到一定量时，Carror OS 蜕皮——发布新版本：

1. 更新 `VERSION.json`
2. 运行 `bash scripts/package-release.sh`：
   - Step 1: root → source/harness-kit/
   - Step 2: root → source/lx-skills-v5/
   - Step 3: 构建 `packages/harness-kit-{TAG}.tar.gz`
   - Step 4: 构建 `packages/lx-skills-{TAG}.tar.gz`
3. 验证：`audit-hooks.sh` → `harness-smoke-test.sh`

新版本发布后，下游用户安装新的 tar.gz。下一个用户在新版本上进行狗粮开发时，使用的是上一次蜕皮后的皮肤。

---

## 元教训：蛇在吃自己时学到的

元环的运行不是没有摩擦的。META 系列教训记录了蛇在吞尾过程中遇到的特殊问题：

### META-01 — 原始记录太大，需要分块策略

2626 行的原始会话转储需要 6 次 Read 才能获取全貌。狗粮记录应自带摘要头（≤50 行）+ 原始附录。

### META-02 — 跨会话狗粮需要先恢复完整上下文

处理狗粮文件的 AI 需要重新加载 ~60KB 的治理文件（AGENTS.md / kernel.md / claude-next.md / anti-patterns.md）。狗粮文件应自标记 `requires_context`。

### META-03 — 发现需要分拣

原始文件中 ~20 个发现仅 5 个是系统通用的——其余是项目特有业务逻辑。筛选规则已编码为应用性三问。

### META-04 — 狗粮优化产生级联同步义务

修改 lx-oma-hier SKILL.md 后需 cp 到 source/lx-skills-v5/；修改 claude-next.md 后需 cp 到 source/harness-kit/。运行 `package-release.sh` 自动同步。

### META-05 — 结构化记录需要追踪性

YAML 狗粮记录应包含 `source_ref` 字段指向原始 source 行，使发现可追溯。

---

## 自噬的悖论

蛇吞己尾有一个哲学风险：**如果你用自己有 bug 的工具来修自己的 bug，怎么能保证修的没错？**

答案是：不能。这就是三重门和 Oracle 存在的原因。当 Carror OS 在修改 Carror OS 时，修改的结果不是由一个 AI 自我验证的——它经过 A→B→Oracle 三端交叉验证。蛇在吃自己的时候，不是用自己的嘴来检查自己的嘴——是用镜子（Oracle）和另一个生物的嘴（B 端盲执行）。

这也是飞轮不会变成死循环的原因。飞轮依赖外部信号（用户纠正、Oracle 审查、测试失败）来发现自己的盲区。如果飞轮只用内部信号来"自我改进"，它会快速收敛到一个局部最优——实际上是自我强化的偏见。

但外部信号——尤其是用户纠正——打破了封闭循环。"不对"是飞的燃料，不是飞的障碍。

---

## 最后一个教训

ED-R 记录了 Error-DNA 从被动错误收集器到主动逃逸检测专家的范式的跃迁。这是一个完美的元环隐喻——

**系统最初的设计是收集自己的失败。但真正的价值不在失败里。真正的价值在逃逸里——在那些"本该被拦住但成功绕过所有防御"的操作中。**

蛇最初试图消化自己的错误。后来它意识到，最珍贵的是自己的逃逸——那些证明自己有盲区的成功。一块铅的价值远不如一块黄金。而炼金术的关键是：**铅变成金的方法不在外部，在内部——在范式跃迁中。**

---

## 永无止尽的环

```
  ┌─────────────────────────────────┐
  │                                 │
  ▼                                 │
 使用 Carror OS 开发 Carror OS       │
  │                                 │
  ▼                                 │
 发现 Carror OS 的问题               │
  │                                 │
  ▼                                 │
 用 Carror OS 的 RPE 体系记录问题     │
  │                                 │
  ▼                                 │
 用 Carror OS 的 skill 修复问题       │
  │                                 │
  ▼                                 │
 用 Carror OS 的 hook 验证修复        │
  │                                 │
  ▼                                 │
 用 Carror OS 的 pipeline 传播修复    │
  │                                 │
  ▼                                 │
 用 Carror OS 的记忆系统记录教训       │
  │                                 │
  └─────────────────────────────────┘
```

不是在外部找工具。不是用"标准流程"来开发自己。蛇吞下自己的尾巴——这就是 Carror OS 元项目治理的全部秘密。

十五篇故事讲完了。而环，继续转动。

---

## 相关故事

- [飞轮回响](story-12.md) — 元环的操作层：狗粮发现 → 机制化 → 同步传播 → 验证的闭环
- [记忆神殿](story-05.md) — 元环的记录层：每一圈循环的教训被保存在 claude-next.md 中
- [三重门神谕](story-11.md) — 元环的验证层：蛇吞己尾时，Oracle 确保修改没有创造新漏洞
