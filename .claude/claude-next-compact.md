# 历史教训速查（Compact）

> 完整版 → `Read .claude/claude-next.md`

**教训索引** — 每条背后都是一个生产事故。括号内 = 严重度。

| R# | 一句话教训 | 防御 |
|----|-----------|------|
| R22 | Bash `set -e` 空变量展开 → hook 静默退出 | 用 `${var:-default}` |
| R23 | 磁盘脚本 + settings.json + harness.yaml 三方必须一致 | audit-hooks.sh 校验 |
| R24 | `set -f` 防御 bash glob 污染 | 所有 hook 第一行 `set -f` |
| R26 | matcher 扩大后必须审查脚本内白名单 | 两层过滤语义一致 |
| R29 | `.*` matcher 导致自锁危机 | 禁止万能 matcher |
| R31 | gh CLI 是 permission-gate 盲区 | 显式拦截 gh write |
| R33 | compact-detect 后知识注入丢失 | 每次 compact 后重注入 |
| R34 | 说「系统没这问题」前必须逐文件验证 | grep 看一遍 ≠ 验证 |
| R39 | 注入预算强制 120 行 —— 超限硬截断 | 优先注入核心文件 |
| R40 | Ghost mode 下门禁应降级 | 永不阻断 read/diagnostic |
| R41 | off-by-one → error-dna 99% 数据丢失 | 轮转边界条件验证 |

**原则**: 每发现一个 bug → 写一条 R 教训 → 补一个 hook / smoke test → 永不重犯。
