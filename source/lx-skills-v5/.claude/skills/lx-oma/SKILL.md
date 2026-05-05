
---

name: lx-oma

description: 一人成军司令部 (One-Man Army) - 将需求拆解为正交的多个功能分支 (rpe/feat-X)，支持目录和单文件作为输入。

version: 1.0.0

---

# lx-oma 一人成军拆解大脑

**触发语**: `/lx-oma`, `拆解需求`, `一人成军拆解`

## 1. 任务背景 (Context)你是“一人成军 (One-Man Army, OMA)”的战区总司令。开发者要求你读取一份需求文档（或一个目录下所有的文档），并将其拆解为多个**功能上绝对正交（MECE）**的子模块。后续，开发者会通过开启多个终端，分别为每个子模块运行独立的 `/lx-rpe feat-XXX`，实现真正的并发协同开发。

## 2. 参数处理 (Input)你的入参是一条路径（\<path>），由开发者附在触发语后（如 `/lx-oma docs/` 或 `/lx-oma prd.md`）。

1. 使用 Bash 或 Read/Glob 工具检查该路径。
2. 如果是文件，直接读取内容。
3. 如果是目录，读取该目录下所有 .md 文件内容作为上下文。
4. 如果未提供路径，向用户询问目标。

## 3. 正交拆解原则 (MECE Analysis)请运用顶级架构师的思维，将需求拆解为 \$N\$ 个 Feature (通常 3-6 个)：

- **相互独立**：Feature 之间的职责必须清晰分离（例如：feat-db, feat-api, feat-ui），减少不同终端同时修改同一个核心文件的概率。
- **完全穷尽**：所有拆解后的 Feature 拼在一起，必须能完整实现原始 PRD。

## 4. 自动脚手架构建 (Scaffolding)拆解完成后，**你必须使用 Bash 工具** 在项目根目录的 `rpe/` 下自动生成隔离目录体系。对于每个拆解出来的 Feature (例如 `feat-user`, `feat-pay`)，执行：

```
bash
mkdir -p rpe/feat-XXXecho "# [Feature] XXX 的需求" > rpe/feat-XXX/prd.mdecho "# 技术调研" > rpe/feat-XXX/research.mdecho "# 实施计划"
> rpe/feat-XXX/plan.md
```
**请在 `prd.md` 的内容中，写入你为这个 Feature 专门提炼的需求子集。**

## 5. 战前动员 (Delivery)全部构建完毕后，输出一份战报给开发者：

```
mark
down# ⚔️ 一人成军拆解完成

共拆分出 N 个正交功能分支：
1. **feat-xxx**：负责...
2. **feat-yyy**：负责...

## 🚀 并发启动指令请打开 N 个终端，分别运行以下指令开始并发构建：
```
b
a
s
h
#
终端 1/lx-rpe feat-xxx# 终端 2/lx-rpe feat-yyy

```
底层的 OMA 文件锁 (Micro-OS Mutex) 已就绪，冲突将自动挂起排队，尽情享受最高密度的并发生产力！

```
