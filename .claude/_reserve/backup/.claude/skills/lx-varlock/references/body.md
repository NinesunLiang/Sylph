# lx-varlock — 隐私脱敏代理管理器 (DLP)

## 原子化声明

### scripts/（确定性执行层）| 脚本 | 用途 | 调用时机 ||------|------|---------|| `scripts/varlock.py` | 敏感信息的双向脱敏：代理执行与读写恢复 | 敏感文件或命令交互 |

---

## 核心法则（P - Privacy Data Protection）
**铁律：AI 永远不应该直接看到、请求、或在原生工具中读取/写入/执行任何真实的明文 Token 或密码。**
凡是传给大模型的核心资产都要经过脱敏，执行端再恢复。
1. **绝对禁止使用原生 `Read` 读取 `.env`、`secrets.yml` 等凭据文件**。如果需要读取，必须使用 `python3 .claude/skills/lx-varlock/scripts/varlock.py read <file>`。返回的内容会将真实的密钥如 `222222` 替换为 `[MASKED_KEY_NAME]`。2. **绝对禁止使用原生 `Edit/Write` 写入敏感凭据**。如果需要修改 `.env`，必须输出包含占位符的文本，并调用 `python3 varlock.py write .env "<内容>"`，脚本会在落盘时自动将占位符恢复为明文。3. **禁止在 Bash 工具中组装明文 Token**（如 `curl -H "Auth: sk-ant..."`）。必须使用占位符调用代理：`python3 varlock.py run "curl -H 'Auth: [MASKED_TOKEN]' ..."`。
违反上述任意一条，将被 `privacy-gate.sh` 从底层强制拦截并判定为严重安全违规。

## 执行示例
**1. 读取敏感配置文件：**

```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py read .env# 返回脱敏结果：DB_PASS=[MASKED_DB_PASS]
bashpython3 .claude/skills/lx-varlock/scripts/varlock.py read .env# 返回脱敏结果：DB_PASS=[MASKED_DB_PASS]

```
**2. 写入或修改敏感配置文件：**如果你需要修改 `.env` 中的 `DB_HOST`，同时保持密码不被污染，必须传入包含占位符的内容：

```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py write .env "DB_HOST=127.0.0.1\nDB_PASS=[MASKED_DB_PASS]"
bashpython3 .claude/skills/lx-varlock/scripts/varlock.py write .env "DB_HOST=127.0.0.1\nDB_PASS=[MASKED_DB_PASS]"
```
**3. 执行带密码的测试：**

```bash
#
告诉用户：请打开本地普通终端，执行：python3 .claude/skills/lx-varlock/scripts/varlock.py set OPENAI_API_KEY "sk-xxxx..."
```待用户回复
后
，由 AI 代理执行测试：

```bash
n
3 .claude/skills/lx-varlock/scripts/varlock.py run "curl -X POST <https://api.openai.com/v1/chat/completions> -H 'Authorization: Bearer [MASKED_OPENAI_API_KEY]' -d '{\"model\": \"gpt-4o\"}'"

```

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|脚本执行失败 | 运行脚本 | 提示用户：底层脱敏机制异常，禁止传输任何明文。请手动在脱离 AI 的环境测试。|
|用户拒绝使用脱敏机制 | 强制执行 | **拒绝任务**。明确表示 Carror OS 无法违反数据防泄露 (DLP) 铁律。 |
