# signals/

CarrorOS 信号文件目录。

## 用途

信号文件是轻量级标记文件, 用于在 hook 之间传递状态、触发条件和运行时信号。每个信号文件代表一个特定的事件或条件, 由生产 hook 写入, 由消费 hook 读取。

### 信号文件规范

- **命名**: `snake_case.md` 或 `*.signal`
- **内容**: 简短的状态描述 + 可选元数据 (时间戳/来源/上下文)
- **生命周期**: 消费即清理, 或由 `stop-drain.sh` 统一归档
- **保障**: 永不包含敏感信息 (Token/Key/私钥)

### 当前信号

*(此占位符目录等待运行时信号注册)*

### 相关机制

- 信号产生: `pretool-*` 系列 hook
- 信号消费: 各 gate/guard hook
- 信号清洁: `stop-drain.sh` / `context-compressor.sh`
