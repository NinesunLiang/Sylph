# tokens/ — 运行时令牌

> 每任务一个 `.json` 文件，含步骤定义和状态。
> 按日期分目录（`YYYYMMDD/`）。

## AI 使用守则

> **只读** — token 由 `carros_base.py` / `carros_utils.py` 管理，
> AI 通过 `status`/`verify` 命令查看，不应直接改写。
>
> **按需加载** — 确认任务日期后再 `@.omc/tokens/{date}/{task}.json`，
> 不要一次性遍历 tokens/。

## 文件规则

| 文件 | 格式 | 说明 |
|------|------|------|
| `{task_name}.json` | JSON | 令牌主文件：`{steps: [{id, name, status}], ...}` |
| `{task_name}.json.lock` | 空文件 | 令牌锁，防止并发修改 |

## 目录结构

```
tokens/
├── 20260713/
│   ├── phase0-token-slim.json
│   ├── phase0-token-slim.json.lock
│   └── ...
└── 20260723/
    └── ...
```

## 注意

- 令牌是运行时状态源，由 `carros_base.py` / `carros_utils.py` 管理
- `.lock` 文件为并发安全锁，进程退出自动释放
