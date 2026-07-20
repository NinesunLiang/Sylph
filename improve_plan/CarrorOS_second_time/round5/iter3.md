# 迭代 3 — P3 注入新鲜度守卫(F5/F6)

> 2026-07-20 | 选取理由: 每次会话启动都注入 2 日陈旧 handoff+过期 token 摘要(本会话开场即被注入 skill-hook-adaptive-opt 0/6 幻影任务),误导恢复+浪费上下文

## 施工内容

| 动作 | 文件 | 说明 |
|---|---|---|
| staleness 守卫 | `.claude/hooks/session-start.py` | 新增 STALE_HOURS=24: handoff 头部 ISO 时间戳(回退 mtime)超龄 → 注入时前置 ⚠️ STALE 横幅(保留内容,标注勿直接恢复);token 摘要追加年龄,超龄加"恢复前先核对磁盘态" |
| 文档真相修正 | `.claude/references/omc-path-conventions.md:43` | handoff 路径 `.omc/state/session-handoff.md` → `.omc/session-handoff.md`(对齐 session-start.py:24 现实) |
| F6 结案 | 无需改码 | handoff 头部"AGENTS.md 已 @ 引用"幽灵声称:context_engine.py:478 已于 476a08b 修为真实注入链;磁盘旧文件随下次 compact-write 自愈 |

## 验证证据

1. **live 测试**(当前 29h 陈旧 handoff): 注入出现 `⚠️ [STALE handoff — 更新于 29h前,超 24h]` 横幅;token 摘要带 `token 41m前更新` 年龄标注
2. **回归**: 六套全 rc=0(watermark 25/oracle 31/verify 20/goal-mode 12/launcher/pkg_c)
3. 解析回退链: ISO 优先→mtime 兜底→异常静默(永不阻断,符合 hook 设计)

## 附带发现(未施工,入清单)

- `fallback_matrix.py:47` `_check_idle_time` 读不存在路径 `.omc/state/session-handoff.md` → long_idle 触发器永假;但 `check_trigger` 全仓零调用(死模块)→ 建议归档或接线,人类裁决
- 仓根 `state/session-handoff.md` 孤儿文件(无任何代码读写)→ rm 硬边界,人类清理
- `.omc/tokens/` 日期目录双格式(2026-07-18/ vs 20260718/)→ 统一需迁移,人类裁决

## 分数变化(自评口径)

| 项 | 前 | 后 | 依据 |
|---|---|---|---|
| C2 上下文完整度 | 8 | **9** | 注入链有新鲜度校验,陈旧内容显式标注而非盲信 |
| UX 用户心智负担减轻 | 7 | **8** | 幻影任务不再裸注;STALE 横幅消歧 |
| **C 加权** | 8.67 | **8.81** | +15 |
| **24 项总加权** | 8.53 | **1908/2220 = 8.59** | **+0.06** |
| UX 均分 | 7.57 | **54/70 = 7.71** | +1 |
