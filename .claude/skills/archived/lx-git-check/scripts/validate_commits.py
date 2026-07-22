#!/usr/bin/env python3

"""

校验待推送 commit 的 message 格式（硬编码规则，降级备用，推荐使用 commit_convention.py）。

用法：python3 validate_commits.py --prod-commit <hash>

exit 0=全通过，2=有红线/阻塞违规

"""

import argparse, subprocess, sys, json, re


ALLOWED_TYPES = {"feat","fix","perf","test","docs","style","refactor","build","other","merge","revert"}
HEADER_RE = re.compile(r'^(feat|fix|perf|test|docs|style|refactor|build|other|merge|revert)(\([^)]+\))?!?: .+')
ISSUE_RE = re.compile(r'[a-zA-Z0-9_]+#\d+')

def run(cmd):
    # nosec B602: skill 层 CLI 工具，cmd 为内部 git 命令拼接，非用户原始输入
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)  # nosec B602
    return r.stdout.strip()

def validate_commit(hash_, subject, body):
    violations = []
    type_match = re.match(r'^([a-z]+)', subject)
    type_val = type_match.group(1) if type_match else ""
    if type_val not in ALLOWED_TYPES:
        violations.append({"rule":"M1","level":"block","msg":f"type '{type_val}' 不在允许列表"})
    if not HEADER_RE.match(subject):
        violations.append({"rule":"M2/M3","level":"block","msg":"Header 格式不符合 type(scope): 描述"})
    desc = re.sub(r'^[^:]+:\s*', '', subject)
    if len(desc) > 50:
        violations.append({"rule":"M3","level":"block","msg":f"标题过长({len(desc)}字符，限50)"})
    if type_val in ("feat","perf"):
        full_text = subject + "\n" + body
        if not ISSUE_RE.search(full_text):
            violations.append({"rule":"M5" if type_val=="feat" else "M6", "level":"redline","msg":f"{type_val} 类型必须包含 Issue-ID（格式：项目名#ID）"})
    return violations

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prod-commit", required=True)
    args = p.parse_args()

    raw = run(f"git log {args.prod_commit}...HEAD --format='%H|||%s|||%b|||END'")
    if not raw:
        print(json.dumps({"status":"no_commits","violations":[]}))
        sys.exit(0)

    commits = []
    has_redline = False
    for block in raw.split("|||END"):
        block = block.strip()
        if not block:
            continue
        parts = block.split("|||")
        if len(parts) < 3:
            continue
        hash_, subject, body = parts[0].strip(), parts[1].strip(), parts[2].strip()
        violations = validate_commit(hash_, subject, body)
        if any(v["level"] == "redline" for v in violations):
            has_redline = True
        commits.append({"hash": hash_[:8], "subject": subject, "violations": violations, "passed": len(violations)==0})

    total_blocked = sum(1 for c in commits if not c["passed"])
    print(json.dumps({
        "total": len(commits), "passed": len(commits)-total_blocked,
        "blocked": total_blocked, "has_redline": has_redline, "commits": commits
    }, ensure_ascii=False, indent=2))
    sys.exit(2 if total_blocked > 0 else 0)

if __name__ == "__main__":
    main()
