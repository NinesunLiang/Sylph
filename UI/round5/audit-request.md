# §17a 审计请求 — CarrorOS 前端夜跑控制面落盘 diff（v3.1 → RC）

> 发给：Opus 4.8 / Grok 4.5 / GPT-5.6 Sol（各一份，内容相同）
> 背景：UI/FINAL.md v3.1（已冻结，四轮十二份评审收敛）。本次请你们审的是**它的落盘实现**——防"方案对、修错"。
> 规格原文：`UI/FINAL.md`；操作规程：`.claude/workflows/frontend-overnight/`（4 份）。

## 待审物件（仓库相对路径，请逐个要文件内容或直接给仓库访问）

```
scripts/carroros-gates/
  lib/gate_result.py          # gate-result 信封库：临时文件→schema校验→fsync→原子rename；reducer fail-closed
  lib/common.sh               # 共享库：control_plane_lock 自验（含 settings.json#hooks 伪条目）
  lib/run-gate.sh             # 通用门禁执行器（C2/C4/C5/C6 外部工具包装）
  scope-check.sh              # C1 范围门禁（diff+untracked ⊆ files_allowed；治理路径零触碰）
  c7-check.sh                 # C3 架构门禁（裸色值/魔法px/:global/!important/antd；O2 指标）
  evidence-check.sh           # C7 证据门禁（evidence-index.yaml + code_sha 新鲜度 + ac 聚合）
  finalize-page.sh            # C8a 定稿（从 gate-results 重算 final_status；token 冲突→FAILED_INVARIANT）
  morning-report.sh           # 晨报 + control-plane-scorecard 机器生成
  abstraction-check.sh        # O1 页内重复度（首夜仅指标）
  preflight.sh                # C0 起飞前总门禁（10 项检查，fail-closed）
  gen-control-plane-lock.sh   # 控制面锁生成器（19 项传递依赖 + settings#hooks 段哈希）
  install-night-hook.sh       # settings.json 幂等挂载器
  assertion-catalog.yaml      # O3 封闭词表 v1.0（8 七态 + 9 浮层断言）
  smoke/run-all.sh            # 五类 smoke 套件
  templates/night-manifest.template.yaml + night-manifest.signoff.template.yaml
.claude/hooks/carroros-night-deny.py   # 夜跑信任边界 hook（5 条 deny 规则，夜会话标记驱动）
.omc/scripts/carros_base.py            # 新增三命令：manifest-json / token-write(CAS) / gate-results-init
.claude/workflows/frontend-overnight/  # README / intake / night-loop / phase0-checklist
```

## 已验证证据（请复核是否充分、有无自欺）

- smoke 13/13 绿：正向/反向/崩溃恢复/fail-open×5（解析失败、缺字段、PASS+exit非0、FAIL+exit0、0文件）/篡改×5（手写token称DONE缺C6→exit3、全PASS→DONE、SUPERSEDED排除、lock哈希不符→exit3、当前控制面一致→exit0）
- 篡改用例 5a 单独验证过失败**原因**（stderr 含 "token 声称 done 但门禁缺失/失败"），非碰巧 exit 3
- preflight 对未签署模板 NO-GO 11 项精确命中；模型路由检查能区分 K3 直连 vs DeepSeek 代理
- 夜跑 deny hook 5 条规则自测全对；白天（无夜会话标记）不生效

## 请你们重点攻击的问题

1. **权威链有没有旁路**：模型在夜间（DeepSeek，有 Bash/Edit/Write，deny hook 生效中）还有没有路径能让早晨看到"假的 DONE"？（假设：它能读全部脚本，不能写控制面；token 只能走 token-write CAS API）
2. **fail-closed 有没有洞**：哪个脚本在异常输入下会"跳过检查算通过"？（重点：common.sh 的 lock 自验、evidence-check 的 evidence-index 契约、finalize 的 reducer 输入）
3. **C1 范围门禁的 glob/前缀逻辑**：target repo 是 CarrorOS 子目录时（git show-prefix 非空）有没有绕过或误杀？
4. **night-loop.md 给 DeepSeek 的手册**：有没有指令模糊到模型会"合理误解"成跳门禁/写结论？
5. **分期输入模型**（intake.md）：api_doc 滞后 + inferred 契约登记，有没有会腐蚀权威链的缝隙？
6. 任何你认为是 P0/P1 的其他问题。

## 回执格式

P0（阻断首夜）/ P1（首夜后必修）/ P2（演进）+ 每条：文件:位置 → 缺陷 → 攻击/失败场景 → 修法建议。没有 P0 请明确说"无新 P0"。
