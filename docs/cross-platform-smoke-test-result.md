# 跨平台全量冒烟测试结果报告

**版本**: v6.6.3-stable | **日期**: 2026-06-07

---

## 测试环境

| 环境 | 项目路径 | 部署方式 | Agent 版本 |
|------|----------|----------|------------|
| CC | `~/Desktop/carror-test-cc/` | harness-kit 解压 + rsync hooks/scripts/ | Claude Code v2.1.158 |
| OC | `~/Desktop/carror-test-oc/` | harness-kit 解压 + rsync hooks/scripts/ | OpenCode v1.15.4 |

部署步骤：
1. `rm -rf .claude/`
2. `tar xzf harness-kit-v6.6.3-stable.tar.gz`
3. `rsync -a Carror_OS/.claude/hooks/ test-project/.claude/hooks/`
4. `rsync -a Carror_OS/.claude/scripts/ test-project/.claude/scripts/`

---

## 全量能力矩阵对比

| 维度 | 描述 | CC (%) | OC (%) | Delta | 状态 |
|------|------|--------|--------|-------|------|
| **D1** | Hook 存在性 | **79.3%** | **79.3%** | 持平 | 27 pass / 0 fail / 19 warn（warn 来自内置/未实现） |
| **D2** | Settings 注册 | **0%** | **0%** | 持平 | ⛔ 硬编码 .sh 后缀 |
| **D3** | Bash 语法 | **0%** | **0%** | 持平 | ⛔ 无 .sh hook 文件需要检查 |
| **D4** | 烟雾测试 | **0%** | **0%** | 持平 | ⛔ harness-smoke-test.py exit=1 |
| **D5** | Feature Registry | **100%** ✅ | **100%** ✅ | 持平 | 通过 |
| **D6** | Flywheel 覆盖率 | **50%** ⚠️ | **50%** ⚠️ | 持平 | flywheel.log 存在 |
| **D7** | 三源一致性 | **100%** ✅ | **100%** ✅ | 持平 | 通过 |
| **D8** | Error DNA | **50%** ⚠️ | **100%** ✅ | OC +50% | OC 的 error pipeline 运行正常 |
| **D9** | Oracle 评分 | **100%** ✅ | **100%** ✅ | 持平 | 通过 |
| **D10** | 哲学追溯 | **0%** | **0%** | 持平 | ⛔ 硬编码 .sh 文件名称 |
| **D11** | 铁律机制 | **0%** | **0%** | 持平 | ⛔ 硬编码 .sh 文件名称 |
| **D12** | Skill 可用性 | **0%** | **0%** | 持平 | ⛔ 无 skills/ 目录（harness-only 模式） |
| **D13** | 已知缺陷 | **75%** ⚠️ | **75%** ⚠️ | 持平 | 通过 |
| **D14** | 集成安全 | **0%** | **0%** | 持平 | ⛔ 硬编码 .sh 文件名称 |
| **总分** | | **39.5%** | **43.1%** | | |

---

## 问题清单（按优先级分类）

### P0 — 阻断级（必须立即修复）

| ID | 维度 | 根因 | 修复建议 |
|----|------|------|----------|
| F-01 | D2/D3/D10/D11/D14 | `capability-matrix-test.sh` 硬编码 `.sh` 文件后缀检查（D2 脚本注册、D3 bash-syntax、D10/D11 文件存在性、D14 集成测试均如此） | ✅ D1 已修（检测 .py/.sh 双后缀）；其余维度同样需改为 `.py/.sh` 双态检测 |
| F-02 | D4 | `harness-smoke-test.py` exit=1，但未记录失败原因 | 按 D4 测试脚本的已修复逻辑（py 优先），需要检查 smoke test 具体失败项 |

### P1 — 高优先级

| ID | 维度 | 根因 | 修复建议 |
|----|------|------|----------|
| F-03 | D2 | `settings.json` 注册检测脚本检查 `.sh` 后缀的钩子——但新部署只有 `.py` | 修改注册检测脚本来识别 `.py` 文件注册 |
| F-04 | D10/D11 | 哲学/铁律文件存在性检查仍针对 `.sh` | 改为 `.py/.sh` 双后缀检测 |
| F-05 | D14 | 集成测试检查 `permission-gate.sh`，但已迁移为 `.py` | 改为检测 `permission-gate.py` |
| F-06 | D12 | `skills/` 目录不包含在 harness-kit 中，`enhanced` 模式才有 | 区分安装模式：harness-only 跳过 D12 |

### P2 — 可优化

| ID | 说明 | 状态 |
|----|------|------|
| F-07 | D6 评分需要 harness-kit 内有 flywheel.log？还是允许第一次运行时才生成？ | 待确认 |
| F-08 | OC 插件 `plugin.json` 不存在——`carroros-gov` 目前没有 `.opencode/plugin.json` 文件，OC 侧只能手动挂载 | 待补 |
| F-09 | 19 个 hook 标记为"内置/未实现"，实际已有 `.py` 文件但未被 `harness.yaml` 显式注册为 hooks_enabled | 需核验 |

---

## 环境问题对比

| 项目 | CC | OC |
|------|----|----|
| opencode 版本 | — | ✅ v1.15.4 |
| 插件注册 | — | ⚠️ 无法自动识别（无 plugin.json） |
| 能力矩阵脚本可用 | ✅ | ✅ |
| smoke test 运行 | ✅ .py 运行但 exit=1 | ✅ .py 运行但 exit=1 |
| hooks 目录 | 20 .py 文件存在 | 20 .py 文件存在 |
| harness.yaml 解析 | ✅ | ✅ |

---

## 已完成的修复（本轮）

| 修复 | 文件 | 状态 |
|------|------|------|
| D1 `.sh` → `.py` 双后缀检测 | `source/harness-kit/.claude/scripts/capability-matrix-test.sh` L152-165 | ✅ 已提交 |
| D4 `.sh` → `.py` 优先 | 同上 L221-242 | ✅ 已提交 |
| OC plugin engine 降级 >=1.14.0 | `packages/carroros-gov/package.json` | ✅ 已提交 |
| 发布包排除 .sh（仅暴露 .py） | `scripts/package-release.sh` Step 1 rsync 排除 `--exclude='*.sh'` | ✅ 已提交 |
| source 坏符号链接修复 | `capability-matrix-test.sh` 自指符号链接 → 真实文件 | ✅ 已修复 |
| 3 个迁移 .sh 文件的清理 | source/OC 的旧 .sh 文件删除 | ✅ 已清除 |

---

## 待修复

1. **F-01**: D2/D3/D10/D11/D14 的 `.sh` 硬编码——需要全部改为 `.py/.sh` 双后缀检测（使用与 D1 相同的模式）
2. **F-02**: D4 smoke test exit=1 具体原因排查
3. **F-08**: OC plugin.json 创建
