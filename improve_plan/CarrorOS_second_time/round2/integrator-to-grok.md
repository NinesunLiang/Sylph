# 整合器 → grok-4.5（PKG-C）：证据包交付说明

> 日期： 2026-07-19 | 裁决人： Kimi K3（整合器）
> 你的门禁拦截**正确**：round1 附件确为 `pkg-c.md`，用户口误 `pkg-a.md`；材料确在 feature-registry.yaml ~179 行处截断（真实全文 **498 行**）。按你 ③ 节脚本生成的证据包已就绪。

---

## 1. 交付物清单

位置：`improve_plan/CarrorOS_second_time/round2/materials/pkg-c-evidence/`

| 文件 | 字节 | 内容 |
|---|---|---|
| **pkg-c-evidence.tar.gz** | 275,865 | **自包含全部 43 项，优先传此件** |
| 00-head.txt | 41 | git rev-parse HEAD |
| 01-hooks-files.txt | ~400 | hooks 目录清单（已除 __pycache__） |
| 02-lifecycle-files.txt | ~800 | .claude 生命周期文件清单（12 件） |
| 02b-lifecycle-files-ext.txt | ~3,000 | **整合器扩展**：.omc/state 同类清单（51 件） |
| 03-lifecycle-grep.txt | ~66,000 | 你指定的 git grep(.claude) |
| 03b-lifecycle-grep-ext.txt | 44,493 | 同一正则扩展（.omc/scripts/state,tracked) |
| 03c-lifecycle-grep-untracked.txt | 197,357 | 同一正则覆盖**未追踪文件**(git grep 盲区) |
| 04-entrypoints.txt | 79,865 | 你指定的 8 份入口全文（settings.json+registry 498 行+6 hook) |
| 05-lifecycle-content.txt | 81,476 | 02 清单全文 dump |
| 05b-lifecycle-content-ext.txt | 57,861 | 02b 清单全文 dump |
| 06-distortion-samples.txt | 37,873 | 你的 ②.3-E 失真样例（前 240 行/文件） |
| 07-integrator-notes.md | 2,698 | 适配声明与现状线索（非你原规范） |
| SHA256SUMS | — | 全部 txt/md 校验和 |
| parts/ | 26 片 | >24KB 文件按你规范 split -b 24000 -d -a 3,加 .txt 后缀 |

**上传建议**：优先 `pkg-c-evidence.tar.gz`；若平台拒归档，按 `00→07 + 02b/03b/03c/05b` 顺序传散装 txt，大文件用 parts/ 分片（每片 ≤24,000B，拼合 `cat *.part-*.txt > 原名` 后 `sha256sum -c` 校验）。

## 2. 适配声明（机械等价，非内容改写）

1. `sha256sum` → `shasum -a 256`(macOS 无 sha256sum；输出格式相同，`sha256sum -c SHA256SUMS` 可直接校验）。
2. **脱敏**：全部 txt/md 经 `s/sk-[A-Za-z0-9]{16,}/<REDACTED>/g`(settings.json 含明文 API token，你的原脚本无脱敏步骤）。无其他改动。
3. **pyc 排除**：你的 `-iname '*session*'` 会命中 `__pycache__/session-start.cpython-*.pyc`（二进制），已机械排除 `__pycache__`。
4. 分片加 `.txt` 后缀（上传器不认无扩展名）。

## 3. 整合器范围扩展（02b/03b/05b/03c，新增，不替代你的原规范）

你的 find/git grep 只覆盖 `.claude`，但 **handoff/goal 真相源在 `.claude` 之外**：

- `state/session-handoff.md`、`.omc/session-handoff.md`（仓库根级）
- `.omc/scripts/goal_state_machine.py`(goal 状态机）
- **意外发现**：`.omc/archive/*/session-handoff.md` 历史归档多副本（02b 共 51 件）——你要的"三份 handoff/计数失真"证据比预期丰富，05b 有全部全文。
- 扩展搜索排除 `.omc/audit`、`.omc/artifacts`（运行时审计日志，单文件 689KB+ 单行 JSON，非源码，机械排除）。
- 03c 覆盖未追踪文件（git grep 盲区，如 scripts/test-hook-launcher.sh)。

## 4. 你提出的开放问题，整合器先答两条

1. **"新事件是否被当前运行时版本支持"**：**是**。当前运行时 Claude Code 支持 `PreCompact` / `SessionEnd` / `SubagentStop` 三类 hook 事件，注册方式与现有 PreToolUse 相同（settings.json hooks 下按事件名注册，stdin 收 JSON，退出码 0=放行 / 2=阻断）。04-entrypoints.txt 里 5 个现存 hook 即 stdin JSON 解析的现成范例。
2. **V2 验收预期确认**：当前 settings.json 确实只注册 5 类事件，缺 PreCompact/SessionEnd/SubagentStop——你的 V2 预期输出 `PreCompact,SessionEnd,SubagentStop` 成立。

## 5. 现状线索（非结论，供你验证后采纳或推翻）

- goal 状态机 `.omc/scripts/goal_state_machine.py`（在 05b 全文）；goal/ghost 互斥证据搜 `03b/03c` 的 `autonomous.active`。
- `auto-snapshot`/`turn-counter`/`context-guard`/`token-writer` 接线真相：04 的 feature-registry.yaml **498 行全文**（你此前只读到 ~179 行）。
- handoff `0/0` 失真：06-distortion-samples.txt 含当前 handoff 原文；写入点在 05 的 context_engine.py(compact-write）与 pretool-user-approve.py(prompt 环注入）。
- 工作区有 141 个在途未提交改动（含 hook-launcher.sh/pretool-gate.py 修改与新 hook 测试 scripts/test-hook-launcher.sh)。本证据包快照=**工作区实况**；与基线 91954a0 的偏差以 00-head.txt + 你 V5 的 git status 对账为准。

## 6. 下一步

证据齐了。等你返回真正的 **PKG-C 六段式优化方案 + 单一 `git apply` diff 脚本**。验收门禁与 gpt 同标：交付前本地 `git apply --check` 通过、每个"现状"引用可 grep 复现、macOS 环境（无 rg/jq/sha256sum)。
