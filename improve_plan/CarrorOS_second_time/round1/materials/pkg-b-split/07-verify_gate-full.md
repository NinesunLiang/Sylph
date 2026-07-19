# verify_gate.py 全文

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 孤儿验证门,403 行
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/verify_gate.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS VerifyGate
     4	
     5	Purpose:
     6	  Match executor.md evidence against plan.md verify rules to decide step completion.
     7	  Only VerifyGate VERIFIED allows plan.md [x].
     8	
     9	Commands:
    10	  verify --step <step_id> --plan <path> --executor <path> [--token <path>]
    11	
    12	Output:
    13	  VERIFIED / WARN / BLOCKED / REJECTED
    14	
    15	Constraints:
    16	  - Python 3.10+ standard library only
    17	  - Does not execute fixes
    18	  - Does not alter executor evidence
    19	  - Evidence-level enforcement:
    20	    E3 command exit=0 > E2 file_assertion > E1 user_confirmation > E0 narrative (rejected)
    21	"""
    22	
    23	from __future__ import annotations
    24	
    25	import argparse
    26	import json
    27	import re
    28	import sys
    29	from dataclasses import dataclass, asdict
    30	from datetime import datetime, timezone
    31	from pathlib import Path
    32	from typing import Any
    33	
    34	SOFT_COMPLETION_PHRASES = [
    35	    "应该好了", "看起来可以", "基本完成", "大概没问题",
    36	    "已经处理", "完成了",
    37	    "looks good", "should work", "probably fixed",
    38	    "可以了", "没问题",
    39	]
    40	
    41	
    42	@dataclass
    43	class VerifyDecision:
    44	    decision: str  # VERIFIED | WARN | BLOCKED | REJECTED
    45	    reason: str
    46	    step: str
    47	    matched: list[str]
    48	    missing: list[str]
    49	    warnings: list[str]
    50	    required_action: str | None = None
    51	
    52	
    53	def now_iso() -> str:
    54	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    55	
    56	
    57	def today() -> str:
    58	    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    59	
    60	
    61	def read_text(path: Path) -> str:
    62	    if not path.exists():
    63	        return ""
    64	    return path.read_text(encoding="utf-8")
    65	
    66	
    67	def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    68	    if not path.exists():
    69	        return default or {}
    70	    with path.open("r", encoding="utf-8") as f:
    71	        return json.load(f)
    72	
    73	
    74	def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    75	    path.parent.mkdir(parents=True, exist_ok=True)
    76	    with path.open("a", encoding="utf-8") as f:
    77	        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    78	
    79	
    80	def parse_verify_rules(plan_text: str, step: str) -> list[str]:
    81	    """Extract verify rules for a given step from plan.md."""
    82	    rules: list[str] = []
    83	    in_step = False
    84	    step_prefixes = [f"- [ ] {step}:", f"- [x] {step}:", f"- [X] {step}:"]
    85	
    86	    for line in plan_text.splitlines():
    87	        stripped = line.strip()
    88	        # Check if we're entering the target step
    89	        if any(stripped.startswith(p) for p in step_prefixes):
    90	            in_step = True
    91	            continue
    92	        # Exit step on next step heading or step marker
    93	        if in_step and (stripped.startswith("- [") or stripped.startswith("## ")):
    94	            if stripped.startswith("- [") and not any(stripped.startswith(p) for p in step_prefixes):
    95	                break
    96	        if in_step:
    97	            m = re.match(r"- verify:\s*(.+)$", stripped)
    98	            if m:
    99	                rules.append(m.group(1).strip())
   100	    if not rules:
   101	        # Fallback: search globally
   102	        for line in plan_text.splitlines():
   103	            m = re.match(r"- verify:\s*(.+)$", line.strip())
   104	            if m:
   105	                rules.append(m.group(1).strip())
   106	    return rules
   107	
   108	
   109	def parse_evidence(executor_text: str, step: str) -> list[dict[str, Any]]:
   110	    """Extract evidence entries for a given step from executor.md."""
   111	    evidence: list[dict[str, Any]] = []
   112	    current: dict[str, Any] = {}
   113	    in_entry = False
   114	
   115	    for line in executor_text.splitlines():
   116	        stripped = line.strip()
   117	        m = re.match(r"^###\s+(EV-\S+)", stripped)
   118	        if m:
   119	            if current and current.get("step") == step:
   120	                evidence.append(current)
   121	            current = {"id": m.group(1)}
   122	            in_entry = True
   123	            continue
   124	        m = re.match(r"^###\s+(FAIL-\S+)", stripped)
   125	        if m:
   126	            if current and current.get("step") == step:
   127	                evidence.append(current)
   128	            current = {"id": m.group(1), "type": "failure"}
   129	            in_entry = True
   130	            continue
   131	        if in_entry:
   132	            for key in ("step", "type", "source", "exit_code", "file", "assertion",
   133	                        "evidence_level", "confirmation", "change_summary"):
   134	                kv = re.match(rf"- {key}:\s*(.+)$", stripped)
   135	                if kv:
   136	                    val = kv.group(1).strip()
   137	                    if key == "exit_code":
   138	                        try:
   139	                            val = int(val)
   140	                        except ValueError:
   141	                            pass
   142	                    current[key] = val
   143	            if stripped.startswith("## "):
   144	                if current and current.get("step") == step:
   145	                    evidence.append(current)
   146	                current = {}
   147	                in_entry = False
   148	
   149	    if current and current.get("step") == step:
   150	        evidence.append(current)
   151	
   152	    return evidence
   153	
   154	
   155	def is_soft_completion(text: str) -> bool:
   156	    lowered = text.lower().strip()
   157	    return any(phrase.lower() in lowered for phrase in SOFT_COMPLETION_PHRASES)
   158	
   159	
   160	def match_verify_rule(rule: str, evidence: list[dict[str, Any]]) -> tuple[bool, str, list[str]]:
   161	    """Match a single verify rule against available evidence."""
   162	    warnings: list[str] = []
   163	
   164	    # command: rule
   165	    cm = re.match(r"^command:(.+)$", rule)
   166	    if cm:
   167	        expected_cmd = cm.group(1).strip()
   168	        for ev in evidence:
   169	            if ev.get("type") == "failure":
   170	                continue
   171	            src = str(ev.get("source", "")).strip()
   172	            ec = ev.get("exit_code")
   173	            el = str(ev.get("evidence_level", ""))
   174	            if src and (src == expected_cmd or src.endswith("/" + expected_cmd) or expected_cmd.endswith(src)):
   175	                if ec == 0 and el == "E3":
   176	                    return True, f"command match: {src} exit=0", []
   177	                elif ec == 0:
   178	                    warnings.append(f"command {src} exit=0 but evidence_level={el} (expected E3)")
   179	        return False, f"no matching command evidence for: {expected_cmd}", warnings
   180	
   181	    # file: rule
   182	    fm = re.match(r"^file:(.+?)\s+contains\s+(.+)$", rule)
   183	    if fm:
   184	        expected_file = fm.group(1).strip()
   185	        expected_assertion = fm.group(2).strip()
   186	        for ev in evidence:
   187	            if ev.get("type") == "failure":
   188	                continue
   189	            ef = str(ev.get("file", "")).strip()
   190	            ea = str(ev.get("assertion", "")).strip()
   191	            el = str(ev.get("evidence_level", ""))
   192	            if ef and (ef == expected_file or ef.endswith("/" + expected_file)):
   193	                if is_soft_completion(ea):
   194	                    warnings.append(f"file_assertion for {ef} contains soft completion: '{ea}'")
   195	                    return False, "soft_completion_in_assertion", warnings
   196	                if expected_assertion.lower() in ea.lower():
   197	                    if el in ("E2", "E3"):
   198	                        return True, f"file assertion match: {ef} contains '{expected_assertion}'", []
   199	                    warnings.append(f"file assertion for {ef} has evidence_level={el} (expected E2/E3)")
   200	                else:
   201	                    warnings.append(f"file assertion for {ef} doesn't contain '{expected_assertion}'")
   202	        return False, f"no matching file assertion for: {expected_file}", warnings
   203	
   204	    # assertion: rule
   205	    am = re.match(r"^assertion:(.+)$", rule)
   206	    if am:
   207	        expected = am.group(1).strip().lower()
   208	        for ev in evidence:
   209	            if ev.get("type") == "failure":
   210	                continue
   211	            if is_soft_completion(str(ev.get("assertion", ""))):
   212	                warnings.append(f"assertion contains soft completion")
   213	                continue
   214	            if expected in str(ev.get("assertion", "")).lower():
   215	                return True, f"assertion match: '{expected}'", []
   216	            txt = str(ev.get("output_tail", "")).lower()
   217	            if expected in txt and ev.get("exit_code") == 0:
   218	                return True, f"assertion in command output: '{expected}'", []
   219	        return False, f"no matching assertion for: {expected}", warnings
   220	
   221	    return False, f"unrecognized verify rule: {rule}", warnings
   222	
   223	
   224	def parse_spec_acs(spec_path: Path, step: str | None = None) -> list[str]:
   225	    """Parse Acceptance Criteria from spec.md — returns list of AC rules
   226	
   227	    spec.md 格式:
   228	        - AC1 [command:] <desc>
   229	        - AC2 [file:] <desc>
   230	        - AC3 [assertion:] <desc>
   231	    """
   232	    spec_text = read_text(spec_path)
   233	    if not spec_text:
   234	        return []
   235	
   236	    rules = []
   237	    for line in spec_text.splitlines():
   238	        stripped = line.strip()
   239	        # Match: - AC1 [command:] description
   240	        m = re.match(r"^\s*-\s*(AC\d+)\s*\[(command:|file:|assertion:)\]\s*(.+)", stripped)
   241	        if m:
   242	            prefix = m.group(2)  # e.g. "command:"
   243	            desc = m.group(3).strip()
   244	            rules.append(f"{prefix}{desc}")
   245	            continue
   246	        # Match: - AC1: description (no type prefix, default assertion:)
   247	        m2 = re.match(r"^\s*-\s*(AC\d+):\s*(.+)", stripped)
   248	        if m2:
   249	            desc = m2.group(2).strip()
   250	            rules.append(f"assertion:{desc}")
   251	
   252	    return rules
   253	
   254	
   255	def verify_step(step: str, plan_path: Path, executor_path: Path, token_path: Path | None = None,
   256	                spec_path: Path | None = None) -> VerifyDecision:
   257	    plan_text = read_text(plan_path)
   258	    executor_text = read_text(executor_path)
   259	
   260	    plan_text = read_text(plan_path)
   261	    if not plan_text:
   262	        return VerifyDecision("REJECTED", "plan_missing", step, [], [], [])
   263	
   264	    executor_text = read_text(executor_path)
   265	    if not executor_text:
   266	        return VerifyDecision("BLOCKED", "executor_missing", step, [], [], [])
   267	
   268	    # Parse verify rules for this step
   269	    verify_rules = parse_verify_rules(plan_text, step)
   270	
   271	    # Also merge AC rules from spec.md (if available)
   272	    spec_acs = []
   273	    if spec_path and spec_path.exists():
   274	        spec_acs = parse_spec_acs(spec_path, step)
   275	    all_rules = verify_rules + [r for r in spec_acs if r not in verify_rules]
   276	
   277	    if not all_rules:
   278	        return VerifyDecision("REJECTED", "no_verify_rules", step, [], [], [],
   279	                              "Plan step must have verify rules or spec.md must have ACs.")
   280	    verify_rules = all_rules
   281	
   282	    # Check for invalid rule syntax
   283	    valid_prefixes = ("command:", "file:", "assertion:", "user:")
   284	    for rule in verify_rules:
   285	        if not any(rule.startswith(p) for p in valid_prefixes):
   286	            return VerifyDecision("REJECTED", f"invalid_verify_prefix: {rule}", step, [], [], [],
   287	                                  "Verify rule must start with command:/file:/assertion:/user:")
   288	
   289	    # Parse evidence
   290	    evidence = parse_evidence(executor_text, step)
   291	    if not evidence:
   292	        return VerifyDecision("BLOCKED", "no_evidence_for_step", step, [], verify_rules, [])
   293	
   294	    # Check for soft completion in evidence assertions
   295	    for ev in evidence:
   296	        assertion = str(ev.get("assertion", ""))
   297	        confirmation = str(ev.get("confirmation", ""))
   298	        if is_soft_completion(assertion) or is_soft_completion(confirmation):
   299	            return VerifyDecision("REJECTED", "soft_completion_in_evidence", step, [], verify_rules, [])
   300	
   301	    # Check for unresolved failures
   302	    failures = [ev for ev in evidence if ev.get("type") == "failure"]
   303	    # Remove failures that have subsequent covering success evidence
   304	    for fail in failures:
   305	        fail_action = str(fail.get("action", ""))
   306	        # Check if there's a successful command evidence with same source
   307	        covered = False
   308	        for ev in evidence:
   309	            if ev.get("type") == "failure":
   310	                continue
   311	            if ev.get("exit_code") == 0:
   312	                src = str(ev.get("source", ""))
   313	                if src and fail_action.endswith(src):
   314	                    covered = True
   315	                    break
   316	        if not covered:
   317	            return VerifyDecision("BLOCKED", f"unresolved_failure:{fail.get('id', 'unknown')}",
   318	                                  step, [], verify_rules, [])
   319	
   320	    # Match each verify rule
   321	    matched_rules: list[str] = []
   322	    missing_rules: list[str] = []
   323	    all_warnings: list[str] = []
   324	
   325	    for rule in verify_rules:
   326	        ok, reason, warns = match_verify_rule(rule, evidence)
   327	        all_warnings.extend(warns)
   328	        if ok:
   329	            matched_rules.append(reason)
   330	        else:
   331	            missing_rules.append(reason)
   332	
   333	    # Check user confirmation rules separately (weaker match needed)
   334	    user_rules = [r for r in missing_rules if r.startswith("no matching")]
   335	    user_verify = [r for r in verify_rules if r.startswith("user:")]
   336	    for vr in user_verify:
   337	        expected = vr[5:].strip().lower()
   338	        for ev in evidence:
   339	            if ev.get("type") != "user_confirmation":
   340	                continue
   341	            conf = str(ev.get("confirmation", "")).lower()
   342	            if is_soft_completion(conf):
   343	                all_warnings.append(f"user confirmation contains soft completion: '{conf}'")
   344	                continue
   345	            if len(conf) >= 8 and expected in conf:
   346	                matched_rules.append(f"user confirmation match: '{expected}'")
   347	                user_rules_to_remove = [r for r in missing_rules if "user:" in r]
   348	                for rr in user_rules_to_remove:
   349	                    if rr in missing_rules:
   350	                        missing_rules.remove(rr)
   351	
   352	    # Decision
   353	    if not missing_rules and not all_warnings:
   354	        return VerifyDecision("VERIFIED", "all_verify_rules_matched", step, matched_rules, [], [])
   355	    elif not missing_rules and all_warnings:
   356	        return VerifyDecision("WARN", "all_verify_matched_with_warnings", step, matched_rules, [], all_warnings)
   357	    elif missing_rules:
   358	        return VerifyDecision("BLOCKED", "evidence_missing", step, matched_rules, missing_rules, all_warnings)
   359	
   360	    return VerifyDecision("BLOCKED", "unknown", step, matched_rules, missing_rules, all_warnings)
   361	
   362	
   363	def write_audit(decision: VerifyDecision, token: dict[str, Any] | None = None) -> None:
   364	    event = {
   365	        "event_type": "verify_decision",
   366	        "timestamp": now_iso(),
   367	        "step": decision.step,
   368	        "decision": decision.decision,
   369	        "reason": decision.reason,
   370	        "matched": decision.matched,
   371	        "missing": decision.missing,
   372	        "warnings": decision.warnings,
   373	        "required_action": decision.required_action,
   374	    }
   375	    if token:
   376	        event["task_id"] = token.get("task", {}).get("id", "unknown")
   377	        event["level"] = token.get("session", {}).get("level", "unknown")
   378	    append_jsonl(Path(".omc/audit") / f"{today()}.jsonl", event)
   379	
   380	
   381	def main() -> int:
   382	    parser = argparse.ArgumentParser()
   383	    parser.add_argument("--step", required=True)
   384	    parser.add_argument("--plan", required=True)
   385	    parser.add_argument("--executor", required=True)
   386	    parser.add_argument("--token", required=False)
   387	    parser.add_argument("--spec", required=False,
   388	                       help="spec.md 路径 — 可选，提供 AC 规则以增强验证")
   389	    args = parser.parse_args()
   390	
   391	    token = read_json(Path(args.token)) if args.token else None
   392	    spec_path = Path(args.spec) if args.spec else None
   393	    result = verify_step(args.step, Path(args.plan), Path(args.executor),
   394	                         Path(args.token) if args.token else None, spec_path)
   395	
   396	    write_audit(result, token)
   397	
   398	    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
   399	    return 0 if result.decision == "VERIFIED" else 1
   400	
   401	
   402	if __name__ == "__main__":
   403	    raise SystemExit(main())
```
