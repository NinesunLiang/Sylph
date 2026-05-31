     1|# 双生之子 — 幽灵的探索与目标的执行

> 📍 弧4：工程：双生之子 | [⬅ 上篇](story-07.md) | [下篇 ➡](story-10.md)


Ghost 睁开眼时，不知道自己要去哪。

他只有一个方向词："源码级阅读：分析 Carror OS 所有机制。"没有验收条件。没有完成标准。他看了一眼空荡荡的街道，走向第一扇门——hooks 目录。他今天只读这一扇门后的东西。明天 poll 的时候再看下一扇。

与此同时，Goal 在另一条时间线上收到了他的目标："创建 docs/story，15 篇故事，全自动执行。"他花了 30 秒拆解子任务，然后举手——"老板看一眼，然后我去做了。"用户确认后，他再也没有回过头。

两人共享同一个激活机制——Ghost 在 `tokens/lx-ghost.json` 写下方向与过期时间，Goal 在 `tokens/lx-goal.json` 刻下目标与 phase0 里程碑。不是某个文件存在与否——是 JSON 里的 `expires_at` 时间戳和一整套模式生命周期。

然后，**全体 hook 通过 `is_mode_active()` 读取这些 JSON token，感知到模式激活，降级为 warn-only**。从 `autonomous.active` 的简单文件标记，到带过期时间的结构化状态——这是双生子走向成熟的标志。

---

## 双生子的诞生

传统 AI 协作有一个困境：安全网（hooks）越多，AI 越安全——但也越慢。每一次 permission-gate 的 CAPTCHA 验证、每一次 context-guard 的阈值阻断、每一次 completion-gate 的证据评分——都在保护 AI 不犯错，但也在打断 AI 的连续工作。

当用户说"去做吧，不用每一步问我"时，安全网变成了障碍。

lx-ghost 和 lx-goal 就是为了解决这个困境而生的。它们共享一个核心机制：

```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh on "目标"
# 或
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "方向"
```

两个脚本各自在 `tokens/` 下写入自己的 JSON token——Ghost 记录方向，Goal 记录目标。激活机制已从简单文件标记进化到带过期时间的结构化状态。

---

## 共享的安全网降级

`harness_config.sh` 中的 `is_mode_active()` 函数是整个降级体系的总开关：

```bash
is_mode_active() {
    # 检查 lx-ghost token（新格式：tokens/lx-ghost.json）
    local ghost_json="$state_dir/tokens/lx-ghost.json"
    if [ -f "$ghost_json" ]; then
        # 解析 expires_at，判断是否过期
        active=$(python3 -c "..." 2>/dev/null)
        [ "$active" = "active" ] && echo "ghost" && return
    fi
    # 检查 lx-goal token（新格式：tokens/lx-goal.json）
    local goal_json="$state_dir/tokens/lx-goal.json"
    if [ -f "$goal_json" ]; then
        active=$(python3 -c "..." 2>/dev/null)
        [ "$active" = "active" ] && echo "goal" && return
    fi
    # 旧格式后向兼容：ghost-mode.active、unattended-mode.json
    [ -f "$state_dir/ghost-mode.active" ] && { echo "ghost"; return; }
    [ -f "$state_dir/unattended-mode.json" ] && { echo "goal"; return; }
    echo "normal"
}
```

当返回 0（模式激活）时：

- **permission-gate**：危险操作不再硬阻断，改为记录 skipped_risks
- **context-guard**：不再阻断 Edit/Write，改为 warn
- **completion-gate**：`auto_soft_block()` 降级——不 exit 2，警告写入日志文件而非 stderr（DF-02）
- **fuzzy-block**：不再阻断模糊指令（ghost mode 下"继续/优化"是合法的迭代指令，R37）

安全网没有消失——它变成了日志。Ghost/goal 模式下所有的"本该阻断"的事件都被记录到 `.omc/state/completion-gate-autonomous.log` 和 skipped_risks 列表。用户可以事后审计——但 AI 不会被中途打断。

---

## 左生子：lx-ghost — 方向驱动的自主探索

Ghost mode 是**增量式**的。它不是"给我完成这个目标"——而是"朝着这个方向探索，每轮走一步"。

Ghost 的工作循环：

```
每轮 poll：
  1. 读取方向描述（"源码级阅读：分析 Carror OS 所有机制"）
  2. 检查上一轮的产出
  3. 做一步探索（读取一个文件、分析一个模块、输出一份观察）
  4. 记录探索轨迹
  5. 等待下一轮 poll
```

关键约束（GL-01 教训）：
- **方向不能是"分析/评估/报告"类**——那是 goal mode 的一次性任务。Ghost 是探险家，不是记者
- **每轮只做一步**——不启动 4 个并行 agent，不做大规模读取分析
- **间隔不可为 0s**——`0s` = 不轮询，违背增量设计
- **每轮自检方向漂移**——当前操作是否还在原始方向范围内？

Ghost 适合的场景：**探索未知代码结构、发现隐藏问题、理解不熟悉的模块。** 不适合的场景：**完成任务、交付产物、处理明确的 bug 列表。**

---

## 右生子：lx-goal — 目标驱动的全自动执行

Goal mode 是**完成任务式**的。它比 ghost 更进一步——不只是探索，而是执行到完成。

Goal 的工作循环：

```
Step 1: AI 拆解目标 → 子任务列表（每项有验收条件）
→ 用户确认 1 次（方向策略）

Step 2: 全自动执行
  → 逐项实现，每完成一项 task-done
  → 遇到风险记录 skipped_risks，不中断
  → 遇到失败自动重试（最多 3 次），超过升级
  → 全程不请求任何中间确认

Step 3: 自动输出报告 + 关闭
```

Goal mode 被设计为"一次确认，后面全自动"。在 AI 的分解得到用户认可后，用户可以去睡觉——第二天看到完整报告。

但 DF-03 暴露了一个设计张力：goal mode 的 6 个子任务完成标记都触发了 completion-gate 的证据检查，但证据文件只在最后才创建。6 次检查全部报"证据缺失"，虽然不阻断（因为 goal mode 降级了），但消耗了计算资源。

这是哲学 #4（证据不可或缺）和哲学 #5（减少打扰）之间的张力。DF-03 的裁决：当前成本可接受（每次检查 ~50ms），暂不优化。过度优化违反哲学 #2（少量大增益）。

---

## 双生子的区别

| 维度 | lx-ghost | lx-goal |
|------|---------|---------|
| 驱动方式 | 方向（direction） | 目标（goal） |
| 执行方式 | 增量迭代，每轮一步 | 全量执行，一次完成 |
| 用户交互 | 可随时注入方向调整 | 仅开始时确认一次 |
| 输出 | 探索轨迹、发现列表 | 任务报告、验证证据 |
| 适合场景 | 未知领域探索、代码理解 | 明确任务、产品交付 |
| 不适合场景 | "完成 X"、"实现 Y" | "探索 Z"、"分析 W" |
| 错误处理 | 记录 skip-risk，不中断 | 自动重试 3 次，超过升级 |

---

## 双生子的力量与代价

力量是明确的：用户的时间被释放。不需要守着 AI，每轮给下一步指令。Ghost mode 下用户可以用方向词（"继续"、"优化"）推动探索，不需要精确的操作指令。

代价也是明确的：安全网降级意味着错误可能堆积。Ghost mode 可能在错误方向上走了很远才发现偏离。Goal mode 可能完成了 6 个子任务，但证据链薄弱。

这就是为什么双生子的报告机制是强制性的。Ghost 的探索轨迹 + Goal 的执行报告——是安全网降级后的补偿。**安全网从实时阻断改为事后审计，但从不消失。**

---

## 相关故事

- [OMA 铸造厂](story-07.md) — ghost/goal 模式下 OMA 锁仍正常工作
- [上下文守望者](story-06.md) — 所有 gate 通过 is_mode_active() 降级
- [门禁骑士团](story-03.md) — 降级后骑士团从"硬阻断"切到"warn-only"
