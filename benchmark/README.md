# CarrorOS Benchmark Framework

> 组件消融 A/B + 配对多次运行 + 30/60/100 轮长会话 + 强制故障注入 + 隐藏确定性验收

## 架构概览

```
benchmark/
├── runner.py              # 主入口：编排整个测试流程
├── ablation.py            # 消融组配置（A-G 七组）
├── task_loader.py         # 任务加载与校验
├── environment.py         # 测试环境构建（git checkout + CarrorOS 组件注入）
├── collector.py           # 指标采集
├── reporter.py            # 报告生成
├── schemas.py             # 数据结构定义
├── tasks/                 # 任务库（80 个任务 × 10 类）
│   ├── 01_repo_locate/    # 仓库定位与小修复
│   ├── 02_multi_file/     # 多文件重构
│   ├── 03_cross_module/   # 跨模块 Bug
│   ├── 04_migration/      # 依赖升级/迁移
│   ├── 05_fuzzy_req/      # 模糊需求实现
│   ├── 06_test_fix/       # 测试修复
│   ├── 07_perf_concur/    # 性能/并发
│   ├── 08_long_recovery/  # 长期恢复
│   ├── 09_high_risk/      # 高风险
│   └── 10_adversarial/    # 对抗性
├── configs/               # 消融组配置
│   ├── A_bare.yaml
│   ├── B_entry_prompt.yaml
│   └── ...
└── reports/               # 输出报告
    ├── capability-amplification.md
    ├── long-running-stability.md
    └── ...
```

## 核心流程

```
task_loader.py: 加载任务定义 + 任务仓库 commit
       ↓
ablation.py: 选择消融组 (A-G) → 生成组件启用/禁用配置
       ↓
environment.py: git checkout task repo + 
                选择性注入 CarrorOS 组件 + 
                设置模型/budget 控制变量
       ↓
runner.py: 启动 Claude Code/OpenCode 会话 →
           注入任务 prompt →
           监控执行 →
           超时/预算耗尽时终止
       ↓
collector.py: 运行验证脚本 →
              采集指标 →
              写入 experiment-run.yaml
       ↓
reporter.py: 聚合所有 run →
             配对统计分析 →
             生成 7 份报告
```

## 快速开始

```bash
# 阶段 1：20 任务小型消融
python3 benchmark/runner.py --phase 1

# 阶段 2：80 任务正式能力测试
python3 benchmark/runner.py --phase 2 --model deepseek-v4-flash

# 生成报告
python3 benchmark/reporter.py --report-dir benchmark/reports/
```
