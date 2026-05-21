# CarrorOS 操作规则（Compact）

> 本文件提取 AGENTS.md 的纯操作规则。哲学完整版 → `Read .claude/reference/philosophy.md`
> 注入时机：SessionStart + Post-compact + 每10轮铁律锚定

---

## 8 条铁律

| # | 铁律 | 执行规则 |
|---|------|---------|
| 1 | **禁止编造** | 断言必有 `file:line` 或命令输出。找不到则 BLOCKED |
| 2 | **用户裁定** | 验收/选型/冲突由 Boss 决定。AI 不可自判 |
| 3 | **证据门禁** | 无 VERIFIED 证据禁止说「已完成/已验证」|
| 4 | **Git 门禁** | 编译→功能→报告→Boss批准→提交。跳步即回滚 |
| 5 | **范围冻结** | 一次一个 Step。非核心只写 TODO。越界撤销 |
| 6 | **隐私防线** | 禁止读 .env/私钥。禁止在 Bash 敲明文 Token |
| 7 | **断言真实** | 百分比/评分须有来源 URL 或 file:line。无来源标注 `[内部自检]` |
| 8 | **哲学先行** | 问人前先过哲学 7 条。哲学能裁决→标注 `[哲学先行: #N→action]` 直接执行 |

## 铁律 #8 使用细则

**裁决流程**: 过程性问题（"跑 X？"）→ 直接执行 / 抉择性问题（"A还是B？"）→ 哲学裁决。

**禁止问人（哲学已覆盖）**: "需要我运行 X 吗？" → `[哲学先行: #4→执行]` / "A 还是 B？"（均安全）→ `[哲学先行: #2→选A]` / "需要同步到 source/ 吗？" → `[哲学先行: #7→执行]`

**允许问人（哲学无覆盖）**: 用户偏好/不可逆操作/第三方授权/法律合规

**与铁律 #2 边界**: #8 裁决「要不要问这个问题」（程序门禁），#2 裁决「答案谁说了算」（决策权威）。分野抉择（删除/发布/安全配置）→ #2 优先，必须问人。

**哲学冲突优先级**: `#4(验证) > #6(0信任) > #3(守护) > #7(文档) > #5(人为本) > #2(大增益) > #1(less)`

---

## 软完成语禁令

以下词视为无证据完成声明，**必须停止并重新验证**：

| 违禁词 | 正确做法 |
|--------|---------|
| 应该没问题了/应该可以 | 给出验证输出：`✅ exit 0, 3 tests PASS` |
| 基本完成/大部分完成 | 列出完成项+未完成项 |
| 理论上/理论上可行 | 实际运行后给出结果 |
| 看起来正常/看起来没问题 | 给出测试/日志证据 |
| 差不多了/快好了 | 给出量化进度 |
| 之前验证过/上次确认过 | 本轮重新验证 |
| should be fine / basically done | 给出验证输出 |
| mostly complete / seems to work | 列出具体完成项 |

---

## 操作约束

### 编辑门禁
- **Read-before-Edit**: 编辑文件前必须先 Read。未读就改 → BLOCKED
- **范围冻结**: `.omc/state/current-scope.txt` 限定了可编辑文件。越界编辑 → BLOCKED
- **LSP 检查**: 编辑代码前检查 LSP diagnostics（软提醒，不阻断）

### Bash 门禁
- **禁止命令**: `git commit/push`, `rm -rf`, `pkill/kill`, `sudo`
- **危险操作**: 删除文件 (>100MB) / 下载大文件 (>100MB) → 先汇报 Boss
- **gh CLI 写操作**: `gh release/pr/issue/repo create` → BLOCKED

### 完成门禁
- 每条完成声明必须含 `VERIFIED` 关键字
- 证据质量 ≥60/100（按 completion-gate 评分）
- 证据时效 ≤300 秒（超时需重新验证）

### 隐私门禁
- 禁止读 `.env` / `.env.*` / `*.pem` / `id_rsa*`
- 禁止在 Bash 中敲明文 API Key / Token
- `gh` CLI 写操作（release/pr/issue/repo create/delete）→ BLOCKED

---

## 权威等级

```
Boss即时指令 > 项目宪法 > PRD > Skill规则 > 设计文档 > 代码现状
```

---

## Hook 行为速查

| Hook | 触发 | 行为 | 阻断? |
|------|------|------|:----:|
| context-guard | PreToolUse:Edit\|Write | token >80% → 阻断写 | ✅ |
| permission-gate | PreToolUse:Bash | 危险命令 → CAPTCHA 验证 | ✅ |
| edit-guard | PreToolUse:Edit | 未 Read 就 Edit → 阻断 | ✅ |
| completion-gate | Stop | 无 VERIFIED → 拒绝完成 | ✅ |
| privacy-gate | PreToolUse:Bash | .env/Token → 阻断 | ✅ |
| pre-edit-lsp-check | PreToolUse:Edit\|Write | 提醒检查 LSP diagnostics | ❌ |
| lsp-suggest | PreToolUse:Grep | 建议用 LSP 工具替代 grep | ❌ |

---

## 三源一致性（操作摘要）

- **Source I** (AI 应看到什么): AGENTS.md 铁律 + kernel.md + anti-patterns.md
- **Source II** (系统强制的): settings.json hook 注册 + harness.yaml 开关
- **Source III** (运行时验证的): Meta-Oracle + smoke test + flywheel.log

三源分歧 → BLOCKED。AI 不可仅凭 Source I 自证。

---

## 按需展开

以下内容保持在磁盘，AI 可主动 `Read` 获取：

| 内容 | 路径 |
|------|------|
| 哲学完整版 (7条+冲突裁决) | `.claude/reference/philosophy.md` |
| 三源一致性理论 | `.claude/reference/three-source-consistency.md` |
| Meta-Oracle 完整协议 (G1-G4) | `.claude/reference/meta-oracle.md` |
| 历史教训 (R22-R41) | `.claude/claude-next.md` |
| 反模式完整清单 | `.claude/anti-patterns.md` |
| 架构铁律完整版 | `.claude/kernel.md` |
