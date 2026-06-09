#!/usr/bin/env python3
"""
score-delta.py — 语义改进可感知性: before/after runtime 数据对比
P2-7: 记录每项语义修复的 before/after runtime 数据
用法: python3 .claude/scripts/score-delta.py [--since <timestamp>]
"""
import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TS = datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def pct(a: int, b: int) -> str:
    if b == 0:
        return "0"
    return f"{a * 100 / b:.1f}"


def run(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    return subprocess.run(cmd, **default)


def main():
    os.chdir(str(PROJECT_ROOT))

    since_ts = sys.argv[2] if len(sys.argv) > 2 else "0"
    output_file = STATE_DIR / f"score-delta-{TS}.json"
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== Score Delta v1 (语义改进可感知性) @ {TS} ===")

    # R1: Flywheel 覆盖率变化
    fw_log = Path.home() / ".claude" / "flywheel.log"
    fw_covered = 0
    if fw_log.exists() and fw_log.stat().st_size > 0:
        lines = fw_log.read_text(encoding="utf-8").splitlines()
        unique = set()
        for line in lines:
            parts = line.split(",")
            if len(parts) >= 2:
                unique.add(parts[1].strip())
        fw_covered = len(unique)
    
    harness_yaml = PROJECT_ROOT / ".claude" / "harness.yaml"
    fw_enabled = 0
    if harness_yaml.exists():
        text = harness_yaml.read_text(encoding="utf-8")
        in_hooks = False
        for line in text.splitlines():
            if line.startswith("hooks_enabled:"):
                in_hooks = True
                continue
            if in_hooks and line.startswith("  ") and ": true" in line:
                fw_enabled += 1
            elif in_hooks and not line.startswith("  "):
                in_hooks = False

    fw_pct = pct(fw_covered, fw_enabled)

    # R2: Error DNA 噪声率
    ed_total = 0
    ed_noise = 0
    ed_path = STATE_DIR / "error-dna.jsonl"
    if ed_path.exists():
        ed_total = len(ed_path.read_text(encoding="utf-8").splitlines())
        ed_noise = sum(1 for line in ed_path.read_text(encoding="utf-8").splitlines() if '"status": "noise"' in line)
    ed_noise_pct = pct(ed_noise, ed_total)

    # R3: 矛盾检测统计
    cont_total = 0
    cont_true = 0
    cont_bash = 0
    churn_path = STATE_DIR / "edit-churn-log.jsonl"
    if churn_path.exists():
        lines = churn_path.read_text(encoding="utf-8").splitlines()
        cont_total = len(lines)
        for line in lines:
            if '"contradiction": true' in line:
                cont_true += 1
            if '"type": "bash_edit"' in line:
                cont_bash += 1

    # R4: Hook 证据覆盖率
    hooks_dir = PROJECT_ROOT / ".claude" / "hooks"
    hook_total = len([f for f in hooks_dir.glob("*.sh")
                      if f.name not in ("harness_config.sh", "agentic-ui.sh")])
    hook_evid = 0
    hook_ev_path = STATE_DIR / "hook-evidence.jsonl"
    if hook_ev_path.exists():
        unique = set()
        for line in hook_ev_path.read_text(encoding="utf-8").splitlines():
            parts = line.split('"')
            if len(parts) >= 4:
                unique.add(parts[3])
        hook_evid = len(unique)
    hook_evid_pct = pct(hook_evid, hook_total)

    # R5: 构建健康度
    build_streak = 0
    build_path = STATE_DIR / "build-fail-gate.json"
    if build_path.exists():
        try:
            d = json.loads(build_path.read_text(encoding="utf-8"))
            build_streak = d.get("streak", 0)
        except Exception:
            pass

    # 语义改进可感知清单
    delta_items = []

    # E6: 假阳性率变化
    if cont_true > 0 and cont_total > 0:
        revert_count = 0
        for line in churn_path.read_text(encoding="utf-8").splitlines():
            if '"type": "revert"' in line:
                revert_count += 1
        cont_fp = max(0, cont_true - revert_count)
        cont_fp_rate = pct(cont_fp, cont_true)
        delta_items.append(f"E6: contradiction=true 计数={cont_true}, 回退确认={revert_count}")

    # C8: 源镜像漂移状态
    audit_script = PROJECT_ROOT / ".claude" / "scripts" / "audit-hooks.sh"
    if audit_script.exists():
        result = run(f"bash {audit_script} --check-source-mirror 2>/dev/null")
        for line in result.stdout.splitlines():
            if "🔴 严重:" in line:
                mirror_red = line.split("🔴 严重:")[-1].strip().split()[0]
                delta_items.append(f"C8: source mirror CRITICAL 漂移={mirror_red}")
                break
        else:
            delta_items.append("C8: source mirror 无严重漂移")

    # Bash 编辑检测覆盖率 (DG-107)
    if cont_bash > 0:
        delta_items.append(f"P0-2: Bash 编辑检测已激活, 记录={cont_bash}条")
    else:
        delta_items.append("P0-2: Bash 编辑检测待验证（无 Bash 编辑记录）")

    # Retry-Budget 清理状态 (P1-4)
    rb_path = STATE_DIR / "retry-budget.json"
    if rb_path.exists():
        try:
            d = json.loads(rb_path.read_text(encoding="utf-8"))
            rb_count = len(d.get("signatures", {}))
            delta_items.append(f"P1-4: retry-budget 签名数={rb_count}")
        except Exception:
            delta_items.append("P1-4: retry-budget 解析失败")
    else:
        delta_items.append("P1-4: retry-budget 已清理（build 成功自动清除）")

    print("--- 运行时快照 ---")
    print(f"R1 飞轮覆盖率:       {fw_covered}/{fw_enabled} = {fw_pct}%")
    print(f"R2 错误信噪比:       {ed_noise}/{ed_total} = {ed_noise_pct}%")
    print(f"R3 矛盾检测:         总计={cont_total} 矛盾标记={cont_true} Bash编辑={cont_bash}")
    print(f"R4 Hook证据:          {hook_evid}/{hook_total} = {hook_evid_pct}%")
    print(f"R5 构建健康:         streak={build_streak}")
    print("---")
    delta_str = " ".join(delta_items)
    print(f"语义改进可感知: {delta_str}")

    # JSON 输出
    report = {
        "generated_at": TS,
        "runtime_snapshot": {
            "flywheel_coverage_pct": float(fw_pct),
            "error_dna_noise_pct": float(ed_noise_pct),
            "contradiction_total": cont_total,
            "contradiction_true": cont_true,
            "bash_edits_detected": cont_bash,
            "hook_evidence_pct": float(hook_evid_pct),
            "build_streak": build_streak,
        },
        "semantic_improvements": delta_str,
    }
    output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("---")
    print(f"Delta written: {output_file}")


if __name__ == "__main__":
    main()
