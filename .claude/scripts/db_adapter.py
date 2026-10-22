#!/usr/bin/env python3
"""
Hermes 会话读取 + Obsidian 记忆宫殿适配器
提供三个子命令：
  - recent: 读取最近 N 轮 Hermes QQ 对话
  - progressive: 按层级检索记忆宫殿（L1 殿 → L2 房间 → L3 展柜）
  - links: 维护/查询记忆关系图
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import re

# ─── 路径常量 ─────────────────────────────────────────────────────
HERMES_STATE_DB = Path.home() / ".hermes" / "state.db"
PALACE_ROOT = Path.home() / "Desktop" / "database"
PALACE_INDEX = PALACE_ROOT / "🏛️_记忆宫殿总索引.md"
MEMORY_LOG = PALACE_ROOT / ".hermes-memory-log.jsonl"
SHOWCASE_PATTERN = "📋_展柜_提纯知识.md"

# ─── Hermes 会话读取 ──────────────────────────────────────────────

def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """读取最近的 QQ 会话（来自 state.db）"""
    if not HERMES_STATE_DB.exists():
        return []
    
    conn = sqlite3.connect(HERMES_STATE_DB)
    conn.row_factory = sqlite3.Row
    try:
        # 先查 sessions 表结构
        cursor = conn.execute("PRAGMA table_info(sessions)")
        cols = [row[1] for row in cursor.fetchall()]
        
        # 查询最近的 QQ 会话 - 使用 started_at 排序
        if "source" in cols:
            cursor = conn.execute("""
                SELECT * FROM sessions 
                WHERE source = 'qqbot' 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (limit,))
        elif "platform" in cols:
            cursor = conn.execute("""
                SELECT * FROM sessions 
                WHERE platform = 'qqbot' 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (limit,))
        else:
            cursor = conn.execute("""
                SELECT * FROM sessions 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (limit,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        return sessions
    finally:
        conn.close()


def get_session_messages(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """读取指定会话的消息"""
    if not HERMES_STATE_DB.exists():
        return []
    
    conn = sqlite3.connect(HERMES_STATE_DB)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("PRAGMA table_info(messages)")
        cols = [row[1] for row in cursor.fetchall()]
        
        # 尝试不同的列名
        session_col = "session_id" if "session_id" in cols else ("chat_id" if "chat_id" in cols else None)
        if not session_col:
            return []
        
        cursor = conn.execute(f"""
            SELECT * FROM messages 
            WHERE {session_col} = ? 
            ORDER BY created_at ASC 
            LIMIT ?
        """, (session_id, limit))
        
        messages = [dict(row) for row in cursor.fetchall()]
        return messages
    finally:
        conn.close()


# ─── 记忆宫殿：L1/L2/L3 层级检索 ──────────────────────────────────

def parse_palace_index() -> Dict[str, Any]:
    """解析总索引，返回 {domain: {rooms: [...], keywords: [...], folder: str}}"""
    if not PALACE_INDEX.exists():
        return {}

    content = PALACE_INDEX.read_text(encoding="utf-8", errors="replace")
    result = {}

    # 匹配 L1 门牌行：### 🛡️ 殿10: 军事联盟  _关键词_
    # 或者：### 🎬 多媒体画像  _关键词_
    # 或者：### 🛡️ 军事联盟  _关键词_ （无编号）
    # 或者：### ⚙️ 工作流  _关键词_
    # 或者：### 🛠️ 环境与工具  _关键词_
    # emoji 范围：\U00002600-\U000026FF (misc symbols) + \U0001F000-\U0001FFFF (emoji) + \uFE0F (variation selector)
    # 名称：非贪婪匹配到 `  _` 前
    domain_pattern = r"###\s+([\w\U00002600-\U000026FF\U0001F000-\U0001FFFF\uFE0F]+)\s+(?:殿(\d+):\s+)?(.+?)\s+_\s*([^_]+)\s*_"
    # 匹配房间级链接：- 🔗 进入 [[军事联盟/📋_军事联盟索引.md|军事联盟]]
    room_link_pattern = r"-\s+🔗\s+进入\s+\[\[([^/\]]+)/[^|\]]+\|([^\]]+)\]\]"
    # 匹配房间级门牌：- 🚪 房间级门牌: [[军事联盟/殿索引.md|军事联盟·殿索引]]
    room_door_pattern = r"-\s+🚪\s+房间级门牌:\s+\[\[([^/\]]+)/[^|\]]+\|([^\]]+)\]\]"

    # 先收集所有门牌行，建立名称到 folder 的映射（从 🔗 进入 / 🚪 房间级门牌 反推）
    folder_by_name = {}
    room_links = re.findall(room_link_pattern, content)
    for folder, display in room_links:
        folder_by_name[display] = folder
    room_doors = re.findall(room_door_pattern, content)
    for folder, display in room_doors:
        folder_by_name[display] = folder

    # 再匹配所有 ### 开头的行
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('###'):
            continue
        m = re.match(domain_pattern, line)
        if m:
            emoji, num, name, keywords = m.groups()
            domain_key = f"殿{num}_{name}" if num else name
            # 优先用 room_link/door 里的 folder 名，没有则用 name
            folder = folder_by_name.get(name, name)
            result[domain_key] = {
                "emoji": emoji,
                "num": num or "",
                "name": name,
                "folder": folder,  # 实际文件夹名
                "keywords": [k.strip() for k in keywords.split("/") if k.strip()],
                "rooms": []
            }

    # 提取房间链接（🔗 进入）
    for folder, display in room_links:
        for dkey, dinfo in result.items():
            if folder in dkey or dkey.endswith(folder) or dkey == folder or dinfo["folder"] == folder:
                dinfo["rooms"].append({"folder": folder, "display": display})
                break

    # 提取房间门牌（🚪 房间级门牌）
    for folder, display in room_doors:
        for dkey, dinfo in result.items():
            if folder in dkey or dkey.endswith(folder) or dkey == folder or dinfo["folder"] == folder:
                # 避免重复
                if not any(r["folder"] == folder for r in dinfo["rooms"]):
                    dinfo["rooms"].append({"folder": folder, "display": display})
                break

    return result


def find_all_showcases() -> List[Path]:
    """扫描所有展柜文件"""
    return sorted(PALACE_ROOT.rglob(SHOWCASE_PATTERN))


def progressive_search(query: str, level: int = 1, min_confidence: float = 0.1, limit: int = 10) -> Dict[str, Any]:
    """
    渐进式检索：
    level=1: 只搜殿级索引（L1 门牌行关键词）
    level=2: 殿级命中后，搜该殿下的房间索引
    level=3: 房间命中后，搜展柜全文
    """
    index = parse_palace_index()
    results = []
    
    if level >= 1:
        # L1: 殿级关键词匹配
        query_lower = query.lower()
        for dkey, dinfo in index.items():
            score = 0
            matched_keywords = []
            for kw in dinfo["keywords"]:
                if query_lower in kw.lower():
                    score += 1
                    matched_keywords.append(kw)
            if score > 0:
                # 简化置信度：只要有匹配就给高分，匹配越多分越高
                confidence = min(0.3 + score * 0.15, 1.0)
                if confidence >= min_confidence:
                    results.append({
                        "level": 1,
                        "type": "domain",
                        "domain": dkey,
                        "name": dinfo["name"],
                        "emoji": dinfo["emoji"],
                        "matched_keywords": matched_keywords,
                        "confidence": confidence,
                        "rooms_count": len(dinfo["rooms"])
                    })
        
        # 按置信度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        results = results[:limit]
    
    if level >= 2 and results:
        # L2: 对命中的殿，搜房间索引文件
        for r in results:
            if r["level"] == 1 and r.get("rooms_count", 0) > 0:
                dkey = r["domain"]
                for room in index[dkey]["rooms"]:
                    room_index_path = PALACE_ROOT / room["folder"] / "殿索引.md"
                    if room_index_path.exists():
                        room_content = room_index_path.read_text(encoding="utf-8", errors="replace")
                        # L1 已确认域相关，直接解析所有子房间
                        import re
                        subroom_pattern = r'\|\s*🚪\s+([^|]+)\s*\|\s*([^|]+)\s*\|\s*\[📋展柜\]\(([^)]+)\)\s*\|'
                        for match in re.finditer(subroom_pattern, room_content):
                            subroom_name = match.group(1).strip()
                            subroom_keywords = match.group(2).strip()
                            subroom_showcase = match.group(3).strip()
                            # 跳过表头行
                            if subroom_name in ["房间名", "关键词"]:
                                continue
                            # 子房间文件夹名从 showcase 路径推导
                            subroom_folder = subroom_showcase.split('/')[0] if '/' in subroom_showcase else subroom_name
                            r.setdefault("rooms", []).append({
                                "folder": f"{room['folder']}/{subroom_folder}",
                                "display": subroom_name,
                                "matched": True
                            })
    
    if level >= 3:
            # L3: 搜展柜全文 —— 仅搜 L1/L2 命中的域/房间
            # L1 返回的 domain 是 domain_key，需要映射到实际文件夹名
            l1_folders = set()
            l2_room_folders = set()
            for r in results:
                if r["level"] == 1 and r.get("rooms_count", 0) > 0:
                    # 从 index 里拿 folder
                    dkey = r["domain"]
                    if dkey in index:
                        l1_folders.add(index[dkey].get("folder", r.get("name", dkey)))
                    # L2 matched rooms
                    for room in r.get("rooms", []):
                        if room.get("matched"):
                            l2_room_folders.add(room["folder"])

            showcase_results = []
            for showcase in find_all_showcases():
                room_name = showcase.parent.name
                domain_name = showcase.parent.parent.name

                # 计算相对路径用于匹配
                rel_path = str(showcase.parent.relative_to(PALACE_ROOT))

                # 过滤：只搜 L1 命中的域（用文件夹名匹配）
                if l1_folders and domain_name not in l1_folders:
                    continue
                # 如果有 L2 命中房间，进一步过滤（用相对路径匹配）
                if l2_room_folders and rel_path not in l2_room_folders:
                    continue

                content = showcase.read_text(encoding="utf-8", errors="replace")

                # 关键词匹配
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if query.lower() in line.lower() and len(line.strip()) > 10:
                        # 上下文
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        context = "\n".join(lines[start:end])

                        showcase_results.append({
                            "level": 3,
                            "type": "showcase_entry",
                            "domain": domain_name,
                            "room": room_name,
                            "content": line.strip()[:300],
                            "context": context[:500],
                            "path": str(showcase)
                        })

            showcase_results = showcase_results[:limit]
            return {
                "query": query,
                "level": level,
                "l1_results": results,
                "l3_results": showcase_results
            }
    
    return {
        "query": query,
        "level": level,
        "l1_results": results
    }


# ─── 记忆关系链接 ────────────────────────────────────────────────

LINKS_FILE = PALACE_ROOT / ".palace" / "memory_links.jsonl"

def ensure_links_file():
    LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LINKS_FILE.exists():
        LINKS_FILE.write_text("")

RELATION_TYPES = {"supports", "contradicts", "depends_on", "affects", "derived_from", "supersedes"}

def links_add(from_id: str, relation: str, to_id: str, note: str = "") -> Dict[str, Any]:
    if relation not in RELATION_TYPES:
        return {"success": False, "error": f"未知关系类型: {relation}，可用: {RELATION_TYPES}"}
    
    ensure_links_file()
    entry = {
        "id": f"link_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "from": from_id,
        "relation": relation,
        "to": to_id,
        "note": note,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    with open(LINKS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    return {"success": True, "link": entry}


def links_related(memory_id: str, depth: int = 1) -> Dict[str, Any]:
    ensure_links_file()
    if not LINKS_FILE.exists():
        return {"memory_id": memory_id, "related": []}
    
    links = []
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                links.append(json.loads(line))
    
    # 构建邻接表
    adj = {}
    for link in links:
        adj.setdefault(link["from"], []).append((link["relation"], link["to"], link))
        adj.setdefault(link["to"], []).append((f"reverse_{link['relation']}", link["from"], link))
    
    # BFS 查找相关
    visited = set()
    related = []
    queue = [(memory_id, 0)]
    
    while queue and len(related) < 20:
        current, d = queue.pop(0)
        if current in visited or d > depth:
            continue
        visited.add(current)
        
        if current in adj:
            for rel, target, link in adj[current]:
                if target not in visited:
                    related.append({
                        "memory_id": target,
                        "relation": rel,
                        "link": link
                    })
                    queue.append((target, d + 1))
    
    return {"memory_id": memory_id, "depth": depth, "related": related}


def links_list() -> List[Dict[str, Any]]:
    ensure_links_file()
    links = []
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                links.append(json.loads(line))
    return links


# ─── CLI 入口 ─────────────────────────────────────────────────────

def cmd_recent(args):
    sessions = get_recent_sessions(args.limit)
    print(json.dumps({
        "count": len(sessions),
        "sessions": sessions
    }, ensure_ascii=False, indent=2))


def cmd_progressive(args):
    result = progressive_search(args.query, args.level, args.min_confidence, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_links(args):
    if args.action == "add":
        result = links_add(args.from_id, args.relation, args.to_id, args.note or "")
    elif args.action == "related":
        result = links_related(args.memory_id, args.depth)
    elif args.action == "list":
        result = {"links": links_list()}
    else:
        result = {"error": f"未知 action: {args.action}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Hermes + Obsidian 数据库适配器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    
    # recent
    p = sub.add_parser("recent", help="读取最近 N 轮 Hermes QQ 会话")
    p.add_argument("-n", "--limit", type=int, default=10)
    p.set_defaults(func=cmd_recent)
    
    # progressive
    p = sub.add_parser("progressive", help="渐进式检索记忆宫殿（L1→L2→L3）")
    p.add_argument("query", help="搜索查询")
    p.add_argument("--level", type=int, default=1, choices=[1, 2, 3], help="检索层级")
    p.add_argument("--min-confidence", type=float, default=0.5)
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_progressive)
    
    # links
    p = sub.add_parser("links", help="记忆关系链接")
    p.add_argument("action", choices=["add", "related", "list"])
    p.add_argument("--from-id", help="来源记忆ID")
    p.add_argument("--relation", choices=sorted(RELATION_TYPES))
    p.add_argument("--to-id", help="目标记忆ID")
    p.add_argument("--note", default="")
    p.add_argument("--memory-id", help="查询的记忆ID")
    p.add_argument("--depth", type=int, default=1)
    p.set_defaults(func=cmd_links)
    
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())