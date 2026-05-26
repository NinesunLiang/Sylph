# audit — 漂移检测

四类检测规则：

| 规则 | 检测内容 | 严重度 |
|------|---------|--------|
| ID 孤儿检测 | feature 引用了 master 中不存在的 ID | high |
| 版本落后检测 | feature 最后同步 < 最后一次 reconcile | medium |
| 冲突定义检测 | feature 中定义与 master 不一致 | high |
| 孤立变更检测 | pending decision 超过 7 天未处理 | high |

> **范围**：v1 实现 ID 孤儿 + 版本落后，v2 扩展完整四类规则。
