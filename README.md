# CarrorOS — 治理体系

继承自 CarrorOS 哲学传统，以 round3 重构方案为唯一设计源的全新治理系统。

## 核心架构

任务等级：
```
L1:    Plan → Step → Verify → Archive
L2 : Base + Context Watermark + Low-frequency Oracle + Learning Flywheel
```

使用场景：
```
base: 轻度治理，简单工作流，无复杂环结构，deepseek-v4-flash/qwen3.7-plus 等中低阶模型驱动；
enhence: 全量治理，可以复杂工作流，可以有复杂loop, opus4.6+/gpt5.5+ 等高阶模型驱动；
```

### 10 模块降级为内部实现

| 模块 | 角色 | 暴露为 |
|------|------|--------|
| IntakeGate | 任务入口分类 | carros_base.py init |
| PlanBuilder | 计划冻结 | 模板 plan.md |
| PreActionGate | 安全门禁 | pretool-action-gate.py hook |
| Executor Ledger | 执行证据 | executor.md 模板 |
| VerifyGate | 完成门 | carros_base.py verify |
| Context Engine | 上下文管理 | 水位阈值配置 |
| Oracle | 高阶复核 | 低频触发（仅 L2）|
| Fallback | 降级熔断 | 内部裁决器 |
| CLI | 观测接口 | carros_base.py status |
| Archive | 归档封存 | carros_base.py archive |

## 快速开始

```bash
# 1. 初始化任务
python3 .claude/scripts/carros_base.py init --task-id my-task-001

# 2. 查看状态
python3 .claude/scripts/carros_base.py status

# 3. 每 tick 递增
python3 .claude/scripts/carros_base.py tick

# 4. 验证 step
python3 .claude/scripts/carros_base.py verify --step S1

# 5. lint 检查
python3 .claude/scripts/carros_base.py lint

# 6. 归档
python3 .claude/scripts/carros_base.py archive

# 7. 跑 bench 测试
python3 .claude/scripts/carros_base.py bench
```

## 平台支持

| 平台 | 状态 |
|------|------|
| Claude Code | ✅ hooks 注册 |
| OpenCode | ✅ plugin |
| 独立 CLI | ✅ carros_base.py |
| macOS | ✅ 已测试 |
| Windows/WSL | ✅ pathlib 路径 |
| Linux | ✅ |

## 目录结构

```
CarrorOS/
├── AGENTS.md                    # 核心入口
├── .claude/                     # 可复用核心资产
│   ├── scripts/                 # python脚本
│   ├── references/              # 渐进式披露md文档库
│   ├── hooks/                   # 6 个 CC hooks
│   ├── nodes/                   # 原子化节点
│   ├── schemas/                 # 原子化接口
│   ├── settings.json            # CC hooks 注册
│   ├── harness.yaml             # hook 开关表
│   ├── kernel.md                # 冻结规则+飞轮入口
│   ├── claude-next.md           # 范式经验学习
│   └── index.md                 # 渐进披露注册表
├── .omc/
│   ├── tasks/{date}/{task_name}/{research|plan|executor|stats/|sub_tasks/}                       # 任务文档系统
│   └── tasks/{date}/{task_name}.json                       # 任务令牌系统，含有终端id信息
└── opencode/                    # OpenCode plugin
```

## 规则

见 AGENTS.md（8 铁律 + 哲学 7 条 + 路由规则）。

## 设计源

所有设计源自 `~/Desktop/重构3/round3/`。CarrorOS 作为材料和对照组保留。

## 文档系统

任务系统：.omc/tasks/{data}/{task_name}/[ research.md | plan.md | executor.md |  sub_tasks/ |state/ ] 

token系统：.omc/tokens/{data}/{task_name}.json // 所有的和会话级别的token存这里，如：goal\无人模式\ai任务

子任务系统：.omc/tasks/{data}/{task_name}/sub_tasks/{sub_task_name}/[ research.md | plan.md | executor.md] 

子任务令牌系统：.omc/tasks/{data}/{task_name}/sub_tasks/tokens/{sub_task_name}.json

rpe文档系统：rpe/{feature_name}/[ research.md | plan.md | executor.md ｜ state/ ] // rpe模式一般不走无人模式，不需要令牌;

# test change
# test
# track test
# test
