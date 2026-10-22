#!/usr/bin/env python3
"""lightweight_memory_tidy.py — Standalone memory/user compression.

Run manually or weekly via cron. Enforces hard char limits via value-score trimming.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ─── CONFIG ──────────────────────────────────────────────
MEMORY_FILE = Path.home() / ".hermes" / "memories" / "MEMORY.md"
USER_FILE = Path.home() / ".hermes" / "memories" / "USER.md"
MEMORY_LIMIT = 1600
USER_LIMIT = 800
SIM_THRESHOLD = 0.85
COLD_DAYS = 90
# ─── END CONFIG ──────────────────────────────────────────

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

try:
    from sentence_transformers import SentenceTransformer
    EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    HAS_EMBED = True
except Exception as e:
    HAS_EMBED = False
    print(f"[tidy] embedding 不可用: {e}，用字符串兜底", file=sys.stderr)

def embed(text: str) -> list[float]:
    if HAS_EMBED:
        return EMBED_MODEL.encode(text, normalize_embeddings=True).tolist()
    return [hash(text) % 1000 / 1000.0] * 384

def cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b: return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a)**0.5
    nb = sum(y*y for y in b)**0.5
    return dot/(na*nb) if na and nb else 0.0

def parse_memory_file(filepath: Path) -> list[dict]:
    if not filepath.exists(): return []
    lines = filepath.read_text(encoding="utf-8").splitlines()
    entries = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#") or line == "§": continue
        entries.append({"text": line, "line_num": i, "raw": line, "embedding": embed(line)})
    return entries

def classify_entry(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["喜欢", "偏好", "审美", "习惯", "口味", "风格", "极简", "素净", "变化", "不重复"]):
        return "preference"
    if any(k in t for k in ["不对", "纠正", "错了", "不是这样", "重来", "别", "不要", "禁止", "禁", "不要重复"]):
        return "correction"
    if any(k in t for k in ["烦", "累", "卡住", "不行", "受不了", "痛点", "爆炸", "过载", "太多", "无限", "信息爆炸", "记忆", "轻量化"]):
        return "pain_point"
    if any(k in t for k in ["要", "需要", "想要", "缺", "技能", "能力", "想学", "想会", "超级agent", "自我进化", "自我迭代"]):
        return "skill_gap"
    return "other"

def deduplicate(entries: list[dict]) -> list[dict]:
    kept = []
    for e in entries:
        merged = False
        for k in kept:
            if cosine_sim(e["embedding"], k["embedding"]) > SIM_THRESHOLD:
                if len(e["text"]) > len(k["text"]):
                    k["text"] = e["text"]
                    k["raw"] = e["raw"]
                k["merged_from"] = k.get("merged_from", 0) + 1
                merged = True
                break
        if not merged:
            kept.append(e)
    return kept

def enforce_limit(entries: list[dict], limit: int) -> list[dict]:
    type_score = {"preference": 4, "correction": 4, "pain_point": 3, "skill_gap": 3, "other": 1}
    for e in entries:
        e["_score"] = type_score.get(e.get("type", "other"), 1)
        e["_score"] += e.get("line_num", 0) * 0.001
    entries.sort(key=lambda x: x["_score"], reverse=True)
    total = sum(len(e["text"]) for e in entries)
    if total <= limit: return entries
    kept = []
    kept_chars = 0
    for e in entries:
        if kept_chars + len(e["text"]) <= limit:
            kept.append(e)
            kept_chars += len(e["text"])
        else:
            break
    return kept

def write_back(filepath: Path, entries: list[dict], header: str):
    lines = [header, ""]
    for e in entries:
        lines.append(e["text"])
    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    print("=== 轻量化记忆数据库开始 ===")
    
    memory_entries = parse_memory_file(MEMORY_FILE)
    user_entries = parse_memory_file(USER_FILE)
    
    for e in memory_entries: e["type"] = classify_entry(e["text"])
    for e in user_entries: e["type"] = classify_entry(e["text"])
    
    mem_types = {}
    for e in memory_entries: mem_types[e["type"]] = mem_types.get(e["type"], 0) + 1
    user_types = {}
    for e in user_entries: user_types[e["type"]] = user_types.get(e["type"], 0) + 1
    
    print(f"[memory] 原条目: {len(memory_entries)} | 分类: {mem_types}")
    print(f"[user] 原条目: {len(user_entries)} | 分类: {user_types}")
    
    memory_dedup = deduplicate(memory_entries)
    user_dedup = deduplicate(user_entries)
    
    print(f"[memory] 去重后: {len(memory_dedup)} (合并了 {len(memory_entries) - len(memory_dedup)} 条)")
    print(f"[user] 去重后: {len(user_dedup)} (合并了 {len(user_entries) - len(user_dedup)} 条)")
    
    memory_final = enforce_limit(memory_dedup, MEMORY_LIMIT)
    user_final = enforce_limit(user_dedup, USER_LIMIT)
    
    mem_chars_before = sum(len(e["text"]) for e in memory_entries)
    mem_chars_after = sum(len(e["text"]) for e in memory_final)
    user_chars_before = sum(len(e["text"]) for e in user_entries)
    user_chars_after = sum(len(e["text"]) for e in user_final)
    
    print(f"[memory] 字符数: {mem_chars_before} -> {mem_chars_after} (限制 {MEMORY_LIMIT})")
    print(f"[user] 字符数: {user_chars_before} -> {user_chars_after} (限制 {USER_LIMIT})")
    
    backup_dir = MEMORY_FILE.parent / "_backup_lightweight"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if MEMORY_FILE.exists():
        (backup_dir / f"MEMORY.md.{ts}").write_text(MEMORY_FILE.read_text())
    if USER_FILE.exists():
        (backup_dir / f"USER.md.{ts}").write_text(USER_FILE.read_text())
    
    write_back(MEMORY_FILE, memory_final, "# Hermes Memory")
    write_back(USER_FILE, user_final, "# User Profile")
    
    print(f"\n✅ 轻量化完成")
    print(f"  memory: {len(memory_entries)} 条 -> {len(memory_final)} 条, {mem_chars_before} -> {mem_chars_after} 字符")
    print(f"  user: {len(user_entries)} 条 -> {len(user_final)} 条, {user_chars_before} -> {user_chars_after} 字符")
    print(f"  备份在: {backup_dir}")

if __name__ == "__main__":
    main()