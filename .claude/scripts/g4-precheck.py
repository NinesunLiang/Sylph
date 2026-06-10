#!/usr/bin/env python3
"""G4 预检：在 package-release.sh 中收集检查结果 + 注入 Meta-Oracle critic。

完全在 Python 中执行所有检查，不受 bash set -eo pipefail 的影响。
输出：检查日志 + 裁决结果 + 证据文件路径。

用法：
    python3 .claude/scripts/g4-precheck.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")

VERSION = ""
try:
    VERSION = json.loads(Path(PROJECT_ROOT, "VERSION.json").read_text())["version"]
except Exception:
    VERSION = "unknown"


def log_info(msg):
    print(f"  [INFO] {msg}")


def log_pass(msg):
    print(f"  ✅ {msg}")


def log_fail(msg):
    print(f"  [FAIL] {msg}")


def log_warn(msg):
    print(f"  [WARN] {msg}")


# ── 检查项 ────────────────────────────────────────────────────────────

results = []

# G4.1: source mirror
source_mirror_ok = False
audit_sh = Path(PROJECT_ROOT, ".claude", "scripts", "audit-hooks.sh")
if audit_sh.is_file() and os.access(str(audit_sh), os.X_OK):
    log_info("[G4.1] source mirror 一致性检查...")
    try:
        r = subprocess.run(
            ["bash", str(audit_sh), "--check-source-mirror"],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        print(r.stdout)
        if r.returncode == 0:
            log_pass("source mirror 一致")
            source_mirror_ok = True
        else:
            log_fail(f"source mirror 漂移 (exit={r.returncode})")
    except subprocess.TimeoutExpired:
        log_fail("source mirror 检查超时")
else:
    log_warn("audit-hooks.sh 不存在，跳过 source mirror 检查")
results.append(("source mirror 一致性", "PASS" if source_mirror_ok else "FAIL"))

# G4.2: smoke test
smoke_ok = False
smoke_failures = 0
smoke_py = Path(PROJECT_ROOT, ".claude", "scripts", "harness-smoke-test.py")
smoke_sh = Path(PROJECT_ROOT, ".claude", "scripts", "harness-smoke-test.sh")
skip_smoke = "--skip-smoke" in sys.argv

if skip_smoke:
    log_warn("[G4.2] harness-smoke-test SKIPPED (--skip-smoke)")
    smoke_ok = True
elif smoke_py.is_file():
    log_info("[G4.2] harness-smoke-test.py...")
    try:
        r = subprocess.run(
            [sys.executable, str(smoke_py)],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_ROOT,
        )
        if r.stdout:
            for line in r.stdout.splitlines():
                if line.strip():
                    print(f"    {line}")
        if r.returncode == 0:
            # 统计 FAIL 行
            fail_count = len([l for l in r.stdout.splitlines()
                              if re.search(r'FAIL=[1-9]|🔴', l)])
            if fail_count == 0:
                log_pass("smoke test 全绿")
                smoke_ok = True
                smoke_failures = 0
            else:
                log_warn(f"smoke test 有 {fail_count} 项失败")
                smoke_failures = fail_count
        else:
            log_warn(f"smoke test exit={r.returncode}")
            smoke_failures = -1
    except subprocess.TimeoutExpired:
        log_warn("smoke test 超时")
elif smoke_sh.is_file():
    log_info("[G4.2] harness-smoke-test.sh...")
    try:
        r = subprocess.run(
            ["bash", str(smoke_sh)],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_ROOT,
        )
        if r.stdout:
            for line in r.stdout.splitlines():
                if line.strip():
                    print(f"    {line}")
        fail_count = len([l for l in r.stdout.splitlines()
                          if re.search(r'FAIL=[1-9]|🔴', l)])
        if fail_count == 0 and r.returncode == 0:
            log_pass("smoke test 全绿")
            smoke_ok = True
            smoke_failures = 0
        else:
            log_warn(f"smoke test exit={r.returncode}, failures={fail_count}")
            smoke_failures = fail_count
    except subprocess.TimeoutExpired:
        log_warn("smoke test 超时")
else:
    log_warn("smoke test 脚本不存在，跳过")

smoke_status = "PASS" if smoke_ok else f"FAIL ({smoke_failures} failures)"
results.append(("harness smoke test", smoke_status))

# G4.3: VERSION.json
version_ok = False
version_path = Path(PROJECT_ROOT, "VERSION.json")
if version_path.is_file():
    log_info("[G4.3] VERSION.json 一致性...")
    try:
        v = json.loads(version_path.read_text())
        ver = v.get("version", "")
        if ver == VERSION:
            log_pass(f"VERSION.json 一致 ({ver})")
            version_ok = True
        else:
            log_fail(f"VERSION.json 版本 {ver} != 期望 {VERSION}")
    except (json.JSONDecodeError, OSError) as e:
        log_fail(f"VERSION.json 读取失败: {e}")
else:
    log_fail("VERSION.json 不存在")
results.append(("VERSION.json 一致性", "PASS" if version_ok else "FAIL"))

# ── 注入 Meta-Oracle critic ──────────────────────────────────────────

# 写证据文件
evidence = "\n".join(f"  {name}: {value}" for name, value in results)
evidence_file = f"/tmp/g4-evidence-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
Path(evidence_file).write_text(evidence)
print(f"\n[EVIDENCE FILE: {evidence_file}]")

# 调用 meta-oracle-review.py，注入检查结果
meta_oracle_py = Path(PROJECT_ROOT, ".claude", "scripts", "meta-oracle-review.py")
if meta_oracle_py.is_file():
    log_info("Calling Meta-Oracle critic with evidence injection...")
    env = os.environ.copy()
    env["G4_CHECK_RESULTS"] = evidence
    try:
        r = subprocess.run(
            [sys.executable, str(meta_oracle_py), "G4"],
            capture_output=True, text=True, timeout=120,
            cwd=PROJECT_ROOT, env=env,
        )
        if r.stdout:
            print(r.stdout)
        if r.stderr:
            print(r.stderr, file=sys.stderr)
        # 提取裁决
        verdict_match = re.search(
            r'\[Meta-Oracle: (ACCEPT|ADVISORY|REJECT)\]',
            r.stdout or "",
        )
        if verdict_match:
            print(f"\n[Meta-Oracle: {verdict_match.group(1)}]")
    except subprocess.TimeoutExpired:
        print("[ERROR] Meta-Oracle critic 超时", file=sys.stderr)
else:
    log_warn("meta-oracle-review.py 不存在")
    print("\n[NO VERDICT: meta-oracle-review.py missing]")

# ── 清理 ──
# 证据文件在 bash 端清理
