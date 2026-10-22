#!/usr/bin/env python3
"""observe.py — Extract 4 tag types from Hermes QQ conversation."""

from __future__ import annotations
import json
import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────
ALLOWED_TAGS = {"preference", "correction", "pain_point", "skill_gap"}
ALLOWED_SOURCES = {"user", "assistant", "tool"}
MAX_TURNS = 50
HERMES_STATE_DB = Path.home() / ".hermes" / "state.db"
# ─── END CONFIG ──────────────────────────────────────────

SYSTEM_PROMPT = f"""你是观察提取器。从最近 {MAX_TURNS} 轮对话中，只抽取四类结构化观察：

1. preference — 用户偏好/审美/口味/习惯
2. correction — 用户纠正/否定/「不对/别/不要/禁止」
3. pain_point — 用户痛点/卡点/「烦/累/不行/爆炸/过载」
4. skill_gap — 用户明确要的新能力/技能需求

其它内容（闲聊、一次性任务细节、已过期计划、单纯事实陈述）一律丢弃。

输出 JSON：
{{
  "observations": [
    {{"tag": "preference", "text": "具体观察文本", "source": "user", "confidence": 0.9}},
    ...
  ],
  "extracted_at": "ISO8601"
}}

硬规则：
- tag 必须在 {ALLOWED_TAGS} 中
- source 必须在 {ALLOWED_SOURCES} 中
- confidence 0.0-1.0
- text 单行、自包含、去对话标记
- 观察数 ≤ 20
"""


def load_recent_conversation(limit: int = MAX_TURNS) -> list[dict]:
    """Load recent QQ conversations from Hermes state.db."""
    if not HERMES_STATE_DB.exists():
        return []
    
    conn = sqlite3.connect(HERMES_STATE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get recent sessions from QQ
    cursor.execute("""
        SELECT id, title, started_at 
        FROM sessions 
        WHERE source = 'qqbot' 
        ORDER BY started_at DESC 
        LIMIT 5
    """)
    sessions = cursor.fetchall()
    
    if not sessions:
        return []
    
    # Get messages from the most recent session
    session_id = sessions[0]['id']
    cursor.execute("""
        SELECT role, content, timestamp
        FROM messages
        WHERE session_id = ?
          AND role IN ('user', 'assistant')
          AND content IS NOT NULL
          AND TRIM(content) != ''
        ORDER BY timestamp DESC
        LIMIT ?
    """, (session_id, limit))
    messages = list(reversed(cursor.fetchall()))
    
    conn.close()
    
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def call_llm(prompt: str) -> str:
    """Call local kilo-free model."""
    import requests
    import json
    
    # Use the kilo-free endpoint with a specific free model
    base_url = "http://127.0.0.1:8770/v1"
    model = "nvidia/nemotron-3.5-super-vl:free"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4000
    }
    
    try:
        # 本机代理绕过系统代理，否则会被 127.0.0.1:29290 拦截返回 502
        session = requests.Session()
        session.trust_env = False
        resp = session.post(f"{base_url}/chat/completions", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"].get("content") or ""
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        return ""


def extract_observations(conversation_turns: list[dict]) -> list[dict]:
    """Extract observations using LLM."""
    if not conversation_turns:
        return []
    
    # Format conversation for LLM
    conv_text = "\n".join([
        f"{t['role']}: {str(t['content'])[:600]}"
        for t in conversation_turns[-MAX_TURNS:]
    ])
    
    prompt = f"以下是最近 {len(conversation_turns[-MAX_TURNS:])} 轮对话：\n\n{conv_text}\n\n请按格式输出 JSON。"
    
    response = call_llm(prompt)
    if not response:
        return []
    
    try:
        data = json.loads(response)
        return data.get("observations", [])
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return data.get("observations", [])
            except:
                pass
    return []


def main():
    conversation = load_recent_conversation()
    
    obs = extract_observations(conversation)
    
    # Code-side whitelist (double enforcement)
    filtered = [o for o in obs if o.get("tag") in ALLOWED_TAGS]
    
    print(json.dumps({
        "observations": filtered,
        "extracted_at": datetime.now().isoformat()
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()