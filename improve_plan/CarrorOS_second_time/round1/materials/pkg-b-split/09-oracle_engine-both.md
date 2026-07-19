# oracle_engine.py 双副本

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 同上
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.omc/scripts/oracle_engine.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_engine.py — Oracle/Meta-Oracle 高阶复核裁决引擎
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_engine.py <review_pack_path>
     7	
     8	7.md §6: L2 Model-pass-curve (7 维度)
     9	7.md §7: L3 Multi-Judge 投票 (Safety/Correctness/Architecture)
    10	7.md §8: Meta-Oracle 归一裁决
    11	
    12	Output: JSON with decision/reason/score fields
    13	"""
    14	
    15	import json
    16	import sys
    17	import math
    18	from pathlib import Path
    19	from datetime import datetime, timezone
    20	
    21	
    22	# ── L2 Pass-curve 评分器 ──
    23	# 7.md §6: 7 个固定维度
    24	
    25	SCORE_DIMENSIONS = [
    26	    "evidence_coverage",
    27	    "scope_integrity",
    28	    "regression_risk",
    29	    "security_risk",
    30	    "contract_preservation",
    31	    "failure_resolution",
    32	    "archive_readiness",
    33	]
    34	
    35	CRITICAL_FLOOR = 60
    36	ACCEPT_AVERAGE = 80
    37	WARN_AVERAGE = 65
    38	
    39	
    40	def _calc_evidence_coverage(pack: dict) -> dict:
    41	    """证据覆盖度 (0-100) — 对齐铁律 2"""
    42	    evidence = pack.get("verify_evidence", [])
    43	    if not evidence:
    44	        return {"score": 0, "detail": "no verify evidence"}
    45	    
    46	    # 每个 evidence_level：E3=100, E2=70, E1=40
    47	    scores = []
    48	    for e in evidence:
    49	        lvl = e.get("evidence_level", "E1")
    50	        if lvl == "E3":
    51	            scores.append(100)
    52	        elif lvl == "E2":
    53	            scores.append(70)
    54	        else:
    55	            scores.append(40)
    56	    
    57	    avg = sum(scores) / len(scores)
    58	    
    59	    # 检查是否有 exit_code 证据
    60	    has_command = any(e.get("type") == "command" for e in evidence)
    61	    has_test = any("test" in e.get("source", "").lower() for e in evidence)
    62	    
    63	    bonus = 0
    64	    if has_command:
    65	        bonus += 5
    66	    if has_test:
    67	        bonus += 10
    68	    
    69	    final = min(100, avg + bonus)
    70	    return {"score": round(final, 1), "detail": f"{len(evidence)} evidence items, avg_level={round(avg)}"}
    71	
    72	
    73	def _calc_scope_integrity(pack: dict) -> dict:
    74	    """范围完整性 (0-100) — 对齐铁律 3"""
    75	    scope = pack.get("scope", [])
    76	    completed = pack.get("completed_steps", [])
    77	    
    78	    if not scope and not completed:
    79	        return {"score": 100, "detail": "no scope constraints"}
    80	    
    81	    # 检查是否所有 scope 文件都被覆盖
    82	    files_changed = pack.get("diff_summary", {}).get("files_changed", 0)
    83	    risk_files = pack.get("diff_summary", {}).get("risk_files", [])
    84	    
    85	    if risk_files:
    86	        # 有风险文件时仅检查已知 scope 覆盖
    87	        score = max(60, 100 - len(risk_files) * 10)
    88	    elif files_changed == 0:
    89	        score = 100
    90	    else:
    91	        score = max(70, 100 - files_changed * 5)
    92	    
    93	    return {"score": round(score, 1), "detail": f"{len(scope)} scope items, {len(completed)} steps"}
    94	
    95	
    96	def _calc_regression_risk(pack: dict) -> dict:
    97	    """回归风险 (0-100) — 分数越高风险越低"""
    98	    diff = pack.get("diff_summary", {})
    99	    insertions = diff.get("insertions", 0)
   100	    deletions = diff.get("deletions", 0)
   101	    files_changed = diff.get("files_changed", 0)
   102	    
   103	    if files_changed == 0:
   104	        return {"score": 100, "detail": "no diff changes"}
   105	    
   106	    # 大规模变更 = 高回归风险
   107	    total = insertions + deletions
   108	    file_penalty = max(0, files_changed - 3) * 5
   109	    size_penalty = 0
   110	    if total > 500:
   111	        size_penalty = 20
   112	    elif total > 200:
   113	        size_penalty = 10
   114	    
   115	    base = 100 - file_penalty - size_penalty
   116	    
   117	    # 额外惩罚：配置/依赖变更
   118	    risk_files = diff.get("risk_files", [])
   119	    for rf in risk_files:
   120	        if any(k in rf.lower() for k in ["config", "dep", "package", "lock"]):
   121	            base -= 10
   122	    
   123	    return {"score": round(max(0, base), 1), "detail": f"{files_changed} files, {total} line changes"}
   124	
   125	
   126	def _calc_security_risk(pack: dict) -> dict:
   127	    """安全风险 (0-100) — 对齐铁律 4"""
   128	    risk_hints = pack.get("risk_hints", [])
   129	    
   130	    # 硬扣分项
   131	    score = 100
   132	    hints_lower = [h.lower() for h in risk_hints]
   133	    
   134	    if "auth_change" in hints_lower:
   135	        score -= 30
   136	    if "permission" in hints_lower:
   137	        score -= 25
   138	    if "production" in hints_lower:
   139	        score -= 20
   140	    if "cross_module" in hints_lower:
   141	        score -= 10
   142	    
   143	    # 检查 diff 中是否有 .env / credential 类文件
   144	    diff = pack.get("diff_summary", {})
   145	    risk_files = diff.get("risk_files", [])
   146	    for rf in risk_files:
   147	        if any(k in rf.lower() for k in [".env", "credential", "secret", "key", "token"]):
   148	            score -= 40
   149	    
   150	    return {"score": round(max(0, score), 1), "detail": f"risk_hints: {risk_hints}"}
   151	
   152	
   153	def _calc_contract_preservation(pack: dict) -> dict:
   154	    """契约保持 (0-100)"""
   155	    constraints = pack.get("user_constraints", [])
   156	    
   157	    if not constraints:
   158	        return {"score": 90, "detail": "no explicit constraints"}
   159	    
   160	    # 有约束时默认保守给分
   161	    score = max(70, 100 - len(constraints) * 5)
   162	    
   163	    return {"score": round(score, 1), "detail": f"{len(constraints)} constraints"}
   164	
   165	
   166	def _calc_failure_resolution(pack: dict) -> dict:
   167	    """失败解决 (0-100)"""
   168	    failures = pack.get("recent_failures", [])
   169	    
   170	    if not failures:
   171	        return {"score": 100, "detail": "no recent failures"}
   172	    
   173	    resolved = sum(1 for f in failures if f.get("covered_by"))
   174	    total = len(failures)
   175	    
   176	    if total == 0:
   177	        return {"score": 100, "detail": "no failures"}
   178	    
   179	    ratio = resolved / total
   180	    score = ratio * 100
   181	    
   182	    return {"score": round(score, 1), "detail": f"{resolved}/{total} failures resolved"}
   183	
   184	
   185	def _calc_archive_readiness(pack: dict) -> dict:
   186	    """归档就绪度 (0-100)"""
   187	    trigger = pack.get("trigger", "")
   188	    completed = pack.get("completed_steps", [])
   189	    
   190	    if trigger == "final_acceptance":
   191	        # 最终归档需要步阶梯完成
   192	        if not completed:
   193	            return {"score": 20, "detail": "no completed steps for final_acceptance"}
   194	        score = min(100, len(completed) * 20)
   195	    else:
   196	        score = 80
   197	    
   198	    return {"score": round(score, 1), "detail": f"trigger={trigger}, {len(completed)} steps"}
   199	
   200	
   201	def run_l2_pass_curve(pack: dict) -> dict:
   202	    """L2 Model-pass-curve — 7.md §6: 7 维度结构化评分"""
   203	    calculators = {
   204	        "evidence_coverage": _calc_evidence_coverage,
   205	        "scope_integrity": _calc_scope_integrity,
   206	        "regression_risk": _calc_regression_risk,
   207	        "security_risk": _calc_security_risk,
   208	        "contract_preservation": _calc_contract_preservation,
   209	        "failure_resolution": _calc_failure_resolution,
   210	        "archive_readiness": _calc_archive_readiness,
   211	    }
   212	    
   213	    scores = {}
   214	    total = 0.0
   215	    critical_issues = []
   216	    
   217	    for dim, calc_fn in calculators.items():
   218	        result = calc_fn(pack)
   219	        scores[dim] = result["score"]
   220	        total += result["score"]
   221	        
   222	        if result["score"] < CRITICAL_FLOOR:
   223	            critical_issues.append({
   224	                "dimension": dim,
   225	                "score": result["score"],
   226	                "detail": result["detail"],
   227	            })
   228	    
   229	    average = round(total / len(calculators), 2)
   230	    
   231	    return {
   232	        "scores": scores,
   233	        "average": average,
   234	        "critical_issues": critical_issues,
   235	    }
   236	
   237	
   238	# ── L3 Multi-Judge 投票 ──
   239	# 7.md §7: Safety / Correctness / Architecture
   240	
   241	def run_l3_multi_judge(pack: dict, l2_result: dict) -> list:
   242	    """L3 Multi-Judge — 基于 L2 评分推导 Judge 投票"""
   243	    scores = l2_result["scores"]
   244	    judges = []
   245	    
   246	    # Judge-A: Safety — 基于 security_risk + 检查高风险 hint
   247	    security = scores.get("security_risk", 100)
   248	    risk_hints = [h.lower() for h in pack.get("risk_hints", [])]
   249	    
   250	    if security < 60:
   251	        vote = "REJECT"
   252	        reason = "security_risk below critical floor"
   253	    elif security < 75 or any(h in risk_hints for h in ["auth_change", "production", "permission"]):
   254	        vote = "WARN"
   255	        reason = "elevated security risk or sensitive risk hint"
   256	    else:
   257	        vote = "ACCEPT"
   258	        reason = "no significant security concern"
   259	    
   260	    judges.append({
   261	        "judge": "Safety",
   262	        "vote": vote,
   263	        "reason": reason,
   264	        "required_action": "review security impact" if vote != "ACCEPT" else None,
   265	    })
   266	    
   267	    # Judge-B: Correctness — 基于 evidence + regression
   268	    evidence = scores.get("evidence_coverage", 0)
   269	    regression = scores.get("regression_risk", 100)
   270	    
   271	    if evidence < 60 or regression < 60:
   272	        vote = "REJECT"
   273	        reason = "insufficient evidence or high regression risk"
   274	    elif evidence < 75 or regression < 75:
   275	        vote = "WARN"
   276	        reason = "evidence or regression coverage below threshold"
   277	    else:
   278	        vote = "ACCEPT"
   279	        reason = "evidence and regression acceptable"
   280	    
   281	    judges.append({
   282	        "judge": "Correctness",
   283	        "vote": vote,
   284	        "reason": reason,
   285	        "required_action": "strengthen test coverage" if vote != "ACCEPT" else None,
   286	    })
   287	    
   288	    # Judge-C: Architecture — 基于 scope + contract
   289	    scope = scores.get("scope_integrity", 100)
   290	    contract = scores.get("contract_preservation", 100)
   291	    
   292	    if scope < 60 or contract < 60:
   293	        vote = "REJECT"
   294	        reason = "scope violation or contract break"
   295	    elif scope < 75 or contract < 75:
   296	        vote = "WARN"
   297	        reason = "architectural concerns in scope or contract"
   298	    else:
   299	        vote = "ACCEPT"
   300	        reason = "architecture consistent"
   301	    
   302	    judges.append({
   303	        "judge": "Architecture",
   304	        "vote": vote,
   305	        "reason": reason,
   306	        "required_action": "review scope boundaries" if vote != "ACCEPT" else None,
   307	    })
   308	    
   309	    return judges
   310	
   311	
   312	# ── Meta-Oracle 归一裁决 ──
   313	# 7.md §8: 冲突归一规则
   314	
   315	META_RULES = {
   316	    "accept_accept": "ACCEPT",
   317	    "accept_warn": "WARN",
   318	    "warn_accept": "WARN",
   319	    "warn_warn": "WARN",
   320	}
   321	
   322	
   323	def run_meta_oracle(l2_result: dict, judges: list) -> dict:
   324	    """Meta-Oracle 归一裁决 — 7.md §8"""
   325	    l2_decision = _l2_decision(l2_result)
   326	    l3_vote_map = {j["judge"]: j["vote"] for j in judges}
   327	    
   328	    # 任一安全类 REJECT → 不允许自动覆盖
   329	    safety_vote = l3_vote_map.get("Safety", "")
   330	    if safety_vote == "REJECT":
   331	        return {
   332	            "decision": "REJECT",
   333	            "reason": "l3_reject:Safety",
   334	            "required_action": "obtain human security approval",
   335	            "l2_decision": l2_decision,
   336	            "l3_votes": l3_vote_map,
   337	        }
   338	    
   339	    # 其他 REJECT
   340	    if any(v == "REJECT" for v in l3_vote_map.values()):
   341	        reject_judges = [j for j in judges if j["vote"] == "REJECT"]
   342	        return {
   343	            "decision": "REJECT",
   344	            "reason": f"l3_reject:{','.join(j['judge'] for j in reject_judges)}",
   345	            "required_action": "rerun VerifyGate or repair evidence",
   346	            "l2_decision": l2_decision,
   347	            "l3_votes": l3_vote_map,
   348	        }
   349	    
   350	    # L2 决定
   351	    if l2_decision == "REJECT":
   352	        return {
   353	            "decision": "REJECT",
   354	            "reason": "l2_reject",
   355	            "required_action": "rerun VerifyGate or repair evidence",
   356	            "l2_decision": l2_decision,
   357	            "l3_votes": l3_vote_map,
   358	        }
   359	    
   360	    if l2_decision == "ESCALATE":
   361	        return {
   362	            "decision": "ESCALATE",
   363	            "reason": "l2_escalate",
   364	            "required_action": "human decision required",
   365	            "l2_decision": l2_decision,
   366	            "l3_votes": l3_vote_map,
   367	        }
   368	    
   369	    # 两个及以上 WARN
   370	    warn_count = sum(1 for v in l3_vote_map.values() if v == "WARN")
   371	    if warn_count >= 2:
   372	        return {
   373	            "decision": "WARN",
   374	            "reason": "l3_multi_warn",
   375	            "required_action": "address all warnings before next phase",
   376	            "l2_decision": l2_decision,
   377	            "l3_votes": l3_vote_map,
   378	        }
   379	    
   380	    # 一个 WARN + 两个 ACCEPT → 由 Meta-Oracle 裁断
   381	    if warn_count == 1:
   382	        if l2_decision == "ACCEPT":
   383	            decision = "ACCEPT"
   384	            reason = "l2_accept_with_notes"
   385	        else:
   386	            decision = "WARN"
   387	            reason = "l2_or_l3_warn"
   388	        return {
   389	            "decision": decision,
   390	            "reason": reason,
   391	            "required_action": None,
   392	            "l2_decision": l2_decision,
   393	            "l3_votes": l3_vote_map,
   394	        }
   395	    
   396	    # 三个 ACCEPT
   397	    if l2_decision == "ACCEPT":
   398	        return {
   399	            "decision": "ACCEPT",
   400	            "reason": "l2_l3_accept",
   401	            "required_action": None,
   402	            "l2_decision": l2_decision,
   403	            "l3_votes": l3_vote_map,
   404	        }
   405	    
   406	    # L2 WARN + L3 全 ACCEPT → WARN
   407	    return {
   408	        "decision": "WARN",
   409	        "reason": "l2_warn",
   410	        "required_action": "address l2 warnings before proceeding",
   411	        "l2_decision": l2_decision,
   412	        "l3_votes": l3_vote_map,
   413	    }
   414	
   415	
   416	def _l2_decision(l2_result: dict) -> str:
   417	    """从 L2 pass-curve 推导裁决"""
   418	    average = l2_result["average"]
   419	    critical = l2_result["critical_issues"]
   420	    
   421	    if critical:
   422	        return "REJECT"
   423	    
   424	    if average >= ACCEPT_AVERAGE:
   425	        return "ACCEPT"
   426	    
   427	    if average >= WARN_AVERAGE:
   428	        return "WARN"
   429	    
   430	    return "REJECT"
   431	
   432	
   433	# ── 主入口 ──
   434	
   435	def main():
   436	    if len(sys.argv) < 2:
   437	        print(json.dumps({"error": "Usage: oracle_engine.py <review_pack_path>"}))
   438	        return 1
   439	    
   440	    pack_path = Path(sys.argv[1])
   441	    if not pack_path.exists():
   442	        print(json.dumps({"error": f"Review pack not found: {pack_path}"}))
   443	        return 1
   444	    
   445	    pack = json.loads(pack_path.read_text())
   446	    
   447	    # L2 pass-curve
   448	    l2 = run_l2_pass_curve(pack)
   449	    
   450	    # L3 Multi-Judge
   451	    judges = run_l3_multi_judge(pack, l2)
   452	    
   453	    # Meta-Oracle 归一
   454	    meta = run_meta_oracle(l2, judges)
   455	    
   456	    # 构建输出
   457	    output = {
   458	        "decision": meta["decision"],
   459	        "reason": meta["reason"],
   460	        "trigger": pack.get("trigger", "unknown"),
   461	        "phase": pack.get("phase", "execute"),
   462	        "l2_average": l2["average"],
   463	        "l2_scores": l2["scores"],
   464	        "l2_critical_issues": l2["critical_issues"],
   465	        "l3_votes": meta["l3_votes"],
   466	        "required_action": meta.get("required_action"),
   467	        "residual_risk": [],
   468	        "timestamp": datetime.now(timezone.utc).isoformat(),
   469	    }
   470	    
   471	    # 构建 residual_risk
   472	    for issue in l2["critical_issues"]:
   473	        output["residual_risk"].append(
   474	            f"{issue['dimension']} score={issue['score']}: {issue['detail']}"
   475	        )
   476	    for j in judges:
   477	        if j["vote"] != "ACCEPT":
   478	            output["residual_risk"].append(
   479	                f"{j['judge']}: {j['reason']}"
   480	            )
   481	    
   482	    print(json.dumps(output, indent=2, ensure_ascii=False))
   483	    return 0
   484	
   485	
   486	if __name__ == "__main__":
   487	    sys.exit(main())
```

## `.claude/scripts/oracle_engine.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_engine.py — Oracle/Meta-Oracle 高阶复核裁决引擎
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_engine.py <review_pack_path>
     7	
     8	7.md §6: L2 Model-pass-curve (7 维度)
     9	7.md §7: L3 Multi-Judge 投票 (Safety/Correctness/Architecture)
    10	7.md §8: Meta-Oracle 归一裁决
    11	
    12	Output: JSON with decision/reason/score fields
    13	"""
    14	
    15	import json
    16	import sys
    17	import math
    18	from pathlib import Path
    19	from datetime import datetime, timezone
    20	
    21	
    22	# ── L2 Pass-curve 评分器 ──
    23	# 7.md §6: 7 个固定维度
    24	
    25	SCORE_DIMENSIONS = [
    26	    "evidence_coverage",
    27	    "scope_integrity",
    28	    "regression_risk",
    29	    "security_risk",
    30	    "contract_preservation",
    31	    "failure_resolution",
    32	    "archive_readiness",
    33	]
    34	
    35	CRITICAL_FLOOR = 60
    36	ACCEPT_AVERAGE = 80
    37	WARN_AVERAGE = 65
    38	
    39	
    40	def _calc_evidence_coverage(pack: dict) -> dict:
    41	    """证据覆盖度 (0-100) — 对齐铁律 2"""
    42	    evidence = pack.get("verify_evidence", [])
    43	    if not evidence:
    44	        return {"score": 0, "detail": "no verify evidence"}
    45	    
    46	    # 每个 evidence_level：E3=100, E2=70, E1=40
    47	    scores = []
    48	    for e in evidence:
    49	        lvl = e.get("evidence_level", "E1")
    50	        if lvl == "E3":
    51	            scores.append(100)
    52	        elif lvl == "E2":
    53	            scores.append(70)
    54	        else:
    55	            scores.append(40)
    56	    
    57	    avg = sum(scores) / len(scores)
    58	    
    59	    # 检查是否有 exit_code 证据
    60	    has_command = any(e.get("type") == "command" for e in evidence)
    61	    has_test = any("test" in e.get("source", "").lower() for e in evidence)
    62	    
    63	    bonus = 0
    64	    if has_command:
    65	        bonus += 5
    66	    if has_test:
    67	        bonus += 10
    68	    
    69	    final = min(100, avg + bonus)
    70	    return {"score": round(final, 1), "detail": f"{len(evidence)} evidence items, avg_level={round(avg)}"}
    71	
    72	
    73	def _calc_scope_integrity(pack: dict) -> dict:
    74	    """范围完整性 (0-100) — 对齐铁律 3"""
    75	    scope = pack.get("scope", [])
    76	    completed = pack.get("completed_steps", [])
    77	    
    78	    if not scope and not completed:
    79	        return {"score": 100, "detail": "no scope constraints"}
    80	    
    81	    # 检查是否所有 scope 文件都被覆盖
    82	    files_changed = pack.get("diff_summary", {}).get("files_changed", 0)
    83	    risk_files = pack.get("diff_summary", {}).get("risk_files", [])
    84	    
    85	    if risk_files:
    86	        # 有风险文件时仅检查已知 scope 覆盖
    87	        score = max(60, 100 - len(risk_files) * 10)
    88	    elif files_changed == 0:
    89	        score = 100
    90	    else:
    91	        score = max(70, 100 - files_changed * 5)
    92	    
    93	    return {"score": round(score, 1), "detail": f"{len(scope)} scope items, {len(completed)} steps"}
    94	
    95	
    96	def _calc_regression_risk(pack: dict) -> dict:
    97	    """回归风险 (0-100) — 分数越高风险越低"""
    98	    diff = pack.get("diff_summary", {})
    99	    insertions = diff.get("insertions", 0)
   100	    deletions = diff.get("deletions", 0)
   101	    files_changed = diff.get("files_changed", 0)
   102	    
   103	    if files_changed == 0:
   104	        return {"score": 100, "detail": "no diff changes"}
   105	    
   106	    # 大规模变更 = 高回归风险
   107	    total = insertions + deletions
   108	    file_penalty = max(0, files_changed - 3) * 5
   109	    size_penalty = 0
   110	    if total > 500:
   111	        size_penalty = 20
   112	    elif total > 200:
   113	        size_penalty = 10
   114	    
   115	    base = 100 - file_penalty - size_penalty
   116	    
   117	    # 额外惩罚：配置/依赖变更
   118	    risk_files = diff.get("risk_files", [])
   119	    for rf in risk_files:
   120	        if any(k in rf.lower() for k in ["config", "dep", "package", "lock"]):
   121	            base -= 10
   122	    
   123	    return {"score": round(max(0, base), 1), "detail": f"{files_changed} files, {total} line changes"}
   124	
   125	
   126	def _calc_security_risk(pack: dict) -> dict:
   127	    """安全风险 (0-100) — 对齐铁律 4"""
   128	    risk_hints = pack.get("risk_hints", [])
   129	    
   130	    # 硬扣分项
   131	    score = 100
   132	    hints_lower = [h.lower() for h in risk_hints]
   133	    
   134	    if "auth_change" in hints_lower:
   135	        score -= 30
   136	    if "permission" in hints_lower:
   137	        score -= 25
   138	    if "production" in hints_lower:
   139	        score -= 20
   140	    if "cross_module" in hints_lower:
   141	        score -= 10
   142	    
   143	    # 检查 diff 中是否有 .env / credential 类文件
   144	    diff = pack.get("diff_summary", {})
   145	    risk_files = diff.get("risk_files", [])
   146	    for rf in risk_files:
   147	        if any(k in rf.lower() for k in [".env", "credential", "secret", "key", "token"]):
   148	            score -= 40
   149	    
   150	    return {"score": round(max(0, score), 1), "detail": f"risk_hints: {risk_hints}"}
   151	
   152	
   153	def _calc_contract_preservation(pack: dict) -> dict:
   154	    """契约保持 (0-100)"""
   155	    constraints = pack.get("user_constraints", [])
   156	    
   157	    if not constraints:
   158	        return {"score": 90, "detail": "no explicit constraints"}
   159	    
   160	    # 有约束时默认保守给分
   161	    score = max(70, 100 - len(constraints) * 5)
   162	    
   163	    return {"score": round(score, 1), "detail": f"{len(constraints)} constraints"}
   164	
   165	
   166	def _calc_failure_resolution(pack: dict) -> dict:
   167	    """失败解决 (0-100)"""
   168	    failures = pack.get("recent_failures", [])
   169	    
   170	    if not failures:
   171	        return {"score": 100, "detail": "no recent failures"}
   172	    
   173	    resolved = sum(1 for f in failures if f.get("covered_by"))
   174	    total = len(failures)
   175	    
   176	    if total == 0:
   177	        return {"score": 100, "detail": "no failures"}
   178	    
   179	    ratio = resolved / total
   180	    score = ratio * 100
   181	    
   182	    return {"score": round(score, 1), "detail": f"{resolved}/{total} failures resolved"}
   183	
   184	
   185	def _calc_archive_readiness(pack: dict) -> dict:
   186	    """归档就绪度 (0-100)"""
   187	    trigger = pack.get("trigger", "")
   188	    completed = pack.get("completed_steps", [])
   189	    
   190	    if trigger == "final_acceptance":
   191	        # 最终归档需要步阶梯完成
   192	        if not completed:
   193	            return {"score": 20, "detail": "no completed steps for final_acceptance"}
   194	        score = min(100, len(completed) * 20)
   195	    else:
   196	        score = 80
   197	    
   198	    return {"score": round(score, 1), "detail": f"trigger={trigger}, {len(completed)} steps"}
   199	
   200	
   201	def run_l2_pass_curve(pack: dict) -> dict:
   202	    """L2 Model-pass-curve — 7.md §6: 7 维度结构化评分"""
   203	    calculators = {
   204	        "evidence_coverage": _calc_evidence_coverage,
   205	        "scope_integrity": _calc_scope_integrity,
   206	        "regression_risk": _calc_regression_risk,
   207	        "security_risk": _calc_security_risk,
   208	        "contract_preservation": _calc_contract_preservation,
   209	        "failure_resolution": _calc_failure_resolution,
   210	        "archive_readiness": _calc_archive_readiness,
   211	    }
   212	    
   213	    scores = {}
   214	    total = 0.0
   215	    critical_issues = []
   216	    
   217	    for dim, calc_fn in calculators.items():
   218	        result = calc_fn(pack)
   219	        scores[dim] = result["score"]
   220	        total += result["score"]
   221	        
   222	        if result["score"] < CRITICAL_FLOOR:
   223	            critical_issues.append({
   224	                "dimension": dim,
   225	                "score": result["score"],
   226	                "detail": result["detail"],
   227	            })
   228	    
   229	    average = round(total / len(calculators), 2)
   230	    
   231	    return {
   232	        "scores": scores,
   233	        "average": average,
   234	        "critical_issues": critical_issues,
   235	    }
   236	
   237	
   238	# ── L3 Multi-Judge 投票 ──
   239	# 7.md §7: Safety / Correctness / Architecture
   240	
   241	def run_l3_multi_judge(pack: dict, l2_result: dict) -> list:
   242	    """L3 Multi-Judge — 基于 L2 评分推导 Judge 投票"""
   243	    scores = l2_result["scores"]
   244	    judges = []
   245	    
   246	    # Judge-A: Safety — 基于 security_risk + 检查高风险 hint
   247	    security = scores.get("security_risk", 100)
   248	    risk_hints = [h.lower() for h in pack.get("risk_hints", [])]
   249	    
   250	    if security < 60:
   251	        vote = "REJECT"
   252	        reason = "security_risk below critical floor"
   253	    elif security < 75 or any(h in risk_hints for h in ["auth_change", "production", "permission"]):
   254	        vote = "WARN"
   255	        reason = "elevated security risk or sensitive risk hint"
   256	    else:
   257	        vote = "ACCEPT"
   258	        reason = "no significant security concern"
   259	    
   260	    judges.append({
   261	        "judge": "Safety",
   262	        "vote": vote,
   263	        "reason": reason,
   264	        "required_action": "review security impact" if vote != "ACCEPT" else None,
   265	    })
   266	    
   267	    # Judge-B: Correctness — 基于 evidence + regression
   268	    evidence = scores.get("evidence_coverage", 0)
   269	    regression = scores.get("regression_risk", 100)
   270	    
   271	    if evidence < 60 or regression < 60:
   272	        vote = "REJECT"
   273	        reason = "insufficient evidence or high regression risk"
   274	    elif evidence < 75 or regression < 75:
   275	        vote = "WARN"
   276	        reason = "evidence or regression coverage below threshold"
   277	    else:
   278	        vote = "ACCEPT"
   279	        reason = "evidence and regression acceptable"
   280	    
   281	    judges.append({
   282	        "judge": "Correctness",
   283	        "vote": vote,
   284	        "reason": reason,
   285	        "required_action": "strengthen test coverage" if vote != "ACCEPT" else None,
   286	    })
   287	    
   288	    # Judge-C: Architecture — 基于 scope + contract
   289	    scope = scores.get("scope_integrity", 100)
   290	    contract = scores.get("contract_preservation", 100)
   291	    
   292	    if scope < 60 or contract < 60:
   293	        vote = "REJECT"
   294	        reason = "scope violation or contract break"
   295	    elif scope < 75 or contract < 75:
   296	        vote = "WARN"
   297	        reason = "architectural concerns in scope or contract"
   298	    else:
   299	        vote = "ACCEPT"
   300	        reason = "architecture consistent"
   301	    
   302	    judges.append({
   303	        "judge": "Architecture",
   304	        "vote": vote,
   305	        "reason": reason,
   306	        "required_action": "review scope boundaries" if vote != "ACCEPT" else None,
   307	    })
   308	    
   309	    return judges
   310	
   311	
   312	# ── Meta-Oracle 归一裁决 ──
   313	# 7.md §8: 冲突归一规则
   314	
   315	META_RULES = {
   316	    "accept_accept": "ACCEPT",
   317	    "accept_warn": "WARN",
   318	    "warn_accept": "WARN",
   319	    "warn_warn": "WARN",
   320	}
   321	
   322	
   323	def run_meta_oracle(l2_result: dict, judges: list) -> dict:
   324	    """Meta-Oracle 归一裁决 — 7.md §8"""
   325	    l2_decision = _l2_decision(l2_result)
   326	    l3_vote_map = {j["judge"]: j["vote"] for j in judges}
   327	    
   328	    # 任一安全类 REJECT → 不允许自动覆盖
   329	    safety_vote = l3_vote_map.get("Safety", "")
   330	    if safety_vote == "REJECT":
   331	        return {
   332	            "decision": "REJECT",
   333	            "reason": "l3_reject:Safety",
   334	            "required_action": "obtain human security approval",
   335	            "l2_decision": l2_decision,
   336	            "l3_votes": l3_vote_map,
   337	        }
   338	    
   339	    # 其他 REJECT
   340	    if any(v == "REJECT" for v in l3_vote_map.values()):
   341	        reject_judges = [j for j in judges if j["vote"] == "REJECT"]
   342	        return {
   343	            "decision": "REJECT",
   344	            "reason": f"l3_reject:{','.join(j['judge'] for j in reject_judges)}",
   345	            "required_action": "rerun VerifyGate or repair evidence",
   346	            "l2_decision": l2_decision,
   347	            "l3_votes": l3_vote_map,
   348	        }
   349	    
   350	    # L2 决定
   351	    if l2_decision == "REJECT":
   352	        return {
   353	            "decision": "REJECT",
   354	            "reason": "l2_reject",
   355	            "required_action": "rerun VerifyGate or repair evidence",
   356	            "l2_decision": l2_decision,
   357	            "l3_votes": l3_vote_map,
   358	        }
   359	    
   360	    if l2_decision == "ESCALATE":
   361	        return {
   362	            "decision": "ESCALATE",
   363	            "reason": "l2_escalate",
   364	            "required_action": "human decision required",
   365	            "l2_decision": l2_decision,
   366	            "l3_votes": l3_vote_map,
   367	        }
   368	    
   369	    # 两个及以上 WARN
   370	    warn_count = sum(1 for v in l3_vote_map.values() if v == "WARN")
   371	    if warn_count >= 2:
   372	        return {
   373	            "decision": "WARN",
   374	            "reason": "l3_multi_warn",
   375	            "required_action": "address all warnings before next phase",
   376	            "l2_decision": l2_decision,
   377	            "l3_votes": l3_vote_map,
   378	        }
   379	    
   380	    # 一个 WARN + 两个 ACCEPT → 由 Meta-Oracle 裁断
   381	    if warn_count == 1:
   382	        if l2_decision == "ACCEPT":
   383	            decision = "ACCEPT"
   384	            reason = "l2_accept_with_notes"
   385	        else:
   386	            decision = "WARN"
   387	            reason = "l2_or_l3_warn"
   388	        return {
   389	            "decision": decision,
   390	            "reason": reason,
   391	            "required_action": None,
   392	            "l2_decision": l2_decision,
   393	            "l3_votes": l3_vote_map,
   394	        }
   395	    
   396	    # 三个 ACCEPT
   397	    if l2_decision == "ACCEPT":
   398	        return {
   399	            "decision": "ACCEPT",
   400	            "reason": "l2_l3_accept",
   401	            "required_action": None,
   402	            "l2_decision": l2_decision,
   403	            "l3_votes": l3_vote_map,
   404	        }
   405	    
   406	    # L2 WARN + L3 全 ACCEPT → WARN
   407	    return {
   408	        "decision": "WARN",
   409	        "reason": "l2_warn",
   410	        "required_action": "address l2 warnings before proceeding",
   411	        "l2_decision": l2_decision,
   412	        "l3_votes": l3_vote_map,
   413	    }
   414	
   415	
   416	def _l2_decision(l2_result: dict) -> str:
   417	    """从 L2 pass-curve 推导裁决"""
   418	    average = l2_result["average"]
   419	    critical = l2_result["critical_issues"]
   420	    
   421	    if critical:
   422	        return "REJECT"
   423	    
   424	    if average >= ACCEPT_AVERAGE:
   425	        return "ACCEPT"
   426	    
   427	    if average >= WARN_AVERAGE:
   428	        return "WARN"
   429	    
   430	    return "REJECT"
   431	
   432	
   433	# ── 主入口 ──
   434	
   435	def main():
   436	    if len(sys.argv) < 2:
   437	        print(json.dumps({"error": "Usage: oracle_engine.py <review_pack_path>"}))
   438	        return 1
   439	    
   440	    pack_path = Path(sys.argv[1])
   441	    if not pack_path.exists():
   442	        print(json.dumps({"error": f"Review pack not found: {pack_path}"}))
   443	        return 1
   444	    
   445	    pack = json.loads(pack_path.read_text())
   446	    
   447	    # L2 pass-curve
   448	    l2 = run_l2_pass_curve(pack)
   449	    
   450	    # L3 Multi-Judge
   451	    judges = run_l3_multi_judge(pack, l2)
   452	    
   453	    # Meta-Oracle 归一
   454	    meta = run_meta_oracle(l2, judges)
   455	    
   456	    # 构建输出
   457	    output = {
   458	        "decision": meta["decision"],
   459	        "reason": meta["reason"],
   460	        "trigger": pack.get("trigger", "unknown"),
   461	        "phase": pack.get("phase", "execute"),
   462	        "l2_average": l2["average"],
   463	        "l2_scores": l2["scores"],
   464	        "l2_critical_issues": l2["critical_issues"],
   465	        "l3_votes": meta["l3_votes"],
   466	        "required_action": meta.get("required_action"),
   467	        "residual_risk": [],
   468	        "timestamp": datetime.now(timezone.utc).isoformat(),
   469	    }
   470	    
   471	    # 构建 residual_risk
   472	    for issue in l2["critical_issues"]:
   473	        output["residual_risk"].append(
   474	            f"{issue['dimension']} score={issue['score']}: {issue['detail']}"
   475	        )
   476	    for j in judges:
   477	        if j["vote"] != "ACCEPT":
   478	            output["residual_risk"].append(
   479	                f"{j['judge']}: {j['reason']}"
   480	            )
   481	    
   482	    print(json.dumps(output, indent=2, ensure_ascii=False))
   483	    return 0
   484	
   485	
   486	if __name__ == "__main__":
   487	    sys.exit(main())
```
