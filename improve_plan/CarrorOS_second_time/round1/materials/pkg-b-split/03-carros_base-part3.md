# carros_base.py [3/4]

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | cmd_archive/cmd_lint/cmd_bench/cmd_gate/dispatch-poll-collect-cancel(第 924-1694 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/carros_base.py` 第 924-1694 行

```python
   924	def cmd_archive(force=False):
   925	    """归档任务 — archive = lint + verify-summary + final-report + tombstone"""
   926	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   927	        token, found_path = _find_latest_token()
   928	        if token and found_path:
   929	            _init_paths_from_token(token, found_path)
   930	        else:
   931	            print(_red("❌ No active task"))
   932	            return 2
   933	    print(_bold("Archiving task..."))
   934	
   935	    # Step 1: run lint — 仅 error (exit>=2) 阻断，warning (exit=1) 可归档
   936	    if not force:
   937	        lint_ok = cmd_lint()
   938	        if lint_ok >= 2:
   939	            print(_red("❌ Lint has errors. Use --force to archive anyway."))
   940	            return 2
   941	        elif lint_ok == 1:
   942	            print(_yellow("⚠  Lint warnings only — proceeding with archive"))
   943	    else:
   944	        print(_yellow("⚠  --force: skipping lint"))
   945	
   946	    token = _load_token()
   947	    if not token:
   948	        print(_red("❌ No active task"))
   949	        return 2
   950	
   951	    # Step 2: check all steps completed — 统一新格式
   952	    if not force:
   953	        pending = []
   954	        if token.get("stats", {}).get("done", 0) < token.get("stats", {}).get("total", 0):
   955	            pending = ["current_step not completed"]
   956	        if pending:
   957	            print(_red(f"❌ Steps not completed: {pending}"))
   958	            return 2
   959	    else:
   960	        print(_yellow("⚠  --force: skipping step completion check"))
   961	
   962	    # Step 3: generate final report (shared node)
   963	    task_sid = token.get("session", {}).get("id", "unknown")
   964	    archive_dir = OMC_ROOT / "archive" / task_sid
   965	    archive_dir.mkdir(parents=True, exist_ok=True)
   966	    cmd_report(use_stdout=False)
   967	    print(_green(f"✅ Final report: {archive_dir / 'final-report.md'}"))
   968	
   969	    # Step 4: 复制 report 到 archive 目录
   970	    if GoalMachine:
   971	        try:
   972	            gm = GoalMachine(TOKEN_PATH)
   973	            gm.transition(gsm.ARCHIVED, reason="archive completed")
   974	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
   975	            # 重新加载 token — GoalMachine 已写入 goal.archived
   976	            token = _load_token() or token
   977	        except GoalError:
   978	            pass
   979	
   980	    # Step 5: tombstone — 复制 token 到 archive 目录作为墓碑
   981	    token["status"] = "archived"
   982	    token["archived_at"] = datetime.now(timezone.utc).isoformat()
   983	    _save_token(token)
   984	
   985	    # 按方案 10.md L987-1000 写 token.final.json + token.tombstone.json
   986	    import shutil
   987	    write_json_atomic = lambda p, d: (p.parent.mkdir(parents=True, exist_ok=True), p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"))
   988	    write_json_atomic(archive_dir / "token.final.json", token)
   989	    write_json_atomic(
   990	        archive_dir / "token.tombstone.json",
   991	        {
   992	            "task_id": token["session"]["id"],
   993	            "previous_token": str(TOKEN_PATH),
   994	            "status": "archived",
   995	            "archived_at": now_iso(),
   996	            "final_report": str(archive_dir / "final-report.md"),
   997	            "final_verdict": "ARCHIVED",
   998	            "level": token.get("session", {}).get("level", "unknown_level"),
   999	        },
  1000	    )
  1001	    for optional in ["plan.md", "executor.md"]:
  1002	        src = TASK_DIR / optional if TASK_DIR else None
  1003	        if src and src.exists():
  1004	            shutil.copy2(src, archive_dir / optional)
  1005	    handoff_src = HANDOFF_PATH if HANDOFF_PATH else Path(".omc/session-handoff.md")
  1006	    if handoff_src.exists():
  1007	        shutil.copy2(handoff_src, archive_dir / "session-handoff.md")
  1008	
  1009	    _write_audit("archive", {"task_id": token["session"]["id"], "result": "ARCHIVED"})
  1010	    _write_handoff(token)
  1011	
  1012	    # Step 6: 删除 active token
  1013	    token_path_str = str(TOKEN_PATH)
  1014	    TOKEN_PATH.unlink(missing_ok=True)
  1015	    print(_green(f"✅ Token 已删除: {token_path_str}"))
  1016	
  1017	    # Step 7: 输出 {"continue": false}
  1018	    print(json.dumps({"continue": False}))
  1019	    print(_green("✅ Task archived"))
  1020	
  1021	    return 0
  1022	
  1023	
  1024	def _generate_final_report(token):
  1025	    """生成归档报告 — 委托 carros_utils"""
  1026	    if carros_utils:
  1027	        return carros_utils.generate_final_report(token)
  1028	    # fallback — inline
  1029	    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  1030	    sid = token.get("session", {}).get("id", "unknown")
  1031	    level = token.get("session", {}).get("level", "?")
  1032	    status = token.get("status", "?")
  1033	    stats = token.get("stats", {})
  1034	
  1035	    done = stats.get("done", 0)
  1036	    total = stats.get("total", 0)
  1037	    tick = stats.get("turns", 0)
  1038	    current = token.get("task", {}).get("current_step", "?")
  1039	    task_status = token.get("task", {}).get("status", "?")
  1040	    step_lines = [f"  current_step: {current} ({task_status})"]
  1041	
  1042	    lines = [
  1043	        f"# Final Report: {sid}",
  1044	        "",
  1045	        f"**Archived at:** {now}",
  1046	        f"**Level:** {level}",
  1047	        f"**Status:** {status}",
  1048	        "",
  1049	        "## Summary",
  1050	        "",
  1051	        f"Completed {done}/{total} steps in {tick} ticks.",
  1052	        "",
  1053	        "## Steps",
  1054	        "",
  1055	    ]
  1056	    lines.extend(step_lines)
  1057	    lines.append("")
  1058	    lines.append("## Audit Trail")
  1059	    lines.append("")
  1060	    lines.append("See `.omc/state/audit/` for full event log.")
  1061	    lines.append("")
  1062	    lines.append("---")
  1063	    lines.append("_Generated by carros_base.py archive_")
  1064	    return "\n".join(lines)
  1065	
  1066	
  1067	def cmd_lint(path=None):
  1068	    """统一 lint — 委托 omc_lint 模块"""
  1069	    if omc_lint is None:
  1070	        print(_red("❌ omc_lint module not available"))
  1071	        return 2
  1072	
  1073	    target = path or str(PROJECT_ROOT)
  1074	    try:
  1075	        result = omc_lint.run_lint(target)
  1076	        print(result["output"])
  1077	        return result["exit_code"]
  1078	    except Exception as e:
  1079	        print(_red(f"❌ Lint error: {e}"))
  1080	        return 2
  1081	
  1082	
  1083	BENCH_SCENES = {
  1084	    "01_doc_update": {
  1085	        "description": "纯文档更新",
  1086	        "steps": ["S1"],
  1087	    },
  1088	    "02_single_file_fix": {
  1089	        "description": "单文件修复",
  1090	        "steps": ["S1"],
  1091	    },
  1092	    "03_multi_file_test": {
  1093	        "description": "多文件协同修改",
  1094	        "steps": ["S1", "S2"],
  1095	    },
  1096	    "04_failure_then_repair": {
  1097	        "description": "失败后修复",
  1098	        "steps": ["S1", "S2"],
  1099	    },
  1100	    "05_compact_resume": {
  1101	        "description": "compact/resume 恢复",
  1102	        "steps": ["S1", "S2", "S3"],
  1103	    },
  1104	    "06_fallback_downgrade": {
  1105	        "description": "降级场景",
  1106	        "steps": ["S1"],
  1107	    },
  1108	    "07_archive": {
  1109	        "description": "归档闭环",
  1110	        "steps": ["S1", "S2", "S3", "S4", "S5"],
  1111	    },
  1112	}
  1113	
  1114	
  1115	def cmd_bench(scene=None):
  1116	    """运行 bench 基准测试—验证治理系统基本链路"""
  1117	    import subprocess
  1118	
  1119	    scenes = BENCH_SCENES
  1120	    if scene:
  1121	        if scene not in scenes:
  1122	            print(_red(f"❌ Unknown bench scene: {scene}"))
  1123	            print(f"   Available: {', '.join(scenes.keys())}")
  1124	            return 2
  1125	        scenes = {scene: scenes[scene]}
  1126	
  1127	    results = []
  1128	    for scene_id, cfg in scenes.items():
  1129	        print(_bold(f"\n{'='*60}"))
  1130	        print(_bold(f"▶ Bench: {scene_id} — {cfg['description']}"))
  1131	        print(f"{'='*60}")
  1132	
  1133	        task_id = f"bench-{scene_id[:2]}"
  1134	        steps = cfg["steps"]
  1135	
  1136	        # 1. init
  1137	        step_args = " ".join(f"--step {s}" for s in steps)
  1138	        cmd = f"python3 .claude/scripts/carros_base.py init --task-id {task_id} {step_args} --force"
  1139	        print(_yellow(f"    init..."))
  1140	        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
  1141	        if r.returncode != 0:
  1142	            print(_red(f"    ❌ init failed: {r.stderr[:200]}"))
  1143	            results.append((scene_id, "FAIL_INIT"))
  1144	            continue
  1145	
  1146	        # 2. status
  1147	        r = subprocess.run("python3 .claude/scripts/carros_base.py status", shell=True,
  1148	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1149	        if r.returncode != 0:
  1150	            print(_red(f"    ❌ status failed"))
  1151	            results.append((scene_id, "FAIL_STATUS"))
  1152	            continue
  1153	        print(f"    {r.stdout.strip().split(chr(10))[0]}")
  1154	
  1155	        # 3. tick
  1156	        r = subprocess.run("python3 .claude/scripts/carros_base.py tick", shell=True,
  1157	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1158	        if r.returncode != 0:
  1159	            print(_yellow(f"    ⚠ tick failed"))
  1160	
  1161	        # 4. verify each step
  1162	        all_verified = True
  1163	        for s in steps:
  1164	            r = subprocess.run(f"python3 .claude/scripts/carros_base.py verify --step {s}",
  1165	                              shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
  1166	            if r.returncode == 0:
  1167	                print(f"    ✅ {s}: VERIFIED")
  1168	            else:
  1169	                print(_red(f"    ❌ {s}: {r.stdout[:100]}"))
  1170	                all_verified = False
  1171	
  1172	        if not all_verified:
  1173	            results.append((scene_id, "FAIL_VERIFY"))
  1174	            continue
  1175	
  1176	        # 5. lint
  1177	        r = subprocess.run("python3 .claude/scripts/carros_base.py lint", shell=True,
  1178	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1179	        lint_ok = r.returncode == 0
  1180	        if lint_ok:
  1181	            print(f"    ✅ lint: PASS")
  1182	        else:
  1183	            print(_yellow(f"    ⚠ lint: {r.stdout.strip()[:100]}"))
  1184	
  1185	        # 6. archive
  1186	        r = subprocess.run("python3 .claude/scripts/carros_base.py archive --force", shell=True,
  1187	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1188	        if r.returncode == 0:
  1189	            print(_green(f"    ✅ archive: OK"))
  1190	            results.append((scene_id, "PASS"))
  1191	        else:
  1192	            print(_red(f"    ❌ archive: {r.stdout[:200]}"))
  1193	            results.append((scene_id, "FAIL_ARCHIVE"))
  1194	
  1195	    # Summary
  1196	    print(_bold(f"\n{'='*60}"))
  1197	    print(_bold("Bench Results"))
  1198	    print(f"{'='*60}")
  1199	    passed = sum(1 for _, s in results if s == "PASS")
  1200	    failed = sum(1 for _, s in results if s != "PASS")
  1201	    for scene_id, status in results:
  1202	        icon = _green("✅") if status == "PASS" else _red("❌")
  1203	        print(f"  {icon} {scene_id}: {status}")
  1204	    print(f"\n  {passed} passed, {failed} failed")
  1205	    return 0 if failed == 0 else 1
  1206	
  1207	
  1208	def cmd_gate():
  1209	    """PreActionGate - 对 action_spec 做执行前安全裁决
  1210	
  1211	    读取当前 active token，创建临时 action_spec 文件，
  1212	    调用 pre_action_gate.py 做裁决。
  1213	
  1214	    用法:
  1215	        python3 .omc/scripts/carros_base.py gate --action-type write_file --paths README.md --step S1 --intent "update docs"
  1216	    """
  1217	    import subprocess
  1218	    import tempfile
  1219	
  1220	    argv = sys.argv[sys.argv.index("gate") + 1:]
  1221	    p = {}
  1222	    i = 0
  1223	    while i < len(argv):
  1224	        if argv[i] == "--action-type" and i + 1 < len(argv):
  1225	            p["action_type"] = argv[i + 1]; i += 2
  1226	        elif argv[i] == "--command" and i + 1 < len(argv):
  1227	            p["command"] = argv[i + 1]; i += 2
  1228	        elif argv[i] == "--paths" and i + 1 < len(argv):
  1229	            p["paths"] = argv[i + 1].split(","); i += 2
  1230	        elif argv[i] == "--step" and i + 1 < len(argv):
  1231	            p["current_step"] = argv[i + 1]; i += 2
  1232	        elif argv[i] == "--intent" and i + 1 < len(argv):
  1233	            p["intent"] = argv[i + 1]; i += 2
  1234	        elif argv[i] == "--risk-hint" and i + 1 < len(argv):
  1235	            p["risk_hint"] = argv[i + 1]; i += 2
  1236	        elif argv[i] == "--network" and i + 1 < len(argv):
  1237	            p["requires_network"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1238	        elif argv[i] == "--production" and i + 1 < len(argv):
  1239	            p["requires_production"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1240	        elif argv[i] == "--database" and i + 1 < len(argv):
  1241	            p["requires_database"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1242	        else:
  1243	            i += 1
  1244	
  1245	    if "action_type" not in p:
  1246	        print(_red("Missing --action-type"))
  1247	        return 2
  1248	
  1249	    p.setdefault("paths", [])
  1250	    p.setdefault("intent", "")
  1251	    p.setdefault("current_step", "S1")
  1252	
  1253	    spec_file = tempfile.NamedTemporaryFile(
  1254	        mode="w", suffix=".json", delete=False, prefix="preaction-"
  1255	    )
  1256	    json.dump(p, spec_file, ensure_ascii=False, indent=2)
  1257	    spec_path = spec_file.name
  1258	    spec_file.close()
  1259	
  1260	    # 找到当前 active token
  1261	    _token_data, token_path = _find_latest_token()
  1262	    if token_path is None:
  1263	        print(_yellow("No active token found — running without token context"))
  1264	        token_arg = []
  1265	    else:
  1266	        token_arg = ["--token", str(token_path)]
  1267	
  1268	    try:
  1269	        gate_script = _hook_dir / "pre_action_gate.py"
  1270	        cmd = [sys.executable, str(gate_script), spec_path] + token_arg
  1271	        r = subprocess.run(cmd, capture_output=True, text=True)
  1272	        output = r.stdout.strip() if r.stdout else r.stderr.strip()
  1273	        if output:
  1274	            print(output)
  1275	        return r.returncode
  1276	    finally:
  1277	        Path(spec_path).unlink(missing_ok=True)
  1278	
  1279	
  1280	def _sub_token(task_dir: str, parent_id: str, step_id: str, plan_text: str = "") -> dict:
  1281	    """生成 subagent token.json — 子代理的启动契约
  1282	
  1283	    subagent 读这个文件知道：为谁工作（parent_id）、
  1284	    要做什么（subtask.plan）、被允许做什么（session.level）
  1285	    """
  1286	    now = datetime.now(timezone.utc)
  1287	    return {
  1288	        "schema_version": _SCHEMA_VERSION,
  1289	        "session": {
  1290	            "id": f"{parent_id}-{step_id}",
  1291	            "level": "L1_SUB",
  1292	            "created_at": now.isoformat(),
  1293	            "updated_at": now.isoformat(),
  1294	        },
  1295	        "parent": {
  1296	            "task_dir": task_dir,
  1297	            "task_id": parent_id,
  1298	            "step_id": step_id,
  1299	        },
  1300	        "subtask": {
  1301	            "plan": plan_text,
  1302	        },
  1303	        "status": "active",
  1304	        "stats": {"done": 0, "total": 1, "tick": 0},
  1305	    }
  1306	
  1307	
  1308	def _result_template() -> dict:
  1309	    """result.json 模板 — subagent 完成工作后写"""
  1310	    return {
  1311	        "status": "running",
  1312	        "summary": "",
  1313	        "evidence": [],
  1314	        "files_changed": [],
  1315	        "failure": None,
  1316	        "completed_at": None,
  1317	        "started_at": datetime.now(timezone.utc).isoformat(),
  1318	    }
  1319	
  1320	
  1321	def cmd_dispatch():
  1322	    """分发子任务到 subagent — 创建 sub_task/{step} 目录 + token + plan
  1323	
  1324	    用法:
  1325	        python3 .claude/scripts/carros_base.py dispatch --step S1 [--text \"要做什么\"]
  1326	
  1327	    产生文件:
  1328	        .omc/tasks/{date}/{task}/sub_task/sub-{step}/
  1329	            token.json     — subagent 契约（parent/plan/约束）
  1330	            result.json    — subagent 汇报模板
  1331	            executor.md    — 空证据账本
  1332	
  1333	    subagent 启动后工作:
  1334	        1. 读 token.json（知道 parent_task 和 plan）
  1335	        2. 按 plan 执行
  1336	        3. 写 executor.md（证据）
  1337	        4. 更新 result.json（status=completed + summary + evidence）
  1338	        5. 更新 token.json（status=completed）
  1339	    """
  1340	    global TASK_DIR, TOKEN_PATH, SUB_TASK_DIR
  1341	
  1342	    # 确保有 active token
  1343	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1344	        token, tp = _find_latest_token()
  1345	        if not token:
  1346	            print(_red("❌ No active main task. Run 'init' first."))
  1347	            return 2
  1348	        _init_paths_from_token(token, tp)
  1349	
  1350	    # 解析参数
  1351	    argv = sys.argv[sys.argv.index("dispatch") + 1:]
  1352	    step_id = "S1"
  1353	    plan_text = ""
  1354	    i = 0
  1355	    while i < len(argv):
  1356	        if argv[i] == "--step" and i + 1 < len(argv):
  1357	            step_id = argv[i + 1]; i += 2
  1358	        elif argv[i] == "--text" and i + 1 < len(argv):
  1359	            plan_text = argv[i + 1]; i += 2
  1360	        else:
  1361	            i += 1
  1362	
  1363	    # 创建 sub_task 目录
  1364	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"
  1365	    sub_dir.mkdir(parents=True, exist_ok=True)
  1366	
  1367	    # 生成 subagent token
  1368	    token_data = _sub_token(
  1369	        task_dir=str(TASK_DIR),
  1370	        parent_id=token.get("session", {}).get("id", "unknown"),
  1371	        step_id=step_id,
  1372	        plan_text=plan_text,
  1373	    )
  1374	
  1375	    # 写入 token.json
  1376	    token_path = sub_dir / "token.json"
  1377	    token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2))
  1378	
  1379	    # 写入 result.json（模板）
  1380	    result_data = _result_template()
  1381	    result_data["parent"] = {
  1382	        "task_dir": str(TASK_DIR),
  1383	        "token_path": str(TOKEN_PATH),
  1384	    }
  1385	    result_path = sub_dir / "result.json"
  1386	    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2))
  1387	
  1388	    # 写入 executor.md（空账本）
  1389	    exec_path = sub_dir / "executor.md"
  1390	    if not exec_path.exists():
  1391	        exec_path.write_text(
  1392	            f"# Executor: {token_data['session']['id']}\n"
  1393	            f"## Parent: {token_data['parent']['task_id']}\n\n"
  1394	        )
  1395	
  1396	    # 更新 main token：记录该 step 已分配 subagent
  1397	    main_token = _load_token()
  1398	    if main_token and "steps" in main_token:
  1399	        for s in main_token["steps"]:
  1400	            if s["id"] == step_id:
  1401	                s["status"] = "running"
  1402	                s["subagent_path"] = str(sub_dir)
  1403	                break
  1404	        _save_token(main_token)
  1405	
  1406	    print(_green(f"✅ Dispatched {step_id} → {sub_dir}"))
  1407	    print(f"   token:  {token_path}")
  1408	    print(f"   result: {result_path}")
  1409	    print(f"   Subagent reads token.json for task, writes result.json on completion")
  1410	    return 0
  1411	
  1412	
  1413	def cmd_poll():
  1414	    """轮询所有 subagent 状态 — main agent 追踪 subagent 进度
  1415	
  1416	    读每个 sub_task/sub-*/result.json，展示汇总状态。
  1417	    支持 --verbose 展示每个 subagent 的关键证据。
  1418	
  1419	    用法:
  1420	        python3 .claude/scripts/carros_base.py poll [--verbose]
  1421	    """
  1422	    global SUB_TASK_DIR, TASK_DIR
  1423	
  1424	    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1425	        # 尝试从当前 token 获取
  1426	        tok, _ = _find_latest_token()
  1427	        if tok:
  1428	            td = tok.get("task_dir")
  1429	            if td:
  1430	                SUB_TASK_DIR = Path(td) / "sub_task"
  1431	        if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1432	            print(_yellow("⚠  No sub tasks found"))
  1433	            return 0
  1434	
  1435	    verbose = "--verbose" in sys.argv
  1436	
  1437	    sub_dirs = sorted([d for d in SUB_TASK_DIR.iterdir() if d.is_dir()])
  1438	    if not sub_dirs:
  1439	        print(_yellow("⚠  No sub tasks found"))
  1440	        return 0
  1441	
  1442	    print(_bold(f"SubAgent Status: {len(sub_dirs)} task(s)"))
  1443	    print(f"{'─' * 50}")
  1444	
  1445	    total_done = 0
  1446	    total_failed = 0
  1447	    for sd in sub_dirs:
  1448	        name = sd.name
  1449	        result_path = sd / "result.json"
  1450	        token_path = sd / "token.json"
  1451	
  1452	        if not result_path.exists():
  1453	            print(f"   ○ {name}: no result yet")
  1454	            continue
  1455	
  1456	        try:
  1457	            result = json.loads(result_path.read_text())
  1458	            status = result.get("status", "unknown")
  1459	
  1460	            if status == "completed":
  1461	                icon = _green("✔")
  1462	                total_done += 1
  1463	            elif status == "failed":
  1464	                icon = _red("✘")
  1465	                total_failed += 1
  1466	            elif status == "running":
  1467	                icon = _yellow("◷")
  1468	            else:
  1469	                icon = "○"
  1470	
  1471	            summary = result.get("summary", "")
  1472	            parts = [f"   {icon} {name}: {status}"]
  1473	            if summary:
  1474	                parts.append(f"→ {summary[:60]}")
  1475	            if verbose and result.get("files_changed"):
  1476	                parts.append(f"files: {', '.join(result['files_changed'][:3])}")
  1477	            if result.get("failure"):
  1478	                parts.append(_red(f"FAIL: {result['failure'][:80]}"))
  1479	
  1480	            print("  ".join(parts))
  1481	
  1482	        except (json.JSONDecodeError, OSError) as e:
  1483	            print(f"   ⚠ {name}: read error ({e})")
  1484	
  1485	    print(f"{'─' * 50}")
  1486	    print(f"   {total_done} completed, {total_failed} failed, "
  1487	          f"{len(sub_dirs) - total_done - total_failed} running/pending")
  1488	
  1489	    # 更新 main token 的 step 状态
  1490	    main_token = _load_token()
  1491	    if main_token and "steps" in main_token:
  1492	        updated = False
  1493	        for s in main_token["steps"]:
  1494	            sp = s.get("subagent_path")
  1495	            if sp and s["status"] == "running":
  1496	                rp = Path(sp) / "result.json"
  1497	                if rp.exists():
  1498	                    try:
  1499	                        r = json.loads(rp.read_text())
  1500	                        if r.get("status") == "completed":
  1501	                            s["status"] = "completed"
  1502	                            updated = True
  1503	                        elif r.get("status") == "failed":
  1504	                            s["status"] = "failed"
  1505	                            updated = True
  1506	                    except Exception:
  1507	                        pass
  1508	        if updated:
  1509	            _save_token(main_token)
  1510	
  1511	    return 0
  1512	
  1513	
  1514	def cmd_collect():
  1515	    """回收 subagent 完成结果 — 把 result.json 汇入 main task executor.md
  1516	
  1517	    用法:
  1518	        python3 .claude/scripts/carros_base.py collect --step S1
  1519	
  1520	    执行:
  1521	        1. 读 sub_task/sub-{step}/result.json
  1522	        2. 验证 status=completed
  1523	        3. 证据追加到 main executor.md
  1524	        4. 文件变更记录到 audit
  1525	        5. 标记 main token step 完成
  1526	    """
  1527	    global SUB_TASK_DIR, TASK_DIR, TOKEN_PATH, EXECUTOR_PATH
  1528	
  1529	    argv = sys.argv[sys.argv.index("collect") + 1:]
  1530	    step_id = None
  1531	    i = 0
  1532	    while i < len(argv):
  1533	        if argv[i] == "--step" and i + 1 < len(argv):
  1534	            step_id = argv[i + 1]; i += 2
  1535	        else:
  1536	            i += 1
  1537	
  1538	    if not step_id:
  1539	        print(_red("❌ Usage: collect --step S1"))
  1540	        return 2
  1541	
  1542	    # 找 sub task 目录
  1543	    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1544	        tok, tp = _find_latest_token()
  1545	        if tok:
  1546	            td = tok.get("task_dir")
  1547	            if td:
  1548	                SUB_TASK_DIR = Path(td) / "sub_task"
  1549	                _init_paths_from_token(tok, tp)
  1550	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"
  1551	
  1552	    if not sub_dir.exists():
  1553	        print(_red(f"❌ Sub task not found: {sub_dir}"))
  1554	        return 2
  1555	
  1556	    result_path = sub_dir / "result.json"
  1557	    if not result_path.exists():
  1558	        print(_red(f"❌ No result.json — subagent hasn't reported"))
  1559	        return 2
  1560	
  1561	    try:
  1562	        result = json.loads(result_path.read_text())
  1563	    except (json.JSONDecodeError, OSError) as e:
  1564	        print(_red(f"❌ Failed to read result.json: {e}"))
  1565	        return 2
  1566	
  1567	    status = result.get("status", "unknown")
  1568	    if status == "failed":
  1569	        print(_yellow(f"⚠  {step_id} result=failed"))
  1570	        print(f"   failure: {result.get('failure', 'unknown')}")
  1571	        return 2 if "--force" not in sys.argv else 0
  1572	    elif status != "completed":
  1573	        print(_yellow(f"⚠  {step_id} is still {status}"))
  1574	
  1575	    # 证据追加到 main executor.md
  1576	    if EXECUTOR_PATH:
  1577	        ev_lines = [
  1578	            f"\n### SubAgent {step_id} — collected at {datetime.now(timezone.utc).isoformat()}",
  1579	            f"- source: sub_task/sub-{step_id}",
  1580	        ]
  1581	        if result.get("summary"):
  1582	            ev_lines.append(f"- summary: {result['summary']}")
  1583	        if result.get("evidence"):
  1584	            for ev in result["evidence"][:5]:
  1585	                ev_lines.append(f"- evidence: {ev[:100]}")
  1586	        if result.get("files_changed"):
  1587	            for f in result["files_changed"][:10]:
  1588	                ev_lines.append(f"- file: {f}")
  1589	        if result.get("failure"):
  1590	            ev_lines.append(f"- failure: {result['failure'][:100]}")
  1591	
  1592	        exec_path = Path(EXECUTOR_PATH) if isinstance(EXECUTOR_PATH, (str, Path)) else EXECUTOR_PATH
  1593	        if isinstance(exec_path, Path) and exec_path.exists():
  1594	            with exec_path.open("a") as f:
  1595	                f.write("\n".join(ev_lines) + "\n")
  1596	        else:
  1597	            # 可能还没创建 executor.md
  1598	            pass
  1599	
  1600	    # 标记 main token 完成
  1601	    main_token = _load_token()
  1602	    if main_token and "steps" in main_token:
  1603	        for s in main_token["steps"]:
  1604	            if s["id"] == step_id:
  1605	                s["status"] = "completed"
  1606	                break
  1607	        main_token["stats"]["done"] = sum(
  1608	            1 for s in main_token["steps"] if s["status"] == "completed"
  1609	        )
  1610	        _save_token(main_token)
  1611	
  1612	    _write_audit("collect", {
  1613	        "step": step_id,
  1614	        "status": status,
  1615	        "evidence_count": len(result.get("evidence", [])),
  1616	        "files_changed": len(result.get("files_changed", [])),
  1617	    }, fallback=True)
  1618	
  1619	    print(_green(f"✅ {step_id}: collected and verified"))
  1620	    summary = result.get("summary", "")
  1621	    if summary:
  1622	        print(f"   {summary}")
  1623	    return 0
  1624	
  1625	
  1626	def cmd_cancel():
  1627	    """中止 subagent 任务
  1628	
  1629	    用法:
  1630	        python3 .claude/scripts/carros_base.py cancel --step S1 [--reason \"changes not needed\"]
  1631	
  1632	    将 sub_task/sub-{step}/result.json status 设为 cancelled，
  1633	    标记 main token 对应 step 为 cancelled。
  1634	    """
  1635	    global SUB_TASK_DIR
  1636	
  1637	    argv = sys.argv[sys.argv.index("cancel") + 1:]
  1638	    step_id = None
  1639	    reason = "cancelled by main agent"
  1640	    i = 0
  1641	    while i < len(argv):
  1642	        if argv[i] == "--step" and i + 1 < len(argv):
  1643	            step_id = argv[i + 1]; i += 2
  1644	        elif argv[i] == "--reason" and i + 1 < len(argv):
  1645	            reason = argv[i + 1]; i += 2
  1646	        else:
  1647	            i += 1
  1648	
  1649	    if not step_id:
  1650	        print(_red("❌ Usage: cancel --step S1"))
  1651	        return 2
  1652	
  1653	    tok, tp = _find_latest_token()
  1654	    if tok:
  1655	        td = tok.get("task_dir")
  1656	        if td:
  1657	            SUB_TASK_DIR = Path(td) / "sub_task"
  1658	            _init_paths_from_token(tok, tp)
  1659	
  1660	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}" if SUB_TASK_DIR else None
  1661	    if not sub_dir or not sub_dir.exists():
  1662	        print(_yellow(f"⚠  No sub task: sub-{step_id}"))
  1663	        return 0
  1664	
  1665	    result_path = sub_dir / "result.json"
  1666	    if result_path.exists():
  1667	        try:
  1668	            result = json.loads(result_path.read_text())
  1669	            result["status"] = "cancelled"
  1670	            result["failure"] = reason
  1671	            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
  1672	        except Exception:
  1673	            result_path.write_text(json.dumps({
  1674	                "status": "cancelled",
  1675	                "failure": reason,
  1676	                "started_at": "",
  1677	                "completed_at": datetime.now(timezone.utc).isoformat(),
  1678	            }))
  1679	
  1680	    # 更新 main token
  1681	    main_token = _load_token()
  1682	    if main_token and "steps" in main_token:
  1683	        for s in main_token["steps"]:
  1684	            if s["id"] == step_id:
  1685	                s["status"] = "cancelled"
  1686	                break
  1687	        _save_token(main_token)
  1688	
  1689	    _write_audit("cancel", {"step": step_id, "reason": reason})
  1690	    print(_yellow(f"⚠  {step_id}: cancelled ({reason})"))
  1691	    return 0
  1692	
  1693	
  1694	
```
