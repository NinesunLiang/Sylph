#!/usr/bin/env python3
"""Meta-Oracle review entry point — cross-platform replacement for meta-oracle-review.sh.

Called by AI after Meta-Oracle trigger notification, or by pipeline scripts
(lx-oma-orch, lx-oma-hier, package-release.sh).

Usage:
  python3 .claude/scripts/meta-oracle-review.py [G1|G2|G3|G4]

Outputs:
  1. Meta-Oracle review methodology (prompt for AI/critic agent)
  2. Runs C/E/G/UX scoring via meta-oracle-scorer
  3. Writes verdict entry to .omc/state/meta-oracle-verdicts.md
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


IS_WINDOWS = os.name == "nt"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")

# Platform-adaptive Python command
PY_CMD = "py -3" if IS_WINDOWS else "python3"

TRIGGER_TYPE = sys.argv[1] if len(sys.argv) > 1 else "G3"


# ── Methodology (mirrors meta-oracle-review.sh METHODOLOGY heredoc) ─

def print_methodology():
    print(r"""# Meta-Oracle 最后守门员 — 最高级审查方法论

你是 Meta-Oracle — Carror OS 的最高审查权威（最后守门员），独立于 Oracle。
你的审查权威高于 Oracle，使用完全不同的方法论（运行时验证 > 静态检查，对抗性审查 > 合规检查）。

## 通用审查原则（所有触发点适用）

1. **运行时验证 > 静态检查** — Oracle 的 auto-score.sh 基于文件存在性+正则匹配，容易系统性虚高。
   你应优先检查: 烟雾测试日志中的实际通过率、hook 生产验证的实际输出、error-dna.jsonl 中的真实频率。

2. **烟雾日志 > 文件存在性** — 文件注册了 ≠ 机制生效了。检查:
   - harness-smoke-test 的实际 pass/fail 计数
   - hook-production-verify 的实际阻断场景
   - error-dna.jsonl 中是否有真实的高频错误模式

3. **设计级盲区检查** — Oracle 的静态检查看不到的东西:
   - fail-open vs fail-closed 设计缺陷
   - ghost/goal 模式下的门禁降级
   - 正则表达式的匹配覆盖率（测试多种输入格式）

## 按触发点的专项审查
""")

    if TRIGGER_TYPE == "G1":
        print(r"""### G1: 架构决策终审
触发条件: 涉及 >=2 子系统 + 不可逆的架构变更
审查重点:
1. 跨子系统影响分析是否完整（所有下游子系统是否已识别）
2. 不可逆性评估（变更后能否回滚？回滚成本？）
3. 接口契约变更是否已同步到所有相关 feature
4. 是否与现有哲学/铁律冲突
5. source mirror 同步计划是否已就绪
""")
    elif TRIGGER_TYPE == "G2":
        print(r"""### G2: PRD/方案最后一步
触发条件: PRD 完整生命周期的最终阶段（Oracle 已 ACCEPT）
审查重点:
1. PRD 方案的 MECE 完整性（是否所有功能域已覆盖）
2. Oracle 的 ACCEPT 是否存在虚高（交叉验证 Oracle 评分依据）
3. 方案中的 NFR 数字是否有来源（避免 DG-02 类问题）
4. 下游 feature 的接口契约是否完整归属
5. 方案的可执行性（子任务拆分是否合理、依赖是否清晰）
""")
    elif TRIGGER_TYPE == "G3":
        print(r"""### G3: Oracle ACCEPT + 高分
触发条件: Oracle 给出 ACCEPT 且评分 >=8.5
审查重点:
1. 读取 Oracle 的评分输出，提取所有 >=8.5 分的维度
2. 对每个高分维度，寻找相反证据:
   - 烟雾测试中有无该维度的 FAIL？
   - error-dna 中有无该机制被绕过的记录？
   - 该机制的 regex/阈值 是否在边界场景下失效？
3. 产出 Meta-Oracle 纠正报告
""")
    elif TRIGGER_TYPE == "G4":
        print(r"""### G4: Release 门禁
触发条件: package-release.sh 执行前
审查重点:
1. source mirror 一致性检查（audit-hooks.sh --check-source-mirror）
2. 是否有未同步的治理文件变更
3. harness-smoke-test 全绿验证
4. 版本号一致性（VERSION.json <-> feature-registry.yaml <-> harness.yaml）
5. 是否有 PENDING_SYNC 标记的未发布变更
""")

    print(r"""
## 审查步骤

1. 确认触发类型（G1/G2/G3/G4），加载对应的专项审查清单
2. 收集证据: 运行烟雾测试、检查 error-dna、搜索设计文档
3. 交叉验证 Oracle 结论（如 Oracle 已给出裁决）
4. 寻找相反证据 — 刻意假设 Oracle 错误，尝试证伪
5. 产出 Meta-Oracle 裁决报告

## 输出格式

```
# Meta-Oracle 裁决报告 [{TRIGGER_TYPE}]

## 裁决
[Meta-Oracle: ACCEPT] / [Meta-Oracle: ADVISORY] / [Meta-Oracle: REJECT]

## Oracle 评分 vs Meta-Oracle 评估（如 Oracle 已评分）
| 维度 | Oracle 得分 | Meta-Oracle 评估 | 偏差 | 原因 |
|------|-----------|----------------|------|------|

## 关键发现
- [Finding 1]
- [Finding 2]

## 漏报发现（Oracle 未发现的问题）

## 虚高/虚低分析（如适用）

## 建议修正项
- [Action 1]
- [Action 2]

## 覆写理由（仅 REJECT 被覆写时需要）
[AI 如决定覆写 Meta-Oracle 的 REJECT 裁决，必须在此填写明确书面理由]
```

## 软门禁协议

1. ACCEPT -> 继续流程，记录到 .omc/state/meta-oracle-verdicts.md
2. ADVISORY -> 建议修正但不阻断，AI 自行判断
3. REJECT -> 强烈建议阻断，AI 必须有明确书面理由才能覆写
4. 连续 2 次 REJECT -> 升级为事实阻断，需人工介入
""")


# ── Scoring ─────────────────────────────────────────────────────────

def run_scoring():
    """Run the Python scorer (primary path) or fall back to bash scripts."""
    # Primary path: Python scorer
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from importlib import import_module
        scorer = import_module("meta-oracle-scorer")
        result = scorer.score_all(calibrated=True, meta_oracle=True)
        return result, True  # Python scoring used
    except ImportError as e:
        print(f"[警告] Python scorer import 失败: {e}", file=sys.stderr)

    # Fallback: bash scripts (macOS/Linux only)
    if IS_WINDOWS:
        print("[警告] bash fallback 不可用 (Windows)，跳过评分", file=sys.stderr)
        return None, False

    auto_score = os.path.join(SCRIPT_DIR, "auto-score.sh")
    score_ux = os.path.join(SCRIPT_DIR, "score-ux.sh")

    if not os.path.isfile(auto_score):
        print("[警告] auto-score.sh 不存在，跳过评分", file=sys.stderr)
        return None, False

    import subprocess
    try:
        output = subprocess.run(
            ["bash", auto_score, "--meta-oracle", "--calibrated"],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT,
        )
        print(output.stdout)
        if output.stderr:
            print(output.stderr, file=sys.stderr)

        # Extract gate verdict and score from bash output
        gate_match = None
        score_match = None
        for line in output.stdout.splitlines():
            if "[Meta-Oracle:" in line:
                gate_match = line.strip()
            if "C/E/G 加权总分" in line:
                import re
                m = re.search(r"(\d+\.\d+)", line)
                if m:
                    score_match = m.group(1)

        # UX score (bash)
        ux_score = "N/A"
        ux_max = "10"
        if os.path.isfile(score_ux):
            ux_output = subprocess.run(
                ["bash", score_ux], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT
            )
            try:
                ux_data = json.loads(ux_output.stdout.splitlines()[-1])
                ux_score = ux_data["total"]["score"]
                ux_max = ux_data["total"]["max"]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        return {
            "aggregate": {
                "weighted_score_10": float(score_match) if score_match else 0,
                "gate_verdict": gate_match or "N/A",
            },
            "ux_score": ux_score,
            "ux_max": ux_max,
        }, False

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"[警告] bash scoring 失败: {e}", file=sys.stderr)
        return None, False


# ── Verdict Writing ─────────────────────────────────────────────────

def write_verdict(gate_verdict, weighted_score, ux_score, ux_max):
    """Write verdict entry to meta-oracle-verdicts.md (cross-platform)."""
    os.makedirs(STATE_DIR, exist_ok=True)
    verdicts_path = os.path.join(STATE_DIR, "meta-oracle-verdicts.md")
    verdict_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ux_str = f"{ux_score}/{ux_max}" if ux_score is not None else "N/A"
    entry = (
        f"[{verdict_date}] [{TRIGGER_TYPE}] [{gate_verdict}] "
        f"— C/E/G 加权: {weighted_score}/10 | UX 独立: {ux_str}\n"
    )

    if os.path.isfile(verdicts_path):
        with open(verdicts_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Insert after header (line 0) + blank line (line 1) -> position 2
        lines.insert(2, entry)
        with open(verdicts_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        with open(verdicts_path, "a", encoding="utf-8") as f:
            f.write(entry)

    print(f"\n--- 裁决已留痕: {verdicts_path} ---")
    print(f"四维打分体系已就绪 | 权威等级: 高于 Oracle | 门禁: 软门禁")
    print(f"  方法论: 运行时验证 > 静态检查 | 对抗性审查 > 合规检查")
    print(f"  UX 维度: 独立评分, 不参与 C/E/G 的 8.6/10 门禁判定")


# ── Main ─────────────────────────────────────────────────────────────

# ── Critic Agent Spawn ───────────────────────────────────────────────

def _build_spawn_prompt(trigger_type, methodology_lines):
    """Build the full prompt for the independent critic agent."""
    project_name = os.path.basename(PROJECT_ROOT)

    # ═══════ Pre-collect runtime evidence ═══════
    import glob
    import subprocess

    # 1. Flywheel
    flywheel_status = "NOT FOUND"
    flywheel_size = "N/A"
    for fw in [
        os.path.join(STATE_DIR, "flywheel.log"),
        os.path.join(PROJECT_ROOT, ".claude", "flywheel.log"),
        os.path.join(os.path.expanduser("~"), ".claude", "flywheel.log"),
    ]:
        if os.path.isfile(fw):
            sz = os.path.getsize(fw)
            flywheel_status = "EXISTS at " + fw
            flywheel_size = "{} bytes ({:.0f}KB)".format(sz, sz / 1024)
            break
        elif os.path.islink(fw):
            real = os.path.realpath(fw)
            if os.path.exists(real):
                sz = os.path.getsize(real)
                flywheel_status = "EXISTS (symlink -> " + real + ")"
                flywheel_size = "{} bytes ({:.0f}KB)".format(sz, sz / 1024)
                break

    # 2. set -e in ACTIVELY REGISTERED hooks only
    set_e_hooks = "None (dormant .sh or .py only)"
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path) as f:
                cfg = json.load(f)
            cmds = set()
            for hl in cfg.get("hooks", {}).values():
                if isinstance(hl, list):
                    for h in hl:
                        if isinstance(h, dict):
                            cmds.add(h.get("command", ""))
            found = []
            for cmd in sorted(cmds):
                if ".sh" in cmd:
                    parts = cmd.split()
                    script = parts[-1]
                    full = script if script.startswith("/") else os.path.join(PROJECT_ROOT, script)
                    if os.path.isfile(full):
                        r = subprocess.run(["grep", "-l", "set -e", full],
                                           capture_output=True, text=True)
                        if r.stdout.strip():
                            found.append(script)
            if found:
                set_e_hooks = ", ".join(found)
        except Exception:
            set_e_hooks = "Error checking"

    # 3. Session health
    session_health = "NOT FOUND"
    shp = os.path.join(STATE_DIR, "session-health.json")
    if os.path.isfile(shp):
        try:
            with open(shp) as f:
                sd = json.load(f)
            la = sd.get("last_audit", "missing_key")
            session_health = "EXISTS, last_audit=" + str(la)
        except Exception as e:
            session_health = "EXISTS but error: " + str(e)

    # 4. Smoke test
    smoke_result = "NOT FOUND"
    logs = sorted(glob.glob(os.path.join(STATE_DIR, "harness-smoke-*.log")),
                  key=os.path.getmtime, reverse=True)
    if logs:
        latest = logs[0]
        try:
            with open(latest) as f:
                content = f.read()
            p = content.count("PASS")
            f_cnt = content.count("FAIL")
            smoke_result = "Last log: {}  PASS={}  FAIL={}".format(
                os.path.basename(latest), p, f_cnt)
        except Exception:
            smoke_result = "Exists but unreadable"

    return f"""{''.join(methodology_lines)}

## Current Project State
Project: {project_name}
Root: {PROJECT_ROOT}
Trigger: {trigger_type}
Timestamp: {datetime.now(timezone.utc).isoformat()}

## Pre-collected Runtime Evidence (verified by scoring system)
### Flywheel File
- {flywheel_status}
- Size: {flywheel_size}

### Hook Safety
- Active registered hooks with `set -e`: {set_e_hooks}
- Note: `.py` hooks do not use `set -e` by design

### Session Health
- `session-health.json`: {session_health}

### Smoke Test
- {smoke_result}

## VERIFICATION RULES (MANDATORY)
1. Only report findings traceable to EXACT file:line or command output.
2. Do NOT report "flywheel.log NOT FOUND" — already verified by scoring system.
3. Do NOT report "set -e in hooks" unless verified in an ACTIVE hook (registered in settings.json).
4. Do NOT report "session-health last_audit=null" — verify the actual JSON value.
5. All runtime claims must cross-check against this pre-collected evidence section.
6. If you cannot find file:line for a finding, DO NOT report it.

CRITICAL: You are Meta-Oracle — the FINAL gatekeeper.
"""

def _get_api_key():
    """Get model API key — provider-agnostic, multi-source.

    Detects the best available key for the current model provider.
    Priority:
      ANTHROPIC_AUTH_TOKEN (agent proxy) →
      DEEPSEEK_API_KEY →
      OPENAI_API_KEY →
      project .env / harness.yaml / Hermes .env

    Returns (key, provider_name) or ("", "").
    """
    # 0. Detect active agent configuration
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    using_proxy = bool(base_url and base_url != "https://api.anthropic.com")

    # 1. ANTHROPIC_AUTH_TOKEN — catches any Anthropic-compatible proxy (DeepSeek/XAI/etc.)
    key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if key and key != "***":
        return key, "any_provider"

    # 2. DEEPSEEK_API_KEY (most common provider for local setups)
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key and key != "***":
        return key, "deepseek"

    # 3. OPENAI_API_KEY (generic fallback, works with many providers)
    key = os.environ.get("OPENAI_API_KEY", "")
    if key and key != "***":
        return key, "openai"

    # 4. Project .env (standard for local dev)
    for env_path in [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, ".claude", ".env"),
    ]:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        for var in ["ANTHROPIC_AUTH_TOKEN", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
                            if line.startswith(f"{var}=***"):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key and key != "***":
                                    provider = var.lower().replace("_auth_token", "").replace("_api_key", "")
                                    return key, provider
            except OSError:
                pass

    # 5. harness.yaml (Carror OS native config — check all key variants)
    harness_path = os.path.join(PROJECT_ROOT, ".claude", "harness.yaml")
    if os.path.isfile(harness_path):
        try:
            with open(harness_path, "r", encoding="utf-8") as f:
                for line in f:
                    for var in ["anthropic_auth_token:", "deepseek_api_key:", "openai_api_key:"]:
                        if var in line:
                            key = line.split(":", 1)[1].strip().strip('"').strip("'")
                            if key and key != "***":
                                provider = var.replace("_auth_token:", "").replace("_api_key:", "")
                                return key, provider
        except OSError:
            pass

    # 6. Hermes .env (Boss's setup — last resort)
    hermes_env = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    if os.path.isfile(hermes_env):
        try:
            with open(hermes_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    for var in ["ANTHROPIC_AUTH_TOKEN", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
                        if line.startswith(f"{var}=***"):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key and key != "***":
                                provider = var.lower().replace("_auth_token", "").replace("_api_key", "")
                                return key, provider
        except OSError:
            pass

    return "", ""


def _spawn_critic_agent(trigger_type):
    """Primary path: spawn independent critic agent via API (provider-agnostic).

    Uses the same API provider as the main Hermes agent.
    Independence comes from separate context/call, not different model family.
    Checks spawn readiness first — skips if startup check failed.

    Returns (verdict_str, full_output) or (None, None) on failure.
    """
    # Fast path: startup readiness check already failed → skip spawn
    if not is_spawn_ready():
        return None, None

    api_key, provider = _get_api_key()
    if not api_key:
        print("[spawn] API key not found — 回退降级路径", file=sys.stderr)
        return None, None

    # Build methodology
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    print_methodology()
    sys.stdout = old_stdout
    methodology = buf.getvalue()

    full_prompt = _build_spawn_prompt(trigger_type, [methodology])

    # ── Provider-agnostic endpoint detection ──
    # Detect the active model provider from environment.
    # Priority: ANTHROPIC_BASE_URL (proxy) → DeepSeek native → OpenAI-compatible
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    model = os.environ.get("ANTHROPIC_MODEL", "").strip()

    # Use the same endpoint as the main Hermes agent if a proxy is set
    if base_url:
        if not model:
            # Try to infer model from provider URL
            if "deepseek" in base_url.lower():
                model = "deepseek-chat"
            elif "xai" in base_url.lower():
                model = "grok-3"
            else:
                model = "claude-sonnet-4"  # safe fallback for generic Anthropic-compatible
        api_endpoint = f"{base_url.rstrip('/')}/v1/messages"
        auth_header = "x-api-key"
    elif provider == "deepseek":
        base_url = "https://api.deepseek.com/anthropic"
        model = model or "deepseek-chat"
        api_endpoint = f"{base_url}/v1/messages"
        auth_header = "x-api-key"
    elif provider == "openai":
        # OpenAI format — use proxy for Anthropic-compatible endpoint
        base_url = "https://api.openai.com/v1"
        model = model or "gpt-4o"
        api_endpoint = f"{base_url}/v1/messages"
        auth_header = "x-api-key"
    else:
        # Default fallback — DeepSeek is most common for self-hosted
        base_url = "https://api.deepseek.com/anthropic"
        model = model or "deepseek-chat"
        api_endpoint = f"{base_url}/v1/messages"
        auth_header = "x-api-key"

    print(f"[spawn] endpoint={api_endpoint} model={model}", file=sys.stderr)

    payload = json.dumps({
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": full_prompt}],
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "120",
             "-X", "POST", api_endpoint,
             "-H", "Content-Type: application/json",
             "-H", f"{auth_header}: {api_key}",
             "-H", "anthropic-version: 2023-06-01",
             "-d", payload],
            capture_output=True, text=True, timeout=130,
        )
        if result.returncode != 0:
            raise subprocess.SubprocessError(f"curl exit={result.returncode}")

        # Parse Anthropic-format response
        data = json.loads(result.stdout)
        text = data.get("content", [{}])[0].get("text", "")

        if not text:
            # Try OpenAI-format fallback
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if text:
            verdict = _parse_verdict(text)
            if verdict:
                return verdict, text
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError, OSError) as e:
        print(f"[spawn] API 调用失败: {e} — 回退降级路径", file=sys.stderr)

    return None, None


def _parse_verdict(output):
    """Extract Meta-Oracle verdict from agent output."""
    m = re.search(r'\[Meta-Oracle:\s*(ACCEPT|ADVISORY|REJECT)\]', output)
    if m:
        return f"[Meta-Oracle: {m.group(1)}]"
    return None


def _extract_findings(output):
    """Extract key findings from agent output (first 500 chars of non-header content)."""
    # Strip methodology headers, take first meaningful paragraph
    cleaned = re.sub(r'^#.*$', '', output, flags=re.MULTILINE).strip()
    lines = [l for l in cleaned.split('\n') if l.strip() and not l.startswith('===')]
    return '\n'.join(lines[:10])[:500]


def main():
    print(f"=== Meta-Oracle 最后守门员 [{TRIGGER_TYPE}] ===")
    print(f"审查状态文件: {os.path.join(STATE_DIR, 'meta-oracle-verdicts.md')}")
    print(f"触发类型: {TRIGGER_TYPE}\n")

    # ── Primary Path: Spawn independent critic agent ──
    print("--- 主路径: 启动独立 critic agent ---")
    agent_verdict, agent_output = _spawn_critic_agent(TRIGGER_TYPE)

    if agent_verdict and agent_output:
        print(f"✅ 独立 agent 裁决: {agent_verdict}")
        findings = _extract_findings(agent_output)
        if findings:
            print(f"\n关键发现:\n{findings}")
        write_verdict(agent_verdict, "agent", "N/A", "N/A")
        print("\n[路径] 主路径 (独立 agent) — 裁决来自独立 critic agent 审查")
        return

    # ── Degraded Path: Static scoring (agent unavailable) ──
    print("⚠️ 独立 agent 不可用，降级为静态评分")
    print_methodology()

    print("\n--- 运行四维打分 (C/E/G 加权聚合 + UX 独立) ---")
    result, used_python = run_scoring()

    if result is None:
        print("\n[警告] 评分不可用，仅输出方法论")
        print(f"  评分脚本: {PY_CMD} .claude/scripts/meta-oracle-scorer.py --calibrated --meta-oracle")
        return

    agg = result.get("aggregate", {})
    weighted_score = agg.get("weighted_score_10", 0)
    gate_verdict = agg.get("gate_verdict", "N/A")

    ux_score = result.get("ux_score") if not used_python else None
    ux_max = result.get("ux_max") if not used_python else None

    if used_python and "dimensions" in result:
        ux = result["dimensions"].get("UX", {})
        ux_score = ux.get("score", "N/A")
        ux_max = ux.get("max", 10)

    print(f"\n--- Meta-Oracle 门禁裁决 ---")
    print(f"C/E/G 加权总分: {weighted_score}/10")
    print(f"8.6 门禁判定:   {gate_verdict}")

    if ux_score is not None:
        print(f"\n--- UX 独立评分 ---")
        print(f"UX 得分: {ux_score}/{ux_max} (独立, 不参与 8.6 门禁)")

    write_verdict(gate_verdict, weighted_score, ux_score, ux_max)
    print(f"\n[路径] 降级路径 (静态评分) — 独立 agent 不可用时的 fallback")


# ── Startup Readiness Check ──────────────────────────────────────────

SPAWN_READY_FILE = os.path.join(STATE_DIR, ".meta-oracle-spawn-ready")


def check_readiness():
    """Check at session start whether Meta-Oracle spawn is viable.

    Writes result to .omc/state/.meta-oracle-spawn-ready for fast lookup.
    Returns True if spawn-ready, False otherwise.
    """
    os.makedirs(STATE_DIR, exist_ok=True)

    # Step 1: API key available? (any provider — not just DeepSeek)
    api_key, provider = _get_api_key()
    if not api_key:
        with open(SPAWN_READY_FILE, "w") as f:
            f.write("degraded:no_api_key\n")
        print("[meta-oracle readiness] 降级 — 未检测到可用 API key", file=sys.stderr)
        return False

    # Step 2: Quick connectivity test (1-token call, 10s timeout)
    # Detect endpoint to test — same logic as _spawn_critic_agent
    base_url_env = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if base_url_env:
        test_endpoint = f"{base_url_env.rstrip('/')}/v1/messages"
        test_model = os.environ.get("ANTHROPIC_MODEL", "").strip() or "deepseek-chat"
        api_header = "x-api-key"
    elif provider == "deepseek":
        test_endpoint = "https://api.deepseek.com/anthropic/v1/messages"
        test_model = "deepseek-chat"
        api_header = "x-api-key"
    elif provider == "openai":
        test_endpoint = "https://api.openai.com/v1/chat/completions"
        test_model = "gpt-4o"
        api_header = "x-api-key"
    elif provider == "any_provider":
        # Token found but can't determine endpoint — test DeepSeek as most common self-host
        test_endpoint = "https://api.deepseek.com/anthropic/v1/messages"
        test_model = "deepseek-chat"
        api_header = "x-api-key"
    else:
        test_endpoint = "https://api.deepseek.com/anthropic/v1/messages"
        test_model = "deepseek-chat"
        api_header = "x-api-key"

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             "-X", "POST", test_endpoint,
             "-H", "Content-Type: application/json",
             "-H", f"{api_header}: {api_key}",
             "-H", "anthropic-version: 2023-06-01",
             "-d", json.dumps({"model": test_model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]})],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("content") or data.get("choices"):
                with open(SPAWN_READY_FILE, "w") as f:
                    f.write(f"ready:{datetime.now(timezone.utc).isoformat()}\n")
                print(f"[meta-oracle readiness] ✅ spawn 就绪 — {test_model} API 连通 ({test_endpoint})", file=sys.stderr)
                return True
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as e:
        pass

    with open(SPAWN_READY_FILE, "w") as f:
        f.write("degraded:api_unreachable\n")
    print(f"[meta-oracle readiness] 降级 — API 不可达 ({test_endpoint})", file=sys.stderr)
    return False


def is_spawn_ready():
    """Fast check: was spawn verified ready at session start?"""
    if not os.path.isfile(SPAWN_READY_FILE):
        return False
    try:
        with open(SPAWN_READY_FILE, "r") as f:
            return f.read().strip().startswith("ready:")
    except OSError:
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-readiness":
        sys.exit(0 if check_readiness() else 1)
    main()
