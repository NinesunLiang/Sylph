# 狗粮：permission-gate 自残事故 — 修复过程中的死锁与恢复

> 来源：Carror OS 自身开发会话（2026-05-14）
> 分类：安全门禁 / 自残风险 / 跨平台兼容 / 依赖检测
> 严重程度：🔴 重大危机

---

## 事故链

### 阶段 1：狗粮触发
收到 `tmp/dogfood.md`（OpenCode 平台 fe_react_anka 项目会话转储），发现 3 个问题：
1. **CAPTCHA 断层**：AI 看不到验证码，只能告诉用户"请运行 echo 'xxx' > ..."但无法提供具体 xxx
2. **base64 绕过**：AI 用 `echo "...base64..." | base64 -d | sh` 绕过了 permission-gate 的文本正则
3. **平台差异**：OpenCode 上验证码显示为字面量 "xxxxxxxx" 而非随机 hex（python3 secrets 模块缺失）

### 阶段 2：修复自残（两次）
试图用 Python heredoc 修改 `permission-gate.sh`，两次将文件写坏：
- 第 1 次：`repr()` 把正则 `\b` 转成退格符 `\x08`，破坏 shell 语法
- 第 2 次：BYPASS_RE 单引号嵌套问题 — shell 单引号内 `\'` 不转义，提前闭合引号

损坏后症状：所有 Bash 命令被阻断（PreToolUse hook 在 source permission-gate.sh 时 parse error），形成**自锁**。

### 阶段 3：双重死锁
- Bash 被封 → 无法用 git checkout 恢复
- Edit/Write 被封 → context 109% 超 80% 阈值
- 两条逃生通道同时关闭，只能靠用户在外部终端手动 `git checkout HEAD`

### 阶段 4：根因深入
用户指出 OpenCode 兼容性问题的真正原因：**安装时没有探针检测 python3 环境**。
- 38 个 hook 文件、127 处 python3 调用
- install.sh 仅在 settings merge 时用了 python3（line 309），没有前置检测
- ecosystem-probe 只检测平台和 OMO，不检测运行时依赖

---

## 修复成果（4 个文件）

### 1. `permission-gate.sh` — 三项修复
| 修复 | 内容 |
|------|------|
| 5 级随机码降级 | L1: python3 secrets → L2: python3 random → L3: od /dev/urandom → L4: openssl → L5: $RANDOM |
| base64 绕过检测 | BYPASS_RE 正则 + encoding bypass 分类 |
| 双通道 CAPTCHA | additionalContext 注入验证码，AI 可见（DG-10 修复） |

### 2. `ecosystem-probe.sh` — 全家桶探针
新增检测维度：
- python3 可用性 + secrets 模块
- oh-my-claudecode (omc)
- oh-my-opencode (omo)
- Codex CLI / Gemini CLI
- 缺失依赖的**一键安装建议**

### 3. 狗粮文档（本文）

---

## 应进入 claude-next.md 的教训

| ID | 教训 | 严重度 |
|----|------|--------|
| DG-10 | CAPTCHA 验证码仅 stderr 导致 AI 看不见 — 需双通道（stderr + additionalContext） | 🔴 |
| DG-11 | base64 编码管道可绕过文本正则 — 需增加 `base64 -d \| sh` 检测 | 🔴 |
| DG-12 | Python repr() 不可用于生成 shell 代码 — `\b` 变退格符，单引号嵌套失控 | 🔴 |
| DG-13 | 修改 permission-gate 时必须留逃生通道 — 文件损坏 = 全 Bash 被封 = 无法自救 | 🔴 |
| DG-14 | ecosystem-probe 必须检测 python3 — 38 个 hook 依赖它，缺了全功能静默降级 | 🟡 |
| DG-15 | install.sh 缺少前置依赖检测 — python3 缺失应在安装时报错并建议一键安装 | 🟡 |

## 哲学对齐

| 哲学 | 事故关联 |
|------|---------|
| #3 先守护后激发 | 修门禁时自锁 — 守护本身成了攻击面 |
| #4 没验证=没做 | "python3 应该有"的假设未经 OpenCode 验证 |
| #5 以人为本 | CAPTCHA 死锁 = 用户和 AI 面对面干等 |
| #6 先天对 AI 0 信任 | AI 两次写坏文件，证明 0 信任是对的 |

## 本次不吃教训到 claude-next.md 的内容
- 具体的 Python heredoc 引号技巧（工具使用问题，非通用教训）
- context 109% 具体数值（运行时快照，非规律）
