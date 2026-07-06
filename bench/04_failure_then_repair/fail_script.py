#!/usr/bin/env python3
"""
一个故意引入 bug 的数据处理脚本：
- 输入：CSV 格式数据（name,score）
- 处理：按分数排序，筛选 >= 60 分的条目
- Bug：文件路径写死为不存在路径，且计算逻辑有除零错
"""
import json
import sys

DATA_FILE = "/tmp/nonexistent_bench_data.csv"  # Bug 1: 不存在路径

def parse_csv(content):
    rows = []
    for line in content.strip().split("\n"):
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
    total = sum(r["score"] for r in rows)
    # Bug 2: 除零 — 当 rows 为空时 crash
    avg = total / len(rows)
    return {"total": total, "avg": avg, "count": len(rows)}

def main():
    try:
        with open(DATA_FILE) as f:
            content = f.read()
    except FileNotFoundError as e:
        print(f"FAILED: 数据文件不存在 — {e}", file=sys.stderr)
        sys.exit(1)

    rows = parse_csv(content)
    passed = filter_pass(rows)
    stats = calc_stats(passed)
    print(json.dumps({"rows": passed, "stats": stats}, indent=2))

if __name__ == "__main__":
    main()
