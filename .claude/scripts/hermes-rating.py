#!/usr/bin/env python3
"""
CarrorOS 评分器 — 按 Boss 提供的 35 项指标体系
C1-C9 (能力维度, 总分100)
E1-E8 (错误防护, 总分100)
长期治理 (7项)
用户体验 (7项, 独立不计入总分)
"""
import json, os, sys, subprocess, time

PROJECT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
CLAUDE_DIR = os.path.join(PROJECT, ".claude")
OMC_DIR = os.path.join(PROJECT, ".omc")
STATE_DIR = os.path.join(OMC_DIR, "state")

def e(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except: return ""

def exists(p):
    return os.path.exists(os.path.join(PROJECT, p))

def ls_dir(p):
    d = os.path.join(PROJECT, p)
    if os.path.isdir(d):
        return [f for f in os.listdir(d) if not f.startswith('.')]
    return []

# ── C1-C9: 能力维度 (各最高分列在括号中) ──
results = {}
detail = {}

# C1: 指令清晰度 (15) — AGENTS.md 哲学铁律清晰度
c1 = 0
agents_content = ""
for fname in [".claude/AGENTS.compact.md", "AGENTS.md"]:
    fp = os.path.join(PROJECT, fname)
    if os.path.exists(fp):
        with open(fp) as f: agents_content += f.read()
if not agents_content:
    for fname in [".claude/AGENTS.md"]:
        fp = os.path.join(PROJECT, fname)
        if os.path.exists(fp):
            with open(fp) as f: agents_content += f.read()
phi_count = agents_content.count("哲学")
iron_count = agents_content.count("铁律")
hierarchy = "权威链" in agents_content or "哲学冲突裁决" in agents_content or "优先级" in agents_content
c1 = min(15, 
     (3 if phi_count >= 2 else 1) +
     (3 if iron_count >= 5 else 1) +
     (3 if hierarchy else 0) +
     (3 if agents_content else 0) +
     (3 if exists(".claude/index.md") else 0))
detail["C1"] = f"哲学引用{phi_count}次/铁律{iron_count}条/层级{hierarchy}: {c1}/15"

# C2: 上下文完整度 (15) — 系统环/路由索引/反模式
c2 = 0
c2 += 4 if exists(".claude/kernel.md") else 0
c2 += 4 if exists(".claude/index.md") else 0
c2 += 3 if exists(".claude/anti-patterns.md") else 0
c2 += 4 if exists(".claude/claude-next.md") else 0
detail["C2"] = f"kernel+index+anti+practices → {c2}/15"

# C3: 流程结构化 (15) — 五阶工作流+执行模式
c3 = 0
c3 += 5 if exists(".claude/workflow-standard/README.md") else 0
c3 += 5 if exists(".claude/reference/execution-modes.md") else 0
c3 += 5 if exists(".claude/reference/autonomous-decision-chain.md") else 0
detail["C3"] = f"workflow+modes+decision-chain → {c3}/15"

# C4: 输出规范化 (10) — terminal-safety +完成门禁
c4 = 0
hooks_dir = os.path.join(CLAUDE_DIR, "hooks")
skills_dir = os.path.join(CLAUDE_DIR, "skills", "lx-goal")
c4 += 3 if os.path.isdir(os.path.join(CLAUDE_DIR, "rules")) else 0
c4 += 4 if os.path.isdir(hooks_dir) and any(f.endswith(".py") for f in os.listdir(hooks_dir)) else 0
c4 += 3 if os.path.isdir(skills_dir) else 0
detail["C4"] = f"rules+hooks+skills → {c4}/10"

# C5: 工具生命周期 (10) — feature-registry + 机制生命周期
c5 = 0
c5 += 5 if exists(".claude/feature-registry.yaml") else 0
c5 += 5 if exists(".claude/reference/mechanism-lifecycle.md") else 0
detail["C5"] = f"registry+lifecycle → {c5}/10"

# C6: 知识密度 (10) — claude-next.md + anti-patterns.md + 狗粮
c6 = 0
cn = os.path.join(CLAUDE_DIR, "claude-next.md")
if exists(".claude/claude-next.md"):
    sz = os.path.getsize(cn)
    c6 += 5 if sz > 5000 else (3 if sz > 1000 else 1)
ap = os.path.join(CLAUDE_DIR, "anti-patterns.md")
if exists(".claude/anti-patterns.md"):
    sz2 = os.path.getsize(ap)
    c6 += 5 if sz2 > 3000 else (3 if sz2 > 1000 else 1)
detail["C6"] = f"claude-next({os.path.getsize(cn) if exists('.claude/claude-next.md') else 0}B)+anti-patterns → {c6}/10"

# C7: 关联编排 (10) — 子代理/Cron/race
c7 = 0
c7 += 4 if exists(".claude/skills/lx-race/SKILL.md") else 0
c7 += 3 if exists(".claude/nodes/README.md") else 0
if os.path.isdir(hooks_dir):
    hooks = [f for f in os.listdir(hooks_dir) if f.endswith((".sh", ".py"))]
    if len(hooks) >= 15: c7 += 3
    elif len(hooks) >= 8: c7 += 2
    else: c7 += 1
detail["C7"] = f"race({exists('.claude/skills/lx-race/SKILL.md')})+nodes({exists('.claude/nodes/README.md')})+hooks → {c7}/10"

# C8: 可维护性 (10) — 命名规范+版本号+打包
c8 = 0
c8 += 4 if exists("VERSION.json") else 0
# 检测 .sh 或 .py
c8_sh_or_py = 0
for ext in ["sh", "py"]:
    if exists(f".claude/scripts/package-release.{ext}"):
        c8_sh_or_py = 3
        break
c8 += c8_sh_or_py
c8 += 3 if exists(".claude/harness.yaml") else 0
detail["C8"] = f"version+package+harness → {c8}/10"

# C9: 错误恢复 (10) — 三次修复机制+会话交接
c9 = 0
# 检测修复上限声明（可能在 AGENTS.md 或 anti-patterns.md）
c9_retry = 0
if exists(".claude/anti-patterns.md") and ("三次修复" in open(os.path.join(CLAUDE_DIR, "anti-patterns.md"), encoding='utf-8').read()):
    c9_retry = 4
elif "修复上限" in agents_content or "3轮" in agents_content:
    c9_retry = 4
c9 += c9_retry
# 检测 session-handoff (支持 .md, .json)
c9_handoff = 0
for hf in ["session-handoff.md", "session-handoff-v2.json"]:
    if exists(f".omc/state/{hf}"):
        c9_handoff = 3
        break
c9 += c9_handoff
c9 += 3 if any("completion-gate" in f for f in (os.listdir(hooks_dir) if os.path.isdir(hooks_dir) else [])) else 0
detail["C9"] = f"retry-mech+handoff+completion-gate → {c9}/10"

# ── E1-E8: 错误防护 (各最高分在括号) ──

# E1: 目标漂移 (20) — scope 机制
e1 = 0
if exists(".claude/hooks/pretool-edit-scope.py"): e1 += 10
# current-scope.txt 可能运行时生成而非静态存在；检测 scope 相关文件
e1_scope_file = 0
for sf in ["current-scope.txt", "pretool-scope-gate.py", "pretool-plan-gate.py"]:
    if exists(f".claude/scripts/{sf}") or exists(f".claude/hooks/{sf}"):
        e1_scope_file = 5
        break
e1 += e1_scope_file
e1 += 5 if "范围冻结" in agents_content else 0
detail["E1"] = f"edit-scope+scope-txt+scope-freeze → {e1}/20"

# E2: 幻觉输出 (20) — 证据门禁+预输出检查
e2 = 0
e2 += 8 if exists(".claude/hooks/completion-gate.py") else 0
e2 += 6 if "证据门禁" in agents_content else 0
e2 += 6 if "禁止编造" in agents_content else 0
detail["E2"] = f"completion-gate+evidence+no-fabricate → {e2}/20"

# E3: 虚假完成 (15) — 软完成语检测
e3 = 0
e3 += 8 if "软完成语" in agents_content else 0
# 软完成语检测可能合并在 completion-gate.py 中
e3 += 7 if exists(".claude/hooks/pretool-soft-complete-detect.py") or (exists(".claude/hooks/completion-gate.py") and "软完成语" in open(os.path.join(CLAUDE_DIR, "hooks", "completion-gate.py"), encoding='utf-8').read()) else 0
detail["E3"] = f"soft-complete-words+detect-hook → {e3}/15"

# E4: 惯性执行 (12) — 哲学先行
e4 = 0
e4 += 6 if "哲学先行" in agents_content else 0
e4 += 6 if exists(".claude/reference/autonomous-decision-chain.md") else 0
detail["E4"] = f"philosophy-first+decision-chain → {e4}/12"

# E5: 症状混淆 (10) — 根因分析
e5 = 0
e5 += 5 if exists(".claude/skills/lx-root-cause-analysis/SKILL.md") else 0
e5 += 5 if "症状" in agents_content or "根因" in agents_content or "RCA" in agents_content else 0
detail["E5"] = f"root-cause-skill+mentions → {e5}/10"

# E6: 自我矛盾 (13) — 三源一致性
e6 = 0
e6 += 7 if exists(".claude/reference/three-source-consistency.md") else 0
e6 += 6 if "三源一致性" in agents_content else 0
detail["E6"] = f"three-source+phi-consistency → {e6}/13"

# E7: 过度自信 (10) — 置信度标注
e7 = 0
e7 += 5 if "置信度" in agents_content else 0
e7 += 5 if "已验证" in agents_content else 0
detail["E7"] = f"confidence-markers+verified-syntax → {e7}/10"

# E8: 上下文遗忘 (10) — 会话交接+抗compact
e8 = 0
e8 += 5 if exists(".omc/state/session-handoff.md") else 0
e8 += 5 if exists(".claude/workflow-standard/README.md") else 0
detail["E8"] = f"handoff+workflow-standard → {e8}/10"

# ── 长期治理 (7项, 每项10分) ──
g = {}

g["抗衰减防线"] = min(10, 
    (5 if exists(".claude/hooks/harness_lib.py") or exists(".claude/hooks/harness_config.sh") else 0) +
    (3 if exists(".claude/hooks/heartbeat-cron.sh") or exists(".claude/hooks/heartbeat.py") else 0) +
    (2 if exists(".claude/hooks/recovery-cron.sh") or exists(".claude/hooks/recovery.py") else 0))

g["AI赋能全流程自动化"] = min(10,
    (4 if exists(".claude/skills/lx-goal/SKILL.md") else 0) +
    (3 if exists(".claude/skills/lx-ghost/SKILL.md") else 0) +
    (3 if exists(".claude/skills/lx-status/SKILL.md") else 0))

g["学习笔记积累"] = min(10,
    (5 if exists(".claude/claude-next.md") and os.path.getsize(".claude/claude-next.md") > 3000 else 0) +
    (5 if exists(".claude/anti-patterns.md") and os.path.getsize(".claude/anti-patterns.md") > 3000 else 0))

g["长期目标一致性"] = min(10,
    (5 if exists(".claude/reference/meta-oracle.md") else 0) +
    (3 if exists(".claude/reference/three-source-consistency.md") else 0) +
    (2 if "一致性" in agents_content else 0))

g["功能标志分明"] = min(10,
    (5 if exists(".claude/harness.yaml") else 0) +
    (5 if exists(".claude/hooks/pretool-harness-gate.py") or exists(".claude/hooks/pretool-plan-gate.py") else 0))

g["内置安全与洞察"] = min(10,
    (4 if exists(".claude/hooks/permission-gate.py") else 0) +
    (3 if exists(".claude/hooks/privacy-gate.py") else 0) +
    (3 if exists(".claude/reference/red-team.md") else 0))

g["Evaluation评测框架"] = min(10,
    (4 if exists(".claude/scripts/meta-oracle-scorer.py") else 0) +
    (3 if exists(".claude/scripts/capability-matrix-test.py") or exists(".claude/scripts/capability-matrix-test.sh") else 0) +
    (3 if exists(".claude/scripts/smoke-test.py") or exists(".claude/scripts/smoke-test.sh") else 0))

# ── 用户体验 (7项, 每项10分, 独立) ──
ux = {}

# UX1: 长期目标一致性
ux["长期目标一致性"] = min(10,
    (4 if exists(".claude/harness.yaml") else 0) +
    (3 if exists(".claude/hooks") else 0) +
    (3 if len(ls_dir(".claude/skills")) >= 10 else 2 if len(ls_dir(".claude/skills")) >= 5 else 1))

# UX2: 用户心智负担减轻
ux["用户心智负担减轻"] = min(10,
    (4 if exists(".claude/AGENTS.compact.md") else 0) +
    (4 if exists("./docs/guides/cn/tutorial-05.md") else 0) +
    (2 if len(ls_dir(".claude/skills")) >= 20 else 0))

# UX3: 交互现代化
ux["交互现代化"] = min(10,
    (4 if "/lx-goal" in (e("grep -r 'lx-goal' " + os.path.join(PROJECT, "docs") + " 2>/dev/null") if os.path.isdir(os.path.join(PROJECT, "docs")) else "") else 0) +
    (3 if exists(".claude/scripts/qqbot") else 0) +
    (3 if exists(".claude/scripts/cron") else 0))

# UX4: 用户掌控感
ux["用户掌控感"] = min(10,
    (4 if "用户裁定" in agents_content else 0) +
    (3 if "权限分明" in agents_content else 0) +
    (3 if exists(".claude/hooks") and any("permission" in f for f in os.listdir(hooks_dir)) else 0))

# UX5: AI智能感
ux["ai智能感"] = min(10,
    (4 if len(ls_dir(".claude/skills")) >= 20 else (2 if len(ls_dir(".claude/skills")) >= 10 else 0)) +
    (3 if exists(".claude/nodes/README.md") else 0) +
    (3 if exists(".claude/reference/skill-graph.md") else 0))

# UX6: 行为可预测
ux["行为可预测"] = min(10,
    (4 if agents_content and "铁律" in agents_content else 0) +
    (3 if exists(".claude/workflow-standard/README.md") else 0) +
    (3 if "哲学冲突裁决" in agents_content else 0))

# UX7: 人机权限分明
ux["人机权限分明"] = min(10,
    (4 if exists(".claude/hooks/permission-gate.py") else 0) +
    (3 if exists(".claude/hooks/privacy-gate.py") else 0) +
    (3 if "隐私防线" in agents_content else 0))

# ── 总分计算 ──
cs = [c1,c2,c3,c4,c5,c6,c7,c8,c9]
es = [e1,e2,e3,e4,e5,e6,e7,e8]
c_total = sum(cs)
e_total = sum(es)
g_total = sum(g.values())
ux_total = sum(ux.values())

report = {
    "project": PROJECT,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "C_能力维度": {
        "总分": f"{c_total}/100",
        "项目": {f"C{i+1}": cs[i] for i in range(9)},
        "明细": detail
    },
    "E_错误防护": {
        "总分": f"{e_total}/100",
        "项目": {f"E{i+1}": es[i] for i in range(8)},
        "明细": detail
    },
    "G_长期治理": {
        "项目": {k: f"{v}/10" for k,v in g.items()},
        "总分": f"{g_total}/70"
    },
    "UX_用户体验": {
        "项目": {k: f"{v}/10" for k,v in ux.items()},
        "总分": f"{ux_total}/70"
    }
}

# 输出
out = json.dumps(report, ensure_ascii=False, indent=2)
print(out)

# 保存
os.makedirs(STATE_DIR, exist_ok=True)
ts = time.strftime("%Y%m%d-%H%M%S")
with open(os.path.join(STATE_DIR, f"hermes-rating-{ts}.json"), "w", encoding="utf-8") as f:
    f.write(out)
print(f"\n✅ 报告已保存: {STATE_DIR}/hermes-rating-{ts}.json", file=sys.stderr)
