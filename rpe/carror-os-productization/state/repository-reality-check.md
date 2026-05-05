# Repository Reality Check

> **Date**: 2026-05-04
> **Scope**: Full Carror OS repository scan before Phase 1 execution

---

## 1. Inventory

| Category | Count | Notes |
|----------|-------|-------|
| Hooks (.sh) | 27 | proactive-handoff.sh 超出文档声称的 26，但无冲突 |
| Skills (SKILL.md) | 23 | 匹配文档声称 |
| Skills (total entries) | 25 | + TEMPLATE.md + VERSION |
| Scripts (.py) | 3 | context_monitor.py（僵尸，见下文）、oma_lock_manager.py、test_oma_lock.py |
| Docs (.md) | 57 | 分布于 6 个子目录 |
| Empty files (excl. node_modules) | 2 | registry.yaml (0B, schema output 占位), .last-user-prompt (0B, OMC state) |

---

## 2. Key Path Verification

| Path | Expected | Actual | Verdict |
|------|---------|--------|---------|
| `AGENTS.md` | 存在 | ✅ 存在 | ✅ PASS |
| `CLAUDE.md` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/harness.yaml` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/harness_config.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/completion-gate.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/context-guard.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/permission-gate.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/privacy-gate.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/hooks/error-dna.sh` | 存在 | ⚠️ 存在但损坏 | ⚠️ Known (RPE-001) |
| `.claude/hooks/pretool-edit-scope.sh` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/scripts/context_monitor.py` | 存在 | ✅ 存在 | ⚠️ Zombie (见 4.2) |
| `.claude/scripts/oma_lock_manager.py` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/feature-registry.yaml` | 需创建 | ❌ 不存在 | ⚠️ Planned (RPE-004) |
| `.claude/skills/lx-status/SKILL.md` | 存在 | ✅ 存在 | ✅ PASS |
| `.claude/skills/lx-rpe/SKILL.md` | 存在 | ✅ 存在 | ✅ PASS |
| `rpe/carror-os-productization/` | 存在 | ✅ 存在 | ✅ PASS |

---

## 3. Empty & Placeholder Detection

| File | Size | Nature |
|------|------|--------|
| `.claude/schemas/output/registry.yaml` | 0B | 空 schema output, 无影响 |
| `.omc/state/.last-user-prompt` | 0B | OMC 状态文件, 正常 |
| `.claude/skills/lx-frontend-test/SKILL.md` | 9 lines | 极简，可能仅为占位符 |

**Verdict**: 无严重空文件问题。lx-frontend-test 过短，非关键路径。

---

## 4. Pre-identified Issues (Research Cross-check)

### 4.1 error-dna.sh — 确认损坏

文件 281 字节，4 bug 全部确认：
- Line 5-6: `[ "$TOOL_NAME" != "\nbash" ]` — 嵌入式换行符使 `bash` 命令永不匹配
- Line 10: `mkdir -p .omc/state echo` — 无 `&&` 分隔，创建名为 `echo` 的目录
- `$DNA_FILE` 未定义 — 写入目标无效
- 换行损坏 JSON — 生成非法 JSON

**→ RPE-001 完全重写**

### 4.2 context_monitor.py — 僵尸代码确认

- `context_monitor.py` 磁盘存在 (53 行, 逻辑完整)
- 但 `token-tracking-index.json` **不存在** — 无任何文件写入此路径
- proactive-handoff.sh 调用 context_monitor.py → 读取默认值 usage=0, limit=200000 → 永不会触发 50% 报警

**→ RPE-003 AC-3.3 创建写入者或移除引用**

### 4.3 Doc-Content Mismatch

| File | Issue | Severity |
|------|-------|----------|
| `docs/technical/product-guide.md` | 含"终极审判"等内部语气 | ⚠️ Low (RPE-010 修复) |
| `docs/technical/architecture-review.md` | 多处"终极"/"终极原因"等内部语气 | ⚠️ Low (RPE-010 修复) |

**→ RPE-010 marketing 重写时一并处理**

---

## 5. Version Consistency

| Source | Version |
|--------|---------|
| `.claude/skills/VERSION` | 6.1.8 |
| `README.md` badge | v6.1.8 |
| AGENTS.md header | v6.1.8 |

**Verdict**: ✅ 一致

---

## 6. Phase Execution Readiness

| Phase | BLOCKED? | Condition |
|-------|----------|-----------|
| Phase 0 (RPE-000) | ✅ **GO** | 本报告完成 |
| Phase 1 (RPE-001~005) | ✅ **GO** | 关键路径均存在，损坏组件有明确修复路径 |
| Phase 1.5 (RPE-012~013) | ⚠️ 阻塞 | 依赖 Phase 1 修复就绪 |
| Phase 2 (RPE-006~008) | ✅ **GO** | 无硬依赖阻塞 |
| Phase 3 (RPE-010~011) | ⚠️ 阻塞 | 依赖 Phase 2 完成 |
| Phase 5 (RPE-014~017) | ✅ **GO** | 无硬依赖阻塞 |

**Per AC-0.6**: 关键实现路径全部确认存在。无 BLOCKED。

---

## 7. Summary

```
✅ Hooks: 27 (all gates present, error-dna.sh needs rewrite)
✅ Skills: 23 (lx-frontend-test minimal, non-critical)
✅ Scripts: 3 (context_monitor.py zombie, RPE-003 fix)
✅ Docs: 57 .md files, 6 directories
✅ Key paths: 13/14 verified, feature-registry.yaml planned
✅ Empty files: 2, both benign
✅ Version consistency: 6.1.8 across all sources
✅ Phase readiness: Phase 0+1+2+5 GO, Phase 1.5+3 blocked on dependencies
```

**No blocking issues found. Phase 1 can proceed.**
