# CarrorOS 设计落地 — Research

## 1. 当前代码库完整分析

### 1.1 目录结构快照

```
Desktop/CarrorOS/
├── AGENTS.md                    ← 治理铁律 + L1/L2 工作流
├── CLAUDE.md                    ← 指向 AGENTS.md
├── 重构指导文档/                  ← 10 份设计文档（1.md~10.md）
│   ├── 1.md  IntakeGate         ← 任务入口与L1/L2分级
│   ├── 2.md  PlanBuilder        ← 计划生成器
│   ├── 3.md  PreActionGate      ← 动作级安全门
│   ├── 4.md  Executor Ledger    ← 执行证据账本
│   ├── 5.md  VerifyGate         ← 完成裁决门
│   ├── 6.md  Context Engine     ← 上下文水位/压缩/恢复
│   ├── 7.md  Oracle/Meta-Oracle ← 高阶复核
│   ├── 8.md  Fallback Protocol  ← 降级熔断
│   ├── 9.md  CLI Integration    ← 观测与执行接口
│   └── 10.md Archive/Sovereign  ← 最终归档
│
├── .claude/
│   ├── hooks/                    ← 11 个 .py hook
│   │   ├── carroros_hooklib.py       ← 共用库
│   │   ├── userprompt-level-hint.py  ← L2 关键词提示
│   │   ├── userprompt-session-resume.py  ← 引用了不存在的 context_engine.py
│   │   ├── pretool-action-gate.py    ← 部分命令拦截
│   │   ├── pretool-fallback-check.py ← stamp-only 桩
│   │   ├── pretool-plan-gate.py      ← 检查 plan.md 存在
│   │   ├── pretool-edit-scope.py     ← 检查 scope 冻结
│   │   ├── pretool-sensitive-edit.py ← 敏感路径检查
│   │   ├── posttool-audit.py         ← 审计记录
│   │   ├── posttool-completion-gate.py → Stop 事件上
│   │   └── statusline-command.sh     ← statusline
│   ├── scripts/                  ← 17 个脚本（6 个 symlink → .omc/scripts/）
│   │   ├── carros_base.py → .omc/scripts/carros_base.py
│   │   ├── intake_gate.py           ← 存在但 hooks 不调用
│   │   ├── plan_builder.py          ← 存在但 hooks 不调用
│   │   ├── context_watermark.py     ← 存在但 hooks 不调用
│   │   ├── oracle_gate.py           ← stub
│   │   ├── oracle_agent.py          ← stub
│   │   ├── meta_oracle.py           ← stub
│   │   ├── oracle_spawn.py          ← stub
│   │   ├── static_oracle_agent.py   ← stub
│   │   ├── runtime_oracle_agent.py  ← stub
│   │   ├── fallback_engine.py → .omc/scripts/fallback_engine.py
│   │   ├── fallback_matrix.py       ← 存在但 hooks 不调用
│   │   ├── carros_utils.py          ← 工具函数
│   │   ├── statusline.py            ← statusline 渲染
│   │   └── omc_lint.py → .omc/scripts/omc_lint.py
│   │
│   ├── settings.json            ← hooks 注册
│   ├── kernel.md                 ← 管理内核
│   ├── index.md                  ← 路由表
│   └── ...
│
├── .omc/
│   ├── scripts/                  ← 源码（54k LOC carros_base.py）
│   ├── audit/                    ← 审计 JSONL
│   ├── archive/                  ← 7 个 bench 归档
│   ├── state/                    ← 状态目录
│   ├── tasks/                    ← 任务文档
│   └── tokens/                   ← token 状态
│
└── 重构差距清单.md                ← 自行诊断的差距清单
```

### 1.2 Hook 注册现状（settings.json）
```json
{
  "hooks": {
    "UserPromptSubmit": [
      "userprompt-level-hint.py",
      "userprompt-session-resume.py"    // 引用不存在的 context_engine.py
    ],
    "PreToolUse": [
      "pretool-sensitive-edit.py",
      "pretool-action-gate.py",
      "pretool-fallback-check.py",     // stamp-only
      "pretool-plan-gate.py",
      "pretool-edit-scope.py"
    ],
    "PostToolUse": [
      "posttool-audit.py"
    ],
    "Stop": [
      "posttool-completion-gate.py"    // 应该在 PreToolUse 而非 Stop
    ]
  }
}
```

### 1.3 缺失的 Hook 注册
| 设计要求的 Hook | 当前状态 |
|---|---|
| SessionStart | **缺失** — 0 个注册 |
| VerifyGate (PreToolUse) | **在 Stop 上，不对** |
| Context Engine compact/resume | **context_engine.py 不存在** |
| Output compression | **完全缺失** |
| Archive check | **缺失** |
| Oracle gate | **缺失** |

### 1.4 关键调用链断裂

```
userprompt-session-resume.py
  → run_script("context_engine.py", ["resume-check", ...])
  → context_engine.py 不存在
  → subprocess returncode=127
  → hook_block("Resume: BLOCK context_engine_missing")
  → 每个新会话启动被阻塞
```

## 2. 设计文档代码状态对照

| 文档 | 设计代码 | 磁盘状态 | 差距 |
|------|---------|---------|------|
| 1.md §11 | `intake_gate.py` 1400 行 | 在 `.claude/scripts/` 存在但 hooks 不调用 | ⚠️ 未接入 hook 链 |
| 2.md §16 | `plan_builder.py` 1460 行 | 存在但 hooks 不调用 | ⚠️ 未接入 hook 链 |
| 3.md §11 | `pre_action_gate.py` 1200 行 | 存在但 hooks 有简化版 | ⚠️ hooks 版本和设计文档不一致 |
| 4.md §13 | `executor_ledger.py` 1180 行 | 不存在 | ❌ |
| 5.md §12 | `verify_gate.py` ~500 行 | 不存在 | ❌ |
| 6.md §13 | `context_engine.py` 1200 行 | **不存在** | ❌ 生产断裂 |
| 7.md §14 | `oracle_engine.py` ~600 行 | 在 `.omc/scripts/` 有但 hooks 不调用 | ⚠️ |
| 8.md §17 | `fallback_engine.py` 1100 行 | 存在但 hooks 版本是 stamp-only | ⚠️ |
| 9.md §8 | `statusline.py` 650 行 | 存在且有效 | ✅ |
| 10.md §11 | `archive_engine.py` 1150 行 | 存在但 hooks 不调用 | ⚠️ |

## 3. 验证系统现状

`feature_verify.py` 的 63 条检查分布：
- 11 条 `lambda: True`（永远通过，不检查任何东西）
- 52 条 grep 源码关键字（只在 .py 文件里搜字符串，不检查运行时行为）
- 0 条真正运行 hook 测试运行时行为

`randomized_bench.py` 的问题：
- 每次迭代之间 `rm -rf .omc/tasks/* .omc/archive/* .omc/tokens/*` 清理中间状态
- 7 个 archive 目录的时间戳全部是同一时刻 → 一次批量运行，不是 30 次随机迭代
- bench 调用的是 carros_base.py bench 内部函数，不是 hooks 链

## 4. 技术方案

### 4.1 架构原则
1. 每个引擎独立文件：`.claude/scripts/<engine>.py`
2. 每个引擎一个 hook：`.claude/hooks/<hook>.py`（调用对应引擎）
3. 所有引擎遵循设计文档中的 spec 代码
4. hooks 通过 settings.json 注册到正确事件点

### 4.2 Hook 返回值规范
```python
# 允许
{"continue": True, "message": "...", "output_additional_context": [...]}
{"continue": False, "message": "BLOCK: reason"}

# 禁止
{"continue": True, "message": "VERIFIED"}  # hook 不输出完成事实
```

### 4.3 Engine CLI 规范
```bash
python3 .claude/scripts/<engine>.py <command> --token <path> --task <path>
# 输出 JSON
# 0 = 允许/OK, 1 = 阻塞/警告, 2 = 错误
```

### 4.4 session-handoff.md 路径
```
.omc/tasks/{date}/{task}/state/session-handoff.md
```

### 4.5 强验证原则
- 验证必须实际运行目标代码（调用 hook, 检查 stdin/stdout）
- 不允许 `lambda: True` 豁免
- 不允许 grep 源码替代运行时验证

## 5. 约束

1. Python 3.10+ 标准库，禁止第三方依赖
2. hooks 只做路由/观察/门禁，不产生完成事实
3. 所有引擎必须写 audit 事件
4. 路径对齐：`.omc/tokens/`, `.omc/tasks/`, `.omc/audit/`, `.omc/archive/`
5. 不改 AGENTS.md / kernel.md / index.md（铁律 6）

## 6. 风险

| 风险 | 可能性 | 影响 | 缓解 |
|------|--------|------|------|
| context_engine.py 实现不匹配 hooks 调用格式 | 中 | 🔴 生产中断 | Phase 0 先在测试环境 mock 调用验证 |
| VerifyGate 误拦截正常写操作 | 中 | 🟡 开发流阻塞 | 白名单 plan.md/executor.md/token.json 写操作 |
| 重构中断已有功能 | 中 | 🟡 开发流阻塞 | 每个 Phase 后运行验证 |
| 旧 carros_base.py 与新引擎冲突 | 低 | 🟡 配置混乱 | 新引擎走 `.claude/scripts/` 独立路径 |

## 7. 建议路径

按生产风险降序实施：
1. Phase 0：修复 context_engine.py 断裂（最紧急）
2. Phase 1：VerifyGate 正确拦截（最关键）
3. Phase 2：Output Compression（节省上下文）
4. Phase 3：Fallback 熔断（安全网）
5. Phase 4：Context Engine 完整（长期任务）
6. Phase 5-7：Oracle/Archive/PreActionGate（L2 功能）
7. Phase 8：验证系统重建

## 8. 待确认问题

- **接受 SessionStart 修正**（已确认）：`userprompt-session-resume.py` 应改为 `SessionStart` 钩子，移除 stamp 补丁
- **旧 `.omc/scripts/carros_base.py` 保留还是迁移？**：现有 54k LOC 的单体脚本，新引擎走 `.claude/scripts/` 独立路径，逐步取代
- **L2_ENHANCE Oracle 是否需要高阶模型？**：oracle_engine.py 可跑在任何模型上（评分靠预设规则），但 Multi-Judge 的设计意图是高阶模型
- **opencode/ 观测是否启用？**：SQLite observer 需要配置 `OPENCODE_SQLITE_PATH`，这个先不动
