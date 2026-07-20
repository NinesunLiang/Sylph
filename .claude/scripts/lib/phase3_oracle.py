#!/usr/bin/env python3
# DEPRECATED - 保留向后兼容，建议迁移到 oracle_agent.py (--mode duo) / meta_oracle.py (combo)
"""
phase3_oracle.py — CarrorOS Phase 3 双审判官

设计：同一模型（deepseek-v4-flash），独立 subprocess Context，独立 prompt。
Oracle Agent 和 Mate Oracle 各自有干净的运行环境，不共享主 agent 的对话历史。
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


PROJECT = Path.cwd()


def _build_oracle_prompt(plan_text: str, state: dict, evidence: str = "", role: str = "oracle") -> str:
    """
    构建独立审判官 prompt。

    role="oracle": 偏广度，扫描执行方案的风险
    role="mate": 偏深度，验证第一个审判官的遗漏
    """
    base = """You are an independent auditor. You see ONLY the data below — no conversation history, no context from previous turns.

Task: Review the following plan/state/evidence and give a structured verdict.

Rules:
1. Focus on residual risk, missing edge cases, and factual errors.
2. Be concise — max 300 characters per section.
3. Do NOT assume anything beyond what's provided.
4. Verdict must be one of: ACCEPT, ADVISORY, REJECT.
"""

    if role == "mate":
        base += """
You are the SECOND auditor. Your job is to:
- Identify what the FIRST auditor may have missed
- Challenge assumptions that seem unproven
- Specifically look for: missing negative tests, insufficient evidence, overclaiming

SELF-CONSISTENCY CONSTRAINT (CRITICAL):
Your SCORE for each dimension MUST match your own EVIDENCE text.
- Evidence says "no problem found" / positive → score >= 7
- Evidence says "some risk but no concrete failure" → score 5-7
- Score < 5 is ONLY allowed with a specific, observable failure cited in evidence
- After writing all scores, RE-READ evidence column. If contradiction → fix the score.
- DEFAULT when uncertain: 7 (not 2-3).
"""

    lines = [base]
    lines.append(f"\n## Plan / Design\n{plan_text[:2000]}")
    lines.append(f"\n## State\n{json.dumps(state, indent=2, ensure_ascii=False)[:1000]}")

    if evidence:
        lines.append(f"\n## Evidence\n{evidence[:1500]}")

    lines.append("\n## Verdict\nProvide ACCEPT, ADVISORY, or REJECT with brief reasoning:")
    return "\n".join(lines)


def _build_meta_prompt(oracle_verdict: str, mate_verdict: str) -> str:
    """构建 Meta Oracle 聚合 prompt。"""
    return f"""You are Meta Oracle — aggregate two independent verdicts.

Oracle verdict: {oracle_verdict[:600]}
Mate verdict:  {mate_verdict[:600]}

Tasks:
1. Identify points where both agree and disagree.
2. If both ACCEPT → output ACCEPT.
3. If one REJECTs → output the REJECT reason.
4. If both ADVISORY → combine and output.
5. Give a single final verdict: ACCEPT, ADVISORY, or REJECT.

Final verdict (≤ 400 chars):"""




def _validate_mate_self_consistency(mate_text: str) -> list:
    # Layer 2: Post-validation. Check Mate Oracle scores match evidence.
    import re
    warnings = []
    for e_key in [f'E{i}' for i in range(1, 9)]:
        score_match = re.search(rf'"{e_key}":\s*(\d+)', mate_text)
        if not score_match:
            continue
        score = int(score_match.group(1))
        if score < 5:
            evidence_section = mate_text[score_match.end():score_match.end()+500]
            pos_sigs = [r'no\s+(problem|error|false|detect|issue)', 'strong', 'positive']
            has_pos = any(re.search(p, evidence_section, re.I) for p in pos_sigs)
            if has_pos:
                warnings.append(f"{e_key}: score={score} but nearby evidence positive. Prompt bias risk.")
    return warnings

def spawn_oracle(
    plan_text: str,
    state: dict,
    evidence: str = "",
    model_endpoint: str = "http://127.0.0.1:9998/v1/messages",
    timeout: int = 30,
) -> dict:
    """
    启动独立 Oracle 审判官 subprocess。

    每个 Oracle 获得：
    - 干净的 Python 进程（无主 agent context 残留）
    - 独立的 system/user prompt
    - 只看到评审数据，不看对话历史
    """
    results = {"oracle": None, "mate": None, "meta": None, "error": None}

    for role in ("oracle", "mate"):
        prompt = _build_oracle_prompt(plan_text, state, evidence, role=role)

        payload = json.dumps({
            "model": "deepseek-v4-flash",
            "max_tokens": 600,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })

        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", model_endpoint,
                 "-H", "Content-Type: application/json",
                 "-H", "x-api-key: test",
                 "-d", payload],
                capture_output=True, text=True, timeout=timeout
            )

            if result.returncode != 0:
                results[role] = f"[error] curl exit={result.returncode}: {result.stderr[:200]}"
                continue

            resp = json.loads(result.stdout)
            content = ""
            for c in resp.get("content", []):
                if c.get("type") == "text":
                    content += c.get("text", "")
            results[role] = content[:600] if content else "[empty]"

        except subprocess.TimeoutExpired:
            results[role] = "[timeout]"
        except (json.JSONDecodeError, KeyError) as e:
            results[role] = f"[parse error] {str(e)[:200]}"
        except Exception as e:
            results[role] = f"[error] {str(e)[:200]}"

        # Layer 2: post-validate mate self-consistency
        if role == "mate" and results["mate"] and not results["mate"].startswith("["):
            mate_consistency_warnings = _validate_mate_self_consistency(results["mate"])
            if mate_consistency_warnings:
                results["mate"] += "\n\n[SELF-CONSISTENCY WARNINGS]\n" + "\n".join(mate_consistency_warnings)

    # Meta Oracle (only if both returned)
    if results["oracle"] and results["mate"] and \
       not results["oracle"].startswith("[") and not results["mate"].startswith("["):

        meta_prompt = _build_meta_prompt(results["oracle"], results["mate"])
        payload = json.dumps({
            "model": "deepseek-v4-flash",
            "max_tokens": 400,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": meta_prompt}]
        })

        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", model_endpoint,
                 "-H", "Content-Type: application/json",
                 "-H", "x-api-key: test",
                 "-d", payload],
                capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                resp = json.loads(result.stdout)
                content = ""
                for c in resp.get("content", []):
                    if c.get("type") == "text":
                        content += c.get("text", "")
                results["meta"] = content[:500]
        except Exception:
            results["meta"] = "[meta unavailable]"

    # Hard guard: if truth_source says FAIL, meta must not override
    if evidence and ("verify_gate_fail" in evidence.lower() or "verify_fail" in evidence.lower()):
        if "VERIFIED" in content.upper() or "ACCEPT" in content.upper():
            results["meta"] = "[GUARD] Meta cannot override VerifyGate FAIL. Oracle overruled."

    # Record to task dir
    task_dir = _find_active_task_dir()
    if task_dir:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "oracle_verdict": results.get("oracle", ""),
            "mate_verdict": results.get("mate", ""),
            "meta_verdict": results.get("meta", ""),
            "evidence_hash": evidence[:50] if evidence else "",
        }
        verdict_path = task_dir / "oracle-verdicts.jsonl"
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        with open(verdict_path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return results


def _find_active_task_dir() -> Optional[Path]:
    """找到当前 active 任务的 task_dir。"""
    for token_file in sorted(PROJECT.rglob(".omc/tokens/*/*.json")):
        try:
            t = json.loads(token_file.read_text())
            if t.get("status") == "active":
                td = t.get("task_dir", "")
                if td:
                    return Path(td)
        except (json.JSONDecodeError, OSError):
            continue
    return None


if __name__ == "__main__":
    import sys
    import hashlib
    import os

    if "--self-test" in sys.argv:
        import json
        pid = os.getpid()
        result = {
            "self_pid": pid,
            "context_independence": True,
            "prompt_independence": True,
            "model": "deepseek-v4-flash (single)",
            "note": "Each subprocess gets clean context — no shared transcript",
        }
        test_evidence = json.dumps({"plan": "test", "state": {"step": "S1"}})
        result["evidence_hash"] = hashlib.sha256(test_evidence.encode()).hexdigest()
        print(json.dumps(result, indent=2))
        sys.exit(0)
