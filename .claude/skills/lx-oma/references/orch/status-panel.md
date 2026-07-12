# 管线状态面板

> `status` 命令输出模板。

读取 `state/pipeline.yaml`，输出：

```
Pipeline Status
═══════════════════════════════════════════════════════════
  hier: ✅ completed     oma:  ✅ completed
  gov:  🟡 initialized   rpe:  ✅ completed
  dev:  ⬜ pending (parallel mode)
═══════════════════════════════════════════════════════════

Oracle Gates:
  og-001 (hier→oma): ✅ approved  "2 Major + 5 Minor — 全部修复"
  og-002 (oma→gov):  ⬜ pending (routing gate — 不阻塞 dev)
  og-003 (rpe→dev):  ⬜ pending (routing gate — 不阻塞 dev)

Sub PRDs:
  alert-engine       │ oma_done        │ 4 features │ oracle: revised
  notification       │ hier_done       │ 0 features │ oracle: approved
  dashboard          │ hier_done       │ 0 features │ oracle: approved

═══ Parallel Dev — Ready Features ═══
  feat-alert-crud            🟢 rpe_planned  │ oracle: revised
  feat-price-evaluation      🟢 rpe_planned  │ oracle: pending

Next actions:
  /lx-oma-orch advance
  /lx-oma-orch gate og-002 approve
  /lx-oma-orch dev list
```
