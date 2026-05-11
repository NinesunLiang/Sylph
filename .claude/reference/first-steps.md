# Carror OS 快速上手（5 步）

> 5 步上手，即刻获得 AI 防御 + 技能体系

## Step 1: 确认安装

```bash
# 查看版本
cat VERSION.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('version','?'))"

# 查看健康状态 — 确认所有组件运转正常
/lx-status
```

## Step 2: 提交第一个任务

直接说你的需求即可。Carror OS 会：
- 自动判断难度（L1/L2/L3/L4）
- 选择对应的 Skill 处理
- 执行完成后自动提供 VERIFIED 证据

**示例**：
```
帮我创建一个 user-login 功能模块，含注册和登录接口
```

## Step 3: 查看进度和状态

```bash
# 健康面板 — 当前系统运行状态
/lx-status

# 查看当前所有活跃任务
/omc-todo
```

## Step 4: 使用技能体系

Carror OS 内置 23 个技能（skill），通过自然语言触发：

| 场景 | 触发语 | 说明 |
|------|--------|------|
| 系统性功能开发 | `/lx-rpe new 功能名 需求描述` | 9 步闭环开发流程 |
| 代码审查 | 说"审查代码"或"review this" | 自动调用 lx-code-review |
| PRD 拆解 | 说"拆解需求"或`/lx-oma-hier 路径` | 按功能域 MECE 拆解 |
| 安全扫描 | 说"安全检查" | 自动调用 lx-security-review |
| 技术调研 | 说"研究一下"或"research" | 自动阅读代码 + 输出调研文档 |

## Step 5: 理解防御机制

系统有 7 条铁律自动保护你：

| # | 铁律 | 表现 |
|---|------|------|
| 1 | 禁止编造 | AI 每个断言都引用 file:line，找不到就说"需验证" |
| 2 | 用户裁定 | 验收/选型由你决定，AI 不自判 |
| 3 | 证据门禁 | 说"完成"前必须提供 VERIFIED 证据 |
| 4 | Git 门禁 | 任何 commit/push 前先报告，等你批准 |
| 5 | 范围冻结 | 只改当前任务文件，额外发现记 TODO |
| 6 | 隐私防线 | 绝不读取 .env/私钥 |
| 7 | 断言真实 | 所有评分/百分比必须有来源 |

---

遇到问题直接问 AI，它会使用上下文守卫自动管理上下文长度。
