#!/usr/bin/env python3
"""
已修复的数据处理脚本：
- 修复 1: 从命令行参数或标准输入读取 CSV 数据
- 修复 2: 空列表时返回空结果而非除零
"""
import json
import sys

def parse_csv(content):
    rows = []
    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        try:
            score = float(parts[1].strip())
        except ValueError:
            continue
        rows.append({"name": name, "score": score})
    return rows

def filter_pass(rows, threshold=60):
    return [r for r in rows if r["score"] >= threshold]

def calc_stats(rows):
    if not rows:
        return {"total": 0, "avg": 0, "count": 0}
    total = sum(r["score"] for r in rows)
    avg = total / len(rows)
    return {"total": total, "avg": avg, "count": len(rows)}

def main():
    # 修复 1: 从 stdin 或命令行参数读取
    if len(sys.argv) > 1:
        data = sys.argv[1]
    else:
        data = sys.stdin.read()

    rows = parse_csv(data)
    passed = filter_pass(rows)
    stats = calc_stats(passed)
    print(json.dumps({"rows": passed, "stats": stats}, indent=2))

if __name__ == "__main__":
    main()
