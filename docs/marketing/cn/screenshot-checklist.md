# 截图与视频素材清单

> **用途**：收集 Carror OS 上线所需的所有场景素材（网站、README、媒体资料包、演示视频）。
> **状态**：活跃
> **最后更新**：2026-05-04
> **总场景数**：12 张截图 + 2 个演示视频

---

## 所需截图

| ID | 场景 | 展示内容 | 优先级 | 参考文件 |
|----|-------|-------------|----------|-----------|
| SS-01 | 安装后首次运行 | CLAUDE.md `@AGENTS.md` 导入成功，治理框架版本显示 | P0 | `.claude/harness.yaml` |
| SS-02 | 权限门禁拦截 | AI 尝试 `rm -rf /tmp/test`，Hook 以编号选择菜单阻断 | P0 | `.claude/hooks/permission-gate.sh` |
| SS-03 | 上下文守卫告警 | AI 上下文 ~80%，`context-guard.sh` 触发 3 选项菜单（继续/总结/紧急总结） | P0 | `.claude/hooks/context-guard.sh` |
| SS-04 | lx-status 面板 | 完整 5 屏显示：Token 趋势 + Error DNA + Flywheel + Feature Registry + 上下文 | P0 | `.claude/scripts/carror_dashboard.py` |
| SS-05 | 完成门禁拦截 | AI 声称"应该没问题了"，`completion-gate.sh` 阻断并索要 VERIFIED 证据 | P0 | `.claude/hooks/completion-gate.sh` |
| SS-06 | 隐私门禁拦截 | AI 尝试读取 `.env` 文件，`privacy-gate.sh` 以 DLP 警告阻断 | P0 | `.claude/hooks/privacy-gate.sh` |
| SS-07 | lx-rpe 状态面板 | 活跃 RPE 任务流水线展示 Phase 进度（Research → Plan → Execute → Verify） | P1 | `.claude/skills/lx-rpe/` |
| SS-08 | Error DNA 可视化 | Error DNA 面板展示分类错误模式、严重程度、修复率 | P1 | `.claude/scripts/carror_error_dna.py` |
| SS-09 | 审计面板摘要 | 审计日志聚合，覆盖 5 个来源：Git、Error DNA、Token 追踪、会话日志、Handoff | P1 | `.claude/scripts/carror_audit.py` |
| SS-10 | /lx-status CLI 输出 | `/lx-status` 命令的原始终端输出，展示实时防御指标 | P1 | `lx-status` skill |
| SS-11 | 渐进式披露 L1 加载 | 会话启动时加载 L1 内核文件：kernel.md + anti-patterns.md + claude-next.md（~120 行） | P1 | 会话启动 Hook |
| SS-12 | README 项目首页 | 最终 README 英雄区，含徽章、架构图、"给 AI 装上刹车"标语 | P2 | `docs/marketing/cn/README-draft.md` |

---

## 所需演示视频

### 演示 1："门禁实战"（60-90 秒）

**目的**：说服怀疑者 Carror OS 提供的是物理级阻断，而非 Prompt 建议。

| 时间 | 场景 | 旁白 |
|------|-------|-----------|
| 0:00-0:10 | 用户在 Claude Code 中输入 `rm -rf /var/www` | "每个 AI 用户都害怕这一刻。" |
| 0:10-0:20 | 权限门禁以 Exit 2 阻断，显示编号菜单 | "Carror OS 不请求——它阻断。物理级。" |
| 0:20-0:30 | AI 无证据声称"完成"，完成门禁拦截 | "并且在工具调用层阻止幻觉。" |
| 0:30-0:45 | /lx-status 面板展示实时防御统计 | "每次拦截都有日志，每道门禁都可验证。" |
| 0:45-0:60 | 并排对比：无治理的 AI CLI（Prompt 被忽略）vs 同一 CLI 加 Carror OS（被阻断） | "Prompt vs 物理。选择你的防御。" |
| 0:60-0:90 | 安装命令 + 最终"刹车已上"画面 | "30 秒。无需守护进程。无需云端。无需订阅。" |

### 演示 2："不止防御——Skill 武器库"（90-120 秒）

**目的**：展示 Carror OS 不仅是一个拦截器，更是一个完整的开发操作系统。

| 时间 | 场景 | 旁白 |
|------|-------|-----------|
| 0:00-0:15 | /lx-rpe 启动新特性流水线 | "Carror OS 也编排你的工作流。" |
| 0:15-0:30 | RPE 流水线：Research → Plan → Execute → Verify 进度 | "从规格到交付代码，每一步都有门禁。" |
| 0:30-0:45 | lx-code-review 检测并修复代码质量问题 | "自动审查，扼杀劣质代码。" |
| 0:45-1:00 | /lx-status 展示累积 Token 节省 | "每个会话都在累积你的节省。" |
| 1:00-1:20 | Error DNA 时间线：发现的 bug、已修复、已验证 | "错误模式被暴露和消除。" |
| 1:20-1:45 | 审计面板：跨会话完整追溯 | "每个操作可审计。每个声明可验证。" |
| 1:45-2:00 | 结束：Logo + "先守护，后武装" | "刹车已上。放心交付。" |

---

## 拍摄设置

### 环境
- **终端**：iTerm2，极简主题（深色背景）
- **字体**：JetBrains Mono Nerd Font（等宽，14pt）
- **窗口**：120x40 字符，无标题栏
- **背景**：桌面干净，无个人文件可见

### 采集设置
- **截图**：PNG，1920x1080 或 2x Retina
- **视频**：MP4，1920x1080 @ 30fps
- **工具**：CleanShot X (macOS) 或 OBS Studio
- **光标**：可见，默认指针（无自定义主题）

### 品牌
- 截图顶部栏：可选，右下角"Carror OS v6.1.9"水印
- 画面内无其他水印或 Logo
- 所有终端提示符使用默认 `$` 或 `%`

---

## 拍摄清单

- [ ] 终端字体/主题在所有画面中保持一致
- [ ] 任何画面中无个人/隐私信息可见
- [ ] 所有画面展示实际运行的 Carror OS（非模拟）
- [ ] 错误状态展示真实错误消息（非模拟）
- [ ] 时序/性能画面展示真实命令输出
- [ ] 演示 1：展示所有 P0 门禁
- [ ] 演示 2：至少展示 lx-rpe + lx-code-review + lx-status
- [ ] 音频：演示视频需干净的配音或文字说明
- [ ] 分辨率：所有素材至少 1920x1080
- [ ] 文件命名：`{category}-{id}-{description}.png`（例如 `gate-ss02-permission-block.png`）
