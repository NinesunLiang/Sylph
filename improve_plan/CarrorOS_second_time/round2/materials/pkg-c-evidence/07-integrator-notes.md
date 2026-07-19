# 整合器说明（随证据包交付，非 grok 原规范内容）

1. **附件归属裁决**：你 round1 收到的是 `pkg-c.md`（正确），用户口误说成 `pkg-a.md`。你的门禁拦截正确。
2. **运行时事件支持**：当前运行时为 Claude Code，**支持 PreCompact / SessionEnd / SubagentStop 三类 hook 事件**，注册方式与现有 PreToolUse/PostToolUse 相同（settings.json 的 hooks 下按事件名注册，stdin 收 JSON，退出码语义：0=放行，2=阻断）。本包 04-entrypoints.txt 的 5 个现存 hook 即 stdin JSON 解析的现成范例。
3. **环境等价替换**：`shasum -a 256` 替代 `sha256sum`（macOS），输出格式相同，`sha256sum -c SHA256SUMS` 可直接校验。
4. **脱敏声明**：全部 txt/md 经 `s/sk-[A-Za-z0-9]{16,}/<REDACTED>/g` 机械替换（settings.json 含明文 API token）。无其他内容改动。
5. **范围扩展（整合器补充，非你的原规范）**：
   - `02b/05b`：你的 find 只扫 `.claude`，但 handoff 真相源在仓库根 `state/session-handoff.md` 与 `.omc/session-handoff.md`，goal 状态机在 `.omc/scripts/goal_state_machine.py`。已用同一组 iname 模式补充。
   - `03b`：同一正则扩展到 `.omc scripts state`（git grep，tracked）。
   - `03c`：同一正则为覆盖**未追踪文件**的补充（git grep 盲区，如 scripts/test-hook-launcher.sh）。
   - 扩展搜索排除 `.omc/audit`、`.omc/artifacts`：运行时审计/产物日志（单文件 689KB+，单行 JSON），非源码，机械排除。
6. **pyc 排除**：你的 `-iname '*session*'` 会匹配 `__pycache__/session-start.cpython-*.pyc`（二进制），已机械排除 `__pycache__`。
7. **分片规范**：>24000B 的文件已按你的规范 `split -b 24000 -d -a 3` 分片于 `parts/`，分片加 `.txt` 后缀（上传器不认无扩展名），`parts/SHA256SUMS.parts` 可校验。若 tar.gz 可上传，优先 tar.gz（自包含）。
8. **现状线索（非结论，供你验证后采纳或推翻）**：
   - 三份 handoff 候选：`state/session-handoff.md`、`.omc/session-handoff.md`，第三份（若存在）待你在 02/02b 清单中证实。
   - goal 状态机：`.omc/scripts/goal_state_machine.py`（在 05b 全文中）。
   - `auto-snapshot`、`turn-counter`、`context-guard`、`token-writer` 的接线真相：见 04 的 feature-registry.yaml **全文 498 行**（你此前只读到 ~179 行）。
   - 工作区现有 141 个在途未提交改动（含 hook-launcher/pretool-gate 修改与新 hook 测试 scripts/test-hook-launcher.sh），本证据包快照=工作区实况，与基线 91954a0 的偏差以 00-head.txt + 你 V5 的 git status 对账为准。
