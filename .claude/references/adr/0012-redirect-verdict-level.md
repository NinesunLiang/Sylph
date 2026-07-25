# ADR-0012: 新增 REDIRECT oracle 判决级别

## 状态

**已实现**（2026-07-25）

## 背景

当前 oracle_classify 有五级判决：PASS / FORCE / TRIGGER / ESCALATE / BLOCK。

BLOCK 返回 `{"continue": false, "reason": "..."}`，硬拦截工具调用。AI 知道被拦，但不知道「怎么做才对」。这导致：

1. AI 卡住或绕行，效率下降
2. 人类不知道发生了什么（需翻日志）
3. 反模式知识（anti-patterns）没有被系统消耗，只存在于 .md 文件中

## 决策

在 oracle_classify 判决级别中新增 **REDIRECT** 级别：

```
PASS → REDIRECT → FORCE/TRIGGER → ESCALATE → BLOCK
                   ↑ 新增
```

### REDIRECT 的行为契约

| 属性 | 值 |
|:----|:----|
| continue | false（仍然阻止本次工具调用）|
| 输出 | `reason`（为什么被拦）+ `redirect_guidance`（正确做法）|
| AI 可见性 | 阻止后 AI 在上下文中看到 guidance，可自行修正重试 |
| 人工介入 | 不需要。零人工等待 |
| 落盘日志 | `.omc/redirects.jsonl` — 记录每次 REDIRECT 事件 |

### REDIRECT 触发条件

按优先级匹配，命中最先匹配的规则即生效：

| 优先级 | 数据源 | 匹配方式 | 示例 |
|:------|:-------|:---------|:-----|
| P0 | 硬编码反模式规则 | tool 命令/参数精确匹配已知反模式 | `\n` 换行分割命令、`cd` 空转 |
| P1 | anti-pattern-redirects.jsonl（动态加载） | 飞轮升华时 stop-flywheel 写入 | 升华后的反模式自动转化为 REDIRECT 规则 |
| P2 | action-loop NARROW (连续 3 次) | 同一工具操作反复执行但未到 BLOCK 阈值 | 第 3 次同类操作重试 → REDIRECT |
| P3 | action-loop REDIRECT (连续 4 次→BLOCK) | REDIRECT 后 AI 继续同一模式 | 第 4 次升级为 BLOCK 硬拦截 |

### REDIRECT 与现有机制的关系

```
BLOCK → 仅拦截，无指引。保留给高危操作（rm -rf /、git push --force 等）
REDIRECT → 拦截 + 指引。适用于反模式、行为错误、常见踩坑
ESCALATE → 上报人类。保留给不确定/权限外
PASS    → 无条件放行
```

### 输出格式

BLOCK 现有格式：
```json
{"continue": false, "reason": "Blocked: action loop detected"}
```

REDIRECT 输出格式：
```json
{
  "continue": false,
  "verdict": "REDIRECT",
  "reason": "终端命令使用了换行符，会导致多行分割解析",
  "redirect_guidance": "将多行命令改为 && 连接的单行:\n  × 错误:\n    cd dir\n    python script.py\n  ✓ 正确:\n    cd dir && python script.py"
}
```

## 理论依据

1. **符合 CarrorOS 哲学**：治理的核心是纠正行为，不是惩罚。REDIRECT 是「纠正+继续」的治理实现
2. **不违反铁律**：AI 仍是自主决策（红绿文件分离不受影响），REDIRECT 是 oracle 级别的指导，不是人类介入
3. **符合原有架构**：不新增 hook 类型，不在 pretool-gate.py 外增加代码，仅在 oracle 判决链加一个分支
4. **ROI 高**：核心逻辑修改 ≈ 40 行代码（判决分支 + guidance 映射表），不需要改动 settings.json、hook 注册、输出格式 schema 等

## 实现细节

### pretool-gate.py 改动（5 处，净增 ~100 行）

1. **新增 `_redirect()` 函数**（L~290）：`continue: False` + `additionalContext`（reason + guidance）+ `.omc/redirects.jsonl` 日志
2. **新增 4 条硬编码反模式规则**（P0）：multi_cmd_newline / redundant_file_probe / gov_file_bypass / cd_churn，各带中文 guidance
3. **新增 `_load_anti_pattern_redirects()` 动态加载器**：从 `.omc/state/anti-pattern-redirects.jsonl` 懒加载（TTL 300s），读取 stop-flywheel 升华时写入的规则
4. **`_oracle_classify()` 扩展**：反模式匹配 → REDIRECT 判决（在 BLOCK 之后、ESCALATE 之前），先硬编码规则再动态规则
5. **action-loop 升级链重构**：NARROW(1-2次) → REDIRECT(3次, 拦截+指引) → BLOCK(4次, 硬拦截)

### stop-flywheel.py 改动

- 升华逻辑扩展：每次升华到 anti-patterns.md 时，自动写入一条 REDIRECT 规则到 `.omc/state/anti-pattern-redirects.jsonl`
- `_to_redirect_rule()` 工具函数：将 pattern_key + guidance 转译为 pretool-gate 可消费的格式

### 反模式规则验证

12 个场景通过单元测试：

| 场景 | 预期 | 结果 |
|:-----|:----|:-----|
| cd_churn | REDIRECT | ✅ |
| multi_cmd_newline | REDIRECT | ✅ |
| gov_file_bypass | REDIRECT | ✅ |
| redundant_file_probe | REDIRECT | ✅ |
| safe command (ls/py/git) | PASS | ✅×3 |
| env_bypass | BLOCK | ✅ |
| rm -rf / | PASS(oracle层, action_gate拦截) | ✅ |
| release_trigger | TRIGGER | ✅ |
| force_auth | FORCE | ✅ |

## 风险

| 风险 | 缓解 |
|:----|:------|
| AI 不理会 guidance 继续犯错 | 累计 REDIRECT 次数 → 达到阈值自动升级为 BLOCK（action-loop 4次 → BLOCK） |
| guidance 内容过于笼统无帮助 | 初始 4 条 P0 规则全部对应真实反模式；动态规则自动产生 |
| LOC 增加维护成本 | REDIRECT 逻辑集中在 oracle 判决分支的 `_ORACLE_ANTI_PATTERN_RULES` + `_load_anti_pattern_redirects()`，不散落 |

## 后续

- 动态规则加载器已就绪；数据源（stop-flywheel 升华）存在但需运行一段时间积累
- 当前 4 条硬编码规则覆盖 E 系列最常见的反模式；I/J 系列由动态规则补充
- 累计 REDIRECT 事件数待达到阈值后评估是否需向 oracle 判决阈值反哺

## 参考

- `pretool-gate.py` — `_redirect()` / `_oracle_classify()` / `_load_anti_pattern_redirects()` / `_check_action_loop()`
- `stop-flywheel.py` — `_to_redirect_rule()` / `_sublimation_check()`
- `anti-patterns.md` — guidance 数据源
- `anti-pattern-redirects.jsonl` — 动态规则持久化文件
