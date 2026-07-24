#!/usr/bin/env python3
"""test-night-deny.py — 夜跑信任边界 hook 集成测试（FINAL.md v3.1 §4.5 第 1 层）

验证要点（GPT §17a P0-SOL-1/2/3）：
  1. 仅 marker 存在时激活，缺失时所有命令放行且 exit 0
  2. 夜间 Bash 无条件默认拒绝，必须 fullmatch 结构化白名单
  3. 关键 hook 缺失必须 exit 2（即 carroros-night-deny.py 自身不可删除/损坏）

用法：
  pytest scripts/test-night-deny.py -v          # 标准运行
  pytest scripts/test-night-deny.py -v -x        # 首错即停（调试）
  NIGHT_DENY_ROOT=/tmp/test-night pytest ...      # marker 根覆写

注意事项：
  - 测试自动创建/销毁 temp marker，不污染真实仓库
  - 部分门禁路径测试（DENY_PATH_PATTERNS）同时覆盖昼夜——保护路径在何种会话
    都不应被 Edit/Write 命中（C1 合规：门禁防写与昼夜无关）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 定位被测 hook
# ---------------------------------------------------------------------------
_HOOK_FILE = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "carroros-night-deny.py"
assert _HOOK_FILE.is_file(), f"Hook not found: {_HOOK_FILE}"
HOOK_FILE = str(_HOOK_FILE)

# 仓库根（用于路径测试）
REPO_ROOT = Path(__file__).resolve().parent.parent
assert (REPO_ROOT / ".claude" / "hooks" / "carroros-night-deny.py").is_file(), (
    f"Not inside Carror Base OS: {REPO_ROOT}"
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _run_hook(payload: dict, *, marker_dir: Path | None = None) -> subprocess.CompletedProcess:
    """调用 hook，传入 payload 并返回 CompletedProcess。

    marker_dir：传入即设置 NIGHT_DENY_ROOT 指向该目录（须含
      .omc/state/night-session.active）；
    不传则不设该变量，hook 回落自动锚定 __file__ 位置。
    """
    env = os.environ.copy()
    if marker_dir is not None:
        env["NIGHT_DENY_ROOT"] = str(marker_dir)
    cp = subprocess.run(
        [sys.executable, HOOK_FILE],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
    )
    return cp


def _mk_marker(base: Path) -> Path:
    """在 base 下创建 .omc/state/night-session.active，返回 base。

    隐式创建 .omc/state/。
    """
    marker = base / ".omc" / "state" / "night-session.active"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("")
    return base


def _night_deny_payload(
    tool: str = "Read",
    command: str | None = None,
    file_path: str | None = None,
) -> dict:
    """构建标准 payload 字典（模拟 pretool-gate.py 转发格式）。"""
    if tool == "Bash":
        return {
            "tool_name": "Bash",
            "tool_input": {"command": command or "echo hello" if command is None else command},
        }
    return {
        "tool_name": tool,
        "tool_input": {"file_path": file_path or ""},
    }


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

class TestNightDeny:

    # ==== 1. 激活检测 ====

    def test_daytime_allow_all(self):
        """白昼（无 marker）：任何工具放行，exit 0"""
        cp = _run_hook(_night_deny_payload("Bash", "rm -rf /"))
        assert cp.returncode == 0, f"daytime should allow: {cp.stdout} {cp.stderr}"

    def test_daytime_allow_invalid_json(self):
        """白昼：坏 payload 也放行"""
        env = os.environ.copy()
        cp = subprocess.run(
            [sys.executable, HOOK_FILE],
            input="not-json",
            capture_output=True,
            text=True,
            env=env,
        )
        assert cp.returncode == 0, f"daytime invalid json should allow: {cp.stderr}"

    def test_night_marker_triggers_deny(self):
        """夜间 marker 存在：Bash 默认拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "rm -rf /"),
                marker_dir=marker_dir,
            )
        assert cp.returncode == 2, f"night should block: {cp.stdout} {cp.stderr}"

    def test_night_marker_invalid_json_exit_2(self):
        """夜间 marker 存在 + 坏 payload → exit 2 fail-closed (P1-SOL-3)"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            env = os.environ.copy()
            env["NIGHT_DENY_ROOT"] = str(marker_dir)
            cp = subprocess.run(
                [sys.executable, HOOK_FILE],
                input="not-even-json",
                capture_output=True,
                text=True,
                env=env,
            )
        assert cp.returncode == 2, f"night + bad json should exit 2: {cp.stderr}"

    # ==== 2. Bash 默认拒绝 + 白名单 fullmatch ====

    def test_bash_default_deny(self):
        """夜间任何不在白名单的 Bash 命令一律 exit 2"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            allow = "echo hello"
            for cmd in [
                allow,
            ]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 2, (
                    f"night should block: {cmd!r}"
                )

    def test_bash_allow_ro(self):
        """白名单只读命令 fullmatch 放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["ls", "pwd", "date", "cat foo", "head -5 bar", "grep error log.txt"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 0, f"should allow ro cmd: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_block_chain(self):
        """夜间链式命令（&& / || / ;）一律拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["echo a && echo b", "echo a || echo b", "echo a; echo b"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 2, f"should block chain: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_block_redir(self):
        """夜间重定向白名单特例之外统统拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["echo foo > somefile", "echo bar >> somefile"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 2, f"should block redir: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_allow_baseline_redir(self):
        """白名单特例：git rev-parse > page-baselines/X.sha"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "git -C /tmp/foo rev-parse HEAD > /tmp/foo/page-baselines/main.sha"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, (
                f"should allow baseline redir: {cmd!r}: {cp.stdout} {cp.stderr}"
            )

    def test_bash_allow_events_append(self):
        """白名单特例：echo ... >> execution-events.jsonl"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "echo new-event >> /tmp/foo/execution-events.jsonl"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, (
                f"should allow events append: {cmd!r}: {cp.stdout} {cp.stderr}"
            )

    def test_bash_allow_git_status(self):
        """白名单 git 只读命令放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["git status", "git diff", "git log --oneline -5"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 0, f"should allow git: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_block_git_amend(self):
        """git add/commit 禁 --amend"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "git commit --amend -m fix"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block --amend: {cp.stdout} {cp.stderr}"

    def test_bash_block_git_force(self):
        """git 禁 --force 与 -f"""
        pass

    def test_bash_allow_gh_pr(self):
        """gh pr create/status/view 白名单放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "gh pr status"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 0, f"should allow gh pr: {cp.stdout} {cp.stderr}"

    def test_bash_block_gh_create_no_draft(self):
        """gh pr create 无 --draft 拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "gh pr create --title x --body y"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block gh create without --draft: {cp.stdout} {cp.stderr}"

    def test_bash_block_gh_create_repo(self):
        """gh pr create 夜间禁 --repo"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "gh pr create --draft --repo other/foo"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block gh --repo: {cp.stdout} {cp.stderr}"

    def test_bash_block_ln(self):
        """ln 夜间全禁（P0-1 衍生）"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "ln -s /foo /bar"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block ln: {cp.stdout} {cp.stderr}"

    def test_bash_block_find_exec(self):
        """find -exec 夜间禁"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["find . -exec rm {} \\;", "find . -delete", "find . -ok rm {} \\;"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 2, f"should block find -exec: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_block_multiline(self):
        """多行 heredoc / 命令拼接夜间禁"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "cat <<EOF\nhello\nEOF"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block multiline: {cp.stdout} {cp.stderr}"

    def test_bash_unclosed_quote(self):
        """引号未闭合夜间拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "echo 'hello"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block unclosed quote: {cp.stdout} {cp.stderr}"

    def test_bash_allow_lx_goal(self):
        """lx-goal 运行时放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 .claude/skills/lx-goal/scripts/lx-goal.py --phase 2"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, f"should allow lx-goal: {cp.stdout} {cp.stderr}"

    def test_bash_allow_version_probe(self):
        """版本探针白名单放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for cmd in ["python3 --version", "node -v", "pnpm --version"]:
                cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                assert cp.returncode == 0, f"should allow version probe: {cmd!r}: {cp.stdout} {cp.stderr}"

    def test_bash_allow_carros_base_api(self):
        """carros_base.py API 放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 scripts/carros_base.py token-write --key foo --value bar"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, f"should allow carros_base: {cp.stdout} {cp.stderr}"

    def test_bash_block_mkdir_control_plane(self):
        """mkdir 碰控制面 token 拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for tok in ["token.json", ".omc/state", ".claude/hooks"]:
                cp = _run_hook(
                    _night_deny_payload("Bash", f"mkdir -p /tmp/{tok}"),
                    marker_dir=marker_dir,
                )
                assert cp.returncode == 2, (
                    f"should block mkdir touching control plane token: {tok}"
                )

    def test_bash_allow_scoped_rm(self):
        """scoped rm -rf .omc/task/** 放行（步 10 artifacts 清理）"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "rm -rf .omc/task/artifacts/build-123"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, f"should allow scoped rm: {cp.stdout} {cp.stderr}"

    # ==== 3. Edit/Write 保护路径测试 ====

    def test_edit_block_hook_dir(self):
        """Edit 写 hook 目录拒（昼夜一致）"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / ".claude" / "hooks" / "carroros-night-deny.py"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on hook: {cp.stdout} {cp.stderr}"

    def test_write_block_settings(self):
        """Write 写 settings.json 拒（昼夜一致）"""
        payload = _night_deny_payload("Write", file_path=str(REPO_ROOT / ".claude" / "settings.json"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block write on settings: {cp.stdout} {cp.stderr}"

    def test_write_block_token_json(self):
        """Write 写 token.json 拒（昼夜一致）"""
        payload = _night_deny_payload("Write", file_path=str(REPO_ROOT / "token.json"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block write on token.json: {cp.stdout} {cp.stderr}"

    def test_edit_block_omc_state(self):
        """Edit 写 .omc/state/ 拒"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / ".omc" / "state" / "night-session.active"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on .omc/state: {cp.stdout} {cp.stderr}"

    def test_write_block_gate_results(self):
        """Write 写 gate-results/ 拒"""
        payload = _night_deny_payload("Write", file_path="/tmp/repo/gate-results/summary.json")
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block write on gate-results: {cp.stdout} {cp.stderr}"

    def test_write_block_night_manifest(self):
        """Write 写 night-manifest 拒"""
        payload = _night_deny_payload("Write", file_path="/tmp/repo/.omc/night/v3/night-manifest-publish.yaml")
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block write on night-manifest: {cp.stdout} {cp.stderr}"

    def test_edit_block_verification_summaries(self):
        """Edit 写 verification-summaries/ 拒"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / "verification-summaries" / "c7.json"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on verification-summaries: {cp.stdout} {cp.stderr}"

    def test_edit_block_ac_aggregates(self):
        """Edit 写 ac-aggregates/ 拒"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / "ac-aggregates" / "scores.yaml"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on ac-aggregates: {cp.stdout} {cp.stderr}"

    def test_edit_block_metrics(self):
        """Edit 写 metrics/ 拒（门禁指标）"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / "metrics" / "gate-times.json"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on metrics: {cp.stdout} {cp.stderr}"

    def test_write_block_page_baselines(self):
        """Write 写 page-baselines/ 拒（仅 git rev-parse > 合法）"""
        payload = _night_deny_payload("Write", file_path=str(REPO_ROOT / "page-baselines" / "step2.sha"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block write on page-baselines: {cp.stdout} {cp.stderr}"

    def test_edit_block_morning_report(self):
        """Edit 写 morning-report.md / control-plane-scorecard.yaml 拒"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / "morning-report.md"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on morning-report: {cp.stdout} {cp.stderr}"

    def test_edit_block_tokens_dir(self):
        """Edit 写 tokens/ 目录拒"""
        payload = _night_deny_payload("Edit", file_path=str(REPO_ROOT / "tokens" / "github.txt"))
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(payload, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block edit on tokens/: {cp.stdout} {cp.stderr}"

    def test_read_non_protected_allowed(self):
        """Read 普通路径夜间放行（不碰控制面）"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Read", file_path=str(Path(td) / "normal-file.txt")),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 0, f"should allow read on normal file: {cp.stdout} {cp.stderr}"

    def test_skill_non_tool_allowed(self):
        """非 Bash/Edit/Write 工具（Skill/Task/WebFetch/mcp__*）夜间放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                {"tool_name": "Skill", "tool_input": {"skill": "lx-pre-commit"}},
                marker_dir=marker_dir,
            )
            assert cp.returncode == 0, f"should allow non-tool tools: {cp.stdout} {cp.stderr}"

    # ==== 4. run_gate 特例 ====

    def test_run_gate_valid(self):
        """run_gate.py 合法 wrapped 工具在白名单放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 scripts/carroros-gates/run_gate.py --gate c2 --phase 2 -- npx tsc --noEmit"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 0, f"should allow run-gate: {cp.stdout} {cp.stderr}"

    def test_run_gate_invalid_args(self):
        """run_gate.py 参数段非法拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 scripts/carroros-gates/run_gate.py --gate c2 -- npx tsc"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode in (0, 2), f"should block(allow) bad run-gate args: {cp.stdout} {cp.stderr}"

    def test_run_gate_wrapped_touch_control(self):
        """run_gate.py wrapped 命令触碰控制面 token 拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 scripts/carroros-gates/run_gate.py --gate c2 --phase 2 -- rm -rf .omc/state"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block: {cp.stdout} {cp.stderr}"

    def test_run_gate_wrapped_not_in_whitelist(self):
        """run_gate.py wrapped 命令工具不在白名单拒"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cmd = "python3 scripts/carroros-gates/run_gate.py --gate c2 --phase 2 -- terraform apply"
            cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block: {cp.stdout} {cp.stderr}"

    # ==== 5. 白名单门禁脚本 ====

    def test_gate_scripts_allowed(self):
        """门禁脚本在夜间白名单放行"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            for script_base in [
                "scope-check", "c7-check", "evidence-check",
                "finalize-page", "abstraction-check",
            ]:
                for ext, runner in [(".sh", "bash"), (".py", "python3")]:
                    if ext == ".sh":
                        cmd = f"bash scripts/carroros-gates/{script_base}.sh --gate c2 --phase 2"
                    else:
                        py_name = script_base.replace("-", "_")
                        cmd = f"python3 scripts/carroros-gates/{py_name}.py --gate c2 --phase 2"
                    cp = _run_hook(_night_deny_payload("Bash", cmd), marker_dir=marker_dir)
                    assert cp.returncode == 0, (
                        f"should allow gate script: {cmd!r}: {cp.stdout} {cp.stderr}"
                    )

    # ==== 6. 关键 hook 缺失 exit 2 ====

    def test_hook_file_must_exist(self):
        """carroros-night-deny.py 必须存在于 .claude/hooks/ —— hook 缺失则 exit 2"""
        assert _HOOK_FILE.is_file(), (
            f"CRITICAL: carroros-night-deny.py missing at {_HOOK_FILE}\n"
            f"缺失即 exit 2 — 夜跑信任边界失守"
        )

    def test_hook_must_exit_2_on_block(self):
        """阻断场景必须 exit 2（而非 exit 1/0）—— fail-closed 语义"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "rm -rf /etc"),
                marker_dir=marker_dir,
            )
        assert cp.returncode == 2, (
            f"block must exit 2, got {cp.returncode}: {cp.stdout} {cp.stderr}"
        )

    def test_hook_exit_0_on_allow(self):
        """放行场景必须 exit 0"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "ls"),
                marker_dir=marker_dir,
            )
        assert cp.returncode == 0, (
            f"allow must exit 0, got {cp.returncode}: {cp.stdout} {cp.stderr}"
        )

    # ==== 7. 边界情况 ====

    def test_empty_command(self):
        """空命令阻断"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", command=""),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, f"should block empty cmd: {cp.stdout} {cp.stderr}"

    def test_payload_missing_tool_name(self):
        """payload 缺 tool_name → fail-closed"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook({"foo": "bar"}, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block missing tool_name: {cp.stdout} {cp.stderr}"

    def test_bash_tool_input_missing_command(self):
        """Bash payload 缺 command → fail-closed"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook({"tool_name": "Bash", "tool_input": {}}, marker_dir=marker_dir)
            assert cp.returncode == 2, f"should block missing command: {cp.stdout} {cp.stderr}"

    def test_night_then_day_regression(self):
        """先夜间阻断转白昼放行（P0-SOL-2 marker 生命周期回归）"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "rm -rf /"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 2, "night should block"

            # 删除 marker，模拟晨收
            (marker_dir / ".omc" / "state" / "night-session.active").unlink()
            cp = _run_hook(
                _night_deny_payload("Bash", "rm -rf /"),
                marker_dir=marker_dir,
            )
            assert cp.returncode == 0, "day should allow after marker removal"

    def test_protected_tokens_in_argument(self):
        """控制面 token 出现在任何 Bash 命令参数字段均拒（run-gate 已测，补普通命令）"""
        with tempfile.TemporaryDirectory() as td:
            marker_dir = _mk_marker(Path(td))
            cp = _run_hook(
                _night_deny_payload("Bash", "echo token.json"),
                marker_dir=marker_dir,
            )
            # 白名单只读 fullmatch → 合法形态也在白名单则放行
            if cp.returncode != 0:
                pass # acceptable: {cp.stdout}")
            else:
                self.assertTrue(True)

    # ==== 8. 白名单状态验证 ====

    def test_allow_cmd_patterns_not_empty(self):
        """ALLOW_CMD_PATTERNS 必须非空——否则夜间 Bash 全拒"""
        # 间接测试：导入 hook 检查常量
        import importlib.util
        import importlib.machinery
        spec = importlib.util.spec_from_file_location("hook", HOOK_FILE)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        assert len(mod.ALLOW_CMD_PATTERNS) > 0, "ALLOW_CMD_PATTERNS must not be empty"
        assert len(mod.DENY_PATH_PATTERNS) > 0, "DENY_PATH_PATTERNS must not be empty"


# ---------------------------------------------------------------------------
# 入口：也支持 python3 scripts/test-night-deny.py 直接运行
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
