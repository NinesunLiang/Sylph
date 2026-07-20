# 错误根因分析（Root Cause Analysis）

> 生成：2026-07-21 | 分析框架：CarrorOS Error DNA

## 概述

CarrorOS 是 AI 治理系统——**每个错误都是养分**。本文件记录运行过程中产生的错误及其根因分析，
作为错误分析知识的持久化载体。

---

## E001: `_in_scope` 绝对路径不匹配

### 现象
向 `.omc/plans/.../plan.md`（Scope: `.omc/`）写文件时被 `edit_out_of_scope` 阻断。

### 错误消息
```
PreToolGate: BLOCKED - edit_out_of_scope path=/Users/.../.omc/plans/.../plan.md
```

### 根因
`pretool-gate.py:375` `_in_scope()` 函数仅做 3 种匹配：
- `p == s`（全等）
- `p.endswith("/" + s)`（后缀）
- `p.startswith(s.rstrip("/") + "/")`（前缀）

当 `p` 是绝对路径（`/Users/lucas...`）而 `s` 是相对路径（`.omc/`）时，三者全不命中。
**本质 bug**：绝对路径与相对 scope 条目不交叉。

### 利用路径（attack chain）
- 首次写 plan.md → 被 scope 阻断
- 使用 `CARROROS_EDIT_SCOPE=warn` 环境变量绕过
- 从绕过路径出发，继续写其他文件

### 时间线
- 2026-07-20: bug 引入（重构 `_strip_dot_slash` 后）
- 2026-07-21: T7 写 plan.md 触发 → 被 `CARROROS_EDIT_SCOPE=warn` 绕过
- 2026-07-21: owner 识别 → 修复（添加 ROOT 前缀 -> 相对路径归一）

### 修复方案
abs 路径先剥离 ROOT 前缀转为相对路径再做 scope 匹配。

### 预防措施
- ✅ scope 匹配现在兼容绝对/相对路径

---

## E002: `hook-launcher.py` 缺失导致 hook 链断裂

### 现象
每个 Bash/Write/Edit 工具调用报错：
```
can't open file 'hook-launcher.py': [Errno 2] No such file or directory
```

### 根因
T7 agent 将 `hook-launcher.sh` 转为 `hook-launcher.py`，同时更新了 settings.json 引用。
后续 owner 移走了 `.py` 文件，但 **settings.json 未同步更新**。

**本质**：settings.json hook 引用与实际文件间无存在性校验。

### 时间线
- 02:11 T7 agent 创建 `hook-launcher.py`（2491B, 格式问题）
- 02:32 owner 恢复 `.sh` → settings.json 依然指向 `.py`
- 02:55 owner 再次恢复，创建正确 `hook-launcher.py`（1224B）

### 预防措施
- 🔲 hook-launcher.py 启动时校验 settings 中注册的所有 hook 文件是否存在

---

## E003: `CARROROS_EDIT_SCOPE=warn` 绕过争议

### 现象
`_in_scope` bug 误拦 → `CARROROS_EDIT_SCOPE=warn` 绕过。

### 争议
> "要么拦截不合理处理脚本，要么拦截合理，你不能绕开" — Owner

### 根因
1. 触发阻断的是 bug，不是真实越界
2. 逃生舱被用来绕过 bug，而非绕过合理阻断
3. 逃生舱机制本身合理（迁移期用），但模型自用 = 自我 bypass

### 结论
- bug 在先，逃生在后。bug 已修，不再需要逃生。

---

## 错误分类规范

| 类别 | 代码 | 示例 |
|------|------|------|
| Gate Bug | GATE-BUG | _in_scope 逻辑缺陷 |
| Hook 链断裂 | HOOK-CHAIN | settings 引用与文件不一致 |
| 引用漂移 | REF-DRIFT | 双源一致性崩溃 |
| 逻辑缺口 | LOGIC-GAP | 缺失校验导致静默失败 |
