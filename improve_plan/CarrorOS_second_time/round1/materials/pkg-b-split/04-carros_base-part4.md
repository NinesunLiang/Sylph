# carros_base.py [4/4]

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | cmd_oracle/cmd_fallback/cmd_plan/cmd_auto/cmd_token_write/main(第 1695-2382 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/carros_base.py` 第 1695-2382 行

```python
  1695	def cmd_oracle():
  1696	    """Oracle 复核 — LLM 驱动双审
  1697	
  1698	    用法:
  1699	        carros_base.py oracle review --task-id <ID> [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>] [--policy security_strict|runtime_strict|fast_path|balanced]
  1700	        carros_base.py oracle health
  1701	        carros_base.py oracle status --task-id <ID>
  1702	
  1703	    Legacy (旧版 oracle_engine.py):
  1704	        carros_base.py oracle <review_pack_path>
  1705	    """
  1706	    import subprocess
  1707	    argv = sys.argv[sys.argv.index("oracle") + 1:]
  1708	
  1709	    # 探测新/旧模式
  1710	    if not argv:
  1711	        print(__doc__)
  1712	        return 2
  1713	
  1714	    if argv[0] == "review":
  1715	        # 新模型 Oracle — 调 model_oracle_spawn.py
  1716	        spawn = _hook_dir / "model_oracle_spawn.py"
  1717	        if not spawn.exists():
  1718	            print("model_oracle_spawn.py not found")
  1719	            return 1
  1720	
  1721	        # 组装子命令
  1722	        cmd = [sys.executable, str(spawn), "review", "--task-id"]
  1723	        # 找 task-id
  1724	        i = 1
  1725	        task_id = None
  1726	        extra_args = []
  1727	        while i < len(argv):
  1728	            a = argv[i]
  1729	            if a == "--task-id" and i + 1 < len(argv):
  1730	                task_id = argv[i + 1]
  1731	                i += 2
  1732	            elif a in ("--plan", "--executor", "--token", "--logs", "--diff", "--policy"):
  1733	                if i + 1 < len(argv):
  1734	                    extra_args.extend([a, argv[i + 1]])
  1735	                    i += 2
  1736	                else:
  1737	                    i += 1
  1738	            else:
  1739	                i += 1
  1740	
  1741	        if not task_id:
  1742	            # 尝试从 token 推断
  1743	            tok, tp = _find_latest_token()
  1744	            if tok:
  1745	                task_id = tok.get("session", {}).get("id", "unknown")
  1746	            else:
  1747	                print(_red("❌ No task-id provided and no active token found"))
  1748	                return 2
  1749	
  1750	        cmd.extend([task_id] + extra_args)
  1751	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
  1752	        print(result.stdout.strip())
  1753	        if result.stderr:
  1754	            print(_yellow(result.stderr[:500]))
  1755	        return result.returncode
  1756	
  1757	    elif argv[0] == "health":
  1758	        spawn = _hook_dir / "model_oracle_spawn.py"
  1759	        if not spawn.exists():
  1760	            print("model_oracle_spawn.py not found")
  1761	            return 1
  1762	        result = subprocess.run([sys.executable, str(spawn), "health"],
  1763	                                capture_output=True, text=True, timeout=10)
  1764	        print(result.stdout.strip())
  1765	        return result.returncode
  1766	
  1767	    elif argv[0] == "reset":
  1768	        spawn = _hook_dir / "model_oracle_spawn.py"
  1769	        if not spawn.exists():
  1770	            print("model_oracle_spawn.py not found")
  1771	            return 1
  1772	        result = subprocess.run([sys.executable, str(spawn), "reset"],
  1773	                                capture_output=True, text=True, timeout=5)
  1774	        print(result.stdout.strip())
  1775	        return result.returncode
  1776	
  1777	    elif argv[0] == "status" and "--task-id" in argv:
  1778	        spawn = _hook_dir / "model_oracle_spawn.py"
  1779	        if not spawn.exists():
  1780	            print("model_oracle_spawn.py not found")
  1781	            return 1
  1782	        idx = argv.index("--task-id") + 1
  1783	        tid = argv[idx] if idx < len(argv) else ""
  1784	        result = subprocess.run([sys.executable, str(spawn), "status", "--task-id", tid],
  1785	                                capture_output=True, text=True, timeout=5)
  1786	        print(result.stdout.strip())
  1787	        return result.returncode
  1788	
  1789	    # Fallback: 旧模式 (direct review_pack_path)
  1790	    pack_path = argv[0]
  1791	    engine = _hook_dir / "oracle_engine.py"
  1792	    if engine.exists():
  1793	        cmd = [sys.executable, str(engine), pack_path]
  1794	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
  1795	        print(result.stdout.strip())
  1796	        return result.returncode
  1797	    print(_red("Unknown oracle subcommand or oracle_engine.py not found"))
  1798	    return 2
  1799	
  1800	
  1801	def cmd_fallback():
  1802	    """Fallback Protocol — 调用 fallback_engine.py 处理能力失效降级"""
  1803	    import subprocess
  1804	    if len(sys.argv) >= 3:
  1805	        failure_type = sys.argv[2]
  1806	        risk = sys.argv[3] if len(sys.argv) >= 4 else None
  1807	        token_path = sys.argv[4] if len(sys.argv) >= 5 else str(TOKEN_PATH or ".omc/state/token.json")
  1808	        engine = _hook_dir / "fallback_engine.py"
  1809	        if not engine.exists():
  1810	            print("fallback_engine.py not found")
  1811	            return 1
  1812	        cmd = [sys.executable, str(engine), failure_type]
  1813	        if risk:
  1814	            cmd.append(risk)
  1815	        cmd.append(token_path)
  1816	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
  1817	        print(result.stdout.strip())
  1818	        return result.returncode
  1819	    print("usage: carros_base.py fallback <failure_type> [risk] [token_path]")
  1820	    return 2
  1821	
  1822	
  1823	def cmd_help():
  1824	    """打印帮助信息"""
  1825	    print(__doc__.strip())
  1826	    return 0
  1827	
  1828	
  1829	def cmd_clarify():
  1830	    """Goal 前置澄清 — 交互式探查目标/AC/边界/依赖，输出 spec.md
  1831	
  1832	    用法:
  1833	        python3 .claude/scripts/carros_base.py clarify --title "任务名"
  1834	        python3 .claude/scripts/carros_base.py clarify --title "任务名" --batch < spec.json
  1835	
  1836	    Goal 状态机: 自动推进到 CLARIFY 状态
  1837	    """
  1838	    import subprocess as sb
  1839	    _omc_scripts_parent = Path(__file__).resolve().parent  # .omc/scripts/ or .claude/scripts/
  1840	    argv = sys.argv[sys.argv.index("clarify") + 1:]
  1841	
  1842	    title = "unnamed"
  1843	    batch = False
  1844	    output_path = None
  1845	    i = 0
  1846	    while i < len(argv):
  1847	        if argv[i] == "--title" and i + 1 < len(argv):
  1848	            title = argv[i + 1]; i += 2
  1849	        elif argv[i] == "--batch":
  1850	            batch = True; i += 1
  1851	        elif argv[i] == "--output" and i + 1 < len(argv):
  1852	            output_path = argv[i + 1]; i += 2
  1853	        else:
  1854	            i += 1
  1855	
  1856	    # 确保有 active token
  1857	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1858	        tok, tp = _find_latest_token()
  1859	        if tok and tp:
  1860	            _init_paths_from_token(tok, tp)
  1861	        else:
  1862	            # 自动 init
  1863	            cmd_init(title, level="L1", steps=["S1"])
  1864	            print(_yellow("  ⚠ 已自动 init 新任务"))
  1865	
  1866	    # 调用 clarify_engine.py — 先找 .omc/scripts/，再找 .claude/scripts/
  1867	    script_candidates = [
  1868	        _omc_scripts_parent / "clarify_engine.py",  # .omc/scripts/
  1869	        _hook_dir / "clarify_engine.py",             # .claude/scripts/
  1870	    ]
  1871	    script = None
  1872	    for cand in script_candidates:
  1873	        if cand.exists():
  1874	            script = cand
  1875	            break
  1876	    if not script:
  1877	        print(_red("❌ clarify_engine.py not found (.omc/scripts/ or .claude/scripts/)"))
  1878	        return 2
  1879	
  1880	    spec_path = output_path or (TASK_DIR / "spec.md") if TASK_DIR else ".omc/spec.md"
  1881	    cmd = [sys.executable, str(script), "--title", title]
  1882	    if batch:
  1883	        cmd.append("--batch")
  1884	    cmd.extend(["--output", str(spec_path)])
  1885	
  1886	    if batch:
  1887	        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
  1888	        print(result.stdout)
  1889	        if result.returncode != 0:
  1890	            print(_red(f"❌ clarify failed: {result.stderr[:200]}"))
  1891	            return 2
  1892	    else:
  1893	        result = sb.run(cmd, timeout=300)
  1894	        if result.returncode != 0:
  1895	            print(_red("❌ clarify cancelled"))
  1896	            return 2
  1897	
  1898	    # 更新 Goal 状态机
  1899	    if GoalMachine:
  1900	        try:
  1901	            gm = GoalMachine(TOKEN_PATH)
  1902	            gm.transition(gsm.CLARIFY, reason=f"clarify: {title}")
  1903	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
  1904	        except GoalError as e:
  1905	            print(_yellow(f"  ⚠ Goal state: {e}"))
  1906	
  1907	    print(_green(f"✅ Clarified: {title}"))
  1908	    print(f"   Spec: {spec_path}")
  1909	    return 0
  1910	
  1911	
  1912	def cmd_plan():
  1913	    """分解 spec.md → 原子任务 → plan.json
  1914	
  1915	    用法:
  1916	        python3 .claude/scripts/carros_base.py plan [--spec spec.md] [--level L2] [--output plan.json]
  1917	
  1918	    流程:
  1919	        1. 读 spec.md
  1920	        2. 调用 task_planner.py 分解为 plan.json
  1921	        3. 更新 Goal 状态机 → PLANNING
  1922	    """
  1923	    argv = sys.argv[sys.argv.index("plan") + 1:]
  1924	    spec_path = None
  1925	    level = "L1"
  1926	    output_path = None
  1927	    i = 0
  1928	    while i < len(argv):
  1929	        if argv[i] == "--spec" and i + 1 < len(argv):
  1930	            spec_path = argv[i + 1]; i += 2
  1931	        elif argv[i] == "--level" and i + 1 < len(argv):
  1932	            level = argv[i + 1]; i += 2
  1933	        elif argv[i] == "--output" and i + 1 < len(argv):
  1934	            output_path = argv[i + 1]; i += 2
  1935	        else:
  1936	            i += 1
  1937	
  1938	    # 确保有 active token
  1939	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1940	        tok, tp = _find_latest_token()
  1941	        if tok and tp:
  1942	            _init_paths_from_token(tok, tp)
  1943	        else:
  1944	            print(_red("❌ No active task. Run 'clarify' or 'init' first."))
  1945	            return 2
  1946	
  1947	    # 找 spec.md
  1948	    spec_file = Path(spec_path) if spec_path else (TASK_DIR / "spec.md")
  1949	    if not spec_file.exists():
  1950	        spec_file = OMC_TASKS / "spec.md"
  1951	    if not spec_file.exists():
  1952	        print(_red(f"❌ spec.md not found. Run 'clarify' first."))
  1953	        return 2
  1954	
  1955	    if task_planner is None:
  1956	        # 直接调用 subprocess
  1957	        planner_script = _hook_dir / "task_planner.py"
  1958	        if not planner_script.exists():
  1959	            print(_red("❌ task_planner.py not available"))
  1960	            return 2
  1961	
  1962	        plan_out = output_path or str(TASK_DIR / "plan.json") if TASK_DIR else ".omc/plan.json"
  1963	        cmd = [sys.executable, str(planner_script), str(spec_file),
  1964	               "--output", plan_out, "--level", level]
  1965	        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
  1966	        print(result.stdout)
  1967	        if result.returncode != 0:
  1968	            return 2
  1969	        plan_path = Path(plan_out)
  1970	    else:
  1971	        parsed = task_planner.parse_spec(spec_file)
  1972	        plan = task_planner.decompose(parsed, level=level)
  1973	        plan_path = Path(output_path) if output_path else (TASK_DIR / "plan.json")
  1974	        task_planner.save_plan(plan, plan_path)
  1975	        print(f"📋 Plan: {len(plan['steps'])} steps, level={level}")
  1976	        for s in plan["steps"]:
  1977	            print(f"   [{s['type']}] {s['id']}: {s['goal'][:50]}")
  1978	
  1979	    # Goal 状态机 → PLANNING
  1980	    if GoalMachine:
  1981	        try:
  1982	            gm = GoalMachine(TOKEN_PATH)
  1983	            gm.transition(gsm.PLANNING, reason=f"plan: {spec_file.name}")
  1984	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
  1985	        except GoalError as e:
  1986	            print(_yellow(f"  ⚠ Goal state: {e}"))
  1987	
  1988	    print(_green(f"✅ Plan generated: {plan_path}"))
  1989	    return 0
  1990	
  1991	
  1992	def cmd_auto():
  1993	    """全自动管道: clarify → plan → distribute → wait → collect → verify → archive
  1994	
  1995	    用法:
  1996	        python3 .claude/scripts/carros_base.py auto [--plan plan.json] [--timeout 300]
  1997	                                                  [--max-concurrency 3] [--no-archive]
  1998	
  1999	    流程:
  2000	        1. 有 plan.json 则跳过 clarify+plan
  2001	        2. 调用 sub_agent_manager auto_run
  2002	        3. 回收后 verify + archive
  2003	    """
  2004	    argv = sys.argv[sys.argv.index("auto") + 1:]
  2005	    plan_path = None
  2006	    timeout = 300
  2007	    max_concurrency = 3
  2008	    no_archive = False
  2009	    i = 0
  2010	    while i < len(argv):
  2011	        if argv[i] == "--plan" and i + 1 < len(argv):
  2012	            plan_path = argv[i + 1]; i += 2
  2013	        elif argv[i] == "--timeout" and i + 1 < len(argv):
  2014	            timeout = int(argv[i + 1]); i += 2
  2015	        elif argv[i] == "--max-concurrency" and i + 1 < len(argv):
  2016	            max_concurrency = int(argv[i + 1]); i += 2
  2017	        elif argv[i] == "--no-archive":
  2018	            no_archive = True; i += 1
  2019	        else:
  2020	            i += 1
  2021	
  2022	    # 确保有 active token
  2023	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  2024	        tok, tp = _find_latest_token()
  2025	        if tok and tp:
  2026	            _init_paths_from_token(tok, tp)
  2027	        else:
  2028	            print(_red("❌ No active task. Run 'init' first."))
  2029	            return 2
  2030	
  2031	    if not TASK_DIR or not TASK_DIR.exists():
  2032	        print(_red("❌ Task directory not found"))
  2033	        return 2
  2034	
  2035	    # 确保 sub_agent_manager 可用
  2036	    if sam is None:
  2037	        print(_yellow("⚠  sub_agent_manager.py not importable, using subprocess fallback"))
  2038	
  2039	    print(_bold(f"🚀 Auto pipeline: {TASK_DIR.name} (timeout={timeout}s, cc={max_concurrency})"))
  2040	
  2041	    # 创建 manager
  2042	    mgr = sam.SubAgentManager(TASK_DIR, PROJECT_ROOT) if sam else None
  2043	
  2044	    if mgr:
  2045	        mgr.set_config(timeout=timeout, max_concurrency=max_concurrency)
  2046	
  2047	    # Step 1: 读取或准备 plan
  2048	    plan = None
  2049	    if plan_path:
  2050	        plan_file = Path(plan_path)
  2051	        if plan_file.exists():
  2052	            plan = json.loads(plan_file.read_text())
  2053	            print(f"📋 Loaded plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2054	    else:
  2055	        existing = TASK_DIR / "plan.json"
  2056	        if existing.exists():
  2057	            plan = json.loads(existing.read_text())
  2058	            print(f"📋 Using existing plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2059	
  2060	    if not plan:
  2061	        print(_red("❌ No plan.json found. Run 'plan' first or specify --plan"))
  2062	        return 2
  2063	
  2064	    # Step 2: 分发 → 等待 → 回收
  2065	    if mgr:
  2066	        result = mgr.auto_run(plan=plan, wait=True)
  2067	    else:
  2068	        # fallback: 直接 carros_base.py dispatch + poll + collect
  2069	        print(_yellow("⚠  Using carros_base.py dispatch/poll/collect fallback"))
  2070	        from subprocess import run as sbrun
  2071	        for step in plan["steps"]:
  2072	            sid = step["id"]
  2073	            r = sbrun([sys.executable, __file__, "dispatch", "--step", sid],
  2074	                      capture_output=True, text=True, timeout=10)
  2075	            print(f"   dispatch {sid}: {'ok' if r.returncode == 0 else r.stderr[:80]}")
  2076	        print("   Tasks dispatched. Run 'poll' to check status.")
  2077	        return 0
  2078	
  2079	    # Step 3: verify 每个完成的 step
  2080	    verified_count = 0
  2081	    if result.get("collect_result"):
  2082	        for sid in result["collect_result"].get("collected", []):
  2083	            r = cmd_verify(step_id=sid)
  2084	            if r == 0:
  2085	                verified_count += 1
  2086	
  2087	    # Step 4: 自动 archive（除非 --no-archive）
  2088	    if not no_archive and verified_count > 0:
  2089	        print(_bold("\n📦 Archiving..."))
  2090	        cmd_archive(force=False)
  2091	
  2092	    # 总结
  2093	    print(_bold(f"\n{'=' * 50}"))
  2094	    print(_bold(f"🏁 Auto pipeline complete"))
  2095	    print(f"   Plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2096	    print(f"   Result: {result.get('summary', '?')}")
  2097	    print(f"   Verified: {verified_count}/{len(plan['steps'])}")
  2098	    print(f"{'=' * 50}")
  2099	    return 0 if result.get("failed", 1) == 0 else 1
  2100	
  2101	
  2102	# ═══════════════════════════════════════════
  2103	# CLI entrypoint
  2104	# ═══════════════════════════════════════════
  2105	
  2106	# ---------------------------------------------------------------------------
  2107	# 夜跑控制面扩展（FINAL.md v3.1 §16 CarrorOS 侧）
  2108	# ---------------------------------------------------------------------------
  2109	
  2110	def cmd_manifest_json():
  2111	    """读取 night-manifest.yaml → 规范化 JSON（scope-check 等门禁消费，免 yq）。
  2112	
  2113	    用法:
  2114	        carros_base.py manifest-json --manifest PATH [--get dotted.path] [--pages]
  2115	        --get   输出单值（标量/JSON），缺失 → exit 2（fail-closed）
  2116	        --pages 仅输出 pages[] 的 id 列表（每行一个）
  2117	    """
  2118	    argv = sys.argv[sys.argv.index("manifest-json") + 1:]
  2119	    manifest_path = None
  2120	    get_path = None
  2121	    pages_only = False
  2122	    page_id = None
  2123	    i = 0
  2124	    while i < len(argv):
  2125	        if argv[i] == "--manifest" and i + 1 < len(argv):
  2126	            manifest_path = argv[i + 1]; i += 2
  2127	        elif argv[i] == "--get" and i + 1 < len(argv):
  2128	            get_path = argv[i + 1]; i += 2
  2129	        elif argv[i] == "--page-id" and i + 1 < len(argv):
  2130	            page_id = argv[i + 1]; i += 2
  2131	        elif argv[i] == "--pages":
  2132	            pages_only = True; i += 1
  2133	        else:
  2134	            i += 1
  2135	    if not manifest_path:
  2136	        print(_red("ERROR: manifest-json 需要 --manifest PATH"), file=sys.stderr)
  2137	        return 2
  2138	    p = Path(manifest_path)
  2139	    if not p.exists():
  2140	        print(_red(f"ERROR: manifest 不存在: {p}"), file=sys.stderr)
  2141	        return 2
  2142	    try:
  2143	        import yaml
  2144	        data = yaml.safe_load(p.read_text(encoding="utf-8"))
  2145	    except Exception as e:
  2146	        print(_red(f"ERROR: manifest 解析失败（fail-closed）: {e}"), file=sys.stderr)
  2147	        return 2
  2148	    if not isinstance(data, dict):
  2149	        print(_red("ERROR: manifest 顶层不是 mapping"), file=sys.stderr)
  2150	        return 2
  2151	    if pages_only:
  2152	        pages = data.get("pages") or []
  2153	        for pg in pages:
  2154	            print(pg.get("id", ""))
  2155	        return 0
  2156	    if page_id:
  2157	        pages = data.get("pages") or []
  2158	        match = [pg for pg in pages if isinstance(pg, dict) and pg.get("id") == page_id]
  2159	        if not match:
  2160	            print(_red(f"ERROR: page 不存在: {page_id}"), file=sys.stderr)
  2161	            return 2
  2162	        data = match[0]
  2163	    if get_path:
  2164	        cur = data
  2165	        for part in get_path.split("."):
  2166	            if isinstance(cur, dict) and part in cur:
  2167	                cur = cur[part]
  2168	            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
  2169	                cur = cur[int(part)]
  2170	            else:
  2171	                print(_red(f"ERROR: 字段缺失: {get_path}"), file=sys.stderr)
  2172	                return 2
  2173	        if isinstance(cur, (dict, list)):
  2174	            print(json.dumps(cur, ensure_ascii=False))
  2175	        elif cur is None:
  2176	            print("null")
  2177	        elif isinstance(cur, bool):
  2178	            print("true" if cur else "false")
  2179	        else:
  2180	            print(cur)
  2181	        return 0
  2182	    print(json.dumps(data, ensure_ascii=False, indent=2))
  2183	    return 0
  2184	
  2185	
  2186	def cmd_token_write():
  2187	    """token.json 唯一合法写入入口（FINAL §4.4：模型对 token 的写入仅允许经此 API）。
  2188	
  2189	    用法:
  2190	        carros_base.py token-write --token-path PATH --set dotted.path=value
  2191	              [--set ...] --expected-revision N
  2192	    CAS 冲突 → exit 3；缺参数 → exit 2。
  2193	    """
  2194	    argv = sys.argv[sys.argv.index("token-write") + 1:]
  2195	    token_path = None
  2196	    sets = []
  2197	    expected = None
  2198	    i = 0
  2199	    while i < len(argv):
  2200	        if argv[i] == "--token-path" and i + 1 < len(argv):
  2201	            token_path = argv[i + 1]; i += 2
  2202	        elif argv[i] == "--set" and i + 1 < len(argv):
  2203	            sets.append(argv[i + 1]); i += 2
  2204	        elif argv[i] == "--expected-revision" and i + 1 < len(argv):
  2205	            expected = int(argv[i + 1]); i += 2
  2206	        else:
  2207	            i += 1
  2208	    if not token_path or not sets or expected is None:
  2209	        print(_red("ERROR: token-write 需要 --token-path/--set/--expected-revision"), file=sys.stderr)
  2210	        return 2
  2211	    token = _load_token(Path(token_path))
  2212	    if token is None:
  2213	        print(_red(f"ERROR: token 不存在或损坏: {token_path}"), file=sys.stderr)
  2214	        return 2
  2215	    for kv in sets:
  2216	        if "=" not in kv:
  2217	            print(_red(f"ERROR: --set 格式应为 path=value: {kv}"), file=sys.stderr)
  2218	            return 2
  2219	        dotted, raw = kv.split("=", 1)
  2220	        try:
  2221	            value = json.loads(raw)
  2222	        except json.JSONDecodeError:
  2223	            value = raw
  2224	        cur = token
  2225	        parts = dotted.split(".")
  2226	        for part in parts[:-1]:
  2227	            nxt = cur.get(part)
  2228	            if not isinstance(nxt, dict):
  2229	                nxt = {}
  2230	                cur[part] = nxt
  2231	            cur = nxt
  2232	        cur[parts[-1]] = value
  2233	    try:
  2234	        _save_token(token, Path(token_path), expected_revision=expected)
  2235	    except CASConflict as e:
  2236	        print(_red(f"CAS_CONFLICT: {e}"), file=sys.stderr)
  2237	        return 3
  2238	    print(_green(f"token 已写入 revision={token.get('revision')}"))
  2239	    return 0
  2240	
  2241	
  2242	def cmd_gate_results_init():
  2243	    """创建页级 gate-results 目录（FINAL §4.4 权威链事实目录）。
  2244	
  2245	    用法:
  2246	        carros_base.py gate-results-init --night-dir .omc/night/{date} --page-id FE-xxx
  2247	    幂等；输出目录路径。
  2248	    """
  2249	    argv = sys.argv[sys.argv.index("gate-results-init") + 1:]
  2250	    night_dir = None
  2251	    page_id = None
  2252	    i = 0
  2253	    while i < len(argv):
  2254	        if argv[i] == "--night-dir" and i + 1 < len(argv):
  2255	            night_dir = argv[i + 1]; i += 2
  2256	        elif argv[i] == "--page-id" and i + 1 < len(argv):
  2257	            page_id = argv[i + 1]; i += 2
  2258	        else:
  2259	            i += 1
  2260	    if not night_dir or not page_id:
  2261	        print(_red("ERROR: gate-results-init 需要 --night-dir/--page-id"), file=sys.stderr)
  2262	        return 2
  2263	    d = Path(night_dir) / "gate-results" / page_id
  2264	    d.mkdir(parents=True, exist_ok=True)
  2265	    print(d)
  2266	    return 0
  2267	
  2268	
  2269	COMMANDS = {
  2270	    "init": cmd_init,
  2271	    "status": cmd_status,
  2272	    "tick": cmd_tick,
  2273	    "verify": cmd_verify,
  2274	    "archive": cmd_archive,
  2275	    "clarify": cmd_clarify,
  2276	    "plan": cmd_plan,
  2277	    "auto": cmd_auto,
  2278	    "lint": cmd_lint,
  2279	    "bench": cmd_bench,
  2280	    "gate": cmd_gate,
  2281	    "dispatch": cmd_dispatch,
  2282	    "poll": cmd_poll,
  2283	    "collect": cmd_collect,
  2284	    "report": cmd_report,
  2285	    "cancel": cmd_cancel,
  2286	    "oracle": cmd_oracle,
  2287	    "fallback": cmd_fallback,
  2288	    "manifest-json": cmd_manifest_json,
  2289	    "token-write": cmd_token_write,
  2290	    "gate-results-init": cmd_gate_results_init,
  2291	    "help": cmd_help,
  2292	}
  2293	
  2294	
  2295	def main(argv=None):
  2296	    if argv is None:
  2297	        argv = sys.argv[1:]
  2298	
  2299	    if not argv or argv[0] in ("-h", "--help", "help"):
  2300	        return cmd_help()
  2301	
  2302	    command = argv[0]
  2303	    if command not in COMMANDS:
  2304	        print(_red(f"Unknown command: {command}"))
  2305	        print(f"Available: {', '.join(COMMANDS.keys())}")
  2306	        return 2
  2307	
  2308	    args = argv[1:]
  2309	
  2310	    if command == "init":
  2311	        task_id = None
  2312	        level = "L1"
  2313	        steps = None
  2314	        task_dir = None
  2315	        user_request = None
  2316	        feature = None
  2317	        auto_mode = False
  2318	        i = 0
  2319	        while i < len(args):
  2320	            if args[i] == "--task-id" and i + 1 < len(args):
  2321	                task_id = args[i + 1]
  2322	                i += 2
  2323	            elif args[i] == "--level" and i + 1 < len(args):
  2324	                level = args[i + 1]
  2325	                i += 2
  2326	            elif args[i] == "--task-dir" and i + 1 < len(args):
  2327	                task_dir = args[i + 1]
  2328	                i += 2
  2329	            elif args[i] == "--step":
  2330	                if steps is None:
  2331	                    steps = []
  2332	                i += 1
  2333	                while i < len(args) and not args[i].startswith("--"):
  2334	                    steps.append(args[i])
  2335	                    i += 1
  2336	            elif args[i] == "--user-request" and i + 1 < len(args):
  2337	                user_request = args[i + 1]
  2338	                i += 2
  2339	            elif args[i] == "--feature" and i + 1 < len(args):
  2340	                feature = args[i + 1]
  2341	                i += 2
  2342	            elif args[i] == "--auto":
  2343	                auto_mode = True
  2344	                i += 1
  2345	            elif args[i] == "--target" and i + 1 < len(args):
  2346	                target = args[i + 1]
  2347	                i += 2
  2348	            else:
  2349	                i += 1
  2350	        if auto_mode:
  2351	            return cmd_auto_init(steps=steps, target=target)
  2352	        return cmd_init(task_id=task_id, level=level, steps=steps, user_request=user_request, task_dir=task_dir, feature=feature)
  2353	
  2354	    elif command == "verify":
  2355	        step_id = None
  2356	        if args and args[0] == "--step" and len(args) >= 2:
  2357	            step_id = args[1]
  2358	        return cmd_verify(step_id=step_id)
  2359	
  2360	    elif command == "archive":
  2361	        force = "--force" in args or "-f" in args
  2362	        return cmd_archive(force=force)
  2363	
  2364	    elif command == "lint":
  2365	        path = args[0] if args else None
  2366	        return cmd_lint(path=path)
  2367	
  2368	    elif command == "manifest-json":
  2369	        return cmd_manifest_json()
  2370	
  2371	    elif command == "token-write":
  2372	        return cmd_token_write()
  2373	
  2374	    elif command == "gate-results-init":
  2375	        return cmd_gate_results_init()
  2376	
  2377	    else:
  2378	        return COMMANDS[command]()
  2379	
  2380	
  2381	if __name__ == "__main__":
  2382	    sys.exit(main())
```
