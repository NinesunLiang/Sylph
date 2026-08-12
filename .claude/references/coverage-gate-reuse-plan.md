# Coverage Gate 复利计划

> 目的：让 `scripts/test-coverage-gate.py` 从"手动看一眼覆盖率"的单次工具，变成嵌入多个治理节点的自动检查器，每个节点自动获益（复利效应）。

---

## 1. 当前状态

### 1.1 做了什么

`scripts/test-coverage-gate.py:1-211` 是一个自包含的 Python 脚本：

- 内置 56 项机制的注册表（`.py:30-91`），每项标注名称、类型（hook/script/skill/gate/meta/lib）、源文件路径模式、对应测试文件 hint
- 调用 `_find_test_file()`（`.py:94-122`）在 `scripts/`、`.claude/hooks/tests/`、`scripts/test-*` 三个目录中查找测试文件
- 调用 `_auto_discover_mechanisms()`（`.py:140-158`）扫描 `.claude/hooks/` 下未注册的 `.py` 文件，查找是否有测试文件通过**子串匹配**关联
- 输出 `Covered/Total` 百分比（`.py:187`）和未覆盖列表（`.py:192-195`）
- `--block` 模式：exit=2 时阻断（`.py:199-201`）
- 报告模式：有未覆盖项 exit=1，全过 exit=0（`.py:203,206`）

### 1.2 当前集成点

仅在 `scripts/run-regression.sh:105` 作为 12 套件之一运行：

```bash
run_suite "coverage-gate" "coverage"  bash -c 'python3 scripts/test-coverage-gate.py; exit 0'
```

**关键问题**：`; exit 0` 吞掉了 exit code，回归永远 PASS，覆盖门永不阻断。

### 1.3 现有优势

- **零外部依赖** — 纯 `pathlib` + `sys`，无第三方包
- **两种发现机制** — 注册表（精确）+ 自动发现（兜底防遗漏）
- **语义清晰** — exit code 区分 0/1/2，调用者可按需解读
- **已有 38 个测试文件** — 覆盖 45/56 ≈ 80%，gap 仅剩 11 项

### 1.4 现有 gap

| 缺口 | 严重度 | 说明 |
|------|--------|------|
| 11 项未覆盖机制 | medium | 硬阻性不够，已 3 个月无新增测试 |
| 注册表与 hooks 目录有双重维护成本 | low | 新增 hook 必须同步更新注册表 |
| `; exit 0` 吞掉了阻拦能力 | high | 回归中 coverage gate 形同虚设 |
| 没有写入审计链 | low | 谁什么时候违规引入无测试机制无记录 |

---

## 2. 复利机会

### Option A — Scorecard 提分前置门禁（推荐：第一优先级）

**概念**：每次 scorecard 提分前自动跑 `--block`，无测试覆盖则拒分。

**当前机制**：`evaluation-framework.md:73-77` 规定每次提分需要 "回归全过 → 写 scorecard.md"，但 coverage gate 没有被纳入回归的必要条件。

**实现方式**：

1. 修改 `scripts/run-regression.sh:105`：去掉 `; exit 0`，让 coverage gate 真正决定回归通过
    
    ```bash
    # 改前: run_suite "coverage-gate" "coverage"  bash -c 'python3 scripts/test-coverage-gate.py; exit 0'
    # 改后: run_suite "coverage-gate" "coverage"  python3 scripts/test-coverage-gate.py --block
    ```
    
2. 在 `evaluation-framework.md` Layer 1 的规则中（`.md:62-66`）增加一条：
    
    ```
    - 回归必须包含 coverage-gate --block 且 exit=0
    - 新增机制必须附测试文件，否则 scorecard 对应轮次自动拒分
    ```
    

**改动量**：2 个文件（run-regression.sh + evaluation-framework.md）≈ 10 行

**影响**：每次提分自动验证覆盖率无退步，新增机制不写测试则无法打分。这是最直接的复利 — 不修改 coverage gate 本身，只去掉它的缰绳。

**风险**：有些机制（如 `meta_oracle`、`lx-goal`）可能是元治理工具，不易拆出独立测试。需要为真正的"不可测试"机制开一个显式放行机制（见 §4.2）。

---

### Option B — Git Pre-Commit Hook（推荐：第二优先级）

**概念**：`git commit` 时自动检测新增了 hook/script 但未附带测试文件。

**当前机制**：项目已有 `lx-pre-commit` skill（`.claude/skills/lx-pre-commit/`），当前支持 `settings.json` hook。不需要 hook-launcher 集成，只需在 pre-commit 阶段加一个脚本调用。

**实现方式**：

1. 在 `.claude/hooks/` 下新增 `pre-commit-coverage-gate.py`：
    - 读取 `git diff HEAD --name-only` 获取 staging 中新增的 `.py` 文件
    - 对每个在 `.claude/hooks/` 或 `.claude/scripts/` 目录下的新增文件，检查是否有 `test-<filename>` 存在
    - 如有未覆盖新增文件，以 `--block` 模式 exit=2，阻止 commit

**脚本示例逻辑**（伪代码）：

```python
staged = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=A"])
for f in staged.stdout.split():
    if f.startswith(".claude/hooks/") and f.endswith(".py"):
        name = Path(f).stem
        if not any(Path("scripts").glob(f"test-{name}.*")):
            print(f"BLOCKED: 新增 hook {f} 无测试文件")
            sys.exit(2)
```

**改动量**：1 个新文件 ≈ 40 行 + 无需修改 settings.json（pre-commit 通过 git hook 注册）

**影响**：从源头阻止"新机制无测试"的情况。新人对代码库不熟悉时也能自动得到提示。

**风险**：
- 本地 git hook 需要手动安装（`git config core.hooksPath`），不在 `.claude/settings.json` 管理范围内
- 过于激进的阻塞可能导致开发者绕路（`--no-verify`），甚至去掉 hook

---

### Option C — 回归套件升级：全覆盖套件分离 + 覆盖率作为硬阻（推荐：第一优先级的子操作）

**概念**：将 coverage gate 从"12 套件"之一提升为回归的全局前置/后置条件。

**当前状态**：`scripts/run-regression.sh:105` 中 coverage gate 被非阻塞地跑在第 11 个，且被 111-124 行的全覆盖套件覆盖了大部分测试。

**实现方式**：

1. 在 `run-regression.sh` 开头（stash 之后、`run_suite` 之前）加：
    
    ```bash
    echo "---"
    echo "[coverage-gate] 前置检查: 所有机制是否有测试覆盖"
    if ! python3 scripts/test-coverage-gate.py --block; then
        echo "ERROR: 覆盖率门未通过，请补写测试或注册显式跳过" >&2
        exit 2
    fi
    ```
    
2. 去掉 `.sh:105` 的 `run_suite "coverage-gate"` 行（因为前置已经跑了）
3. 全覆盖套件（`.sh:111-124`）保留：它会逐一跑 `test-*.py` 作为测试执行，但 coverage gate 的前置检查已经确保了注册表完备性

**改动量**：1 个文件 ≈ 15 行（添加前置检查 + 删掉旧行）

**影响**：回归跑任何测试之前，先确认所有机制都有测试覆盖。如果某个机制突然掉了测试文件（或新增机制无测试），回归直接拒绝启动。

**风险**：同 Option A — 少数元治理机制确实难测试，需要 §4.2 的放行机制。

---

### Option D — lx-goal `done` 阶段自动检查（推荐：第三优先级）

**概念**：在 lx-goal 退出前验证（`SKILL.md:91-113`）中插入 coverage gate 检查，确保 goal 模式执行完毕后系统覆盖率未下降。

**当前机制**：`lx-goal/SKILL.md:94-107` 定义了退出前验证步骤：git status → 跑测试 → 核对 AC → 自审。但没有覆盖 coverage gate。

**实现方式**：

1. 在 `SKILL.md:96`（"跑项目测试命令"）之后追加一行：
    
    ```
    6. 跑 coverage gate: `python3 scripts/test-coverage-gate.py --block` — 确保本次执行未引入无测试的新 hook/script
    ```
    
2. 可选：在 `lx-goal.py` 脚本中增加 `--verify-coverage` 标志，在 `done` 或 `off` 子命令中自动触发
3. 可选：如果 lx-goal 执行中新增了 hook 文件，coverage gate 因无测试而 exit=2 → 自动进入 skipped_risks，在退出报告中提示"新增机制 X 缺少测试文件"

**改动量**：1 个文件（SKILL.md）≈ 5 行变更；可选扩展 lx-goal.py（+10 行）

**影响**：goal 模式（全自动无人值守）执行后不会留下无测试覆盖的债务。

**风险**：如果 goal 模式本身在安装 hook（比如 `lx-goal` 作为 skill 本身不新增 hook），实际触发条件很低。但对正在自动添加治理机制的 goal 模式有价值。

---

### Option E — 注册表自检 + 双向同步（推荐：长期维护改进）

**概念**：目前注册表（`test-coverage-gate.py:30-91`）需要手动维护。新增 hook 时开发者可能忘记添加条目。双向同步减少维护成本。

**当前问题**：`_auto_discover_mechanisms()`（`.py:140-158`）已经尝试自动发现 hooks 中的未注册文件，但它只报 warning，不阻断。

**实现方式**：

1. 在 `test-coverage-gate.py` 中添加 `--validate-registry` 模式：
    - 扫描 `.claude/hooks/*.py` 和 `.claude/scripts/*.py`
    - 对比 `MECHANISMS` 注册表
    - 报告缺失条目（hook 存在但注册表没有）、过时条目（注册表有但文件已删）
    - exit=2 如果差异超过阈值

2. 添加 `--update-registry` 模式：自动将新发现的 hook 加入注册表，标注 `test_hint=None`（待补充）

3. 可选：在回归套件或 CI 中先跑 `--validate-registry` 再跑 `--block`

**改动量**：1 个文件 ≈ 60 行增量

**影响**：注册表与文件系统自动对齐，减少人为维护疏漏。

**风险**：自动添加的条目 test_hint=None 会导致被报告为"未覆盖"，结果是良性噪音 — 迫使开发者显式标注测试文件。

---

## 3. 推荐架构

### 3.1 执行顺序

```
Phase 1 (今天做):  Option A/C 合并 — 回归中激活 coverage gate 阻断
    ↓
Phase 2 (本周内):  Option B — pre-commit 检查新增机制无测试
    ↓
Phase 3 (下个迭代): Option D — lx-goal done 集成
    ↓
Phase 4 (维护期):  Option E — 注册表自检双向同步
```

### 3.2 架构依赖图

```
[新增 hook/script] ──→ Option B (pre-commit) ── 阻塞无测试新增
         │
         └──→ [git commit] ──→ [run-regression]
                                    │
                         Option A/C (coverage gate 前置 → 阻断回归)
                                    │
                         [scorecard 提分] ──→ 自动验证 coverage
                                    │
                         [lx-goal done] ──→ Option D (退出前验证)
```

### 3.3 操作流程

```text
1. 开发者新增 hook X.py
2. git add .claude/hooks/X.py
3. git commit → Option B 检测无 test-X.py → 阻塞
4. 开发者写 test-X.py → git commit 通过
5. 提分 scorecard → 跑回归 → Option A/C 前置 coverage gate --block → 通过
6. 写 scorecard 记录 → 分有效
```

---

## 4. 风险

### 4.1 假阴性（False Negative）

| 来源 | 严重度 | 缓解 |
|------|--------|------|
| `_find_test_file` 使用子串匹配 `h.replace(".py","") in t`（`.py:155`），短名 hook 可能错误命中不相关的测试文件 | low | 注册表精确路径覆盖比自动发现优先级高（`.py:169-174` 先检查 MECHANISMS） |
| 测试文件在非标准位置（如 `tests/integration/`） | low | `_find_test_file` 搜索 3 个位置，所有现有测试都在其中 |
| 一个测试文件覆盖多个机制（如 `test_pkg_c_lifecycle.py` 同时被 `precompact-lifecycle` 和 `lifecycle-ssot` 指向） | none | 设计如此，一个测试文件可被多个机制引用 |

### 4.2 真阴性（False Positive）— 真正的阻断误报

核心问题：**有些机制不是"有独立测试"的语义**。例如：

- `harness_core.py`（`.py:89`）— 共享库，被所有 hook 间接测试，标注 `# implicitly tested`
- `meta_oracle`（`.py:71`）— 元治理，集成测试成本极高
- `agentic_ui.py`（`.py:148`）— 被显式跳过自动发现
- `lx-goal`（`.py:73`）— skill 脚本，通过 skill 本身的行为验证

**缓解方案**：在注册表的 test_hint 字段使用保留标记：

```python
# 无法/不需要独立测试的机制
("harness-core", "lib", [...], None),  # implicitly tested
("meta-oracle", "script", [...], None),  # 元治理，覆盖率通过其他途径保证
```

然后在 `_find_test_file` 中对这些条目特殊处理（或者增加 `is_implicit_covered` 字段）。当前设计已部分支持 — `None` 不触发测试查找，只报"无独立测试"。建议增加一个标记机制：

```python
MECHANISMS = [
    ("name", "type", [paths], test_hint, is_optional=False),
    # is_optional=True 表示允许无独立测试（如隐式覆盖或元治理）
]
```

这些条目被计入 total 但不触发阻断。这个改动约 15 行。

### 4.3 双重复用

全覆盖套件（`.sh:111-124`）会跑所有 `scripts/test-*.py`，其中包括已经被前 15 个 run_suite 跑过的测试。coverage gate 本身不会导致双重复用，但全覆盖套件会多跑一次覆盖率的测试文件。不算 bug，但会延长回归时间。

**缓解**：将 coverage gate 自己的测试文件 `scripts/test-coverage-gate.py` 也加入 `EXCLUDED` 列表（`.sh:112`），避免在全覆盖套件中被重复跑。当前不在列表中，需要加。

### 4.4 临时绕过

`; exit 0` 本身就是一种绕过。去掉它之后，开发者可能通过 `git commit --no-verify`（pre-commit 绕过）或临时修改 threshold 来绕过。无法完全阻止有意的绕过，但审计链可以记录：

- 在 `test-coverage-gate.py` 的 `--block` 模式下，如果发现未覆盖机制，往 `.omc/audit/` 写入 JSONL 事件
- 当前已无审计写入，增加约 20 行

---

## 5. 工作量估算

| Option | 文件数 | 新增行 | 修改行 | 风险 | 复利系数 |
|--------|--------|--------|--------|------|----------|
| A — Scorecard 前置 | 2 | 0 | 10 | low | 3x（每次提分都受益） |
| B — Pre-commit | 1 | 40 | 0 | medium | 2x（每次新增机制受益） |
| C — 回归硬阻 | 1 | 10 | 5 | low | 4x（每次回归都受益） |
| D — lx-goal done | 1-2 | 5-15 | 5 | low | 1x（仅 goal 模式受益） |
| E — 注册表自检 | 1 | 60 | 5 | medium | 1x（维护期节省认知） |

**Phase 1 (A+C) 合计**：2 个文件，15 行改动，预期 15 分钟实施。这是复利回报最高的第一步。

---

## 6. 总结

```
做 → Option A/C（回归前置硬阻） —— 15 分钟，4 倍复利
做 → Option B（Pre-commit 阻断） —— 30 分钟，2 倍复利
考虑 → Option D（lx-goal 集成） —— 15 分钟，1 倍复利
考虑 → Option E（注册表自检） —— 45 分钟，维护期收益
```

核心发现：coverage gate 的设计本身是好的。问题不在 `test-coverage-gate.py`，而在**它没有被接入任何会阻断的节点**。去掉 `; exit 0` 并将 coverage gate 前置到回归头部，是 ROI 最高的单步。
