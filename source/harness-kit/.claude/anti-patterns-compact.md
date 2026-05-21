# 反模式速查（Compact）

> 完整版 → `Read .claude/anti-patterns.md`

| 类别 | 一句话 | 典型表现 |
|------|--------|---------|
| A 假完成 | 无证据说「完成了」 | 应该没问题/基本完成/理论上 |
| B 功能蔓延 | 一次改太多 | 跨 5+ 文件无 Step 拆分 |
| C 破坏性 hook | exit 2 阻断正常流程 | hook 在非关键场景 exit 2 |
| D 隐私泄露 | .env/密钥 被读 | Bash 里有明文 Token |
| E 跳过门禁 | 绕过 verification | 不跑 test 就说 VERIFIED |
| F 幻觉路径 | 编造不存在的文件/路径 | 引用从未创建的文件 |
| G 上下文污染 | 冗余信息淹没关键规则 | 重复注入相同的长文本 |
| H 权威颠倒 | AI 自判优先级 | 忽略 Boss 即时指令 |
| I1 机制影壁 | hook 无 flywheel 埋点 | hook 跑了但无日志可查 |
| I2 纯软约束 | 只提醒不阻断 | AI 可忽略的 hook 提示 |
| L1 静默失败 | hook 静默跳过 | set -e 下某命令失败但整体 exit 0 |
| R 规则漂移 | 文档≠代码 | harness.yaml 说 true 但 hook 不存在 |
| S 语义作弊 | 形式合规但内容空 | VERIFIED: 前面没有证据 |

**关键防御**: 每一项反模式 = 至少一个 hook 的触发条件。发现反模式 → 立即查 harness-smoke-test.sh 对应用例。
