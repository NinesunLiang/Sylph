# 方案: config-drift-probe — 探针预警 harness 配置漂移

## 检测项 + 修复提醒

| 检测到 | 提醒用户怎么做 |
|--------|-------------|
| hook 声明但 .sh 缺失 | `cp source/harness-kit/.claude/hooks/<name>.sh .claude/hooks/` |
| source mirror 漂移 | `python3 .claude/skills/lx-sync/scripts/sync_check.py` → 手动同步 |
| harness.yaml 多了未注册 hook | 移除多余条目或补充 .sh 文件 |
| harness_config 共享函数缺失 | `bash .claude/scripts/audit-hooks.sh` 诊断 |

## 行为
- 从不阻断（exit 0）
- stderr 输出问题 + **具体修复命令**
- flywheel.log 记录
- 支持 --json

## 触发
- 手动：`bash .claude/scripts/config-drift-probe.sh`
- 自动：挂到 flywheel-report.sh（已有周期性 hook）
