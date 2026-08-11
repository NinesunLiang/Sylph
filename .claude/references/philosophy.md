# CarrorOS 哲学体系 （唯一真相源，任何分支文档冲突以此为准）
灵魂裁决链（机械生效，无需协商）：少即是多 > 验证 > 零信任 > 守护 > 文档 > 人本 > 增益
---
## 1. 少即是多
只做必要的、可量化增益的机制；能不做就不做，能简单实现就简单实现，防止系统熵膨胀。少即是多负责取舍，不得绕过铁律、审批或验证。
对应落地实体：feature-registry.yaml、gatekeeper.py、plan_builder.py
---
## 2. 验证 > AI 承诺
CarrorOS 不信任 AI 生成的任何口头结论，所有行为断言必须有可复现证据佐证：测试输出、磁盘日志、内存截图、校验摘要四类证据为法定有效证据，AI 自述、自然语言推演不具备裁决效力。
对应落地实体：compound-verify-gate.py、trace3-e3-completion-gate.md、0003-verifygate-evidence-hierarchy.md
## 3. AI 全链路零信任
CarrorOS 先天不信任 AI 能自主完成状态锁死、修改闭环、边界恪守任意一项要求。开发执行前必须先遍历项目全量依赖树：对存量依赖树全量跑回归测试至 100% 绿，再对新增开发项先写全量失败用例至 100% 红；开发完成后必须对全量依赖树 + 新增代码再跑一轮回归至 100% 绿，禁止跳过任何阶段。
对应落地实体：run-regression.sh、test-*.py 全集合、trace1-e1-scope-defense.md、error-dna.json
## 4. 先守护，后变更
任何涉及不可逆修改、跨路径覆盖、全局状态写入的操作，执行前必须自动将原始快照落地到 `.omc/state/restore/{action_timestamp}/` 目录，并在 lifecycle_ssot 中写入硬链索引；全操作周期内随时支持一键回滚到变更前状态。
对应落地实体：lifecycle_ssot.py、precompact-lifecycle.py、.omc/state/restore 目录约定
## 5. 磁盘状态为唯一真相源
完全不信任 AI 上下文记忆，尤其在上下文窗口溢出、会话压缩、Agent 接力场景下：所有任务状态必须结构化落盘到 `.omc/tasks/{YYYYMMDD}/{task_name}/[research|plan|executor]` 文档集，由 `.omc/tokens/{YYYYMMDD}/{task_name}.json` 令牌做唯一锚点，任务恢复时完全从磁盘读取、不采信内存残余信息。
对应落地实体：token.template.json、task_ssot.py、redirect-mechanism.md、0002-token-lock.md
## 6. 人本独占不可逆裁决
CarrorOS 内置标准化 AI 决策链：`行为合规校验（哲学支撑>不违反铁律>符合当前磁盘状态>高ROI）`，非「删除人类身份凭证、修改生产环境根密码、篡改系统哲学内核」三类不可逆风险场景全部由内核自主决策执行，避免无意义人机交互。仅触发三类风险时将裁决权移交人类，且该裁决结果永久写入证据链不可覆盖。
对应落地实体：pretool-user-approve.py、0005-goal-mode-autonomous-execution.md、handoff.json
## 7. 增益优先，做少得多
所有新增功能必须证明「单行为带来全局可量化增益 > 实现+维护成本」，禁止为了大而全新增无明确收益的模块、钩子、校验规则；无增量增益的冗余代码统一通过僵尸机制处置流程二选一：要么接入主校验链路、要么直接删除。
对应落地实体：feature-registry.yaml、0013-scorecard-gate.md、anti-pattern-redirects.json
```

---

### ③ 精确命令序列
```bash
# 1. 先备份原哲学文档到守护目录
mkdir -p .omc/state/restore/philosophy-upgrade-20260730/
cp .claude/references/philosophy.md .omc/state/restore/philosophy-upgrade-20260730/philosophy.old.md

# 2. 写入优化后的新哲学文档
cat > .claude/references/philosophy.md << 'EOF'
# CarrorOS 哲学体系 （唯一真相源，任何分支文档冲突以此为准）
灵魂裁决链（机械生效，无需协商）：少即是多 > 验证 > 零信任 > 守护 > 文档 > 人本 > 增益
---
## 1. 少即是多
只做必要的、可量化增益的机制；能不做就不做，能简单实现就简单实现，防止系统熵膨胀。少即是多负责取舍，不得绕过铁律、审批或验证。
对应落地实体：feature-registry.yaml、gatekeeper.py、plan_builder.py
---
## 2. 验证 > AI 承诺
CarrorOS 不信任 AI 生成的任何口头结论，所有行为断言必须有可复现证据佐证：测试输出、磁盘日志、内存截图、校验摘要四类证据为法定有效证据，AI 自述、自然语言推演不具备裁决效力。
对应落地实体：compound-verify-gate.py、trace3-e3-completion-gate.md、0003-verifygate-evidence-hierarchy.md
## 3. AI 全链路零信任
CarrorOS 先天不信任 AI 能自主完成状态锁死、修改闭环、边界恪守任意一项要求。开发执行前必须先遍历项目全量依赖树：对存量依赖树全量跑回归测试至 100% 绿，再对新增开发项先写全量失败用例至 100% 红；开发完成后必须对全量依赖树 + 新增代码再跑一轮回归至 100% 绿，禁止跳过任何阶段。
对应落地实体：run-regression.sh、test-*.py 全集合、trace1-e1-scope-defense.md、error-dna.json
## 4. 先守护，后变更
任何涉及不可逆修改、跨路径覆盖、全局状态写入的操作，执行前必须自动将原始快照落地到 `.omc/state/restore/{action_timestamp}/` 目录，并在 lifecycle_ssot 中写入硬链索引；全操作周期内随时支持一键回滚到变更前状态。
对应落地实体：lifecycle_ssot.py、precompact-lifecycle.py、.omc/state/restore 目录约定
## 5. 磁盘状态为唯一真相源
完全不信任 AI 上下文记忆，尤其在上下文窗口溢出、会话压缩、Agent 接力场景下：所有任务状态必须结构化落盘到 `.omc/tasks/{YYYYMMDD}/{task_name}/[research|plan|executor]` 文档集，由 `.omc/tokens/{YYYYMMDD}/{task_name}.json` 令牌做唯一锚点，任务恢复时完全从磁盘读取、不采信内存残余信息。
对应落地实体：token.template.json、task_ssot.py、redirect-mechanism.md、0002-token-lock.md
## 6. 人本独占不可逆裁决
CarrorOS 内置标准化 AI 决策链：`行为合规校验（哲学支撑>不违反铁律>符合当前磁盘状态>高ROI）`，非「删除人类身份凭证、修改生产环境根密码、篡改系统哲学内核」三类不可逆风险场景全部由内核自主决策执行，避免无意义人机交互。仅触发三类风险时将裁决权移交人类，且该裁决结果永久写入证据链不可覆盖。
对应落地实体：pretool-user-approve.py、0005-goal-mode-autonomous-execution.md、handoff.json
## 7. 增益优先，做少得多
所有新增功能必须证明「单行为带来全局可量化增益 > 实现+维护成本」，禁止为了大而全新增无明确收益的模块、钩子、校验规则；无增量增益的冗余代码统一通过僵尸机制处置流程二选一：要么接入主校验链路、要么直接删除。
对应落地实体：feature-registry.yaml、0013-scorecard-gate.md、anti-pattern-redirects.json
EOF
```

---

### ④ 逐条机械验收（命令 + 期望 exit code/stdout）
| 验收命令 | 期望结果 |
|---------|---------|
| `grep -c "^灵魂裁决链.*少即是多 > 验证 > 零信任 > 守护 > 文档 > 人本 > 增益" .claude/references/philosophy.md` | stdout 输出 `2` 且 exit code = 0 |
| `ls .omc/state/restore/philosophy-upgrade-20260730/philosophy.old.md` | 无报错 exit code = 0 |
| `grep -c "^对应落地实体" .claude/references/philosophy.md` | stdout 输出 `14` 且 exit code = 0 |
| `grep "AI 自述、自然语言推演不具备裁决效力" .claude/references/philosophy.md` | 匹配成功 exit code = 0 |
| `grep "开发执行前必须先遍历项目全量依赖树" .claude/references/philosophy.md` | 匹配成功 exit code = 0 |

---

### ⑤ 回滚命令
```bash
# 直接从守护快照恢复原版本
cp .omc/state/restore/philosophy-upgrade-20260730/philosophy.old.md .claude/references/philosophy.md
```

---

### ⑥ 禁止事项
1. 不得在无 ADR、回归测试和人类裁决的情况下修改灵魂裁决链；少即是多保持最高，铁律与硬门禁不可绕过
2. 不得新增第8条顶层哲学，所有新约束必须归入现有7条的子定义范畴
3. 不得删除任何落地实体映射关系，映射的文件必须在项目树根路径下真实存在
4. 不得引入「可根据实际情况调整」这类无边界描述，所有表述必须具备可 grep 校验的明确判定边界