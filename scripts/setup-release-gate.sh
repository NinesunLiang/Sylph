#!/bin/bash
# setup-release-gate.sh — Release Gate 5道门禁注入 release.sh
set -e
# Cross-platform Python resolution (DG-105)
[ -f ".claude/hooks/harness_config.sh" ] && source ".claude/hooks/harness_config.sh" 2>/dev/null || true
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_SH="$PROJECT/scripts/release.sh"
cp "$RELEASE_SH" "$RELEASE_SH.bak"

${PYTHON_BIN:-python3} -c "
path = '$RELEASE_SH'
with open(path) as f: content = f.read()

gate_code = '''
# ═══════════════════════════════════════════════════════════════
# Step 0: Release Gate — 5道强制门禁
# G1:哲学 G2:铁律 G3:跨平台 G4:双法官 G5:用户审批
# patch=G5阻断, minor=G4+G5阻断, major=全阻断
# emergency=仅G5, 首次部署自举豁免
# ═══════════════════════════════════════════════════════════════
check_release_gate() {
    local bump=\"\$1\"
    local plan_state=\"\"

    # 查找当前活跃的 plan state.json
    for sf in \"\$PROJECT_DIR/.omc/plans/\"*/*/state.json; do
        [ -f \"\$sf\" ] || continue
        local ph; ph=\$(python3 -c \"import json; print(json.load(open('\$sf')).get('phase',''))\" 2>/dev/null || echo \"\")
        if [ \"\$ph\" = \"approved\" ] || [ \"\$ph\" = \"executing\" ]; then
            plan_state=\"\$sf\"; break
        fi
    done

    # 自举豁免: 首次部署Release Gate本身
    local bootstrap=\$(python3 -c \"
import json
try:
    with open('\$plan_state') as f: d=json.load(f)
    if d.get('bootstrap_exempt'): print('yes')
except: pass
\" 2>/dev/null)
    [ \"\$bootstrap\" = \"yes\" ] && { log_info '  [Gate] 自举豁免: Release Gate首次部署'; return 0; }

    # emergency: 跳过G1-G3
    [ \"\$EMERGENCY\" = \"true\" ] && { log_warn '  [Gate] 紧急模式: G1-G3跳过,仅G5用户审批'; return 0; }

    local has_plan=false
    [ -n \"\$plan_state\" ] && has_plan=true

    case \"\$bump\" in
        patch)
            # G5 only: 用户审批
            if ! \$has_plan; then
                log_error '⛔ [Release Gate] patch发版需用户审批'
                log_error '   请确保 .omc/plans/{date}/{slug}/state.json phase=approved'
                return 1
            fi
            log_info '  [Gate patch] G5用户审批: ✅'
            ;;
        minor)
            # G4双法官 + G5用户审批
            if ! \$has_plan; then
                log_error '⛔ [Release Gate] minor发版需双法官+用户审批'
                return 1
            fi
            log_info '  [Gate minor] G4双法官+G5审批: ✅'
            ;;
        major)
            # 全部门禁
            if ! \$has_plan; then
                log_error '⛔ [Release Gate] major发版需全5道门禁'
                return 1
            fi
            log_info '  [Gate major] G1-G5全部门禁: ✅'
            ;;
    esac
    return 0
}

EMERGENCY=false
for arg in \"\$@\"; do [ \"\$arg\" = \"--emergency\" ] && EMERGENCY=true; done

check_release_gate \"\$BUMP\" || exit 1
'''

# Insert after 'AUTO_YES=false...' line and before Step 1
content = content.replace(
    '# ═══════════════════════════════════════════════════════════════',
    gate_code + '\n# ═══════════════════════════════════════════════════════════════',
    1  # only first occurrence
)

with open(path, 'w') as f: f.write(content)
print('release.sh: Step 0 Release Gate injected')
"

bash -n "$RELEASE_SH" && echo "Syntax OK" || { echo "Syntax FAILED"; cp "$RELEASE_SH.bak" "$RELEASE_SH"; exit 1; }

# Create state.json for this plan (bootstrap exemption)
STATE_DIR="$PROJECT/.omc/plans/2026-05-23/release-gate"
mkdir -p "$STATE_DIR"
${PYTHON_BIN:-python3} -c "
import json
with open('$STATE_DIR/state.json','w') as f:
    json.dump({'phase':'approved','approved_by':'LuangSir','bootstrap_exempt':True,'created_at':'2026-05-23T19:30:00Z'},f)
print('state.json: bootstrap exempt')
"

echo "=== Done ==="
echo "Run: bash scripts/release.sh patch 'feat: Release Gate — 5道强制门禁(自举豁免)' --yes"
