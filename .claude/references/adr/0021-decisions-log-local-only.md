# 0021. 决策日志本机化：.claude/decisions/DECISIONS.md 不入库、不进安装包

**日期**: 2026-10-24
**来源**: 用户提议「在 .claude/index 引入，但从 omc 迁到 claude 的 DECISIONS.md 不放进安装包，确保每个人下载的都是空的」+ ask_user 选择「三个都改（AGENTS/kernel/index）」
**状态**: 已采纳（D-031）

## 上下文

人类裁决日志原先放在 `.omc/decisions/DECISIONS.md`。`.omc/` 不入库，但人类希望：
1. 决策日志进入 `.claude/` 路由，成为治理地图里可见的房间；
2. 日志仍是**本机历史**，不随代码分发；
3. 每个新安装从空开始，不会带着作者的历史。

分类边界：`DECISIONS.md` = 本机裁决历史（过程）；`references/adr/` = 可复用设计记录（结论）。

## 决策

1. 路径迁到 `.claude/decisions/DECISIONS.md`，在 `.claude/index.md` 增加 `decisions/` 房间入口。
2. 历史文件 `.gitignore`，**不入库**；manifest 显式排除，**不进安装包**。
3. 安装包只带 `.claude/decisions/README.md`（空态说明），首次使用时本机创建 `DECISIONS.md`。
4. 冻结文件（AGENTS.md / kernel.md / index.md）的引用同步更新；人类已授权。
5. ADR 仍留在 `.claude/references/adr/`，作为跨机器追溯的设计记录。

## 后果

- 好处：安装包干净；决策历史不泄漏作者上下文；治理地图仍能指出日志位置。
- 代价：换机器时 `DECISIONS.md` 不跟随，跨机器追溯依赖提交记录 + ADR。
- 机械保证：`test_decisions_local_ssot.py` 锁死路由、gitignore、安装包空态。

## 改动清单

| 文件 | 改动 |
|---|---|
| `.omc/decisions/DECISIONS.md` → `.claude/decisions/DECISIONS.md` | 迁移 |
| `.claude/decisions/README.md` | 新增空态说明（随包） |
| `.claude/index.md` | 房间路由新增 decisions/，移除 .omc 表旧行 |
| `AGENTS.md` / `.claude/kernel.md` | 旧路径改新路径 |
| `.gitignore` | 忽略历史文件 |
| `packaging/manifest.yaml` | include README / exclude DECISIONS |
| `.claude/scripts/test_decisions_local_ssot.py` | 新增回归锚点 |
| `.claude/scripts/test_memory_governance_map.py` | 读取新路径 |
