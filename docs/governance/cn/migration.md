# 数据资产转移与无损升级指南 (Safe Migration Guide)

> **版本**：v6.1.9 | **日期**：2026-05-13
> **核心原则**：升级系统（Update OS）绝对不能抹除用户的数据资产（User Data & Configurations）。
在 Carror OS 中，我们将所有文件严格划分为 **系统态 (System State)** 与 **用户态 (User Assets)**。了解这些边界，将帮助你在跨机器迁移或跨版本热更时，永远保持项目知识与进度的安全。
---
## 1. 资产分类与保护策略
| 资产类型 | 存放位置 | 包含内容 | 升级/迁移策略 |
| :--- | :--- | :--- | :--- |
| **系统核心** (Kernel) | `.claude/hooks/*.sh` / `.opencode/plugins/` | 32 个底层物理拦截器、探针脚本。 | **无情覆盖** (随新版本热更，保证防线最新) |
| **应用技能** (Userland) | `.claude/skills/lx-*/` / `.claude/nodes/` | 24 款流水线技能、Python 确定性脚本、按需加载的 References。 | **无情覆盖** (随新版本热更，保证能力最新) |
| **系统配置** (OS Config) | `.claude/harness.yaml` | 自定义的 80% 熔断阈值、开启/关闭的 Hook 开关。 | **必须保护** (安装脚本会自动备份并还原) |
| **项目记忆** (Memory) | `.claude/claude-next.md` / `.claude/anti-patterns.md` | 大模型踩坑后总结的血泪教训、项目专属反模式。 | **必须保护** (安装脚本会自动备份并还原) |
| **运行时状态** (Runtime) | `.omc/state/` | 错误突变基因库、任务队列、**致命的 DLP 隐私脱敏 Vault**。 | **天然隔离** (安装包完全不触碰) |
| **大特性工作流** (RPE State) | `rpe/{feature_name}/state/` | 大型特性的 `progress.md` 进度快照、`evidence/` 测试铁证。 | **天然隔离** (同上) |
---
## 2. 跨版本一键热更新 (In-Place Upgrade)
当你需要从旧版本的 Carror OS 升级到最新版时，**你无需手动备份任何数据**。
只需要在项目根目录运行最新的云端安装指令：
```bash
curl
 -fsSL <https://raw.githubusercontent.com/your-username/carror-os/main/install.sh> | bash -s -- enhanced
```
**安装脚本的自我修养 (Self-Preservation)**：1. 脚本会检测到当前目录已存在 `.claude/`。2. 在解压前，脚本会将你的 `.claude/harness.yaml`, `.claude/claude-next.md`, `.claude/anti-patterns.md` 复制到安全的内存沙箱（系统临时目录）中。3. 执行 `tar -xzf` 暴力覆盖所有的内核钩子和技能脚本。4. 解压完毕后，脚本将从沙箱中取出你的**原厂配置与记忆资产**，精确还原至 `.claude/` 目录。5. （可选）如果你之前使用的是旧版缺少字段的 `harness.yaml`，系统将提示你手动比对。
---
## 3. 高阶：跨项目大模型智慧克隆 (Cross-Project Intelligence Cloning)
这是一个极具价值的实战场景：**你在项目 A 中积累了几个月的大模型“调教经验”，现在你开启了项目 B（可能是类似的技术栈），你希望让 AI 带着项目 A 的“智慧”和“防坑指南”直接进入项目 B，作为天然的背景知识。**
这就叫作 **跨项目智慧克隆 (Intelligence Transfer)**。
### ✅ 必须搬走的“智慧资产”（记忆与架构经）：请将项目 A 中的以下文件，直接复制到项目 B 的 `.claude/` 目录下：1. **`.claude/claude-next.md` (项目教训记录)**：这是 AI 在项目 A 中通过 `/lx-pre-commit` 失败、被纠正后总结出来的结构化知识。包含着诸如“我们团队喜欢用 `logrus` 而不是标准 `log`”等隐性知识。2. **`.claude/anti-patterns.md` (反模式黑名单)**：这是项目 A 总结出的绝对不能碰的代码写法雷区。> **工程意义**：这相当于直接给 B 项目的大模型注入了 A 项目踩过几百个坑后的老兵经验。它在 B 项目第一次执行代码编写时，就会展现出惊人的老练和前置避坑能力。
### ⚙️ 可以搬走的“防线配置”（习惯预设）：3. **`.claude/harness.yaml` (系统配置)**：如果你在项目 A 中特调了 80% 物理熔断的阈值，或者精心配置了哪些 30 种 Hooks 你要开启/关闭，那么将它搬过去，B 项目将立刻继承你习惯的防护强度。
### ❌ 绝对不要搬走的“运行时垃圾”（会导致严重幻觉）：**永远不要直接把 A 项目的整个 `.claude` 或 `.omc` 文件夹拷贝过去！**请绝对不要复制以下文件，它们带有强烈的 A 项目特定代码路径和变量名的“运行时痕迹”，带到 B 项目只会让大模型产生严重的上下文错乱和幻觉：1. **`.omc/state/error-dna.json`**：这是 A 项目具体的报错堆栈和修复命令，里面全都是 A 项目特有的文件名。2. **`.omc/state/todo-queue.md`**：任务队列，完全不属于 B 项目。3. **`.omc/state/skill-trace.jsonl` 和 `read-tracker.txt`**：执行路径画像和文件读取历史，搬走没有意义。
### ☢️ 极度危险：DLP 隐私脱敏金库：4. **`.omc/state/varlock.json`**：这是你通过 `varlock.py set` 存入的本地明文密码与占位符映射表。**除非项目 A 和 B 共享着同一套测试数据库的密码和一模一样的外部 API Key**，否则绝对不要拷贝脱敏金库！一旦拷贝，不仅可能污染 B 项目的网络请求，甚至带来安全越权风险。
