# carros_base.py [2/4] ★验证核心

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | cmd_status/cmd_tick/_run_dual_judge/**cmd_verify 788-864**/cmd_report(第 589-923 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/carros_base.py` 第 589-923 行

```python
   589	def _find_latest_token(require_active=True):
   590	    """扫描 tokens 目录，找到日期最新且活跃的 token
   591	
   592	    require_active=True: 只返回 status=active 的 token（首选）
   593	    require_active=False: 返回任何一个有效的 token（作为回退）
   594	
   595	    排序规则：按文件 mtime 倒序（最新写的优先），而非文件名排序
   596	    """
   597	    OMC_TOKENS.mkdir(parents=True, exist_ok=True)
   598	    if not OMC_TOKENS.exists():
   599	        return None, None
   600	
   601	    # 收集所有 token 文件，按 mtime 排序
   602	    candidates = []
   603	    for dd in sorted(OMC_TOKENS.iterdir(), reverse=True):
   604	        if dd.is_dir():
   605	            for jf in dd.glob("*.json"):
   606	                try:
   607	                    candidates.append((jf.stat().st_mtime, jf))
   608	                except OSError:
   609	                    continue
   610	
   611	    # 按 mtime 倒序
   612	    candidates.sort(key=lambda x: x[0], reverse=True)
   613	
   614	    fallback = None
   615	    for _, jf in candidates:
   616	        try:
   617	            token = json.loads(jf.read_text())
   618	            if token.get("status") == "active":
   619	                return token, jf
   620	            if fallback is None:
   621	                fallback = (token, jf)
   622	        except (json.JSONDecodeError, OSError):
   623	            continue
   624	
   625	    if fallback and not require_active:
   626	        return fallback
   627	    return None, None
   628	
   629	
   630	def cmd_status(hot_mode=True):
   631	    """展示当前任务状态。默认 Hot Card 模式。--full 出完整状态。"""
   632	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   633	        token, found_path = _find_latest_token()
   634	        if token and found_path:
   635	            _init_paths_from_token(token, found_path)
   636	        else:
   637	            print(_yellow("⚠  No active task"))
   638	            return 0
   639	    token = _load_token()
   640	    if not token:
   641	        print(_yellow("⚠  No active task (token.json not found)"))
   642	        return 0
   643	
   644	    if hot_mode:
   645	        # Hot Card — 极简状态（默认）
   646	        try:
   647	            import lib.hot_card as hc
   648	            card = hc.cmd_status_hot(token, TOKEN_PATH, PLAN_PATH, EXECUTOR_PATH)
   649	            print(card)
   650	            hc_len = len(card)
   651	            if hc_len > 4500:
   652	                print(_yellow(f"\n⚠  Hot Card exceeds 4.5K chars: {hc_len}"))
   653	            return 0
   654	        except ImportError:
   655	            # fallback: lib/ not available
   656	            pass
   657	
   658	    # Full status（--full 模式或 fallback）
   659	    s = token.get("stats", {})
   660	    status_top = token.get("status", "?")
   661	    status_icon = _green("●") if status_top == "active" else _red("●")
   662	    print(f"{status_icon} Task: {token.get('session', {}).get('id', '?')} [{token.get('session', {}).get('level', '?')}]")
   663	    print(f"   Status: {status_top}")
   664	    print(f"   Progress: {s.get('done', 0)}/{s.get('total', 0)} steps completed")
   665	    current_step = token.get("task", {}).get("current_step")
   666	    task_status = token.get("task", {}).get("status")
   667	    blocked = token.get("task", {}).get("blocked")
   668	    current = current_step or "?"
   669	    print(f"   Current Step: {current}")
   670	    print(f"   Task Status: {task_status}")
   671	    if blocked:
   672	        print(f"   Blocked: {blocked}")
   673	    # task-state 追踪展示
   674	    if tst:
   675	        state_info = tst.format_status(token, TOKEN_PATH)
   676	        if state_info:
   677	            print(state_info)
   678	    return 0
   679	
   680	
   681	def cmd_tick():
   682	    """递增 tick 计数器 + 水位检查 + 自动追踪当前步骤状态"""
   683	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   684	        token, found_path = _find_latest_token()
   685	        if token and found_path:
   686	            _init_paths_from_token(token, found_path)
   687	        else:
   688	            print(_red("❌ No active task"))
   689	            return 2
   690	    token = _load_token()
   691	    if not token:
   692	        print(_red("❌ No active task"))
   693	        return 2
   694	
   695	    # 水位检查
   696	    try:
   697	        from lib.water_level import run_water_gate
   698	        gate = run_water_gate(action="tick")
   699	        if not gate["continue"]:
   700	            print(_yellow(f"⚠  {gate['message']}"))
   701	            # Pause: write handoff, request compact
   702	            from lib.handoff_writer import write_handoff
   703	            write_handoff(TASK_DIR, token.get("session",{}).get("id",""), token, PLAN_PATH, executor_path=EXECUTOR_PATH)
   704	            return 0  # soft pause, not error
   705	        elif gate["water"]["level"] == "warn":
   706	            print(_yellow(f"⚠  {gate['message']}"))
   707	    except ImportError:
   708	        pass  # water_level.py not available — continue without
   709	
   710	    # 找当前 pending 步骤 — 从 plan.md 读取
   711	    current_step = None
   712	    if PLAN_PATH and PLAN_PATH.exists():
   713	        plan_content = PLAN_PATH.read_text()
   714	        pending_steps = re.findall(r"^- \[ \] (\S+?):", plan_content, re.MULTILINE)
   715	        if pending_steps:
   716	            current_step = pending_steps[0]
   717	    else:
   718	        current_step = token.get("task", {}).get("current_step")
   719	
   720	    if "tick" in token.get("stats", {}):
   721	        token["stats"]["tick"] += 1
   722	        print(f"   Tick: {token['stats']['tick']}")
   723	    else:
   724	        token["stats"]["turns"] = token["stats"].get("turns", 0) + 1
   725	        print(f"   Turn: {token['stats']['turns']}")
   726	    _save_token(token)
   727	
   728	    # task-state: 记录步骤开始追踪
   729	    if current_step and tst:
   730	        tst.mark_step_started(TOKEN_PATH, current_step)
   731	        print(f"   ◷ Tracking {current_step} (use 'verify' to complete)")
   732	    return 0
   733	
   734	
   735	def _run_dual_judge(token: dict) -> int:
   736	    """L2 任务 verify 自动双审判：static + runtime oracle → meta 聚合。
   737	
   738	    裁决落盘 .omc/state/meta-oracle-verdicts/{task_id}/latest.json。
   739	    Returns: 0=ACCEPT/ADVISORY（放行）, 2=REJECT（verify 不通过）, 3=ESCALATE（放行但提示人工）。
   740	    """
   741	    task_id = token.get("session", {}).get("id", "unknown")
   742	    static_agent = _hook_dir / "static_oracle_agent.py"
   743	    runtime_agent = _hook_dir / "runtime_oracle_agent.py"
   744	    meta = _hook_dir / "meta_oracle.py"
   745	    if not (static_agent.exists() and runtime_agent.exists() and meta.exists()):
   746	        print(_yellow("⚠  dual-judge 脚本缺失，跳过（降级为人工复核）"))
   747	        return 0
   748	
   749	    print("⚖️  L2 双审判官裁决（static → runtime → meta）...")
   750	    for name, agent in (("static", static_agent), ("runtime", runtime_agent)):
   751	        try:
   752	            r = subprocess.run(
   753	                [sys.executable, str(agent), "review", "--task-id", task_id],
   754	                capture_output=True, text=True, timeout=120,
   755	            )
   756	            if r.returncode not in (0, 1):
   757	                print(_yellow(f"⚠  {name} oracle exit={r.returncode}: {r.stderr[:200]}"))
   758	        except Exception as exc:
   759	            print(_yellow(f"⚠  {name} oracle 异常: {exc}"))
   760	
   761	    try:
   762	        r = subprocess.run(
   763	            [sys.executable, str(meta), "aggregate", "--task-id", task_id],
   764	            capture_output=True, text=True, timeout=30,
   765	        )
   766	        out = r.stdout.strip()
   767	        verdict = "UNAVAILABLE"
   768	        try:
   769	            json_start = out.find("{")
   770	            if json_start >= 0:
   771	                verdict = json.loads(out[json_start:]).get("verdict", "UNAVAILABLE")
   772	        except Exception:
   773	            pass
   774	        _write_audit("dual_judge", {"task_id": task_id, "verdict": verdict, "exit": r.returncode})
   775	        if verdict == "REJECT":
   776	            print(_red(f"⚖️  双审判 REJECT — verify 不通过，详见 .omc/state/meta-oracle-verdicts/{task_id}/latest.json"))
   777	            return 2
   778	        if verdict == "ESCALATE":
   779	            print(_yellow(f"⚖️  双审判 ESCALATE — 建议人工复核"))
   780	            return 3
   781	        print(_green(f"⚖️  双审判 {verdict}"))
   782	        return 0
   783	    except Exception as exc:
   784	        print(_yellow(f"⚠  meta 聚合异常: {exc}（降级放行，需人工复核）"))
   785	        return 0
   786	
   787	
   788	def cmd_verify(step_id=None):
   789	    """验证 step 完成 — 标记 plan.md [x] + 写 audit"""
   790	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   791	        token, found_path = _find_latest_token()
   792	        if token and found_path:
   793	            _init_paths_from_token(token, found_path)
   794	        else:
   795	            print(_red("❌ No active task"))
   796	            return 2
   797	    token = _load_token()
   798	    if not token:
   799	        print(_red("❌ No active task"))
   800	        return 2
   801	
   802	    if not PLAN_PATH.exists():
   803	        print(_red("❌ plan.md not found"))
   804	        return 2
   805	
   806	    plan = PLAN_PATH.read_text()
   807	    lines = plan.split("\n")
   808	
   809	    if step_id:
   810	        targets = [step_id]
   811	    else:
   812	        targets = []
   813	        current = token.get("task", {}).get("current_step")
   814	        if current:
   815	            targets.append(current)
   816	        if not targets:
   817	            print(_yellow("⚠  All steps already completed"))
   818	            return 0
   819	
   820	    verified_any = False
   821	    for target in targets:
   822	        pattern = re.compile(r"^- \[ \] " + re.escape(target) + r":", re.MULTILINE)
   823	        replacement = f"- [x] {target}:"
   824	        new_plan, count = pattern.subn(replacement, plan)
   825	        if count > 0:
   826	            plan = new_plan
   827	            # 更新 token — 统一新格式（递增 done 计数器）
   828	            token["stats"]["done"] = token["stats"].get("done", 0) + 1
   829	            if token["stats"]["done"] >= token["stats"]["total"]:
   830	                token["task"]["status"] = "completed"
   831	            _write_audit("verify", {"step": target, "result": "VERIFIED"})
   832	            print(_green(f"✅ {target}: VERIFIED"))
   833	            # task-state: 标记完成
   834	            if tst:
   835	                tst.mark_step_completed(TOKEN_PATH, target)
   836	                verdict = tst.format_tick_verdict(TOKEN_PATH, target)
   837	                if verdict:
   838	                    print(verdict)
   839	            verified_any = True
   840	        else:
   841	            print(_yellow(f"⚠  {target}: not found in plan.md"))
   842	
   843	    if verified_any:
   844	        PLAN_PATH.write_text(plan)
   845	        _save_token(token)
   846	        _write_handoff(token)
   847	
   848	        # L2 双审判官：verify 自动裁决（REJECT → verify 不通过）
   849	        level = token.get("session", {}).get("level", "L1_BASE")
   850	        if level == "L2_ENHANCE":
   851	            judge_rc = _run_dual_judge(token)
   852	            if judge_rc == 2:
   853	                return 2
   854	
   855	        # Goal 状态自动推进: done >= total → VERIFYING
   856	        done = token.get("stats", {}).get("done", 0)
   857	        total = token.get("stats", {}).get("total", 0)
   858	        if done >= total and GoalMachine:
   859	            try:
   860	                gm = GoalMachine(TOKEN_PATH)
   861	                gm.auto_progress(token)
   862	            except GoalError:
   863	                pass
   864	    return 0
   865	
   866	
   867	def cmd_report(use_stdout=True, archive_mode=False):
   868	    """
   869	    生成 final-report.md — 共享节点，所有流程的终止点都应调用。
   870	
   871	    从 executor.md + plan.md + audit JSONL 提取事实，不会编造。
   872	
   873	    Args:
   874	        use_stdout: 输出到 stdout（默认 True）
   875	        archive_mode: 归档模式（写入 task_dir + 额外标记）
   876	
   877	    Returns:
   878	        0 = 成功, 1 = 无活跃任务, 2 = 错误
   879	    """
   880	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   881	        token, tp = _find_latest_token()
   882	        if token and tp:
   883	            _init_paths_from_token(token, tp)
   884	        else:
   885	            print(_red("❌ No active task"))
   886	            return 2
   887	
   888	    token = _load_token()
   889	    if not token:
   890	        print(_red("❌ No active task"))
   891	        return 2
   892	
   893	    report_text = ""
   894	
   895	    if carros_utils and hasattr(carros_utils, "generate_final_report"):
   896	        report_text = carros_utils.generate_final_report(token, TASK_DIR)
   897	    else:
   898	        # fallback brief
   899	        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
   900	        stats = token.get("stats", {})
   901	        sid = token.get("session", {}).get("id", "unknown")
   902	        report_text = (
   903	            f"# Final Report: {sid}\n\n"
   904	            f"**生成时间:** {now}\n"
   905	            f"**状态:** {token.get('status', '?')}\n"
   906	            f"**完成度:** {stats.get('done', 0)}/{stats.get('total', 0)}\n\n"
   907	        )
   908	
   909	    # 输出到 stdout（用户直接看到）
   910	    if use_stdout:
   911	        print(_bold("=" * 50))
   912	        print(report_text)
   913	        print(_bold("=" * 50))
   914	
   915	    # 输出到 task_dir/final-report.md
   916	    if TASK_DIR:
   917	        report_path = TASK_DIR / "final-report.md"
   918	        report_path.write_text(report_text)
   919	        print(_green(f"✅ Report saved: {report_path}"))
   920	
   921	    return 0
   922	
   923	
```
