# 狗粮：Windows 跨平台验收 — 40 个安全守卫静默失效

> 来源：外部用户 OpenCode+Windows 实测验收 + Ghost 模式 100 轮探索（2026-05-23~24）
> 分类：跨平台兼容 / 依赖检测 / 安全降级
> 严重程度：🔴 MAJOR — 35/45 hooks 在 Windows 上哑火，privacy-gate token 检测可被绕过

---

## 事故链

### 阶段 1：Ghost 探索发现

运行 `/lx-ghost` 100 轮自主探索（5h），扫描跨平台兼容性。发现：

- **F2.1**: 49/54 hook 脚本硬编码 `python3`，但 Windows 上 Python 叫 `python.exe`
- **F2.8**: 4 个 Stop hook 用相对路径 → Stop 事件触发时 CWD 漂移 → `No such file`
- **F1.5**: unified.yaml 仅覆盖 15/46 hooks (33%)，31 个 hook 永不跨平台生成

### 阶段 2：外部用户独立验证

收到 `client_fellback/feedback.md` — 另一用户在 Windows + OpenCode 上跑完了 S0-S9 全量验收。

关键数据（独立交叉验证了 Ghost 发现）：

| 指标 | 数值 |
|------|:---:|
| python3 缺失 → 无 fallback 的 hooks | 35/40 |
| jq 缺失 → JSON 解析失败的 hooks | 28/45 |
| privacy-gate token 检测 | jq 缺失时被绕过（安全风险）|
| session-guardian.ts 原生防线 | 4/4 完全生效（救了系统）|

### 阶段 3：根因分析

两个根因在 install.sh 时代就埋下了，修复从未传播到 hook 层：

1. **DG-105 修复不完整**：`resolve_python()` 只在 install.sh 生效。`harness_config.sh` 仍然 `command -v python3` → 失败 → `_HC_CACHE_LOADED="empty"` → 40+ hooks 的 `hc_enabled`/`hc_config` 全部返回 false
2. **`export -f python3` 跨进程无效**：install.sh 创建了 bash 函数别名并 export，但 hooks 是独立 bash 进程，不继承父 shell 的函数导出
3. **jq 从未被自动安装**：install.sh 只检测 jq 是否存在 → 不存在时打印 "jq 未安装（将使用 python3 回退）" → 但 python3 也不存在

### 阶段 4：双法官审核 + 执行

按 "do" 工作流：Oracle (REVISE 7项) → Meta-Oracle (ADVISORY 4盲区) → 修复 11 项。

---

## 修复

| 修复 | 文件 | 影响 |
|------|------|------|
| `$PYTHON_BIN` 解析 + 导出 | `harness_config.sh` | 40+ sourced hooks 自动继承 |
| `python3` → `${PYTHON_BIN:-python3}` | 48 hooks | Windows 上不再哑火 |
| `install_jq()` 9 包管理器 | `install.sh` | pacman/winget/choco/brew/apt/dnf/yum/apk |
| `export -f python3` → DEPRECATED | `install.sh` | 消除误导性修复 |
| `${VAR:-0}` 防空值 ×4 | `token_writer.sh` | 无 python3 时不再产损坏 JSON |
| Stop hook 绝对路径 | `settings.json` | Stop 事件不再 CWD 漂移 |
| 行级 read-tracker | `read-tracker.sh` + `posttool-claim-audit.sh` | AI 编造行号可被检测 |
| 7 项 source mirror 漂移 | 全量 sync | 下个 release 不丢功能 |
| 3 条 DG-111/112/113 | `claude-next.md` | 狗粮闭环 |

---

## 附带产出：行级反编造机制

在修复过程中发现 `posttool-claim-audit.sh`（铁律 #1 刽子手）只验证到文件级：AI 声称 `kernel.md:999` 时，只检查 `kernel.md` 是否被 Read 过，不检查第 999 行是否在 Read 范围内。

升级为两级验证：

| 级别 | 检查内容 | 违规标记 |
|:---:|------|------|
| L1 文件级 | 这个文件被 Read 过吗？ | `UNREAD_FILE` |
| L2 行级 | 这个行号在 Read 行范围内吗？ | `LINE_OUT_OF_RANGE` |

`read-tracker.sh` 同步升级：记录格式从 `/path/file.sh` 改为 `/path/file.sh:1-200`（行范围），同一文件多次 Read 自动合并最宽覆盖。

---

## 为什么 session-guardian.ts 救了系统

最核心的安全防线（Edit/Permission/Privacy/Context Gate）通过 OpenCode TS 插件以 **0 bash spawn** 方式运行。即使 35 个 bash hooks 全部静默失效，session-guardian.ts 的原生 Permission Gate 仍然在 TS 内存态拦截 `git push --force` 和 `rm -rf`。

**双重保险架构奏效**：TS 原生防线 + bash hook 链，两者独立运行、独立失效、独立恢复。

---

## 教训（已写入 claude-next.md）

| DG | 一句话 |
|----|--------|
| DG-111 | `export -f python3` 跨进程无效，真修在 harness_config.sh |
| DG-112 | jq 缺失 → privacy-gate token 检测被绕过 |
| DG-113 | Stop hook 相对路径 CWD 漂移 |

---

## 验证

```bash
VERIFIED: audit-hooks.sh --check-source-mirror → 🔴0 🟡0 ✅
VERIFIED: bash -n 全部 48 hooks 语法通过
VERIFIED: harness_config.sh _resolve_python() 覆盖 Windows 路径
VERIFIED: install.sh install_jq() 覆盖 9 种包管理器
```
