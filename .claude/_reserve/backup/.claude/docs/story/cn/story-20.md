.claude/docs/story/cn/story-20.md
# Story 20: Gate阻断协议演进

> v6.3.8 · Carror OS — 哲学#5(以人为本)+#6(0信任)

## 问题

oracle-gate 使用 continue:false 导致每次编辑治理文件都中断工具链。频繁 "stopped continuation" 让人类困惑。

## 解决方案

确立工作流打断原则: **只有"结束"和"问用户问题"才能用 continue:false**。

| 协议 | 适用 | 机制 |
|------|------|------|
| continue:false | permission-gate, privacy-gate (安全暂停) | Python硬阻断,停止工具链 |
| exit2+continue:true | oracle-gate, blast-radius, terminal-safety | Bash阻断工具,不打断链 |

## 相关机制

- oracle-gate 会话豁免: 一次CAPTCHA绕过→同会话后续自动放行
- checkpoint hook: 阻断事件在收尾报告汇总
- DG-126: Gate阻断后AI必须向人类说明原因+选项