我承接委员会 **PKG-B：验证契约统一**。前两轮关于身份的回复有误；本轮起按 **gpt-5.6-sol / CarrorOS 适应性优化架构师**执行。

你提供的评分足以确定问题优先级，但不足以生成可通过 `git apply --check` 的精确补丁。评分中的 `E3=4`、验证逻辑多源、`oracle_gate.py` 孤儿化以及 `R6/--pipeline/.sh` 冲突，目前仍是待源码核验的审计结论，不能直接当作补丁上下文或 `文件:行号` 证据。

**PKG-B 边界**

我只处理以下事项，避免与另外两包文件交叉：

1. 找出“6处重复验证”的实际位置，确定唯一验证契约来源。
2. 对 `oracle_gate.py` 作二选一裁决：接入生产链或正式删除，不保留僵尸机制。
3. 统一 R6、`--pipeline` 参数及 `.sh` 执行约定。
4. 删除或改写 PKG-B 范围内指向旧验证契约的文档声明。
5. 提供六段式 Markdown 施工方案，不直接修改代码。

以下内容属于其他分包，本包不改：

- PKG-A：`verify_gate` trust 模式、capture 契约、task-spec 强制规则。
- PKG-C：PreCompact、SessionEnd、SubagentStop、handoff 计数及 goal/ghost 互斥。

**请提供源码快照**

最稳妥的方式是上传仓库压缩包，需包含隐藏目录、脚本和测试，但排除 `.git`、依赖目录、密钥与运行产物。若不能上传仓库，请在仓库根目录执行以下命令并提供输出：

```bash
printf '%s\n' '=== TRACKED FILES ==='
git ls-files

printf '%s\n' '=== STATUS ==='
git status --short

printf '%s\n' '=== VALIDATION REFERENCES ==='
rg -n --hidden \
  -g '!.git/**' \
  -g '!node_modules/**' \
  -g '!vendor/**' \
  -g '!dist/**' \
  -g '!build/**' \
  'verify_gate|oracle_gate|cmd_verify|_check_verified|--pipeline|R6|S1|verified|verification|验证|证据' .
```

然后提供下列文件的**完整原文**，不能只截取命中行，因为精确 diff 需要稳定上下文：

- `oracle_gate.py`
- `verify_gate.py` 及其测试文件
- 定义 `cmd_verify`、`_check_verified`、R6、S1 的文件
- 所有包含 `--pipeline` 的文件
- 被上述脚本读取或调用的全部 `.sh`
- 六处重复验证所在文件
- 涉及验证规则的 `lx-*` skill
- hook 注册配置及调用验证脚本的 hook
- 当前 `README`、规范文件、registry/manifest
- `.gitignore`
- 若存在：`pyproject.toml`、`requirements*.txt`、`package.json`、测试入口脚本

可用下面的命令生成带行号证据。将 `<FILE>` 逐一替换为实际路径：

```bash
nl -ba '<FILE>'
```

还需要提供当前提交标识，以便方案声明适用基线：

```bash
git rev-parse HEAD
```

请勿提供 `settings.json` 中的明文 token。该安全问题优先级很高，但不属于 PKG-B 文件集；应由 Kimi K3 单独分配一个零交叉安全修复包。提交材料时将密钥值替换为 `<REDACTED>`，同时保留键名、文件结构和行号。

资料齐全后，我会直接输出严格六段式方案：每个断言附 `文件:行号`，每处变更给出可保存为单一补丁并通过 `git apply --check` 的精确 diff，每条验收包含命令、预期退出码和必要 stdout，不留下开放设计问题。