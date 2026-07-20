# Deprecated Hooks & Scripts

> install.sh `DG-97` 自动清理依据。每次移除 hook 时更新此文件。

## v6.2.0+ 已移除

| Hook/Script | 移除原因 | 替代方案 |
|-------------|---------|---------|
| `pretool-rule-anchor` | 合并到 pretool-edit-scope.sh | `pretool-edit-scope.sh` 内置 rule_anchor_check() |
| `proactive-handoff` | 依赖 context_monitor.py (不存在) | `session-handoff.md` |
| `pretool-ask-guard` | 铁律#8 + meta-oracle-trigger 替代 (2026-05-17) | `meta-oracle-trigger.sh` |
| `posttool-read-cite` | 默认关闭，引用规范由 completion-gate 覆盖 | `completion-gate.sh` |
| `plan-gate` | ROI=0，默认关闭 | — |
| `knowledge-condenser` | ROI=0，从未触发 | — |
| `build-validator` | 默认关闭，与 error-dna 重叠 | `error-dna.sh` |
| `error-dna-auto-fix` | 读旧 .json 格式，需适配 .jsonl | — |

## v6.1.9 移除

| Hook/Script | 移除原因 |
|-------------|---------|
| `ghost-mode.sh` | 废弃兼容包装 → lx-ghost.sh |
| `lx-unattended-toggle.sh` | 废弃兼容包装 → lx-goal.sh |
