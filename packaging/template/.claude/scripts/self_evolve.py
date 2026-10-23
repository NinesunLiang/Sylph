#!/usr/bin/env python3
"""Template: self_evolve.py — Cron entry point for self-evolution pipeline.

Usage: Copy to your scripts dir, ensure observe.py and consolidate.py are in same dir.
"""
from __future__ import annotations
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS_DIR = Path(__file__).parent
OBSERVE = SCRIPTS_DIR / "observe.py"
CONSOLIDATE = SCRIPTS_DIR / "consolidate.py"
REPORTS_DIR = SCRIPTS_DIR / "reports"

def run_observe() -> dict:
    result = subprocess.run([sys.executable, str(OBSERVE)], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"observe.py failed: {result.stderr}")
    return json.loads(result.stdout)

def run_consolidate(observations: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(CONSOLIDATE)],
        input=json.dumps(observations).encode(),
        capture_output=True,
        timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(f"consolidate.py failed: {proc.stderr.decode()}")
    return json.loads(proc.stdout.decode())

def main():
    print(f"[self_evolve] 启动 {datetime.now(timezone.utc).isoformat()}")
    
    REPORTS_DIR.mkdir(exist_ok=True)
    
    try:
        # Step 1: Observe
        print("[self_evolve] 运行 observe.py...")
        obs_data = run_observe()
        observations = obs_data.get("observations", [])
        print(f"[self_evolve] 提取到 {len(observations)} 条观察")
        
        # Step 2: Consolidate
        print("[self_evolve] 运行 consolidate.py...")
        result = run_consolidate(obs_data)
        
        # Step 3: Report
        stats = result.get("stats", {})
        audit_log = result.get("audit_log")
        report_path = REPORTS_DIR / f"self_evolve_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        
        report = f"""# 自我进化日报 {datetime.now().strftime('%Y%m%d_%H%M')}
生成时间: {datetime.now(timezone.utc).isoformat()}

## 统计
- 输入观察数: {stats.get('input', 0)}
- 高置信直接写入: {stats.get('written_memory', 0) + stats.get('written_user', 0)}
- 中置信待确认: {stats.get('pending', 0)}
- 低置信丢弃: {stats.get('discarded', 0)}
- 写入 memory 字符: {stats.get('written_memory', 0)}
- 写入 user 字符: {stats.get('written_user', 0)}

## 审计日志: {audit_log or 'None'}
"""
        report_path.write_text(report)
        print(f"[self_evolve] 报告已生成: {report_path}")
        
        print(json.dumps({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report": str(report_path),
            "audit_log": audit_log,
            "stats": stats
        }, ensure_ascii=False))
        
    except Exception as e:
        print(f"[self_evolve] 错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()