# Node: context_collector

> 并行收集项目上下文（配置文件、现有模式、外部依赖）
> 复用: tdd-spec, browser-verify, debug-spec, root-cause-analysis

## 输入

- `scan_target` schema

## 输出

- `context_summary` schema（见 schemas/atomic/context_summary.yaml）

## 流程

1. 并行启动 2-4 个探索 agent（代码模式/配置/外部文档/测试）
2. 汇总关键发现
3. 标注不确定事项及置信度
4. 输出 context_summary
