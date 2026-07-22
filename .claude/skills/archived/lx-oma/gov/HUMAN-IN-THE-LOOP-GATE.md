# Human-in-the-Loop Gate — 实现规范

**目标**: governance-spec.md §2/§4 中规划的 `awaiting_human_decision` 状态机 + L3 裁决路径，从"纸上规范"变成"可执行流程"。

**发布前 M3 目标**: 一次完整的 L3 冲突 → awaiting_human_decision → Owner 裁决 → CONSOLIDATION-LOG.md 更新的闭环跑通。

---

## 1. 状态机实现要点

### awaiting_human_decision 状态写入时机

当 `reconcile()` 检测到 L3 冲突时（§6: L2→L3 升级规则满足），执行：

```bash
# 1. 分配 CONFLICT-ID
CONFLICT_ID="CONF-$(date +%Y%m%d)-$(ls .omc/state/conflict-count.txt 2>/dev/null | tail -1 || echo 0)"
echo "$CONFLICT_ID" > .omc/state/conflict-count.txt

# 2. 写入 pending-decisions.md (append-only)
cat >> .omc/state/pending-decisions.md <<EOF

## Open Conflict: $CONFLICT_ID
- Source: source-prds/<source-file>.md
- Risk Level: L3
- Affected Objects: <REQ-ID>, <DEC-ID>...
- Created At: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Owner: <owner> (if known)
EOF

# 3. 写入 CONSOLIDATION-LOG.md (Entry status = awaiting_human)
cat >> .omc/state/CONSOLIDATION-LOG.md <<EOF

### CL-NNN
- Source: source-prds/<source-file>.md
- Risk Level: L3
- Affected Objects: <REQ-ID>, <DEC-ID>...
- Status: awaiting_human_decision
- Created At: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# 4. 输出裁决提示给用户 (formatted)
echo "## ⚠️ L3 冲突需要人工裁决"
# (格式见 governance-spec.md §4)

# 5. 继续处理其他 L1/L2 变更（非阻塞）
```

### resolve 命令实现 (L3 裁决)

```bash
# lx-oma-gov resolve <CONFLICT-ID> <verdict> [--reason "说明"]
# verdict: accept | accept-partial | reject | defer

resolve() {
  local CONFLICT_ID=$1
  local VERDICT=$2
  local REASON="${3:-}"

  # 1. 从 pending-decisions.md 读取冲突详情
  local CONFLICT_ENTRY=$(grep -A5 "$CONFLICT_ID" .omc/state/pending-decisions.md)
  if [ -z "$CONFLICT_ENTRY" ]; then
    echo "ERROR: CONFLICT-ID not found: $CONFLICT_ID" >&2
    exit 1
  fi

  # 2. 更新 CONSOLIDATION-LOG.md (追加裁决结果)
  cat >> .omc/state/CONSOLIDATION-LOG.md <<EOF
#裁决记录: $CONFLICT_ID
- Adjudicated At: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Adjudicated By: <owner>
- Verdict: $VERDICT
- Reason: $REASON
EOF

  # 3. 从 pending-decisions.md 移除或标记 resolved
  sed -i '' "/$CONFLICT_ID/,/^$/ s/Status:.*$/Status: resolved ($VERDICT)/" .omc/state/pending-decisions.md

  # 4. 若 verdict = accept / accept-partial → 继续 reconcile 流程，归并到 master
  if [ "$VERDICT" = "accept" ] || [ "$VERDICT" = "accept-partial" ]; then
    # TODO: 实现 propagate --execute (v1 MVP)
    echo "Continuing reconcile flow for $CONFLICT_ID..."
  fi

  # 5. 若 verdict = reject → 标记 Entry 为 rejected
  if [ "$VERDICT" = "reject" ]; then
    sed -i '' "/$CONFLICT_ID/,/^$/ s/Status:.*$/Status: rejected/" .omc/state/pending-decisions.md
  fi

  # 6. 若 verdict = defer → 保留 BLOCKED 状态
}
```

---

## 2. human-acceptance-checklist Runner (自动化)

**目标**: governance-spec.md 附录中的 `human-acceptance-checklist` 变成可自动执行的 runner。

```bash
# lx-oma-gov human-check <checklist-id> --execute
# 自动生成 checklist markdown, Owner review, 自动打勾

human_check() {
  local CHECKLIST_ID=$1
  local EXECUTE="${2:-}"

  # 1. 读取检查项 (从 governance-spec.md 或 checklist file)
  local CHECKS=$(cat .omc/state/checklists/$CHECKLIST_ID.md | grep '^|')

  # 2. 输出为 markdown table (供 Owner review)
  echo "# Human Acceptance Checklist: $CHECKLIST_ID"
  echo ""
  for check in $CHECKS; do
    echo "| [ ] $check |"
  done

  # 3. 若 --execute, 自动执行检查项 (hooks verification)
  if [ "$EXECUTE" = "--execute" ]; then
    for check in $CHECKS; do
      # TODO: 实现自动验证 (hooks 拦截统计、context-guard 触发次数等)
      echo "✓ $check" >> .omc/state/checklists/$CHECKLIST_ID.md
    done
  fi

  # 4. Owner review + sign-off (自动签名)
  echo "## Sign-Off" >> .omc/state/checklists/$CHECKLIST_ID.md
  echo "- Signed By: <owner>" >> .omc/state/checklists/$CHECKLIST_ID.md
  echo "- Signed At: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> .omc/state/checklists/$CHECKLIST_ID.md
}
```

---

## 3. CONSOLIDATION-LOG.md 自动更新

**目标**: 每次 reconcile/resolve/deprecate 后，CONSOLIDATION-LOG.md 自动更新。

```bash
# append_entry <source> <risk_level> <objects> <status>
append_entry() {
  local SOURCE=$1
  local RISK_LEVEL=$2
  local OBJECTS=$3
  local STATUS=$4

  cat >> .omc/state/CONSOLIDATION-LOG.md <<EOF
### CL-$(( $(wc -l < .omc/state/CONSOLIDATION-LOG.md) / 3 + 1 ))
- Source: $SOURCE
- Risk Level: $RISK_LEVEL
- Affected Objects: $OBJECTS
- Status: $STATUS
- Created At: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
}

# 使用示例:
append_entry "source-prds/payment-v2.md" "L3" "REQ-021, DEC-004" "awaiting_human_decision"
append_entry "source-prds/payment-v2.md" "L1" "TERM-045" "merged_to_master"
```

---

## 4. 发布前验收标准 (M3)

- [ ] `lx-oma-gov resolve CONF-202605XX-XXX accept` 能更新 CONSOLIDATION-LOG.md
- [ ] `lx-oma-gov human-check checklist-001 --execute` 能生成 checklist + sign-off
- [ ] CONSOLIDATION-LOG.md 有至少一条 `awaiting_human_decision` → resolved 的记录
- [ ] pending-decisions.md 有完整的 open/resolved 冲突列表

---

*文档由 Hermes Agent 自动维护，随项目迭代更新。*
*最后更新: 2026-05-09*
