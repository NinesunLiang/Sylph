# lx-root-cause-analysis: RCA场景测试
---
本文件定义6个RCA场景测试，验证Phase1-5流程完整性和置信度阈值。

## 场景1: 成功RCA（标准路径）
输入症状: "用户登录后偶发500错误，刷新后恢复正常"
预期流程: Phase1(症状映射) → Phase2(断点隔离) → Phase3(五层Why) → Phase4-5(修复+免疫)
预期置信度: ≥18/25
断言: Phase流转完整，修复指向根因而非症状

## 场景2: Oracle升级
输入症状: "内存泄漏，但复现不稳定，日志不完整"
预期流程: Phase1-2 → Phase3 置信度13-17 → Oracle升级
断言: Oracle-escalation.md被触发，输出包含需要Oracle审核的标记

## 场景3: 置信度不足中止
输入症状: "某天报错一次，日志不全，无法复现"
预期流程: Phase1-2 → Phase3 置信度<13 → 中止
断言: 输出中止信号，不进入Phase4

## 场景4: 语言专项触发
输入症状: "Go服务goroutine泄漏"
预期流程: Phase1触发rules-go.md → Phase3用Go专项模式分析
断言: 引用references/rules-go.md，Go专项模式被加载

## 场景5: 修复循环
输入症状: "修复后问题重现(第三次出现)"
预期流程: Phase4修复 → 验证未通过 → 回到Phase3 → 最多3轮
断言: repair-loop-rules.md被触发，修复循环不超出3轮

## 场景6: 修复免疫
输入症状: "数据库连接池耗尽"
预期流程: Phase4修复 → Phase5三重免疫(测试+验证+监控)
断言: 输出包含Unit Test / Integration Test / Monitor三类免疫措施
