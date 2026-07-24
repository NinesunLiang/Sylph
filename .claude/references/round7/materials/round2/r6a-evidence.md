# R6-A 证据包(E7 oracle 三层精确 BLOCK)

> 索取方：GPT #6。2026-07-20 组装。

## 1. 对抗测试脚本

`snapshots/test-oracle-gate.py`(源：`scripts/test-oracle-gate.py`,8,574 bytes)。

## 2. 31/31 结果

- 结论记录：`improve_plan/CarrorOS_second_time/scorecard.md` + `round4/verdict-reconciliation.md`(31 条对抗用例全 BLOCK,0 漏过 0 误伤)。
- **完整逐条日志：已被 owner 指令清理**(fb89180「清理过程材料与日志——round1/2 materials+R5 终审包+round4 复跑日志」)。诚实声明：现存为结论性记录，非逐条 stdout。
- 可复现：`python3 scripts/test-oracle-gate.py` 随时重跑(round6 回归 4 次均含此套件，PASS)。

## 3. Gate 7 最终 diff

- 施工 commit：`6dcfb90`(feat: R6-A+C 受限施工——E7 oracle 三层精确 BLOCK(31/31 对抗)+R6-C 选定 E2→9)。
- 查看：`git show 6dcfb90 -- .claude/hooks/pretool-gate.py`
- 三层语义：oracle 置信声明 → 无证据 **BLOCK** / 证据弱 **ESCALATE** / 叙事性措辞 **hint**。

## 4. R6 后 hash drift(pretool-gate.py)

```text
e6026aa feat:消除token影响            ← 终态过滤(幻影修复)+ round7 材料
20c41bf feat: settings.json hook 锚定+密钥脱敏
c97e670 feat: round6 迭代2+3(仅 scripts/ 与报告,未动 gate)
```

即 R6-A 后 gate 本体的唯一实质变更 = e6026aa 终态过滤(`_latest_token` 重写),Gate 7 逻辑未动。

## 5. R6-A / R6-C commit 清单

| commit | 内容 |
|---|---|
| `6dcfb90` | R6-A+C 受限施工(三层 BLOCK + E2→9,8.51→8.65 并账) |
| `3ba3d95` | R6 终审收口(R6-A/C 3:0 通过 + owner 裁决内置安全视为通过,ALL_GATES_MET) |
