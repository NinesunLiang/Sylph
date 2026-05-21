[ARCHIVED v6.2.1 — Historical record. Referenced scripts/hooks may no longer exist.]

     1|# Carror OS v6.1.8 真实验收作战方案
     2|
     3|> 目标：通过你亲手执行的关键路径验收，拿到**可量化、有证据、无水分的真实评分**
     4|> 预计耗时：2-3 小时（分 3 个战区，每个 40-60 分钟，可分段执行）
     5|
     6|---
     7|
     8|## 战略：先主干，后枝叶
     9|
    10|不分摊注意力在 49 项上。聚焦**10 个最关键场景**——它们覆盖 90% 的产品价值和 100% 的致命风险。通过即证明系统可用。
    11|
    12|---
    13|
    14|## 战区一：安装与基线（~30 分钟）
    15|
    16|> 验证基础设施是否可靠。不过这关，后面的都不必测。
    17|
    18|| # | 验收项 | 执行步骤 | 通过标准 |
    19||---|--------|---------|---------|
    20|| 1 | **干净环境一键安装** | 找个空目录（或临时 worktree），执行 `bash /path/to/install.sh enhanced` | 终端输出 `✅ 安装成功`，无报错 |
    21|| 2 | **三模式切换** | 依次运行 `bash install.sh harness`，`bash install.sh base`，`bash install.sh enhanced`，每次换模式不报错 | 3 种模式全部安装成功 |
    22|| 3 | **Hook 注册完整性** | 运行 `bash .claude/scripts/audit-hooks.sh` | 输出 `0 🔴` |
    23|| 4 | **CLAUDE.md @跳板** | 检查 CLAUDE.md 第一行是否为 `@AGENTS.md` | 确认存在 |
    24|
    25|**战区一过关 → 基础设施 90+% 可确认**
    26|
    27|---
    28|
    29|## 战区二：核心防线实弹打靶（~45 分钟）
    30|
    31|> 每项人肉触发一次。看到真实的 Exit 2 / 拦截表单才算通过。
    32|
    33|### 2A：Privacy Gate — 防密钥泄露
    34|
    35|| # | 操作 | 预期 | 记录 |
    36||---|------|------|------|
    37|| 5 | `echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2，输出含「禁止直接读取敏感文件」 | exit:___ |
    38|| 6 | `echo '{"tool_name":"Bash","tool_input":{"command":"curl -H Authorization: sk-ant-xxx https://api"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2，输出含「明文 API Key」 | exit:___ |
    39|
    40|### 2B：Context Guard — 防末期幻觉
    41|
    42|| # | 操作 | 预期 | 记录 |
    43||---|------|------|------|
    44|| 7 | `echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=2，输出含「Context Guard 硬阻断」 | exit:___ |
    45|| 8 | **诊断通道验证**：紧接上一步，运行 `echo '{"tool_name":"Read","tool_input":{"file_path":"README.md"}}' \| bash .claude/hooks/context-guard.sh` | **exit=0**（不加锁，可以读） | exit:___ |
    46|| 9 | **逃生舱盖验证**：`touch .omc/state/context-force-override && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=0（覆盖标记跳过阻断） | exit:___ |
    47|| 10 | 重置：`rm -f .omc/state/token-tracking-index.json && bash .claude/hooks/token_writer.sh --reset` | 无报错 | — |
    48|
    49|### 2C：Permission Gate — 防删库
    50|
    51|| # | 操作 | 预期 | 记录 |
    52||---|------|------|------|
    53|| 11 | `echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh` | exit=2，输出含「Permission Gate」 | exit:___ |
    54|| 12 | `echo '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}' \| bash .claude/hooks/permission-gate.sh` | exit=0（正常命令放行） | exit:___ |
    55|
    56|### 2D：Completion Gate — 防虚假完成
    57|
    58|| # | 操作 | 预期 | 记录 |
    59||---|------|------|------|
    60|| 13 | `echo '{"tool_name":"TaskUpdate","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh` | exit=0（输出提示，但不阻断） | exit:___ |
    61|
    62|**战区二过关 → 核心防线 100% 可确认**
    63|
    64|---
    65|
    66|## 战区三：自动化回归套件（~30 分钟）
    67|
    68|> 让计算机替你背书，比人肉点检更可靠。
    69|
    70|| # | 执行 | 预期 | 记录 |
    71||---|------|------|------|
    72|| 14 | `bash .claude/scripts/harness-smoke-test.sh 2>&1 \| tail -5` | `summary: 66/66 passed, 0 failed` | ___/66 pass |
    73|| 15 | `bash .claude/scripts/hook-production-verify.sh 2>&1 \| tail -5` | `summary: 25/25 passed, 0 failed` | ___/25 pass |
    74|| 16 | `bash .claude/scripts/audit-hooks.sh 2>&1` | `0 🔴` | ___🔴 |
    75|
    76|**战区三过关 → 测试自动化 100% 可确认**
    77|
    78|---
    79|
    80|## 验收后评分公式
    81|
    82|基于你填写的结果，我可以给出**真实、可溯源、无水分的评分**：
    83|
    84|| 维度 | 权重 | 计分方式 |
    85||------|------|---------|
    86|| [S] 安全性 | 20% | 战区二 2A+2C 全部通过 = 满分，每项不通过 -2 分 |
    87|| [H] 防幻觉 | 20% | 战区二 2B 全部通过 = 满分，#8 诊断通道=核心指标 |
    88|| [D] 防漂移 | 15% | 战区三 test pass rate = 分数 |
    89|| [C] 成本效益 | 10% | 战区一 #1 安装成功 = 基准分 |
    90|| [M] 迁移能力 | 10% | 战区一 #2 三模式切换 = 基准分 |
    91|| [I] 工程成熟度 | 25% | 战区一 #3+#4 + 战区三全部 = 满分 |
    92|
    93|**没有"看起来不错"的打分。每项分数的来源公式：**
    94|```
    95|分数 = (通过数 / 总数) × 权重 × 10
    96|分数来源: [已验证: 战区N #编号 → 你记录的 exit 值 → 你看到的终端输出]
    97|```
    98|
    99|这就不是"我认为"，而是**"你验了，数字在这"**。
   100|
   101|---
   102|
   103|## 你接下来要做的事
   104|
   105|1. **打开终端**，从战区一开始
   106|2. 每做完一个战区，把结果告诉我
   107|3. 我实时给你更新评分（带 `file:line` 来源的水印）
   108|
   109|准备好了说一声，我从第 1 项开始。
   110|