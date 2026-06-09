#!/usr/bin/env python3
"""
ecosystem-probe.py — SessionStart — 生态探针

Role: 检测运行平台（Claude Code / OpenCode）与 OMO 安装状态，输出软建议
永不阻断，exit 0。SessionStart 时注入平台能力信息，AI 据此调整行为策略。
有 OMO 时：hook 完整运行，gate/skill/context 全功能可用
无 OMO 时：无 hook 环境，AI 需要更保守、更自检
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input, output_continue,
    PROJECT_ROOT, STATE_DIR, HOME_DIR,
)


def detect_omo_family() -> dict:
    """Detect OMO family installations."""
    result = {"omc": False, "omo": False, "codex": False, "gemini": False, "hook_layer": "none"}

    # oh-my-claudecode (omc)
    if shutil.which("omc") is not None:
        result["omc"] = True
        result["omo"] = True
        result["hook_layer"] = "full"
    else:
        try:
            r = subprocess.run(["npm", "list", "-g", "oh-my-claudecode"], capture_output=True, text=True, timeout=10)
            if "oh-my-claudecode" in r.stdout:
                result["omc"] = True
                result["omo"] = True
                result["hook_layer"] = "full"
        except (OSError, subprocess.TimeoutExpired):
            pass

    # oh-my-opencode (omo)
    if shutil.which("omo") is not None:
        result["omo"] = True
        result["hook_layer"] = "full"
    else:
        try:
            r = subprocess.run(["npm", "list", "-g", "oh-my-opencode"], capture_output=True, text=True, timeout=10)
            if "oh-my-opencode" in r.stdout:
                result["omo"] = True
                result["hook_layer"] = "full"
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Codex CLI
    if shutil.which("codex") is not None:
        result["codex"] = True
    else:
        try:
            r = subprocess.run(["npm", "list", "-g", "@openai/codex"], capture_output=True, text=True, timeout=10)
            if "@openai/codex" in r.stdout:
                result["codex"] = True
        except (OSError, subprocess.TimeoutExpired):
            pass
    if (HOME_DIR / ".codex" / "config.json").exists():
        result["codex"] = True

    # Gemini CLI
    if shutil.which("gemini") is not None:
        result["gemini"] = True
    else:
        try:
            r = subprocess.run(["npm", "list", "-g", "@google/gemini-cli"], capture_output=True, text=True, timeout=10)
            if "@google/gemini-cli" in r.stdout:
                result["gemini"] = True
        except (OSError, subprocess.TimeoutExpired):
            pass

    return result


def main():
    if not hc_enabled("ecosystem_probe"):
        output_continue()
        return

    platform = "unknown"
    opencode = False
    omo_family = detect_omo_family()

    # ── Layer 1: Detect from stdin hook_source ──
    input_str = read_input()
    hook_source = ""
    if input_str:
        try:
            data = json.loads(input_str)
            hook_source = (data.get("hook_source") or "").strip()
        except (json.JSONDecodeError, Exception):
            pass

    if hook_source == "opencode-plugin":
        platform = "opencode"
        opencode = True
        if not omo_family["omo"] and not omo_family["omc"]:
            omo_family["hook_layer"] = "partial"
    elif hook_source in ("claude-code-hook", "claude_code_hook"):
        platform = "claude-code"
        omo_family["hook_layer"] = "full"
        if shutil.which("opencode") is not None:
            opencode = True
    else:
        # Layer 2: Environment detection
        if shutil.which("opencode") is not None:
            opencode = True
            platform = "opencode"
            if not omo_family["omo"] and not omo_family["omc"]:
                omo_family["hook_layer"] = "partial"
        if (HOME_DIR / ".claude" / "projects").exists():
            platform = "claude-code"
            omo_family["hook_layer"] = "full"

    # ── Runtime dependency detection ──
    python3_ok = shutil.which("python3") is not None
    python3_has_secrets = False
    missing_deps = ""

    if python3_ok:
        try:
            subprocess.run(
                [sys.executable, "-c", "import secrets"],
                capture_output=True, timeout=5,
            )
            python3_has_secrets = True
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        missing_deps += "python3 "

    # ── LSP server detection ──
    lsp = {
        "pyright": False, "tsserver": False, "go": False,
        "rust": False, "serena": False, "total": 0,
    }
    if shutil.which("pyright") is not None or shutil.which("pyright-langserver") is not None:
        lsp["pyright"] = True
        lsp["total"] += 1
    else:
        try:
            r = subprocess.run(["pip", "show", "pyright"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                lsp["pyright"] = True
                lsp["total"] += 1
        except (OSError, subprocess.TimeoutExpired):
            pass

    if shutil.which("typescript-language-server") is not None:
        lsp["tsserver"] = True
        lsp["total"] += 1

    if shutil.which("gopls") is not None:
        lsp["go"] = True
        lsp["total"] += 1

    if shutil.which("rust-analyzer") is not None:
        lsp["rust"] = True
        lsp["total"] += 1

    # Serena check with cache
    serena_cache = STATE_DIR / ".serena-checked"
    if shutil.which("serena") is not None:
        lsp["serena"] = True
        lsp["total"] += 1
    else:
        try:
            r = subprocess.run(["pip", "show", "serena-agent"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                lsp["serena"] = True
                lsp["total"] += 1
        except (OSError, subprocess.TimeoutExpired):
            pass

    if not lsp["serena"] and shutil.which("uvx") is not None:
        if serena_cache.exists():
            try:
                mtime = os.path.getmtime(str(serena_cache))
                if time.time() - mtime < 86400:
                    lsp["serena"] = serena_cache.read_text().strip() == "True"
                    if lsp["serena"]:
                        lsp["total"] += 1
            except OSError:
                pass
        else:
            try:
                r = subprocess.run(
                    ["timeout", "5", "uvx", "--from", "serena-agent", "serena", "--help"],
                    capture_output=True, timeout=10,
                )
                if r.returncode == 0:
                    lsp["serena"] = True
                    lsp["total"] += 1
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                serena_cache.parent.mkdir(parents=True, exist_ok=True)
                serena_cache.write_text(str(lsp["serena"]), encoding="utf-8")
            except OSError:
                pass

    # LSP level
    lsp_level = "none"
    if platform == "opencode" and opencode:
        lsp_level = "full"
    elif platform == "claude-code":
        lsp_level = "partial" if lsp["total"] >= 1 else "none"
    elif omo_family["codex"]:
        lsp_level = "bridge" if lsp["serena"] else "none"

    # Context limit
    ctx_limit_file = STATE_DIR / "model-context-limit"
    ctx_limit = "unset"
    if ctx_limit_file.exists():
        ctx_limit = ctx_limit_file.read_text().strip() or "unset"

    # ── Output probe info ──
    print()
    print("<ecosystem-probe>")
    print(f"platform:   {platform}")
    print(f"opencode:   {opencode}")
    print(f"omo:        {omo_family['omo']}")
    print(f"omc:        {omo_family['omc']}")
    print(f"codex:      {omo_family['codex']}")
    print(f"gemini:     {omo_family['gemini']}")
    print(f"hook_layer: {omo_family['hook_layer']}")
    print(f"python3:    {python3_ok}")
    print(f"py_secrets: {python3_has_secrets}")
    print(f"context_limit: {ctx_limit}")
    print(f"missing:    {missing_deps or 'none'}")
    print(f"lsp_level:  {lsp_level}")
    print(f"lsp_pyright: {lsp['pyright']}")
    print(f"lsp_typescript: {lsp['tsserver']}")
    print(f"lsp_go:     {lsp['go']}")
    print(f"lsp_rust:   {lsp['rust']}")
    print(f"lsp_serena: {lsp['serena']}")
    print(f"lsp_servers: {lsp['total']}")
    print("</ecosystem-probe>")

    # ── Soft suggestions ──
    if platform == "opencode" and not omo_family["omo"] and not omo_family["omc"]:
        print("[soft-suggest] OpenCode 已安装但未安装 OMO (oh-my-openagent)。")
        print("[soft-suggest] Carror OS 的 hook 门禁/技能/skill 依赖 OMO 兼容层。无 OMO 时仅基础功能可用。")
        print("[soft-suggest] 安装: npx oh-my-opencode install --no-tui --claude no --openai no --gemini no --skip-auth")

    if platform == "claude-code" and not omo_family["omc"]:
        print("[soft-suggest] Claude Code 平台建议安装 OMC (oh-my-claudecode) 获得完整 hook 门禁。")
        print("[soft-suggest] 安装: npx oh-my-claudecode install")

    if not python3_ok:
        print(f"[soft-suggest] ⚠️ python3 未安装 — 38 个 hook（127 处调用）依赖它。")
        print("[soft-suggest] macOS: brew install python3")
        print("[soft-suggest] Linux: apt install python3")
    elif not python3_has_secrets:
        print("[soft-suggest] ⚠️ python3 缺 secrets 模块（Python < 3.6），权限门禁降级。")
        print("[soft-suggest] 升级: brew upgrade python3 或 apt upgrade python3")

    # LSP suggestions
    if lsp_level == "none" and platform != "unknown":
        print()
        print("[lsp-suggest] 🔍 LSP 语义引擎未配置 — AI 将只能用 grep 理解代码（低效且容易出错）")
        print("[lsp-suggest] LSP 可让 AI 获得 IDE 级别的代码理解：跳转定义、查找引用、实时诊断")
        print("[lsp-suggest] 安装指南: Read docs/guides/cn/lsp-setup.md")

    if platform == "claude-code" and lsp_level == "none":
        print("[lsp-suggest] Claude Code: /plugin install pyright-lsp@claude-plugins-official")
        print("[lsp-suggest] 前置依赖: pip install pyright")
    elif platform == "claude-code" and lsp_level == "partial":
        print(f"[lsp-suggest] LSP 部分就绪 ({lsp['total']} 服务器)，建议安装更多语言服务器以覆盖本项目")

    if omo_family["codex"] and not lsp["serena"]:
        print("[lsp-suggest] Codex CLI 无原生 LSP，建议通过 Serena MCP 桥接")
        print("[lsp-suggest] 安装: pip install serena-agent && serena start --context codex")
        print("[lsp-suggest] 然后在 ~/.codex/config.toml 中配置 MCP 服务器")

    if platform == "opencode":
        print("[lsp-suggest] OpenCode LSP 已内置 (40+ 服务器)，设置 lsp:true 即可启用")
        opencode_json = PROJECT_ROOT / ".opencode.json"
        home_opencode_json = HOME_DIR / ".opencode.json"
        lsp_enabled = False
        for f in [opencode_json, home_opencode_json]:
            if f.exists():
                try:
                    content = f.read_text(encoding="utf-8")
                    if '"lsp".*true' in content:
                        lsp_enabled = True
                except OSError:
                    pass
        if not lsp_enabled:
            print('[lsp-suggest] ⚠️ 当前项目未启用 LSP — 在 .opencode.json 中设置 "lsp": true')

    output_continue()
    flywheel_event("ecosystem_probe", "probe_complete", "P2", platform)


if __name__ == "__main__":
    main()
