# 错误码

> 共享体系见 `@../../schemas/atomic/error_codes.yaml`，前缀 `ORCH`。

超时 15 分钟（含子 skill），最多重试 2 次。

## orch 特定错误码

- `ERR-ORCH-12`：pipeline.yaml 解析失败
- `ERR-ORCH-32`：并发写冲突 → 原子写入
