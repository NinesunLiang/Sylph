#!/usr/bin/env python3
"""consolidate.py — Dedup, JEV gate, route to stores (Real JEV integration)."""

from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ─── CONFIG ──────────────────────────────────────────────
MEMORY_FILE = Path.home() / ".hermes" / "memories" / "MEMORY.md"
USER_FILE = Path.home() / ".hermes" / "memories" / "USER.md"
MEMORY_LIMIT = 1600
USER_LIMIT = 800
SIM_THRESHOLD = 0.85
PATCHES_DIR = Path(__file__).parent / "patches"
REPORTS_DIR = Path(__file__).parent / "reports"
PENDING_FILE = Path.home() / ".hermes" / "memories" / "pending_user_confirm.json"
# ─── END CONFIG ──────────────────────────────────────────

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

try:
    from sentence_transformers import SentenceTransformer
    EMBED = SentenceTransformer("all-MiniLM-L6-v2")
    HAS_EMBED = True
except Exception:
    HAS_EMBED = False

def embed(text: str) -> list[float]:
    if HAS_EMBED:
        return EMBED.encode(text, normalize_embeddings=True).tolist()
    return [hash(text) % 1000 / 1000.0] * 384

def cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b: return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a)**0.5
    nb = sum(y*y for y in b)**0.5
    return dot/(na*nb) if na and nb else 0.0

def load_store(path: Path) -> list[dict]:
    if not path.exists(): return []
    lines = path.read_text().splitlines()
    entries = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#") or line == "§": continue
        entries.append({"text": line, "line": i, "emb": embed(line)})
    return entries

def call_jev(observation: dict, context: str) -> dict:
    """Call real JEV via jev_sweep.py logic for memory observations."""
    import subprocess
    import json as json_lib
    import tempfile
    from pathlib import Path
    
    text = observation.get("text", "")
    tag = observation.get("tag", "")
    confidence = observation.get("confidence", 0.5)
    source = observation.get("source", "user")
    
    # Prepare state for JEV
    state = {
        "purpose": f"Memory observation: {tag}",
        "change_kind": "memory",
        "changed_paths": [],
        "change": text,
        "delivery": {"available": False, "reason": "Not a code change"},
        "repo_context": context or "",
        "repo_context_available": bool(context.strip()),
    }
    
    # Build questions from memory rules
    questions = {}
    rules_path = Path(__file__).parent / "jev_rules_memory.yaml"
    if rules_path.exists():
        import yaml
        registry = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        for rule in registry.get("rules", []):
            prim = "choice" if rule.get("allow_not_applicable") else "noul"
            base = {"type": prim, "instructions": f"该记忆观察是否满足下面这条 CarrorOS 记忆规则？"}
            if prim == "noul":
                base["criteria"] = {
                    "true": f"观察符合规则。规则：{rule['text']}。判据：{rule['criteria_true']}",
                    "false": f"观察违反规则。规则：{rule['text']}。判据：{rule['criteria_false']}",
                }
            else:
                base["criteria"] = {
                    "符合": f"观察符合规则。规则：{rule['text']}。判据：{rule['criteria_true']}",
                    "不符合": f"观察违反规则。规则：{rule['text']}。判据：{rule['criteria_false']}",
                    "不适用": f"观察与该规则无关",
                }
            questions[rule["rule_id"]] = base
    
    if not questions:
        # Fallback to heuristic if no rules
        return _heuristic_jev(observation)
    
    # Call jev_sweep via subprocess (or import if possible)
    try:
        # Use jev_sweep's JevClient directly
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from jev_sweep import JevClient, ensure_frozen_model, MODEL_FROZEN
        
        client = JevClient()
        if not client.api_key:
            return _heuristic_jev(observation)
        
        result = client.judge(state, questions, MODEL_FROZEN)
        
        if "_error" in result or "_http_error" in result:
            return _heuristic_jev(observation)
        
        answers = result.get("answers", {})
        
        # Aggregate verdicts across rules
        high_count = 0
        medium_count = 0
        low_count = 0
        reasons = []
        
        for rule in registry.get("rules", []):
            rid = rule["rule_id"]
            answer = answers.get(rid)
            if not answer:
                continue
            
            # Use jev_sweep's verdict logic
            from jev_sweep import verdict_from_answer, VERDICT_OK, VERDICT_BAD, VERDICT_NA, VERDICT_INSUFFICIENT, VERDICT_UNDECIDED
            verdict = verdict_from_answer(answer, rule)
            
            if verdict == VERDICT_OK:
                if rule.get("escalate_when_uncertain"):
                    medium_count += 1
                    reasons.append(f"{rid}: 符合但需复核")
                else:
                    high_count += 1
                    reasons.append(f"{rid}: 符合")
            elif verdict in (VERDICT_BAD, VERDICT_INSUFFICIENT):
                low_count += 1
                reasons.append(f"{rid}: {verdict}")
            elif verdict == VERDICT_UNDECIDED:
                medium_count += 1
                reasons.append(f"{rid}: 低置信需人工")
            elif verdict == VERDICT_NA:
                pass  # 不适用，忽略
        
        # Determine overall tier
        if high_count > 0 and medium_count == 0 and low_count == 0:
            return {"tier": "high", "reason": "; ".join(reasons) or "JEV 高置信通过"}
        elif medium_count > 0 or (high_count > 0 and low_count == 0):
            return {"tier": "medium", "reason": "; ".join(reasons) or "JEV 中置信需确认"}
        else:
            return {"tier": "low", "reason": "; ".join(reasons) or "JEV 低置信丢弃"}
            
    except Exception as e:
        # Fallback to heuristic on any error
        return _heuristic_jev(observation)


def _heuristic_jev(observation: dict) -> dict:
    """Fallback heuristic when real JEV unavailable."""
    text = observation.get("text", "")
    tag = observation.get("tag", "")
    confidence = observation.get("confidence", 0.5)
    
    hard_keywords = ["禁止", "必须", "铁律", "硬限", "直接写入", "直接给干货", "不许", "零容忍", "拒绝"]
    skill_keywords = ["要", "需要", "想要", "缺", "技能", "学会", "掌握", "不会", "不会用"]
    preference_keywords = ["优先", "偏好", "习惯", "喜欢", "倾向"]
    arch_keywords = ["可逆", "可观测", "低耦合", "稳定性", "可维护性", "先保护数据", "复杂度必须有来源", "省钱优先", "隐私优先", "先验证再配置"]
    pain_keywords = ["坑", "痛点", "踩坑", "失败", "报错", "不想再", "避免", "修复"]
    low_value_keywords = ["你好", "再见", "谢谢", "哈哈", "嗯", "哦", "好的", "行"]
    
    text_lower = text.lower()
    
    if confidence >= 0.8:
        if any(k in text for k in hard_keywords):
            return {"tier": "high", "reason": f"High confidence + hard constraint: {text[:50]}"}
        if any(k in text for k in arch_keywords):
            return {"tier": "high", "reason": f"High confidence + arch principle: {text[:50]}"}
        if any(k in text for k in skill_keywords):
            return {"tier": "medium", "reason": f"High confidence + skill gap: {text[:50]}"}
        if any(k in text for k in pain_keywords):
            return {"tier": "medium", "reason": f"High confidence + pain point: {text[:50]}"}
        if any(k in text for k in preference_keywords):
            return {"tier": "high", "reason": f"High confidence + preference: {text[:50]}"}
        if tag in {"preference", "pain_point"}:
            return {"tier": "high", "reason": f"High confidence + {tag}: {text[:50]}"}
        return {"tier": "medium", "reason": f"High confidence, unclear signal: {text[:50]}"}
    
    if confidence >= 0.5:
        if any(k in text for k in hard_keywords):
            return {"tier": "high", "reason": f"Medium confidence + hard constraint: {text[:50]}"}
        if any(k in text for k in skill_keywords):
            return {"tier": "medium", "reason": f"Medium confidence + skill gap: {text[:50]}"}
        if any(k in text for k in pain_keywords):
            return {"tier": "medium", "reason": f"Medium confidence + pain point: {text[:50]}"}
        if any(k in text for k in arch_keywords):
            return {"tier": "high", "reason": f"Medium confidence + arch principle: {text[:50]}"}
        if any(k in text for k in low_value_keywords):
            return {"tier": "low", "reason": f"Low value content: {text[:50]}"}
        return {"tier": "medium", "reason": f"Medium confidence: {text[:50]}"}
    
    return {"tier": "low", "reason": f"Low confidence ({confidence:.2f}): {text[:50]}"}

def load_pending() -> list[dict]:
    if not PENDING_FILE.exists(): return []
    try:
        return json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_pending(pending: list[dict]) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")

def write_store(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# " + path.stem, "§"]
    for e in entries:
        lines.append(e["text"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    # Read observations from stdin (piped from observe.py)
    data = json.load(sys.stdin)
    observations = data.get("observations", [])
    
    # Load existing stores
    memory = load_store(MEMORY_FILE)
    user = load_store(USER_FILE)
    all_existing = memory + user
    
    # Load pending confirmations
    pending = load_pending()
    
    # Process each observation
    stats = {"input": len(observations), "written_memory": 0, "written_user": 0, "pending": 0, "discarded": 0}
    audit = []
    
    for obs in observations:
        # Dedup against existing
        merged = False
        obs_emb = obs.get("emb", embed(obs["text"]))
        for ex in all_existing:
            if cosine_sim(obs_emb, ex["emb"]) > SIM_THRESHOLD:
                # Merge: keep longer
                if len(obs["text"]) > len(ex["text"]):
                    ex["text"] = obs["text"]
                merged = True
                break
        
        if not merged:
            # JEV gate
            verdict = call_jev(obs, "")
            tier = verdict.get("tier", "low")
            
            if tier == "high":
                # Direct write
                target = memory if obs.get("tag") in {"preference", "pain_point"} else user
                target.append({"text": obs["text"], "emb": obs_emb})
                all_existing.append({"text": obs["text"], "emb": obs_emb})
                stats["written_memory" if target is memory else "written_user"] += 1
                audit.append({"obs": obs, "action": "write", "tier": "high", "reason": verdict["reason"]})
            elif tier == "medium":
                # Add to pending for QQ Bot confirmation
                pending.append({
                    "id": f"p-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(pending)}",
                    "observation": obs,
                    "reason": verdict["reason"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "pending"
                })
                stats["pending"] += 1
                audit.append({"obs": obs, "action": "pending_user", "tier": "medium", "reason": verdict["reason"]})
            else:
                stats["discarded"] += 1
                audit.append({"obs": obs, "action": "discard", "tier": "low", "reason": verdict["reason"]})
    
    # Save pending confirmations
    save_pending(pending)
    
    # Enforce limits (trim by value score if over limit)
    def trim_store(entries: list[dict], limit: int, name: str) -> list[dict]:
        if len(entries) <= limit:
            return entries
        # Sort by text length as proxy for value (longer = more info)
        entries.sort(key=lambda e: len(e["text"]), reverse=True)
        return entries[:limit]
    
    memory = trim_store(memory, MEMORY_LIMIT, "memory")
    user = trim_store(user, USER_LIMIT, "user")
    
    # Write back stores
    write_store(MEMORY_FILE, memory)
    write_store(USER_FILE, user)
    
    # Write audit log
    PATCHES_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    (PATCHES_DIR / f"{today}.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Write report
    REPORTS_DIR.mkdir(exist_ok=True)
    report = f"""# Consolidate Report {today}
Input: {stats['input']}
Written memory: {stats['written_memory']}
Written user: {stats['written_user']}
Pending: {stats['pending']}
Discarded: {stats['discarded']}

"""
    (REPORTS_DIR / f"consolidate_{today}.md").write_text(report, encoding="utf-8")
    
    print(json.dumps({"stats": stats, "audit_log": str(PATCHES_DIR / f"{today}.json")}, ensure_ascii=False))

if __name__ == "__main__":
    main()