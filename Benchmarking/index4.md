---
type: benchmark-report
schema_version: benchmark-report.v1
status: provisional-not_certified
---

# CarrorOS 治理效能 Benchmark

> Certification: **PROVISIONAL / NOT_CERTIFIED**（由 readiness 自动派生）

## 评分

| 维度 | 分数 |
|---|---:|
| C1-C9 能力加权 | 8.6 |
| E1-E8 错误防护 | 8.6 |
| 24 项总加权 | 8.65 |

## 未认证项（自动派生）

- `oracle.missing` [blocker] no valid fresh Oracle verdict
- `regression.entrypoint.drift` [blocker] tests/test-audit-schema.py, tests/test-coverage-gate.py, tests/test-e4-inertia.py, tests/test-fallback-engine.py, tests/test-goal-mode-gate.py, tests/test-hook-launcher.sh, tests/test-lifecycle-mutex.py, tests/test-lx-stepwise.py, tests/test-nine-challenge.py, tests/test-oracle-gate.py, tests/test-task-ssot.py, tests/test-verify-gate.py, tests/test_pkg_c_lifecycle.py
- `goal.e2e.missing` [blocker] complete plan-token-handoff-resume-done/off fixture missing
- `runtime.network.unexecuted` [informational] network worker intentionally not run
- `credentials.unexecuted` [informational] credential paths intentionally not read
- `ci.install.unexecuted` [informational] CI package installation intentionally not run
- `destructive.unexecuted` [informational] destructive state operations intentionally not run

## 认证边界

- 报告事实源为本次 eval-aggregate 输入和 readiness JSON。
- 网络、凭据、CI 安装和破坏性入口不会被自动执行；未执行状态保留为 informational。
- Oracle 缺失、回归入口漂移、Goal E2E 缺失或 SubAgent 矩阵缺失时不得 CERTIFIED。

## 复现

```text
python3 .claude/scripts/eval-aggregate.py --scorecard <scorecard> --meta-verdict <oracle-dir> --output <eval-report>
```
