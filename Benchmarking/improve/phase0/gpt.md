# CarrorOS Headless 轻量化第一阶段施工方案

> 裁决：**退回 Design Doc 13 的 headless 降级方案，批准“单进程 launcher”替代方案。**  
> 本阶段只消除 Python 二次启动，不改变 gate 集、hook 注册、执行顺序、审计粒度、契约或阻断行为。

## ① 目标与不变式

### 1.1 目标

将 Python hook 的执行模型从：

```text
Claude Code
  -> python3 hook-launcher.py hook.py
       -> subprocess.run([sys.executable, hook.py])
```

收敛为：

```text
Claude Code
  -> python3 hook-launcher.py hook.py
       -> runpy.run_path(hook.py)
```

每次 Python hook 调用减少一个 Python 子进程。

`settings.json` 中 Bash 工具当前匹配：

- PreToolUse：`pretool-gate.py`
- PreToolUse：`carroros-night-deny.py`
- PostToolUse：`posttool-sensitive-filter.py`
- PostToolUse：`posttool-output-schema.py`
- PostToolUse：`error-dna.py`

因此，一次 Bash 调用的 Python 进程上限从 10 个降为 5 个。证据：`settings.json:19-42,46-55,75-96`；`hook-launcher.py:61-70`。

### 1.2 不变式

1. **gate 集不变**

   `L1_GATES` 仍为 9 个，`GATES` 仍为 20 个。不得删除或跳过任何现役 gate。证据：`pretool-gate.py:44-78`。

   服务哲学：`守护`。与更高优先级的 `the less,the more` 不冲突，因为本方案减少进程，不减少治理。

2. **hook 注册不变**

   `.claude/settings.json` 不修改。所有 matcher、hook 顺序和 timeout 保持原状。证据：`settings.json:17-128`。

   服务哲学：`守护`、`文档`。

3. **审计行为不变**

   不修改 `_record_gate_decision()`、`_append_audit()` 或 hook-evidence 写入逻辑。Design Doc 记录的审计量只能作为后续测量对象，不能在本阶段直接降频。证据：`13-headless-lightweight-actions.md:54-62`。

   服务哲学：`验证`、`守护`。

4. **阻断输出不变**

   子 hook 的 stdout、stderr 和 `SystemExit` 退出语义必须继续由 launcher 转发。关键 hook 缺失仍退出 2。证据：`hook-launcher.py:31-49,79-91`。

   服务哲学：`守护`。

5. **不新增 headless 检测**

   `sys.stdin.isatty()` 不得用于判断 `claude -p`。hook 的 stdin 是事件 JSON 管道，TTY 状态不能区分交互会话与 print 会话。原方案也承认两种模式没有可靠环境信号。证据：`13-headless-lightweight-actions.md:64-65,71-90`。

   服务哲学：`the less,the more`、`验证`。

6. **不修改 gate contract**

   当前 missing gate 的 enforcement 是警告路径；`_verify_contract_compliance()` 在 WARN 分支记录 `contract_warning` 后返回 `None`，不能把它描述成不可绕过的硬门禁。证据：`helpers.py:contract_warning 分支`。

   服务哲学：`文档`、`守护`。

---

## ② 文件清单

### `.claude/hooks/hook-launcher.py` → `edit`

应用以下完整补丁：

```diff
diff --git a/.claude/hooks/hook-launcher.py b/.claude/hooks/hook-launcher.py
--- a/.claude/hooks/hook-launcher.py
+++ b/.claude/hooks/hook-launcher.py
@@ -1,15 +1,17 @@
 #!/usr/bin/env python3
-"""CarrorOS Hook Launcher — crash-safe v2
+"""CarrorOS Hook Launcher — crash-safe v3
 
-v2: os.execvp → subprocess.run with crash protection.
+v3: Python hooks execute in-process through runpy.
+Shell hooks continue to use subprocess.run.
 Any hook crash/error → valid continue JSON on stdout → no more "hook error" from CC.
 Critical hooks that are missing → exit 2 (block, existing behavior preserved).
 """
 
 import json
 import os
+import runpy
 import subprocess
 import sys
+import traceback
 from pathlib import Path
 
 CRITICAL_HOOKS = {"pretool-gate.py"}
@@ -18,6 +20,28 @@ CRITICAL_HOOKS = {"pretool-gate.py"}
 def _emit_continue(message="", hook_name=""):
     """Emit a valid continue JSON and exit 0 (fail-open)."""
     payload = {"continue": True}
@@ -29,6 +53,25 @@ def _emit_continue(message="", hook_name=""):
         print(message, file=sys.stderr)
 
 
+def _run_python_hook(hook_path, hook_name, stdin_data):
+    """Run one Python hook in this process and preserve SystemExit semantics."""
+    original_stdin = sys.stdin
+    read_fd, write_fd = os.pipe()
+    try:
+        os.write(write_fd, stdin_data.encode("utf-8"))
+    finally:
+        os.close(write_fd)
+
+    try:
+        sys.stdin = os.fdopen(read_fd, "r", encoding="utf-8")
+        runpy.run_path(hook_path, run_name="__main__")
+        return 0
+    except SystemExit as exc:
+        return exc.code if isinstance(exc.code, int) else 1
+    except BaseException:
+        traceback.print_exc(file=sys.stderr)
+        return 1
+    finally:
+        sys.stdin.close()
+        sys.stdin = original_stdin
+
+
 def main():
     if len(sys.argv) < 2:
         _emit_continue("hook-launcher: missing hook name")
@@ -58,17 +101,20 @@ def main():
     env = os.environ.copy()
     env.pop("NIGHT_DENY_ROOT", None)
 
-    cmd = ["bash", hook_path] if hook_name.endswith(".sh") else [sys.executable, hook_path]
+    if not hook_name.endswith(".sh"):
+        os.environ.pop("NIGHT_DENY_ROOT", None)
+        returncode = _run_python_hook(hook_path, hook_name, stdin_data)
+        if returncode != 0:
+            _emit_continue(
+                "hook-launcher: hook crashed (exit="
+                + str(returncode)
+                + "): "
+                + hook_name,
+                hook_name,
+            )
+        return
 
     try:
         result = subprocess.run(
-            cmd,
+            ["bash", hook_path],
             input=stdin_data,
             capture_output=True,
             text=True,
@@ -83,10 +129,6 @@ def main():
         )
         return
 
-    # Forward child output
     if result.stdout:
         sys.stdout.write(result.stdout)
     if result.stderr:
         sys.stderr.write(result.stderr)
 
-    # If child produced no stdout but exited non-zero → crash → emit continue
     if result.returncode != 0 and not result.stdout.strip():
         _emit_continue(
             "hook-launcher: hook crashed (exit=" + str(result.returncode) + "): " + hook_name,
@@ -95,9 +137,6 @@ def main():
         )
         return
 
-    # Child produced stdout (JSON response) — trust it, exit with same code
-    # If child exit code != 0 but has JSON, let CC process the JSON
-    sys.exit(0 if result.stdout.strip().startswith("{") else 0)
-
 
 if __name__ == "__main__":
     main()
```

说明：

- Python hook 不再调用第二个 Python 解释器。
- shell hook 继续走现有 `subprocess.run()`。
- Python hook 异常仍由 launcher 转换成 continue JSON。
- 不触碰 frozen gate 逻辑。

服务哲学：`the less,the more > 验证 > 守护`。

### `.claude/hooks/pretool-gate.py` → 不操作

禁止修改。现役 9/20 gate 全部保留。

### `.claude/hooks/pretool_gates/helpers.py` → 不操作

禁止修改。审计和 contract 行为保持不变。

### `.claude/settings.json` → 仅执行密钥处置，不进入本补丁

上传内容中的 `ANTHROPIC_AUTH_TOKEN` 具有真实密钥格式，必须由人类在提供方撤销并轮换。施工模型不得打印、提交或复制原值。

轮换后由人类通过进程环境注入，仓库文件中的字段必须删除。该密钥操作属于人类独占裁决，不由施工模型自动执行。

### `scripts/carroros-gates/gate-contract.yaml` → 不操作

禁止增加 headless contract，不提高或降低 enforcement。

### `scripts/run-regression.sh` → 不操作

它已经自动发现 `.claude/scripts`、`.claude/skills`、`.claude/hooks` 下的现役测试，并在测试前移出 bypass/goal 状态、退出时恢复。证据：`run-regression.sh:1-48,50-64`。

---

## ③ 精确命令序列

所有命令从仓库根目录执行。

```bash
git status --short
```

期望 exit code：`0`。

创建补丁文件时，DeepSeek 必须把第②段 diff 原样写入：

```bash
git apply --check /tmp/carroros-hook-launcher-v3.patch
```

期望 exit code：`0`，stdout 为空。

```bash
git apply /tmp/carroros-hook-launcher-v3.patch
```

期望 exit code：`0`。

```bash
python3 -m py_compile .claude/hooks/hook-launcher.py
```

期望 exit code：`0`，stdout 为空。

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"printf ok"}}' \
  | python3 .claude/hooks/hook-launcher.py pretool-gate.py \
  > /tmp/carroros-launcher.stdout \
  2> /tmp/carroros-launcher.stderr
```

期望 exit code：`0`。

```bash
python3 -c 'import json; json.loads(open("/tmp/carroros-launcher.stdout", encoding="utf-8").read()); print("VALID_JSON")'
```

期望 exit code：`0`；期望 stdout：

```text
VALID_JSON
```

```bash
bash scripts/run-regression.sh
```

期望 exit code：`0`。

```bash
git diff --check
```

期望 exit code：`0`，stdout 为空。

```bash
git diff -- .claude/hooks/hook-launcher.py
```

期望 exit code：`0`；输出只能包含第②段规定的修改。

---

## ④ 逐条机械验收

### A1：Python hook 不再 spawn Python 子进程

```bash
python3 - <<'PY'
from pathlib import Path
text = Path(".claude/hooks/hook-launcher.py").read_text(encoding="utf-8")
assert "runpy.run_path(hook_path, run_name=\"__main__\")" in text
assert '[sys.executable, hook_path]' not in text
print("PASS single-python-process")
PY
```

期望 exit code：`0`。

期望 stdout：

```text
PASS single-python-process
```

### A2：shell hook 仍使用 subprocess

```bash
python3 - <<'PY'
from pathlib import Path
text = Path(".claude/hooks/hook-launcher.py").read_text(encoding="utf-8")
assert '["bash", hook_path]' in text
assert "subprocess.run(" in text
print("PASS shell-subprocess-preserved")
PY
```

期望 exit code：`0`。

期望 stdout：

```text
PASS shell-subprocess-preserved
```

### A3：gate 数量未改变

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path

path = Path(".claude/hooks/pretool-gate.py")
spec = importlib.util.spec_from_file_location("pretool_gate_acceptance", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert len(module.L1_GATES) == 9, len(module.L1_GATES)
assert len(module.GATES) == 20, len(module.GATES)
print("PASS gates L1=9 L2=20")
PY
```

期望 exit code：`0`。

期望 stdout：

```text
PASS gates L1=9 L2=20
```

### A4：未引入 headless 检测或 gate 降级

```bash
git diff --unified=0 \
  | grep -E 'CARROROS_FORCE_HEADLESS|CARROROS_FORCE_INTERACTIVE|isatty|HEADLESS_GATES'
test "$?" -eq 1
```

期望 exit code：`0`，stdout 为空。

### A5：settings、contract、helpers、pretool gate 未修改

```bash
test -z "$(git diff --name-only -- \
  .claude/settings.json \
  scripts/carroros-gates/gate-contract.yaml \
  .claude/hooks/pretool-gate.py \
  .claude/hooks/pretool_gates/helpers.py \
  scripts/run-regression.sh)"
```

期望 exit code：`0`。

### A6：launcher 返回合法 JSON

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"printf ok"}}' \
  | python3 .claude/hooks/hook-launcher.py pretool-gate.py \
  | python3 -c 'import json,sys; x=json.load(sys.stdin); assert isinstance(x,dict); print("PASS valid-json")'
```

期望 exit code：`0`。

期望 stdout：

```text
PASS valid-json
```

### A7：关键 hook 缺失仍 fail-closed

```bash
python3 .claude/hooks/hook-launcher.py pretool-gate.py.__missing__ \
  </dev/null >/tmp/missing.out 2>/tmp/missing.err
test "$?" -eq 0
```

期望 exit code：`0`。

注意：该命令验证的是非关键未知名称 fail-open。关键 hook 的缺失测试不得通过移动真实 `pretool-gate.py` 实现，因为那会触碰冻结文件。关键缺失分支由静态检查验收：

```bash
python3 - <<'PY'
from pathlib import Path
text = Path(".claude/hooks/hook-launcher.py").read_text(encoding="utf-8")
assert 'CRITICAL_HOOKS = {"pretool-gate.py"}' in text
assert "if hook_name in CRITICAL_HOOKS:" in text
assert "sys.exit(2)" in text
print("PASS critical-missing-exit-2")
PY
```

期望 exit code：`0`。

期望 stdout：

```text
PASS critical-missing-exit-2
```

### A8：完整回归通过

```bash
bash scripts/run-regression.sh
```

期望 exit code：`0`。

期望 stdout 必须同时包含：

```text
发现
```

以及项目现有的最终成功标记。不得通过修改测试发现规则减少测试数量。

### A9：补丁整洁

```bash
git diff --check
```

期望 exit code：`0`，stdout 为空。

---

## ⑤ 回滚命令

仅回滚本方案产生的修改：

```bash
git apply -R /tmp/carroros-hook-launcher-v3.patch
```

期望 exit code：`0`。

```bash
python3 -m py_compile .claude/hooks/hook-launcher.py
```

期望 exit code：`0`。

```bash
git diff --check
```

期望 exit code：`0`。

确认目标文件已回到施工前状态：

```bash
git diff --exit-code -- .claude/hooks/hook-launcher.py
```

期望 exit code：`0`，前提是该文件施工前没有用户未提交修改。

若施工前文件已有用户修改，不得执行反向补丁；应执行：

```bash
git apply --check -R /tmp/carroros-hook-launcher-v3.patch
```

期望 exit code：`0`，随后由整合器只反向应用本补丁，不得使用 `git checkout --`、`git restore` 或 `git reset --hard`。

---

## ⑥ 禁止事项

1. 禁止实现 `_is_headless()`，禁止读取 `sys.stdin.isatty()` 判断模式。
2. 禁止新增 `CARROROS_FORCE_HEADLESS` 或 `CARROROS_FORCE_INTERACTIVE`。
3. 禁止删除、跳过、重排或改名任何 L1/L2 gate。
4. 禁止修改 `_record_gate_decision()`、`_append_audit()` 或 hook-evidence。
5. 禁止修改 `.claude/settings.json` 的 matcher、hook 顺序或 timeout。
6. 禁止修改 `gate-contract.yaml`。
7. 禁止把 `missing_gate: WARN` 描述为硬阻断契约。
8. 禁止合并多个不同 hook 的输出协议；本阶段只消除 launcher 内部的第二个 Python 进程。
9. 禁止增加第三方依赖。
10. 禁止修改 `run-regression.sh` 以跳过失败测试。
11. 禁止在日志、补丁、提交信息或方案中复述已暴露的 API token。
12. 禁止由施工模型自行轮换、撤销或替换密钥；该不可逆操作由人类执行。
13. 任一验收失败后必须立即停止，不得通过放宽断言、删除测试或改成 WARN 继续施工。
14. 本阶段没有达到性能目标时，只提交测量证据；不得顺手实施 gate 降级或审计降频。