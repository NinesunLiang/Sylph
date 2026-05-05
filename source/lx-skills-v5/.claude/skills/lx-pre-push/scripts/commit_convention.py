#!/usr/bin/env python3

"""

commit_convention.py — 通用 commit message 规范管理器


学习一个示例 commit → 提取骨架 → 存储 → 后续校验用骨架而非硬编码规则
用法： python3 commit_convention.py learn "<commit message 示例>" # 从示例学习规范
 python3 commit_convention.py validate "<commit message>" # 按骨架校验
 python3 commit_convention.py show # 展示当前规范
 python3 commit_convention.py reset # 删除当前规范
 python3 commit_convention.py validate-batch --prod <hash> # 批量校验待推送 commits
exit: 0=通过/成功, 1=参数错误, 2=不合规, 3=无规范（需先 learn）
"""
import argparse, sys, json, re, subprocess
from pathlib import Path
from datetime import datetime

CONVENTION_FILE = Path(".omc/state/commit-convention.json")

def run(cmd: str):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

# ── 从示例 commit 提取骨架 ─────────────────────────────────────
def extract_skeleton(sample: str) -> dict:
    """分析示例 commit message，提取骨架规则。不假设任何特定规范，纯粹从示例推断。"""
    lines = sample.strip().split('\n')
    header = lines[0] if lines else ""
    body_lines = lines[2:] if len(lines) > 2 else []
    footer_lines = []
    body_content = []

    # 分离 body 和 footer（空行隔开）
    in_footer = False
    for line in body_lines:
        if re.match(r'^[A-Za-z-]+:', line) or re.match(r'^BREAKING CHANGE', line):
            in_footer = True
        if in_footer:
            footer_lines.append(line)
        else:
            body_content.append(line)

    skeleton = {
        "version": "1.0",
        "learned_at": datetime.now().isoformat(),
        "sample": sample,
        "header": _analyze_header(header),
        "has_body": len(body_content) > 0,
        "body_pattern": _analyze_body(body_content),
        "has_footer": len(footer_lines) > 0,
        "footer_keys": _extract_footer_keys(footer_lines),
        "max_header_length": max(72, len(header) + 10),
        "rules_inferred": []
    }

    h = skeleton["header"]
    if h["has_type"]:
        skeleton["rules_inferred"].append(f"Header 以 type 开头，格式：{h['type_pattern']}")
    if h["has_scope"]:
        skeleton["rules_inferred"].append(f"scope 用 {h['scope_delimiter']} 包裹")
    if h["has_separator"]:
        skeleton["rules_inferred"].append(f"type/scope 与描述用 '{h['separator']}' 分隔")
    if skeleton["has_footer"]:
        skeleton["rules_inferred"].append(f"Footer 包含键：{skeleton['footer_keys']}")

    return skeleton

def _analyze_header(header: str) -> dict:
    """分析 header 结构"""
    result = {
        "raw": header, "has_type": False, "type_value": None, "type_pattern": None,
        "has_scope": False, "scope_value": None, "scope_delimiter": None,
        "has_separator": False, "separator": None, "description": header,
    }
    m = re.match(r'^([a-zA-Z][a-zA-Z0-9_-]*)(\([^)]+\))?(!)?([:\s]+)(.*)', header)
    if m:
        result["has_type"] = True
        result["type_value"] = m.group(1)
        result["type_pattern"] = f"[a-zA-Z][a-zA-Z0-9_-]*"
    if m.group(2):
        result["has_scope"] = True
        result["scope_value"] = m.group(2)[1:-1]
        result["scope_delimiter"] = "()"
    sep = m.group(4).strip()
    result["has_separator"] = True
    result["separator"] = sep
    result["description"] = m.group(5).strip()
    return result

def _analyze_body(body_lines: list) -> str:
    if not body_lines:
        return ""
    if any(l.strip().startswith('-') or l.strip().startswith('*') for l in body_lines):
        return "list"
    if any(re.match(r'^\d+\.', l.strip()) for l in body_lines):
        return "numbered"
    return "paragraph"

def _extract_footer_keys(footer_lines: list) -> list:
    keys = []
    for line in footer_lines:
        m = re.match(r'^([A-Za-z][A-Za-z0-9-]*):', line)
        if m:
            keys.append(m.group(1))
    return list(set(keys))

# ── 按骨架校验 commit ─────────────────────────────────────────
def validate_against_skeleton(commit_msg: str, skeleton: dict) -> tuple[bool, list]:
    """按存储的骨架校验，返回 (passed, violations)"""
    violations = []
    lines = commit_msg.strip().split('\n')
    header = lines[0] if lines else ""
    h_rule = skeleton["header"]

    if len(header) > skeleton["max_header_length"]:
        violations.append(f"Header 过长（{len(header)}字符 > 限制{skeleton['max_header_length']}）")

    if h_rule["has_type"]:
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*', header):
            violations.append("Header 缺少 type 前缀")

    if h_rule["has_separator"] and h_rule["separator"]:
        sep = h_rule["separator"]
        if sep not in header:
            violations.append(f"Header 缺少分隔符 '{sep}'")

    if len(lines) > 1 and lines[1].strip():
        violations.append("Header 与 body 之间缺少空行（Git 规范）")

    return len(violations) == 0, violations

# ── 批量校验待推送 commits ────────────────────────────────────
def validate_batch(prod_commit: str, skeleton: dict) -> dict:
    code, out, _ = run(f"git log {prod_commit}...HEAD --format='%H|||%s|||%b|||END'")
    if code != 0 or not out:
        return {"total": 0, "commits": [], "passed": True}

    results = []
    for block in out.split("|||END"):
        block = block.strip()
        if not block:
            continue
        parts = block.split("|||")
        if len(parts) < 2:
            continue
        hash_ = parts[0].strip()
        subject = parts[1].strip()
        body = parts[2].strip() if len(parts) > 2 else ""
        full = f"{subject}\n\n{body}".strip() if body else subject
        passed, violations = validate_against_skeleton(full, skeleton)
        results.append({
            "hash": hash_[:8], "subject": subject[:60],
            "passed": passed, "violations": violations
        })

    total = len(results)
    failed = [r for r in results if not r["passed"]]
    return {"total": total, "passed": len(failed) == 0, "failed_count": len(failed), "commits": results}

# ── 主程序 ────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="通用 commit message 规范管理器")
    p.add_argument("action", choices=["learn", "validate", "show", "reset", "validate-batch"])
    p.add_argument("message", nargs="?", help="示例 commit 或待校验 commit")
    p.add_argument("--prod", help="validate-batch 用：线上版本 commit hash")
    args = p.parse_args()

    CONVENTION_FILE.parent.mkdir(parents=True, exist_ok=True)

    if args.action == "learn":
        if not args.message:
            print(json.dumps({"error": "请提供示例 commit message"}))
            sys.exit(1)
        skeleton = extract_skeleton(args.message)
        CONVENTION_FILE.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2))
        print(json.dumps({
            "status": "learned", "rules_inferred": skeleton["rules_inferred"],
            "footer_keys": skeleton["footer_keys"],
            "max_header_length": skeleton["max_header_length"],
            "convention_file": str(CONVENTION_FILE)
        }, ensure_ascii=False, indent=2))

    elif args.action == "show":
        if not CONVENTION_FILE.exists():
            print(json.dumps({"status": "no_convention", "message": "尚未学习任何规范，请运行 learn"}))
            sys.exit(3)
        skeleton = json.loads(CONVENTION_FILE.read_text())
        print(json.dumps({
            "status": "exists", "learned_at": skeleton.get("learned_at"),
            "sample": skeleton.get("sample"), "rules_inferred": skeleton.get("rules_inferred", []),
            "max_header_length": skeleton.get("max_header_length"),
            "footer_keys": skeleton.get("footer_keys", [])
        }, ensure_ascii=False, indent=2))

    elif args.action == "reset":
        if CONVENTION_FILE.exists():
            CONVENTION_FILE.unlink()
            print(json.dumps({"status": "reset", "message": "规范已删除，恢复无约束状态"}))
        else:
            print(json.dumps({"status": "nothing_to_reset"}))

    elif args.action == "validate":
        if not CONVENTION_FILE.exists():
            print(json.dumps({"status": "no_convention", "passed": True, "message": "无存储规范，跳过校验（运行 learn 设置规范）"}))
            sys.exit(0)
        if not args.message:
            print(json.dumps({"error": "请提供待校验的 commit message"}))
            sys.exit(1)
        skeleton = json.loads(CONVENTION_FILE.read_text())
        passed, violations = validate_against_skeleton(args.message, skeleton)
        print(json.dumps({"passed": passed, "violations": violations, "message_preview": args.message[:80]}, ensure_ascii=False, indent=2))
        sys.exit(0 if passed else 2)

    elif args.action == "validate-batch":
        if not args.prod:
            print(json.dumps({"error": "--prod <commit> 必须提供"}))
            sys.exit(1)
        if not CONVENTION_FILE.exists():
            print(json.dumps({"status": "no_convention", "passed": True, "message": "无存储规范，跳过校验"}))
            sys.exit(0)
        skeleton = json.loads(CONVENTION_FILE.read_text())
        result = validate_batch(args.prod, skeleton)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["passed"] else 2)

if __name__ == "__main__":
    main()
