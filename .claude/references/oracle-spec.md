# Oracle 门禁规格

> L2 Enhance 核心门禁。5 点触发 → 裁决(Accept/Warn/Reject/Escalate)
> 触发后调用 `.omc/scripts/oracle_gate.py`
> 人类可根据此文档配置 oracle 触发规则

## 触发条件 (5 点)

| # | 触发点 | 匹配规则 | 类型 |
|---|--------|---------|------|
| 1 | 跨系统操作 | file path matches `/etc/`, `/usr/local/`, `/Applications/`, `/System/` | 硬阻断 |
| 2 | 不可逆操作 | command contains `rm -rf`, `dd`, `diskutil`, `sudo`, `chmod 777` | 硬阻断 |
| 3 | 安全/权限变更 | file path matches `.ssh/`, `.env`, `credentials`, `secret`, `id_rsa` | 硬阻断 |
| 4 | 发布动作 | command contains `deploy`, `release`, `publish`, `push --force` | 软上门 |
| 5 | 长时间无人 | session thread_count > 0 且 last_user_message > 3600s | 软上门 |

## 裁决输出

```
ACCEPT   → 直接放行（已验证安全）
WARN     → 继续执行，贴 Oracle 警告到 context
REJECT   → 拦截操作，返回拒绝原因
ESCALATE → 人类审批（生成 CAPTCHA 文件对）
```

## 绕过机制

- `oracle_bypass/` 目录放 `<task_id>_approved.md` 文件 → 自动跳过 Oracle
- 有效期 24h（检查文件 mtime < 86400s）
- 过期间 Oracle 执行后自动删旧 bypass 文件

## 调用方式

```
python3 .omc/scripts/oracle_gate.py --check <触发点ID> [--path <路径>] [--command <命令>]
```

返回 JSON: `{"verdict":"ACCEPT","reason":"..."}`
