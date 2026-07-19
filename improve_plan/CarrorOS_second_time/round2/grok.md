# PKG-C 材料完整性门禁报告

> **结论：当前不能安全生成精确 diff。**  
> 用户消息称材料为 `pkg-a.md`，实际附件名为 **`pkg-c.md`**。附件元数据大小为 **112,674 bytes**，但当前可读取内容在 `.claude/references/feature-registry.yaml` 第 179 行附近截断，尚未取得 handoff 写入点、计数实现、goal/ghost 状态及其操作脚本。  
> 若现在生成 diff，必然违反“每个断言带文件:行号”“`git apply --check` 干净适用”和“零设计空间”三项门禁。

---

## ① 目标与不变式

### 1.1 已确认的基线事实

| 编号 | 断言 | 证据 | 影响 |
|---|---|---|---|
| F1 | 当前 hooks 注册表只有 `PreToolUse`、`UserPromptSubmit`、`PostToolUse`、`SessionStart`、`Stop` 五类事件 | `.claude/settings.json:20-85` | 未注册 `PreCompact`、`SessionEnd`、`SubagentStop` |
| F2 | `SessionStart` 直接调用 `session-start.py` | `.claude/settings.json:64-73` | 生命周期启动端已有入口，应优先复用现有状态约定 |
| F3 | `Stop` 直接调用 `stop-flywheel.py` | `.claude/settings.json:75-84` | 必须先判断其是否已有 handoff/flush 职责，禁止叠加重复机制 |
| F4 | `auto-snapshot` 被登记为默认启用 | `.claude/references/feature-registry.yaml:38-44` | 必须查明其真实实现和接线状态，僵尸机制只能接线或删除 |
| F5 | `turn-counter` 被登记为默认启用 | `.claude/references/feature-registry.yaml:52-58` | handoff 的 `0/0` 失真可能与此计数源相关，不能另建计数器绕过 |
| F6 | `context-guard` 宣称存在 80% 硬阻断 | `.claude/references/feature-registry.yaml:94-100` | PreCompact 必须与既有上下文状态协作，不能再建第二套水位状态 |
| F7 | registry 将 20 余项特性标为默认启用，但当前注册表仅暴露少量聚合入口 | `.claude/references/feature-registry.yaml:2-179`；`.claude/settings.json:20-85` | 不能仅按注册表名称判断僵尸；须检查聚合 hook 内部调用图 |
| F8 | `harness-config` 被声明为所有 hook 共用配置读取器 | `.claude/references/feature-registry.yaml:151-157` | 新生命周期 hook 若确需共享配置，必须复用它，不得新增配置层 |
| F9 | `token-writer` 被声明由 `context-guard` 调用 | `.claude/references/feature-registry.yaml:158-165` | PreCompact 可能依赖 token 状态；必须读取实现后才能确定契约 |

### 1.2 待冻结的不变式

以下不变式方向已经确定，但在取得完整代码前不得落成 diff：

1. **磁盘唯一真相源**  
   handoff 内容、handoff 计数和生命周期状态各自只能有一个规范写入位置。

2. **PreCompact 不可静默失败**  
   持久化失败必须返回非零退出码，并通过 stderr 给出稳定错误码。

3. **计数必须从磁盘事实计算**  
   禁止信任模型声明的 `0/0`；声明值只能与磁盘派生值对账，不能覆盖后者。

4. **`goal ⊕ ghost`**  
   同一 session 不允许 goal 与 ghost 同时 active。非法并存必须机械阻断，不得仅 WARN。

5. **结束事件必须幂等**  
   `SessionEnd`、`SubagentStop` 和现有 `Stop` 即使重复触发，也不得重复增加计数或破坏已有 handoff。

6. **不新建平行生命周期机制**  
   先检查并复活 `auto-snapshot`、`turn-counter` 和现有 handoff 代码；确定无法承担契约后，才允许最小新增入口。

### 1.3 哲学合规

| 拟议方向 | 服务环节 | 冲突裁决 |
|---|---|---|
| 由磁盘重新计算 handoff 计数 | 验证、零信任 | 高于兼容旧声明计数 |
| 持久化失败返回非零 | 验证、守护 | 高于“不中断会话”的便利性 |
| goal/ghost 非法并存阻断 | 零信任、守护 | 高于 ghost 自动探索增益 |
| 复用现有 snapshot/counter | 少、文档 | 若妨碍验证，则以验证为准 |
| 生命周期结束幂等 | 验证、守护 | 高于额外日志或报告增益 |

---

## ② 文件清单：当前状态与缺失材料

### 2.1 已读取文件

| 路径 | 当前操作 | 状态 |
|---|---:|---|
| `.claude/settings.json` | 待定 `edit` | 已读取第 1–91 行 |
| `.claude/references/feature-registry.yaml` | 待定 `edit` | 仅读取到第 179 行附近；完整文件状态未知 |

### 2.2 当前禁止生成 diff 的原因

现有材料只能证明事件未在 `.claude/settings.json` 注册，不能证明：

- 是否已有未注册的 `PreCompact`、`SessionEnd`、`SubagentStop` 脚本；
- `pretool-gate.py`、`posttool-gate.py` 或 `stop-flywheel.py` 是否聚合调用 snapshot/counter；
- 三份 handoff 的实际路径；
- `0/0` 和 `0/3` 分别由哪段代码生成；
- goal/ghost 是文件、目录、JSON 字段还是 Markdown 状态；
- hook 输入 JSON 的字段目前如何解析；
- 仓库中是否已有 hook 测试 harness；
- 新事件是否被当前运行时版本支持。

因此，下面这种只改注册表的补丁**明确不安全，禁止施工**：

```diff
+ "PreCompact": [...]
+ "SessionEnd": [...]
+ "SubagentStop": [...]
```

原因：目标脚本路径、输入契约、退出码语义和幂等行为均未被现有证据证明。

### 2.3 请补充的精确内容

请不要再次发送单个超长 Markdown 汇总文件；请直接上传以下原始文件，或分成不超过 25,000 bytes 的多个 Markdown：

#### A. 必须提供的目录清单

```bash
git rev-parse HEAD
find .claude/hooks -maxdepth 2 -type f -print | LC_ALL=C sort
find .claude -type f \( \
  -iname '*compact*' -o \
  -iname '*handoff*' -o \
  -iname '*session*' -o \
  -iname '*subagent*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' -o \
  -iname '*snapshot*' \
\) -print | LC_ALL=C sort
```

#### B. 必须提供的现有入口全文

```text
.claude/hooks/hook-launcher.sh
.claude/hooks/pretool-gate.py
.claude/hooks/posttool-gate.py
.claude/hooks/session-start.py
.claude/hooks/stop-flywheel.py
.claude/hooks/statusline-command.sh
```

#### C. 必须提供的搜索结果

```bash
git grep -nE \
  'PreCompact|SessionEnd|SubagentStop|handoff|goal|ghost|auto-snapshot|turn-counter|compact-write|compact_write' \
  -- .claude
```

#### D. 必须提供的 handoff/状态原始文件

提供上述 `git grep` 命中的所有：

- handoff 写入函数；
- handoff 读取函数；
- handoff schema；
- goal 创建、读取、清理函数；
- ghost 创建、读取、清理函数；
- counter 读写函数；
- snapshot 读写函数；
- 相关测试文件。

#### E. 必须提供的真实失真样例

请在脱敏副本或临时工作树执行并粘贴原样输出：

```bash
find .claude -type f \( \
  -iname '*handoff*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' \
\) -print -exec sed -n '1,240p' {} \;
```

### 2.4 文件切分规范

若继续使用材料包，请机械执行：

```bash
mkdir -p /tmp/pkg-c-split
split -b 24000 -d -a 3 pkg-c.md /tmp/pkg-c-split/pkg-c.part-
sha256sum pkg-c.md /tmp/pkg-c-split/pkg-c.part-*
```

然后上传全部 `/tmp/pkg-c-split/pkg-c.part-*`。不得摘要或重排内容。

---

## ③ 精确命令序列

当前阶段只进行**只读证据采集**，不得修改仓库：

```bash
set -euo pipefail

test "$(git rev-parse HEAD)" = "91954a0b01f9c53edf94965238308fcb080818eb"

mkdir -p /tmp/carroros-pkg-c-evidence

git rev-parse HEAD \
  > /tmp/carroros-pkg-c-evidence/00-head.txt

find .claude/hooks -maxdepth 2 -type f -print \
  | LC_ALL=C sort \
  > /tmp/carroros-pkg-c-evidence/01-hooks-files.txt

find .claude -type f \( \
  -iname '*compact*' -o \
  -iname '*handoff*' -o \
  -iname '*session*' -o \
  -iname '*subagent*' -o \
  -iname '*goal*' -o \
  -iname '*ghost*' -o \
  -iname '*counter*' -o \
  -iname '*snapshot*' \
\) -print \
  | LC_ALL=C sort \
  > /tmp/carroros-pkg-c-evidence/02-lifecycle-files.txt

git grep -nE \
  'PreCompact|SessionEnd|SubagentStop|handoff|goal|ghost|auto-snapshot|turn-counter|compact-write|compact_write' \
  -- .claude \
  > /tmp/carroros-pkg-c-evidence/03-lifecycle-grep.txt || test "$?" -eq 1

for file in \
  .claude/settings.json \
  .claude/references/feature-registry.yaml \
  .claude/hooks/hook-launcher.sh \
  .claude/hooks/pretool-gate.py \
  .claude/hooks/posttool-gate.py \
  .claude/hooks/session-start.py \
  .claude/hooks/stop-flywheel.py \
  .claude/hooks/statusline-command.sh
do
  if test -f "$file"; then
    printf '\n===== %s =====\n' "$file"
    nl -ba "$file"
  else
    printf '\n===== MISSING: %s =====\n' "$file"
  fi
done > /tmp/carroros-pkg-c-evidence/04-entrypoints.txt

while IFS= read -r file; do
  test -f "$file" || continue
  printf '\n===== %s =====\n' "$file"
  nl -ba "$file"
done < /tmp/carroros-pkg-c-evidence/02-lifecycle-files.txt \
  > /tmp/carroros-pkg-c-evidence/05-lifecycle-content.txt

sha256sum /tmp/carroros-pkg-c-evidence/*.txt \
  > /tmp/carroros-pkg-c-evidence/SHA256SUMS

tar -C /tmp \
  -czf /tmp/carroros-pkg-c-evidence.tar.gz \
  carroros-pkg-c-evidence

sha256sum /tmp/carroros-pkg-c-evidence.tar.gz
```

将 `/tmp/carroros-pkg-c-evidence.tar.gz` 上传。若平台不接受归档，则逐个上传其中六个 `.txt` 文件和 `SHA256SUMS`。

---

## ④ 逐条机械验收

### V1：基线一致

```bash
test "$(git rev-parse HEAD)" = "91954a0b01f9c53edf94965238308fcb080818eb"
```

期望：

- exit code：`0`
- stdout：空

### V2：当前 settings 缺少三个目标事件

```bash
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".claude/settings.json").read_text(encoding="utf-8"))
hooks = data.get("hooks", {})
missing = [
    event
    for event in ("PreCompact", "SessionEnd", "SubagentStop")
    if event not in hooks
]
print(",".join(missing))
raise SystemExit(0 if missing == [
    "PreCompact", "SessionEnd", "SubagentStop"
] else 1)
PY
```

期望：

- exit code：`0`
- stdout：

```text
PreCompact,SessionEnd,SubagentStop
```

该验收仅确认现状，不代表应立即新增注册。

### V3：证据包文件完整

```bash
test -s /tmp/carroros-pkg-c-evidence/00-head.txt
test -s /tmp/carroros-pkg-c-evidence/01-hooks-files.txt
test -f /tmp/carroros-pkg-c-evidence/02-lifecycle-files.txt
test -f /tmp/carroros-pkg-c-evidence/03-lifecycle-grep.txt
test -s /tmp/carroros-pkg-c-evidence/04-entrypoints.txt
test -f /tmp/carroros-pkg-c-evidence/05-lifecycle-content.txt
test -s /tmp/carroros-pkg-c-evidence/SHA256SUMS
test -s /tmp/carroros-pkg-c-evidence.tar.gz
```

期望：

- 每条命令 exit code：`0`
- stdout：空

### V4：证据包哈希可验证

```bash
cd /tmp/carroros-pkg-c-evidence
sha256sum -c SHA256SUMS
```

期望：

- exit code：`0`
- 每行以 `: OK` 结束

### V5：采集阶段未修改仓库

执行采集前先记录：

```bash
git status --porcelain=v1 > /tmp/pkg-c-status.before
```

执行采集后：

```bash
git status --porcelain=v1 > /tmp/pkg-c-status.after
cmp -s /tmp/pkg-c-status.before /tmp/pkg-c-status.after
```

期望：

- exit code：`0`
- stdout：空

---

## ⑤ 回滚命令

本阶段只读，不修改 Git 工作树。仅删除临时证据：

```bash
rm -rf \
  /tmp/carroros-pkg-c-evidence \
  /tmp/carroros-pkg-c-evidence.tar.gz \
  /tmp/pkg-c-status.before \
  /tmp/pkg-c-status.after \
  /tmp/pkg-c-split
```

期望：

- exit code：`0`
- stdout：空

---

## ⑥ 禁止事项

1. **禁止依据附件名误判包归属。** 当前收到的是 `pkg-c.md`，不是用户文字所称的 `pkg-a.md`。
2. **禁止现在直接往 `.claude/settings.json` 添加三个事件。** 尚未证明脚本、输入契约和幂等性。
3. **禁止创建第二套 handoff、counter、goal、ghost 或 snapshot 路径。**
4. **禁止把 registry 的 `enabled_by_default: true` 当作真实接线证据。**
5. **禁止让 `PreCompact` 持久化失败后返回 `0`。**
6. **禁止用日志文本中的声明计数覆盖磁盘派生计数。**
7. **禁止以人工确认替代 hook 触发测试和 `jq` 状态比对。**
8. **禁止修改 PKG-A/PKG-B 所属验证链文件。**
9. **禁止由施工模型猜测文件路径、JSON 字段、hook stdin schema 或退出码。**
10. **禁止生成不能在基线 `91954a0b01f9c53edf94965238308fcb080818eb` 上通过 `git apply --check` 的补丁。**

取得上述完整证据包后，才能返回真正可施工的 **PKG-C 六段式优化方案 + 单一 `git apply` diff 脚本**。