# Oracle Dual Agent Refactor — 重构方案 v1

> 目标：将 `oracle_agent.py` + `meta_oracle.py` 从「孤岛脚本」重构为真正可被 pipeline 消费的双 Agent 评审系统。
>
> 状态：方案文档，待高阶模型审核后执行。

---

## 1. 现状分析

### 1.1 现有文件体系关系

| 文件 | 行数 | 角色 | 是否被调用 |
|------|------|------|-----------|
| `oracle_gate.py` | 138 | 规则匹配门禁（trigger→verdict），走 pre/post hook 链 | ✅ 是（hook 事件驱动） |
| `oracle_agent.py` | 212 | 独立第三方审核（新写） | ❌ 否 |
| `meta_oracle.py` | 433 | 二阶评审评分器（新写） | ❌ 否 |
| `carros_base.py` | 1549 | L1 核心状态机 | ✅ 是（主 CLI） |

### 1.2 现有 Bug 清单

**oracle_agent.py:**

1. **Agent 连通性检测失效** (L50-56)：用 `claude -p echo ready` 做连通性检测，`-p` 不是 query 模式，会阻塞等到 timeout → 永远返回 `None` → 永远走 `local_review` 空转路径
2. **`local_review` 空转** (L74-87)：无 agent 时只打印 prompt 到 stdout，等主 agent 自己审自己。`_save_verdict` 写 `"status": "pending"`，但永远没人更新 → 裁决字段永远 pending
3. **无 task_id 追踪** (L110-162)：`cmd_review` 只有 `--target`(文件路径/描述)，没有 `--task-id` 参数 → 无法与 token pipeline 关联
4. **Bypass 机制不消费** (L176-184)：文件写入 BYPASS_DIR 后，没有任何 pipeline 步骤检查它 → 功能空壳

**meta_oracle.py:**

5. **TOKENS_DIR 路径截断** (L19)：`Path("...ns")`，本应是 `.omc/tokens`。fallback 逻辑 `[TOKENS_DIR, Path(".omc/tokens")]` 碰巧兜住了但这是意外不是设计
6. **_find_plan_for_task glob 深度不够** (L70)：`rglob(f"*/{task_id}/plan.md")` 只匹配一层目录，实际路径是 `.omc/plan/{date}/{taskid}_{time}/plan.md`（两层）→ 匹配不到
7. **G2 正则脆弱** (L129-130)：`r'`([^`]+\.\w+)`'` 从 markdown code block 提取文件名，URL/log 中的点号也会被匹配 → 假阳性
8. **无异常处理**：`_ensure_dirs()` 失败直接崩；`_load_json` 的 FileNotFound 静默吞掉

---

## 2. 重构设计

### 2.1 总体架构

```
carros_base.py verify ──→ oracle_agent.py review ──→ .omc/state/oracle-verdicts/
                              ↓ (pass)
                      meta_oracle.py score ──→ .omc/state/meta-oracle-verdicts/
                              ↓ (pass)
                      carros_base.py verify 继续
```

**核心原则：**
- `oracle_agent.py` = 一级评审（内容审核），`meta_oracle.py` = 二级评审（门禁评分）
- 两者通过 `.omc/state/` 下的同一 `task_id` 关联
- `carros_base.py verify`（默认）或 `carros_base.py gate oracle`（手动）触发链路
- 每个 agent 输出固定 JSON 格式到独立 verdicts 目录

### 2.2 Oracle Agent 重构

**定位变更：** 废除 agent_spawn 和 local_review 两条路——统一改成本地静态分析 + 引用检查 + 安全规则匹配。

**新命令格式：**
```bash
# 核心
python3 .claude/scripts/oracle_agent.py review --target <path> [--task-id <id>] [--strict]

# bypass 管理
python3 .claude/scripts/oracle_agent.py bypass list          # 列出活跃 bypass
python3 .claude/scripts/oracle_agent.py bypass create <id>   # 创建 24h bypass
python3 .claude/scripts/oracle_agent.py bypass check <id>    # 检查 bypass 状态
python3 .claude/scripts/oracle_agent.py bypass cleanup       # 清理过期 bypass

# 状态查看
python3 .claude/scripts/oracle_agent.py status               # 24h 内裁决概览
```

**输出 JSON 格式（版本化）：**
```json
{
  "version": 2,
  "task_id": "20260707-fix-xxx",
  "target": ".claude/scripts/foobar.py",
  "verdict": "ACCEPT|REJECT|ADVISORY",
  "safety": "HIGH|MEDIUM|LOW",
  "architecture_score": 8,
  "evidence_score": 7,
  "reasons": ["说明1", "说明2"],
  "checks": {
    "file_line_evidence": {"pass": true, "count": 5},
    "cmd_output_evidence": {"pass": true, "count": 2},
    "dangerous_pattern": {"pass": true, "matched": []},
    "scope_violation": {"pass": true, "outside_files": []}
  },
  "timestamp": "2026-07-07T01:00:00Z"
}
```

**核心功能拆解：**

1. **静态分析**（替代废弃的 agent_spawn）
   - 读目标文件/目录
   - 匹配安全规则（复用 `oracle_gate.py` 的 TRIGGER_RULES 配置）
   - 检查文件行引用格式（`file:line`）
   - 检查命令输出标记（`exit code`, `PASS/FAIL`）
   - 模式匹配无需 LLM 调用

2. **Bypass 机制全链路**
   - `create`：写 `{BYPASS_DIR}/{task_id}_approved.md` + 时间戳
   - `check`：读文件 + 对比 TTL，返回 bool
   - `cleanup`：批量删除过期文件
   - `list`：展示活跃 bypass 有效期
   - `carros_base.py verify` 在 run oracle 前自动 `bypass check`

3. **task_id 追踪**
   - `--task-id` 参数写入裁决字段
   - 使用 `_find_token_for_task()`（从 meta_oracle 移植过来改好）

**删除或废弃的代码：**
- `_find_available_agent()` — 废弃，不再 spawn
- `_spawn_agent_review()` — 废弃
- `_local_review()` — 废弃

### 2.3 Meta-Oracle 重构

**定位：** 对已完成任务做 G1-G4 门禁评分，输出加权分数 + 详细检视。

**修掉的 bug：**
| # | 位置 | 修复 |
|---|------|------|
| 5 | L19 | `TOKENS_DIR = Path(".omc/tokens")` |
| 6 | L70 | `plan_dir.rglob(f"**/{task_id}/plan.md")`（双星号递归） |
| 7 | L129-130 | 精确模式匹配，过滤 URL 和 log 路径 |
| 8 | 全文件 | 加 try/except + 友好错误信息 |

**改进的评分算法：**

```
final_score = G1 * 0.35 + G2 * 0.25 + G3 * 0.20 + G4 * 0.20
verdict = ACCEPT if final_score >= 8.0 and all(g.pass for g in gates)
verdict = REJECT if final_score < 5.0 or any_critical_failure
verdict = ADVISORY otherwise
```

**G1-G4 门禁实质性改进：**

| 门禁 | 当前 | 改进后 |
|------|------|--------|
| G1 证据质量 | 纯文本正则匹配 `file:line` | 交叉验证：executor.md 引用行数 ←→ 目标文件实际存在+行内数值合理 |
| G2 范围冻结 | 正则提取反引号内路径 | 用精确 glob + 排除.git/claude/omc 等 | 
| G3 验收 | 搜索"VERIFIED"字符串 | 检查 `.omc/state/audit/` 的 verify 事件记录 + token 中的 `verification_count` |
| G4 哲学一致性 | IKIAI/软完成语检查 | 加入对 AGENTS.md 灵魂 7 条的具体匹配（零信任、文档、增益） |

**命令格式：**
```bash
# 单任务评分
python3 .claude/scripts/meta_oracle.py score --task <task-id> [--strict]

# 全量评分
python3 .claude/scripts/meta_oracle.py score --all

# 审计报告
python3 .claude/scripts/meta_oracle.py audit [--days 7] [--threshold 6.0]

# 单步验证
python3 .claude/scripts/meta_oracle.py verify --step S1 [--token <path>]
```

### 2.4 Pipeline 集成

#### carros_base.py 改动

在 `cmd_verify()` 中增加 oracle 检查步骤：

```python
def cmd_verify(step_id=None, skip_oracle=False):
    # ... 现有逻辑 ...
    
    # 新增：Oracle 检查（除非跳过）
    if not skip_oracle:
        oracle_ok = _run_oracle_check(task_id)
        meta_ok = _run_meta_oracle_check(task_id)
        if not oracle_ok:
            print(_yellow("⚠  Oracle: ADVISORY/REJECT — 建议确认后继续"))
            # 不硬阻断，只 warn（L1 流程可以带警告继续）
    
    # ... 继续现有 verify 逻辑 ...
```

新增辅助函数（~30 行，追加到 `carros_base.py`）：

```python
def _run_oracle_check(task_id):
    """调用 oracle_agent.py 做审核，返回 True=通过/False=有问题"""
    import subprocess
    oracle_script = _SCRIPT_DIR / "oracle_agent.py"
    target = str(PLAN_PATH.parent) if PLAN_PATH else "."  # 默认审 plan 目录
    cmd = [sys.executable, str(oracle_script), "review", "--target", target, "--task-id", task_id]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False
        result = json.loads(r.stdout)
        return result.get("verdict") in ("ACCEPT", "ADVISORY")
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        # oracle 不可用时不阻断流程
        return True

def _run_meta_oracle_check(task_id):
    """调用 meta_oracle.py 做评分"""
    # 类似 _run_oracle_check 但调用 meta_oracle.py score --task
```

#### AGENTS.md 路由表改动

在当前 AGENTS.md 末尾追加：

```markdown
## 评审系统（新增）
- Oracle Agent: `python3 .claude/scripts/oracle_agent.py review --target <path> [--task-id <id>]`
  - 一级审核：内容安全 + 引用检查 + 安全规则
  - Bypass: `oracle_agent.py bypass create/check/cleanup`
  - 裁决目录: `.omc/state/oracle-verdicts/`

- Meta-Oracle: `python3 .claude/scripts/meta_oracle.py score --task <task-id>`
  - 二阶评分：G1-G4 门禁 (证据/范围/验收/哲学) 
  - 审计: `meta_oracle.py audit --days 7`
  - 裁决目录: `.omc/state/meta-oracle-verdicts/`

- 全链路: `python3 .claude/scripts/carros_base.py gate oracle`
  - 等价于: oracle_agent.py review → meta_oracle.py score
```

---

## 3. 文件变更清单

### 修改文件 (3)

| 文件 | 变更类型 | 预计行数 |
|------|---------|---------|
| `.claude/scripts/oracle_agent.py` | 重写（140→180 行） | ~180 |
| `.claude/scripts/meta_oracle.py` | 修复+优化（433→300 行） | ~300 |
| `.claude/scripts/carros_base.py` | 追加+2 函数 + gate 命令 | +80 |
| `AGENTS.md` | 追加路由表 | +15 |

### 不变文件 (4)

| 文件 | 原因 |
|------|------|
| `.claude/scripts/oracle_gate.py` | 独立 hook，不参与双 agent 体系 |
| `.claude/scripts/carros_utils.py` | 辅助函数已稳定 |
| `.omc/state/oracle-verdicts/` | 目录结构不变，裁决写入目标 |
| `.omc/state/oracle_bypass/` | 目录结构不变 |

---

## 4. 验收标准

### 4.1 单元级验收

```
$ python3 .claude/scripts/oracle_agent.py review --target .claude/scripts/carros_base.py --task-id test-001
→ 输出 JSON 含 version=2, task_id="test-001", 4 个 checks 全部 pass/false

$ python3 .claude/scripts/oracle_agent.py bypass create test-001
→ "Bypass created for test-001 (24h)"

$ python3 .claude/scripts/oracle_agent.py bypass check test-001
→ true (或 false 如果过期)

$ python3 .claude/scripts/meta_oracle.py score --task test-001
→ 输出 JSON 含 G1-G4 各 pass/score/reasons + final_score + verdict

$ python3 .claude/scripts/carros_base.py gate oracle
→ 输出: Oracle [ACCEPT] → Meta-Oracle [ADVISORY] → 全部通过/不通过
```

### 4.2 回归验收

- `carros_base.py bench 01_doc_update`（不跑 oracle 检查时行为不变）
- `carros_base.py bench 07_archive`（完整 L1 闭环不受影响）
- 所有 `.omc/tokens/` 下的 token 文件不被 side effect
- 已归档的任务不会触发 oracle 检查

### 4.3 边界验收

- 无 `.omc/tokens/` 目录时：oracle bypass check 返回 false，不崩溃
- 无 executor.md 时：`meta_oracle.py verify --step S1` 返回 G1=0/pass=false，不崩溃
- bypass 文件为空时：`bypass check` 返回 false
- `--target` 不存在的文件：返回 `REJECT` + 原因

---

## 5. 执行步骤

```
Step S1: 重写 oracle_agent.py
Step S2: 修复+优化 meta_oracle.py
Step S3: carros_base.py 追加 oracle 集成
Step S4: AGENTS.md 路由表更新
S-Verify: 执行验收标准中的所有测试
S-Archive: 归档方案文档
```
