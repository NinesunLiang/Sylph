# Carror OS Lite — 踩坑笔记

## 使用方式

AI 在犯错/被纠正时自动写入教训。每条三字段格式：

```
### [tag] 问题描述

**根因**：xxx

**纠正**：xxx
```

---

## 种子教训

### [seed:safety] 危险命令拦截

**根因**：rm -rf 类危险命令可能误删项目文件

**纠正**：必须先确认备份再执行，permission-gate 会拦截

### [seed:scope] 一次改一个文件

**根因**：同时改多个文件容易越界搞乱项目

**纠正**：用 pretool-edit-scope 守住边界，一次只改一个

### [seed:handoff] compact 不丢进度

**根因**：compact 后 AI 可能忘记做到哪了

**纠正**：session-resume + handoff-writer 自动恢复任务上下文

---

*每条教训都是 AI 挖过的坑。越挖越聪明。*
