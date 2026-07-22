# claude-next.md — 飞轮学习笔记（指针）

> **唯一数据源已迁移**：`.omc/knowledge/claude-next.md`
> 本文件仅为指针，消除双份分裂（2026-07-18 rpe-f 修复）。
> 飞轮写入：`.claude/hooks/stop-flywheel.py`（Stop hook 自动触发）
> 升华规则：hits≥5 → anti-patterns.md（kernel 候选，晋升需人类裁决）

## 用户纠正记录
→ 见 `.omc/knowledge/claude-next.md`

## 项目偏好
→ 见 `.omc/knowledge/claude-next.md`

## 错误模式
→ 见 `.omc/knowledge/claude-next.md`

## 🏗️ 通用代码质量基线 (2026-07-22)

从 auto-review checkpoint + lx-code-review 经验提取，语言无关。

### P0 红线（必须阻断）
- **硬编码凭据**: APIKey/Password/Secret/Token 不得直接写入代码，必须走环境变量或 Secret Manager
- **无issue TODO**: 所有 TODO/FIXME 必须关联 issue 编号（`#1234`），无引用视作未完成工作
- **无错误处理的外部调用**: HTTP/DB/文件/网络调用必须处理异常，不得 `catch {}` 或 `// ignore`
- **H3/H4 Go专项**: 类型断言无 comma-ok / slice 首元素无 len 检查 → crash 风险

### P1 最佳实践
- **debug 代码不得遗留**: `console.log`/`print`/`debugger`/`pdb.set_trace` 应在提交前移除
- **日志敏感信息**: Token/密码/完整请求体不得出现在日志输出中
- **goroutine 生命周期**: 所有 goroutine 必须有退出机制（context/chan/select）
- **map/slice 不安全访问**: 单返回值 map 访问 + comma-ok | slice `[0]` + len 检查

### P2 持续改进
- 函数 > 80 行 / 嵌套 > 4 层 / 重复代码 ≥ 10 行 → 重构信号
- 注释与代码不一致 → 维护陷阱
