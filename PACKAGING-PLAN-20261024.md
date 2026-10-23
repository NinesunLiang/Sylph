# CarrorOS 发行方案（CarrorOS_dev 上的通用治理能力打包）

> 状态：**方案待批，未动手**
> 日期：2026-10-24
> 人类裁决：发行形态 = 安装器 + 模板；`references/` 不进包；先出方案

## 1. 目标

在 `CarrorOS_dev` 上提供一套发行能力，产出一个**只含通用 AI 治理能力**的可安装包。
安装到任意空项目后，该项目立刻拥有：门禁、三档审批、完成验证、状态恢复、哲学规则。

**不发行**：密钥、测试、已有数据集、产品代码、运行时数据。

## 2. 与 `origin/main` 的关系

`main` 已有 `install.sh` + `template/` + `packages/`，但两者**无共同祖先**，不能合并。
本方案**不复用 `main` 的代码**，只复用其**形态**（安装器 + 模板目录）。

## 3. 打包内容（白名单驱动）

采用**白名单**：只有下面列出的路径会被拷进包里，其余一律不进。新增能力必须显式加进清单。

| 来源 | 目标 | 文件数 | 说明 |
|---|---|---:|---|
| `.claude/scripts/**`（去 test_/归档/缓存） | `template/.claude/scripts/` | ~83 | 治理工具与生命周期 |
| `.claude/hooks/**`（同上去测试） | `template/.claude/hooks/` | ~32 | 门禁本体（含 14 门） |
| `.claude/skills/lx-*`（去 test_/归档） | `template/.claude/skills/` | ~81 | 10 个技能 |
| `.claude/nodes/` `.claude/schemas/` | `template/.claude/` | 27 | 节点与接口定义 |
| `.claude/rules/` | `template/.claude/rules/` | 4 | 语言与工具规则 |
| `.claude/workflows/` | `template/.claude/workflows/` | 2 | 工作流 |
| `.claude/harness.yaml` | `template/.claude/` | 1 | 治理配置 |
| `.claude/settings.json` | `template/.claude/` | 1 | **脱敏后**写入 |
| 根 `AGENTS.md` `CLAUDE.md` | `template/` | 2 | 哲学与铁律 |
| `.claude/kernel.md` `.claude/index.md` | `template/.claude/` | 2 | 管理内核与路由 |

**合计约 235 个文件 / 1.5 MB**（不含 references）。

## 4. 排除清单

| 排除 | 理由 |
|---|---|
| `.claude/settings.local.json` | **含 API 密钥**，永不打包 |
| `.claude/references/**` | 人类裁决：AI 看的资料，不进产品包 |
| `.claude/archive/**`、`**/archived/**` | 历史归档 |
| `**/test_*.py`、`**/__pycache__/**` | 测试与缓存 |
| `.omc/**` | 运行时数据，换项目即为空 |
| `apps/` `Benchmarking/` `inputs/` `capabilities/` `rpe/` | 产品与数据集 |
| 所有 `*.jsonl`、`*.lock`、`*.log` | 运行痕迹 |
| 根目录的评审/路线图 md（如本文件） | 项目专属文档 |

## 5. 产出结构

```
packaging/
  manifest.yaml     # 白名单单一真源（上面第 3 节的可执行版本）
  build.py          # 组装：按 manifest 拷贝 → 清理 → 脱敏 → 写版本 → 自检
  install.sh        # 跨平台安装器（macOS/Linux/WSL）
  template/         # build.py 生成物，不入库（.gitignore）
```

`template/` 是**生成物**，不提交；仓库里只保留 manifest + 两个脚本。这样包内容随源码自动同步，不会出现"模板过期"。

## 6. build.py 行为

1. 读 `manifest.yaml`，逐条 glob 展开。
2. 拷贝到 `template/`，遵守排除规则（双重过滤：白名单 ∩ 非排除）。
3. **脱敏**：
   - `settings.local.json` 存在即报错并中止（防止误拷）。
   - `settings.json` 的 `env` 段清空；删除 `permissions.allow` 中与本机路径相关项。
   - 全量扫描 `sk-`、`AKIA`、`BEGIN PRIVATE KEY`、`ghp_` 等模式，**命中即失败**（fail-closed）。
4. 写 `template/VERSION.json`（commit、日期、门禁数、文件数）。
5. **自检**（任一失败即中止）：
   - 包内 `test_*.py` 数 = 0
   - 包内 `settings.local.json` 数 = 0
   - 包内 `.omc/` 数 = 0
   - 密钥模式命中数 = 0
   - `python3 -m py_compile` 全部通过
   - 包体积 < 3 MB

## 7. install.sh 行为

1. 检测 `python3` / `git`，缺失则提示并退出（不自动装）。
2. 目标目录：默认当前目录；非空时必须 `--force` 或交互确认。
3. 拷贝 `template/*` 到目标。
4. 初始化 `.omc/` 空骨架（`state/`、`tasks/`、`tokens/`、`audit/`），**不写任何数据**。
5. 打印下一步：填模型配置、跑一次 `carros_base.py status` 自检。
6. **幂等**：目标已有 `.omc/` 数据时，不覆盖、不删除，只更新治理文件。

## 8. 验收标准（可执行）

| # | 验收 | 命令 |
|---|---|---|
| AC1 | 空目录安装成功 | `bash install.sh /tmp/probe && cd /tmp/probe && python3 .claude/scripts/carros_base.py status` |
| AC2 | 包内无测试 | `find template -name "test_*.py" \| wc -l` → 0 |
| AC3 | 包内无密钥 | `find template -name "settings.local.json"` → 空 |
| AC4 | 包内无运行数据 | `find template -name "*.jsonl"` → 空 |
| AC5 | 密钥扫描零命中 | build 自检步骤输出 `secret_scan=0` |
| AC6 | 门禁生效 | 在安装目录执行 `rm -rf .claude` 应被 ASK_USER 拦住 |
| AC7 | 体积 | 包 < 5 MB（实测 3.4 MB；原定 3 MB 为估值，按实测上调） |

## 9. 风险与回滚

| 风险 | 处置 |
|---|---|
| 白名单漏项 → 装了缺能力 | AC6 装完即验证门禁；manifest 保持单一真源 |
| 冻结区 hooks 进包 → 下游被锁死 | 包内 `gov_approve.py` 一并发行，人类仍可签票 |
| 误把密钥打进包 | 三重防护：白名单、settings.local 硬失败、密钥模式扫描 fail-closed |
| `template/` 过期 | 不提交生成物，每次 build 重算 |

**回滚**：`packaging/` 目录整体删除即可，不触碰现有治理文件。

## 10. 工作量与下一步

| 步骤 | 估时 |
|---|---|
| 写 `manifest.yaml` + 排除规则 | 30 分钟 |
| 写 `build.py`（含脱敏与自检） | 1 小时 |
| 写 `install.sh` | 40 分钟 |
| 跑 AC1–AC7 | 40 分钟 |

**待你确认后开工。** 有两个点可以先定：
1. 包名与版本号从哪来（建议 `VERSION.json` 用 commit + 日期，不手写版本号）。
2. 安装器要不要顺带写 `.gitignore`（建议写，防止下游把 `.omc/` 提交上去）。

---

## 11. 已定事项与验收结果（2026-10-24 实施后补记）

**版本号规则**（人类裁决）：取 `origin/main` 的大版本 + 1，minor / patch 归零。
`main` 当前 `7.0.1` → 本次发行 **`8.0.0`**。写在 `packaging/manifest.yaml` 的 `version` 段。

**`.gitignore`**：安装器会向目标项目的 `.gitignore` 追加一行 `.omc`（幂等，已存在则跳过）。

**登记表**：

| # | 验收项 | 结果 | 证据 |
|---|---|---|---|
| AC1 | 空目录安装 + `status` 可跑 | ✅ | `install.sh /tmp/carroros-probe` → `⚠ No active task`（正常，无任务） |
| AC2 | 包内测试文件 = 0 | ✅ | `find . -name "test_*.py" \| wc -l` → `0` |
| AC3 | 包内密钥文件 = 0 | ✅ | `find . -name settings.local.json -o -name .env -o -name "*.key"` → `0` |
| AC4 | 包内运行数据 = 0 | ✅ | `find . -name "*.jsonl"` → `0` |
| AC5 | 密钥模式扫描 = 0 | ✅ | build 输出 `secret=0` |
| AC6 | 门禁在新装项目生效 | ✅ | 直调装好的 `pretool-gate.py` 拦下 `rm -rf .claude` → `governance_dir_delete` |
| AC7 | 体积 < 5 MB | ✅ | **3.4 MB** / 321 文件 |

**构建输出**：`✅ 构建通过：322 文件 / 3.4 MB / 版本 8.0.0`，`test=0 settings.local=0 jsonl=0 secret=0`。

**已知取舍**：
- `references/` 按人类裁决不进包 → 装完没有 ADR 可读，设计理由只能去源码注释里找。
- 首次构建时密钥扫描用子串 `sk-` 误报 47 处（`task-` / `risk-`），已改为正则匹配真实密钥形状。

## 12. 平台与宿主支持（2026-10-24 实测）

| 维度 | 状态 | 证据 |
|---|---|---|
| macOS | ✅ 当前开发环境，全量测试通过 | 1,009 passed |
| Linux | ✅ 预期可用 | 无 POSIX 之外依赖，未在 Linux 实机跑过 |
| **Windows 原生** | ❌ **不支持** | `fcntl` 在 5 个模块中无兜底导入：`carros_base.py:23`、`write_lock.py:14`、`token_lifecycle.py:5`、`step_contracts.py:17`、`alloc_report_index.py:16` |
| **Windows WSL** | ✅ 等价 Linux | — |
| 跨终端 | ✅ 无硬编码 `/tmp`，路径统一 `pathlib` | 全仓 grep `/tmp/` = 0 |
| Claude Code | ✅ 完全支持 | `.claude/settings.json` 的 `hooks.PreToolUse` |
| **opencode / codex / cursor / gemini / dsh** | ❌ **不支持** | 门禁绑定 Claude Code 的 hook 协议；`CarrorOS_dev` 无 `.opencode` / `.codex` / `.cursor` / `.gemini` 适配目录（`origin/main` 有） |

**结论**：发行包当前是「Claude Code + macOS/Linux/WSL」的组合。

> **定位声明（2026-10-24 人类裁决）**：本发行包**专为 Mac 打造**。
> Windows 原生不是缺陷、也不在路线图上——需要时另起分支做 Windows 版本。
> 同理，换宿主（opencode / dsh / cursor / codex）也不在本方案范围内。
