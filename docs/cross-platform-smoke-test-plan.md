# 平台化全量冒烟测试方案

> 版本：v1.0 · 2026-06-07 · 波比

## 一、任务概述

CarrorOS v6.6.2 → 发版 → 在 CC 和 OC 两个空项目上跑全量冒烟测试 → 出修复方案 → 双法官验收

## 二、执行步骤

### Step 0: 确认环境

| 工具 | 版本 | 路径/安装方式 |
|---|---|---|
| CarrorOS | v6.6.2 | `~/Desktop/Sylph/Carror_OS/` |
| Claude Code | latest (npm) | `npm install -g @anthropic-ai/claude-code` |
| OpenCode | latest (brew) | `brew install anomalyco/tap/opencode` |

### Step 1: 发版 CarrorOS

跑 `bash scripts/package-release.sh` 打包分发版本。

- 检查版本号是否正确（VERSION.json → v6.6.2）
- 检查 source mirror 一致性
- 打包产出：`./source/harness-kit/`（治理层） + `./packages/carroros-gov/`（OC 插件）

### Step 2: 创建 CC 空项目 → 下载 enhance 版 → 全量冒烟

1. 在空目录创建项目：`mkdir -p ~/Desktop/carror-test-cc && cd ~/Desktop/carror-test-cc`
2. 用 `install.sh` 安装 CarrorOS 治理层（hook 文件 + settings.json）
3. 运行 `bash .claude/scripts/capability-matrix-test.sh`（全量，不传 `--quick`）
4. 记录日志和评分

### Step 3: 创建 OC 空项目 → 下载 enhance 版 → 全量冒烟

1. 在空目录创建项目：`mkdir -p ~/Desktop/carror-test-oc && cd ~/Desktop/carror-test-oc`
2. 用 `install.sh` 安装 CarrorOS 治理层（含 OC 插件复制）
3. 运行 OC 下的烟雾测试（`opencode` 启动后加载插件 + 测试）
4. 记录日志和评分

### Step 4: 对比结果 → 修复方案

对比 CC 和 OC 两个环境的测试结果，针对差异点出修复方案。

### Step 5: 双法官验收

1. Oracle: 静态检查修复方案的完整性和一致性
2. Meta-Oracle: 运行时验证修复后的测试结果

## 三、风险与注意事项

- CC 在本地跑（MTPLX 代理），确保 ANTHROPIC_BASE_URL 配置正确
- OC 可能需要 API key 或特定模型配置
- enhance 版 = 发版打包后的最新稳定版本
- 空项目 = 只有 CarrorOS 治理层，无业务代码

## 四、验收标准

- CC 环境：能力矩阵 ≥ 90%（当前 source 版基线 95.7%）
- OC 环境：所有 CarrorOS hook 正确加载
- 差异项 ≤ 3 个（CC vs OC 的治理层行为一致性）
