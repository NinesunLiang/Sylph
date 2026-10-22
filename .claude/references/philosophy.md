# CarrorOS 哲学体系（裁决链落地实体 + 禁止事项）

> **裁决链（7 条灵魂）唯一真相源 = `AGENTS.md` §灵魂**（每次会话自动加载）。
> 本文件不复述裁决链原文，只承载：① 7 条各自的落地实体映射（可 grep 校验，文件必须真实存在）② 禁止事项。
> 改裁决链 → 改 `AGENTS.md`；改落地实体 → 改本文件。两处冲突时，裁决链以 AGENTS.md 为准，落地实体以本文件为准。

## 裁决链（指向 AGENTS.md，此处不重复原文）

`AGENTS.md §灵魂`：少即是多 > 验证 > 零信任 > 守护 > 文档 > 人本 > 增益（机械生效，无需协商）

## 落地实体映射（每条哲学的可 grep 锚点）

| 哲学 | 落地实体（文件必须真实存在） |
|------|------|
| 1 少即是多 | feature-registry.yaml、gatekeeper.py、plan_builder.py |
| 2 验证 | verify_gate.py、adr/0003-verifygate-evidence-hierarchy.md |
| 3 零信任 | run-regression.sh、test-*.py 全集合 |
| 4 守护 | hooks/lib/lifecycle_ssot.py、hooks/precompact-lifecycle.py、.omc/state/restore/ 目录约定 |
| 5 文档 | token.json（carros_base.py init 生成）、scripts/lib/task_ssot.py、redirect-mechanism.md、adr/0002-token-lock-task-lifecycle.md |
| 6 人本 | hooks/pretool-user-approve.py、adr/0005-goal-mode-autonomous-execution.md、handoff.json |
| 7 增益 | feature-registry.yaml、adr/0013-scorecard-self-rating-audit-gate.md、anti-patterns.md |

> 已移除映射：`trace1-e1-scope-defense.md`（文件不存在，零信任回归由 run-regression.sh + test-*.py 承载）、`anti-patterns.json`（实际为 .md）、`lifecycle_ssot.py`/`task_ssot.py` 路径已修正到真实位置。

---

### 禁止事项
1. 不得在无 ADR、回归测试和人类裁决的情况下修改 AGENTS.md §灵魂裁决链；少即是多保持最高，铁律与硬门禁不可绕过
2. 不得新增第8条顶层哲学，所有新约束必须归入现有7条的子定义范畴
3. 不得删除任何落地实体映射关系，映射的文件必须在项目树根路径下真实存在
4. 不得引入「可根据实际情况调整」这类无边界描述，所有表述必须具备可 grep 校验的明确判定边界
