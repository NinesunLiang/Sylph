.claude/docs/story/cn/story-19.md
# Story 19: 5-Phase Structured Execution Protocol

> v6.3.8 · 哲学 #4(验证) + #6(0信任) 物化

## 触发

任何非 trivial 任务（>3 文件 / 新功能 / 架构变更）自动走 5 阶段：

Phase 1: 调研 → Phase 2: 方案双审(Oracle+Meta-Oracle) → Phase 3: 无人执行 → Phase 4: 结果双审 → Phase 5: 验收报告

## 核心机制

- Phase 3-4 为无人区：AI 不暂停、不提问、不中断、只记录
- 双法官门禁：Oracle(静态检查) + Meta-Oracle(运行时验证) 双签
- 参考：`.claude/reference/structured-execution-protocol.md`

## 相关

- Gate protocol: exit 2 + continue:true (阻断不打断)
- checkpoint hook: 所有工作流结束输出结构化收尾
- release-checklist.sh: 7 Phase 发版流程