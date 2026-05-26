# 错误码

> 共享体系见 `@../../schemas/atomic/error_codes.yaml`，前缀 `HIER`。

## 超时与重试

超时 5 分钟，最多重试 3 次。

## hier 特定错误码

- `ERR-HIER-23`：MECE 校验失败 — 修复后重新拆解
- `ERR-HIER-90`：lx-oma-split 不可用 — 降级手动拆解
