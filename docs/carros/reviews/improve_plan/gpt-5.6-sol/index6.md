# CarrorOS 最终整合重构方案
## 第 6/8 部分：代码、Schema、CLI 与 Hook 实现规范

本部分把前 5 章冻结的治理协议压成一套**最小可运行骨架**。目标不是一次写出所有高级能力，而是先建立不可绕过的核心链：

```text
Task Store
  → Intake / Plan
  → PreActionGate
  → Artifact + Evidence
  → VerifyGate
  → Continuity / Resume
  → Archive
```

核心裁决：

> CLI 只路由；Hook 只拦截；状态文件保存事实；VerifyGate 独占完成权。任何平台适配器都不得绕过领域层直接改写 `VERIFIED`。

---

# 一、最终代码结构

```text
.claude/scripts/
├── carros_base.py
├── carros_enhance.py
└── carros/
    ├── __init__.py
    ├── cli.py
    ├── errors.py
    ├── models.py
    ├── paths.py
    ├── atomic.py
    ├── audit.py
    ├── task_store.py
    ├── state_machine.py
    ├── intake_gate.py
    ├── plan_builder.py
    ├── preaction_gate.py
    ├── artifact_store.py
    ├── evidence_store.py
    ├── verify_gate.py
    ├── document_index.py
    ├── context_engine.py
    ├── disclosure_gate.py
    ├── checkpoint.py
    ├── continuity.py
    ├── resume.py
    ├── archive.py
    ├── metrics.py
    └── platform/
        ├── claude_code.py
        └── opencode.py

.claude/hooks/
└── pretool_gate.py

schemas/
├── task-manifest.schema.json
├── task-state.schema.json
├── context-request.schema.json
├── disclosure-receipt.schema.json
├── evidence.schema.json
├── verify-verdict.schema.json
└── handoff.schema.json

tests/
├── unit/
├── integration/
├── fixtures/
└── conformance/
```

为兼容第 1/8 的目录名，可保留：

```text
.claude/scripts/lib/context_engine.py
```

但它只能作为兼容导入层：

```python
from carros.context_engine import *  # noqa: F401,F403
```

不得形成第二套实现。

---

# 二、依赖方向

依赖必须单向：

```text
CLI / Platform Adapter
        ↓
Application Services
        ↓
Domain Gates / State Machine
        ↓
Task Store / Artifact Store / Document Index
        ↓
Filesystem / SQLite / Git / Provider
```

禁止：

```text
✗ task_store 导入 CLI；
✗ VerifyGate 调用模型决定 PASS；
✗ Hook 直接编辑 state.json；
✗ platform adapter 自行定义任务状态；
✗ context_engine 调用 verify_task；
✗ archive 根据聊天文本决定是否成功。
```

---

# 三、错误模型与 fail-closed

```python
# .claude/scripts/carros/errors.py

class CarrorError(Exception):
    code = "CARROS_ERROR"
    exit_code = 1


class ValidationError(CarrorError):
    code = "VALIDATION_ERROR"
    exit_code = 2


class StateConflict(CarrorError):
    code = "STATE_CONFLICT"
    exit_code = 3


class PermissionDenied(CarrorError):
    code = "PERMISSION_DENIED"
    exit_code = 4


class GateBlocked(CarrorError):
    code = "GATE_BLOCKED"
    exit_code = 5


class EvidenceInvalid(CarrorError):
    code = "EVIDENCE_INVALID"
    exit_code = 6


class ResumeBlocked(CarrorError):
    code = "RESUME_BLOCKED"
    exit_code = 7
```

统一 CLI 错误输出：

```json
{
  "ok": false,
  "error": {
    "code": "STATE_CONFLICT",
    "message": "expected state_version=7, actual=8",
    "recoverable": true
  }
}
```

硬规则：

```text
- Schema 无效：拒绝；
- Hook 解析失败：拒绝高风险工具；
- state_version 冲突：不覆盖；
- Artifact hash 不一致：证据无效；
- denied/allowed 同时命中：denied 获胜；
- 状态未知：不默认 RUNNING；
- 外部副作用状态未知：BLOCKED；
- 平台配置不兼容：降级为显式 CLI Gate，不默认放行。
```

---

# 四、路径与原子写入

## 4.1 安全路径解析

```python
# paths.py
from pathlib import Path

REPO = Path.cwd().resolve()


def repo_path(value: str) -> Path:
    path = (REPO / value).resolve()
    if path != REPO and REPO not in path.parents:
        raise ValueError(f"path escapes repository: {value}")
    return path


def task_dir(task_id: str) -> Path:
    if not task_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in task_id):
        raise ValueError("invalid task id")

    matches = list((REPO / ".omc/tasks").glob(f"*/{task_id}"))
    if len(matches) != 1:
        raise ValueError(f"task must resolve exactly once: {task_id}")
    return matches[0].resolve()
```

## 4.2 原子文件写入

```python
# atomic.py
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: Any) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    atomic_write_bytes(path, payload)
```

说明：单文件 rename 只能保证单文件原子性；跨 `state + evidence + plan` 的操作必须使用事务日志。

---

# 五、状态存储与 compare-and-swap

```python
# task_store.py
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .atomic import atomic_write_json
from .errors import StateConflict, ValidationError
from .paths import task_dir
from .state_machine import validate_transition


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_state(task_id: str) -> dict:
    state = load_json(task_dir(task_id) / "state.json")
    validate_state(state)
    return state


def validate_state(state: dict) -> None:
    required = {
        "schema_version",
        "task_id",
        "status",
        "state_version",
        "plan_version",
        "current_step",
    }
    missing = sorted(required - state.keys())
    if missing:
        raise ValidationError(f"missing state fields: {missing}")


def update_state(
    task_id: str,
    expected_version: int,
    mutate: Callable[[dict], None],
    *,
    actor: str,
    reason: str,
) -> dict:
    path = task_dir(task_id) / "state.json"

    # 生产实现应在此持有跨进程文件锁。
    current = load_json(path)
    actual = current["state_version"]
    if actual != expected_version:
        raise StateConflict(
            f"expected state_version={expected_version}, actual={actual}"
        )

    updated = copy.deepcopy(current)
    old_status = current["status"]
    mutate(updated)
    validate_transition(old_status, updated["status"])

    updated["state_version"] = actual + 1
    updated.setdefault("timestamps", {})["updated_at"] = utc_now()
    validate_state(updated)

    atomic_write_json(path, updated)
    append_audit(task_id, {
        "type": "STATE_UPDATED",
        "actor": actor,
        "reason": reason,
        "from_status": old_status,
        "to_status": updated["status"],
        "state_version_before": actual,
        "state_version_after": actual + 1,
    })
    return updated
```

生产要求：

```text
- macOS/Linux 使用 advisory file lock；
- OpenCode 多会话再叠加 writer lease；
- lease 包含 session_id、PID、过期时间；
- 状态写入前后均检查 lease；
- lease 过期不能自动接管正在进行的外部副作用；
- NFS/网络文件系统部署需改用 SQLite transaction 或服务端 CAS。
```

---

# 六、状态机

```python
# state_machine.py
from .errors import ValidationError

LEGAL = {
    "DRAFT": {"INTAKE_PENDING", "CANCELLED"},
    "INTAKE_PENDING": {"ASK_USER", "BLOCKED", "READY", "CANCELLED"},
    "ASK_USER": {"INTAKE_PENDING", "CANCELLED"},
    "READY": {"PLANNED", "ASK_USER", "BLOCKED", "CANCELLED"},
    "PLANNED": {"RUNNING", "BLOCKED", "CANCELLED"},
    "RUNNING": {
        "RUNNING", "COMPACT_SOON", "VERIFYING", "ASK_USER",
        "BLOCKED", "CANCELLED"
    },
    "COMPACT_SOON": {"RUNNING", "RESUME_REQUIRED", "BLOCKED"},
    "RESUME_REQUIRED": {"RUNNING", "RESUME_REQUIRED", "BLOCKED"},
    "BLOCKED": {"INTAKE_PENDING", "PLANNED", "RUNNING", "VERIFYING", "CANCELLED"},
    "VERIFYING": {"VERIFIED", "WARN", "REJECTED", "BLOCKED"},
    "WARN": {"VERIFIED", "RUNNING", "ASK_USER", "BLOCKED"},
    "REJECTED": {"RUNNING", "CANCELLED"},
    "VERIFIED": {"ARCHIVING"},
    "ARCHIVING": {"ARCHIVED", "BLOCKED"},
    "ARCHIVED": set(),
    "CANCELLED": set(),
}


def validate_transition(source: str, target: str) -> None:
    if target not in LEGAL.get(source, set()):
        raise ValidationError(f"illegal status transition: {source} -> {target}")
```

恢复 `BLOCKED` 时必须记录 `resume_target`，避免随意跳回任意状态。

---

# 七、Artifact 与 Evidence Store

## 7.1 Artifact Store

```python
# artifact_store.py
import hashlib
from pathlib import Path

from .atomic import atomic_write_bytes, atomic_write_json
from .paths import task_dir


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_artifact(task_id: str, kind: str, content: bytes, meta: dict) -> dict:
    digest = sha256_bytes(content)
    suffix = meta.get("suffix", "bin").lstrip(".")
    rel = Path("artifacts") / f"{kind}-{digest[:16]}.{suffix}"
    target = task_dir(task_id) / rel

    if target.exists():
        if sha256_bytes(target.read_bytes()) != digest:
            raise RuntimeError("artifact path collision")
    else:
        atomic_write_bytes(target, content)

    record = {
        "path": rel.as_posix(),
        "sha256": digest,
        "bytes": len(content),
        "kind": kind,
        **{k: v for k, v in meta.items() if k != "suffix"},
    }
    atomic_write_json(target.with_suffix(target.suffix + ".meta.json"), record)
    return record
```

## 7.2 Evidence 追加

```python
# evidence_store.py
import json
import os
from pathlib import Path

from .paths import task_dir


def append_jsonl_fsync(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, data.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def append_evidence(task_id: str, event: dict) -> None:
    required = {"event_id", "task_id", "step", "type", "created_at"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"missing evidence fields: {sorted(missing)}")
    if event["task_id"] != task_id:
        raise ValueError("task id mismatch")
    append_jsonl_fsync(task_dir(task_id) / "evidence.jsonl", event)
```

## 7.3 稳定 Preview

```python
# artifact_store.py
import re

DIAGNOSTIC = re.compile(
    r"error|failed|failure|exception|traceback|panic",
    re.IGNORECASE,
)


def deterministic_preview(text: str, limit: int = 2000) -> str:
    lines = text.splitlines()
    diagnostics = [line for line in lines if DIAGNOSTIC.search(line)][:5]
    rendered = (
        "[head]\n" + text[:600] +
        "\n[diagnostics]\n" + "\n".join(diagnostics) +
        "\n[tail]\n" + text[-800:]
    )
    return rendered[:limit]
```

同一 Artifact 的 Preview 必须按 `artifact_sha256 + strategy_version` 缓存，属于**原件存在条件下的可恢复有界视图**。LLM 自由摘要属于**有损**，不得进入 Evidence 真相链。

---

# 八、PreActionGate

```python
# preaction_gate.py
from fnmatch import fnmatch
from pathlib import PurePosixPath

EXECUTABLE = {"PLANNED", "RUNNING"}


def matches(path: str, patterns: list[str]) -> bool:
    normalized = PurePosixPath(path).as_posix().lstrip("./")
    return any(fnmatch(normalized, p) for p in patterns)


def decide_action(manifest: dict, state: dict, step: dict, action: dict) -> dict:
    if state["status"] not in EXECUTABLE:
        return blocked("G0_STATUS", f"status={state['status']}")

    if action["step_id"] != state["current_step"]:
        return blocked("G2_STEP_MISMATCH", "action is not for current step")

    target = action.get("target")
    denied = manifest["scope"].get("denied_paths", [])
    allowed = step.get("allowed_paths", manifest["scope"].get("allowed_paths", []))

    if target and matches(target, denied):
        return blocked("G1_DENIED_PATH", target)
    if target and not matches(target, allowed):
        return blocked("G3_OUTSIDE_SCOPE", target)

    if action.get("external_side_effect"):
        policy = manifest["scope"].get("external_side_effects", {})
        if not policy.get("allowed", False):
            return blocked("G3_EXTERNAL_EFFECT_DENIED", target or "external")
        if not action.get("idempotency_key"):
            return blocked("G4_IDEMPOTENCY_REQUIRED", "missing idempotency key")
        if action.get("risk") == "high" and not action.get("checkpoint_id"):
            return {
                "decision": "CHECKPOINT_FIRST",
                "rule": "G4_CHECKPOINT_REQUIRED",
            }

    limits = action.get("limits", {})
    if limits.get("files", 1) > action.get("profile_max_files", 1):
        return {"decision": "NARROW", "rule": "G5_FILE_BUDGET"}

    return {
        "decision": "ALLOW",
        "rule": "ALL_GATES_PASSED",
        "state_version": state["state_version"],
        "constraints": {
            "allowed_paths": allowed,
            "denied_paths": denied,
        },
    }


def blocked(rule: str, reason: str) -> dict:
    return {"decision": "BLOCK", "rule": rule, "reason": reason}
```

生产实现必须在工具执行前再次读取最新 `state_version`，防止“审批后状态已改变”的 TOCTOU 问题。

---

# 九、VerifyGate

VerifyGate 只能验证计划中显式声明的规则。

```python
# verify_gate.py
from pathlib import Path

from .artifact_store import sha256_bytes
from .errors import EvidenceInvalid
from .paths import task_dir, repo_path


def verify_command(rule: dict, event: dict, task_id: str) -> dict:
    if event.get("type") != "command_result":
        return fail(rule, "wrong evidence type")
    if event.get("command") != rule["command"]:
        return fail(rule, "command mismatch")
    if event.get("exit_code") != rule.get("expect_exit", 0):
        return fail(rule, "exit code mismatch")

    artifact = task_dir(task_id) / event["artifact"]
    if not artifact.exists():
        raise EvidenceInvalid(f"artifact missing: {artifact}")
    if sha256_bytes(artifact.read_bytes()) != event["sha256"]:
        raise EvidenceInvalid("artifact hash mismatch")

    expected = rule.get("expect_match")
    if expected and expected not in artifact.read_text("utf-8", errors="replace"):
        return fail(rule, "expected output not found")

    return passed(rule, event["event_id"])


def verify_file(rule: dict) -> dict:
    path = repo_path(rule["path"])
    assertion = rule["assertion"]

    if assertion == "exists":
        ok = path.exists()
    elif assertion == "not_exists":
        ok = not path.exists()
    elif assertion == "contains":
        ok = rule["value"] in path.read_text("utf-8")
    else:
        return fail(rule, f"unsupported assertion: {assertion}")

    return passed(rule, None) if ok else fail(rule, "file assertion failed")


def verify_user(rule: dict, state: dict) -> dict:
    question = state.get("question") or {}
    ok = (
        question.get("id") == rule["question_id"] and
        question.get("answered_at") is not None and
        question.get("answer") == rule["expected"]
    )
    return passed(rule, None) if ok else fail(rule, "user confirmation missing")


def passed(rule: dict, event_id: str | None) -> dict:
    return {"verify_id": rule["id"], "result": "PASS", "evidence_event": event_id}


def fail(rule: dict, reason: str) -> dict:
    return {"verify_id": rule["id"], "result": "FAIL", "reason": reason}
```

聚合逻辑：

```python
def aggregate_verdict(checks: list[dict], residual_risks: list[dict]) -> str:
    if any(c["result"] == "BLOCKED" for c in checks):
        return "BLOCKED"
    if any(c["result"] == "FAIL" for c in checks):
        return "REJECTED"
    if residual_risks:
        return "WARN"
    return "VERIFIED"
```

关键事务：

```text
1. state → VERIFYING；
2. 运行/读取验证证据；
3. 写 verdict Artifact；
4. append evidence；
5. CAS 更新 step verdict；
6. 更新 plan 的机器可识别 status；
7. 全部成功后提交事务；
8. 中途失败由 transaction journal 恢复。
```

为了减少多文件半提交，推荐把 step 的权威状态只放在 `state.json`；`plan.md` 的显示状态由 state 投影生成。这样不需要同时修改两个真相源。

---

# 十、Document Index

```python
# document_index.py
from pathlib import Path
import hashlib
import yaml

from .errors import ValidationError


def parse_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text("utf-8")
    if not text.startswith("---\n"):
        raise ValidationError(f"missing front matter: {path}")
    _, header, body = text.split("---\n", 2)
    return yaml.safe_load(header), body


def build_index(root: str = "docs") -> dict:
    entries = []
    active_ids: dict[str, str] = {}

    for path in sorted(Path(root).rglob("*.md")):
        meta, body = parse_front_matter(path)
        doc_id = meta["id"]
        status = meta["status"]

        if status == "active" and doc_id in active_ids:
            raise ValidationError(
                f"duplicate active document id {doc_id}: "
                f"{active_ids[doc_id]}, {path}"
            )
        if status == "active":
            active_ids[doc_id] = path.as_posix()

        entries.append({
            "id": doc_id,
            "path": path.as_posix(),
            "type": meta["type"],
            "authority": meta["authority"],
            "status": status,
            "version": meta["version"],
            "summary": meta["summary"],
            "sections": meta.get("sections", []),
            "content_sha256": hashlib.sha256(
                path.read_bytes()
            ).hexdigest(),
        })

    return {
        "schema_version": "carros.document_index.v1",
        "entries": entries,
    }
```

`resolve_section` 必须：

```text
- 先按 ID 唯一解析 active 文档；
- 校验 authority/status/freshness；
- 按显式 section ID 定位；
- 校验正文 hash；
- 返回有界片段；
- 不因定位失败退化为全文读取。
```

---

# 十一、Context Engine 骨架

```python
# context_engine.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ContextSection:
    name: str
    text: str
    tokens: int
    priority: int
    mandatory: bool
    source: dict | None = None


@dataclass(frozen=True)
class ContextProfile:
    target: int
    soft: int
    hard: int
    partitions: dict[str, int]


def estimate_tokens(text: str) -> int:
    # MVP 保守估算；生产环境应接入模型对应 tokenizer。
    return max(1, (len(text) + 2) // 3)


def fit_sections(sections: list[ContextSection], profile: ContextProfile) -> list[ContextSection]:
    mandatory = [s for s in sections if s.mandatory]
    if sum(s.tokens for s in mandatory) > profile.hard:
        raise ValueError("mandatory context exceeds hard budget")

    result = list(mandatory)
    used = sum(s.tokens for s in result)
    optional = sorted(
        (s for s in sections if not s.mandatory),
        key=lambda s: (-s.priority, s.name),
    )
    partition_used: dict[str, int] = {}

    for section in optional:
        partition_cap = profile.partitions.get(section.name, profile.hard)
        current = partition_used.get(section.name, 0)
        if current + section.tokens > partition_cap:
            continue
        if used + section.tokens > profile.hard:
            continue
        result.append(section)
        used += section.tokens
        partition_used[section.name] = current + section.tokens

    return sorted(result, key=fixed_section_order)
```

编译入口：

```python
def compile_context(task_id: str, user_delta: str, profile_name: str) -> dict:
    manifest = load_manifest(task_id)
    state = load_state(task_id)
    plan = load_plan(task_id)
    step = resolve_current_step(state, plan)
    working_set = load_working_set(task_id)

    validate_working_set_versions(working_set, state, step)
    profile = load_context_profile(profile_name)

    sections = build_sections(
        manifest=manifest,
        state=state,
        step=step,
        working_set=working_set,
        user_delta=user_delta,
        profile=profile,
    )
    selected = fit_sections(sections, profile)
    receipt = build_receipt(task_id, state, selected, profile_name)
    capsule = render_capsule(task_id, state, step, selected, receipt)

    write_capsule_and_receipt(task_id, capsule, receipt)
    return {
        "decision": classify_watermark(capsule["estimated_tokens"], profile),
        "capsule": capsule,
        "receipt": receipt,
    }
```

禁止在此模块导入 `verify_gate` 或 `archive`。

---

# 十二、DisclosureGate

```python
# disclosure_gate.py
DENIED_PREFIXES = (
    "docs/reviews/",
    ".env",
    "secrets/",
    "transcript://",
)

LEVELS = {"D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5}


def decide_disclosure(request: dict, state: dict, working_set: dict, profile: dict) -> dict:
    if request["state_version"] != state["state_version"]:
        return {"decision": "BLOCK", "rule": "STALE_REQUEST"}

    approved, denied = [], []
    for target in request["targets"]:
        ref = target.get("ref") or target.get("path", "")
        if ref.startswith(DENIED_PREFIXES):
            denied.append({"target": target, "rule": "DENIED_SOURCE"})
            continue

        level = LEVELS[target["requested_level"]]
        maximum = LEVELS[profile["disclosure"]["gated_max_level"]]
        if level > maximum:
            return {
                "decision": "NEW_SESSION" if level == 5 else "NARROW",
                "rule": "DISCLOSURE_LEVEL_EXCEEDED",
            }

        if target["max_tokens"] > profile["limits"]["max_request_tokens"]:
            return {"decision": "NARROW", "rule": "TOKEN_REQUEST_TOO_LARGE"}
        approved.append(target)

    if denied and not approved:
        return {"decision": "BLOCK", "denied_targets": denied}
    return {
        "decision": "ALLOW",
        "approved_targets": approved,
        "denied_targets": denied,
    }
```

---

# 十三、Continuity 与 Resume

```python
# continuity.py

def classify_watermark(tokens: int, turns: int, profile: dict) -> str:
    if tokens > profile["limits"]["hard_input_tokens"]:
        return "COMPACT_NOW"
    if (
        tokens > profile["limits"]["soft_input_tokens"] or
        turns >= profile["watermark"]["soft_turns"]
    ):
        return "COMPACT_SOON"
    return "CONTINUE"
```

```python
# resume.py

def resume_task(task_id: str, profile_name: str | None = None) -> dict:
    manifest = load_manifest(task_id)
    state = load_state(task_id)
    plan = load_plan(task_id)

    validate_resume_status(state)
    step = resolve_first_non_verified_step(state, plan)
    validate_step_consistency(state, step)
    validate_verified_steps_have_verdicts(state)
    validate_required_artifacts(task_id, step)
    reconcile_external_effects_or_block(task_id)

    profile = profile_name or state["context"]["profile"]
    reconcile_working_set(task_id, state, step, profile)
    compiled = compile_context(
        task_id,
        user_delta="Resume from durable state.",
        profile_name=profile,
    )

    if compiled["decision"] == "COMPACT_NOW":
        raise ResumeBlocked("mandatory resume context exceeds safe budget")

    return update_state(
        task_id,
        state["state_version"],
        lambda value: value.update({
            "status": "RUNNING",
            "current_step": step["id"],
            "context": {
                **value["context"],
                "profile": profile,
                "decision": "RESUME_OK",
                "capsule_version": compiled["capsule"]["capsule_version"],
            },
        }),
        actor="resume-service",
        reason="durable-state-resume",
    )
```

Resume 最多恢复到 `RUNNING`，绝不能恢复到 `VERIFIED`。

---

# 十四、Archive 实现边界

```python
# archive.py

def archive_preflight(task_id: str) -> list[dict]:
    state = load_state(task_id)
    failures = []

    if state["status"] != "VERIFIED":
        failures.append({"rule": "TASK_NOT_VERIFIED"})

    for step_id, step in state["steps"].items():
        if step["status"] != "VERIFIED":
            failures.append({"rule": "STEP_NOT_VERIFIED", "step": step_id})
        if not step.get("verify_verdict_id"):
            failures.append({"rule": "VERDICT_MISSING", "step": step_id})

    failures.extend(validate_all_verdict_artifacts(task_id, state))
    failures.extend(validate_memory_writeback(task_id))
    failures.extend(validate_no_unresolved_question_or_blocker(state))
    return failures
```

Archive 必须通过 preflight 后执行：

```text
VERIFIED
  → ARCHIVING
  → 构建 staging archive
  → 校验 hash/index/report
  → 原子发布 archive
  → 写 tombstone
  → ARCHIVED
```

完整归档实现与迁移清单在第 8/8 收口。

---

# 十五、JSON Schema 示例

## 15.1 `task-state.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "carros.task_state.v1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "task_id",
    "level",
    "status",
    "state_version",
    "manifest_version",
    "plan_version",
    "current_step",
    "steps",
    "context",
    "verification",
    "timestamps"
  ],
  "properties": {
    "schema_version": {"const": "carros.task_state.v1"},
    "task_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"},
    "level": {"enum": ["L1", "L2"]},
    "status": {
      "enum": [
        "DRAFT", "INTAKE_PENDING", "ASK_USER", "READY", "PLANNED",
        "RUNNING", "COMPACT_SOON", "RESUME_REQUIRED", "BLOCKED",
        "VERIFYING", "WARN", "VERIFIED", "REJECTED", "ARCHIVING",
        "ARCHIVED", "CANCELLED"
      ]
    },
    "state_version": {"type": "integer", "minimum": 1},
    "manifest_version": {"type": "integer", "minimum": 1},
    "plan_version": {"type": "integer", "minimum": 1},
    "current_step": {"type": ["string", "null"]},
    "steps": {"type": "object"},
    "blocker": {"type": ["object", "null"]},
    "question": {"type": ["object", "null"]},
    "context": {"type": "object"},
    "verification": {"type": "object"},
    "timestamps": {"type": "object"}
  }
}
```

## 15.2 Evidence Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "carros.evidence.v1",
  "type": "object",
  "required": [
    "schema_version", "event_id", "task_id", "step",
    "type", "state_version", "created_at"
  ],
  "properties": {
    "schema_version": {"const": "carros.evidence.v1"},
    "event_id": {"type": "string"},
    "task_id": {"type": "string"},
    "step": {"type": "string"},
    "action": {"type": ["string", "null"]},
    "type": {
      "enum": [
        "file_change", "command_result", "user_confirmation",
        "checkpoint", "verify_verdict", "external_effect"
      ]
    },
    "artifact": {"type": "string"},
    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "state_version": {"type": "integer"},
    "created_at": {"type": "string", "format": "date-time"}
  }
}
```

Schema 只验证结构；跨字段不变量仍由领域代码检查，例如：

```text
- VERIFIED step 必须有 verdict_id；
- command_result 必须有 exit_code、Artifact 和 hash；
- user_confirmation 必须关联 question_id；
- external_effect 必须有 execution_id 和 reconciliation 状态。
```

---

# 十六、CLI 单入口

## 16.1 `carros_base.py`

```python
#!/usr/bin/env python3
from carros.cli import main

if __name__ == "__main__":
    raise SystemExit(main(default_level="L1"))
```

## 16.2 `carros_enhance.py`

```python
#!/usr/bin/env python3
from carros.cli import main

if __name__ == "__main__":
    raise SystemExit(main(default_level="L2"))
```

## 16.3 命令树

```text
carros_base.py
├── init
├── intake
├── plan
├── status
├── lint
├── tick
├── gate
├── artifact
│   └── record
├── evidence
│   └── list
├── verify
│   ├── step
│   └── task
├── context
│   ├── compile
│   ├── validate
│   ├── request
│   ├── receipt
│   ├── budget
│   ├── handoff
│   └── compact-check
├── checkpoint
│   ├── create
│   └── validate
├── resume
│   └── preflight
├── effects
│   └── reconcile
└── archive
```

## 16.4 统一输出

```json
{
  "ok": true,
  "command": "gate",
  "task_id": "fix-auth-001",
  "result": {
    "decision": "ALLOW",
    "state_version": 7
  }
}
```

`--human` 可输出适合终端的短视图，但 JSON 是自动化契约。

CLI 禁止输出：

```text
- chain-of-thought；
- 完整 secrets；
- 未脱敏 Artifact 正文；
- SQLite 全 transcript；
- “系统认为已完成”而无 verdict_id；
- 将 WARN 渲染成成功。
```

---

# 十七、Claude Code Hook 单入口

## 17.1 Hook 职责

`pretool_gate.py` 只做：

```text
1. 读取平台传入的工具调用；
2. 映射为 CarrorOS Action Proposal；
3. 调用 PreActionGate；
4. 返回 allow/deny；
5. 记录 audit。
```

不做：

```text
✗ 执行业务命令；
✗ 修改 task step；
✗ 标记 VERIFIED；
✗ 在 Hook 内调用 LLM；
✗ 自行生成 scope。
```

## 17.2 Hook 骨架

```python
#!/usr/bin/env python3
# .claude/hooks/pretool_gate.py
import json
import os
import sys

from carros.preaction_gate import decide_action
from carros.task_store import load_manifest, load_state
from carros.plan_builder import load_current_step


def deny(reason: str, rule: str = "HOOK_FAILURE") -> int:
    print(json.dumps({
        "decision": "deny",
        "reason": reason,
        "rule": rule,
    }))
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        task_id = os.environ.get("CARROS_TASK_ID")
        if not task_id:
            return deny("CARROS_TASK_ID is required")

        manifest = load_manifest(task_id)
        state = load_state(task_id)
        step = load_current_step(task_id, state)
        action = map_tool_call(payload, state)
        verdict = decide_action(manifest, state, step, action)

        if verdict["decision"] == "ALLOW":
            print(json.dumps({"decision": "allow", "verdict": verdict}))
            return 0
        return deny(verdict.get("reason", verdict["decision"]), verdict.get("rule", "GATE"))
    except Exception as exc:
        if os.environ.get("CARROS_FAIL_CLOSED", "1") == "1":
            return deny(f"CarrorOS gate failure: {type(exc).__name__}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
```

平台不同版本的 Hook 输入/返回字段可能变化，因此：

```text
- `map_tool_call` 和输出编码放在 `platform/claude_code.py`；
- 安装时运行 capability probe；
- probe 失败则不宣称 Hook 已启用；
- 高风险操作继续要求显式 `carros gate`；
- 不硬编码未经验证的平台事件 Schema。
```

## 17.3 `.claude/settings.json` 示例

下面是 CarrorOS 建议模板；Hook 事件字段应在安装时适配实际 Claude Code 版本：

```json
{
  "env": {
    "CARROS_TASK_ID": "",
    "CARROS_FAIL_CLOSED": "1",
    "CARROS_CONTEXT_CONFIG": ".omc/context-engine.yaml",
    "CARROS_REQUIRE_DISCLOSURE_RECEIPT": "1"
  },
  "permissions": {
    "defaultMode": "default"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/pretool_gate.py"
          }
        ]
      }
    ]
  }
}
```

如果部署版本不支持该结构，应由安装器生成对应格式，而不是手工猜测。

---

# 十八、OpenCode 包装器与插件接口

OpenCode 路径采用独立适配器，不复用 Claude Hook Schema。

## 18.1 适配接口

```typescript
export interface CarrorActionProposal {
  taskId: string;
  stateVersion: number;
  sessionId: string;
  sessionRole: "execute" | "retrieve" | "review" | "govern";
  tool: string;
  target?: string;
  command?: string;
  externalSideEffect: boolean;
}

export interface CarrorGateVerdict {
  decision: "ALLOW" | "NARROW" | "CHECKPOINT_FIRST" | "ASK_USER" | "BLOCK";
  rule: string;
  reason?: string;
  stateVersion: number;
}
```

## 18.2 单一 Writer

```typescript
export function assertWriter(role: string, mutatesState: boolean): void {
  if (mutatesState && role !== "execute") {
    throw new Error("ONLY_EXECUTE_SESSION_CAN_WRITE_STATE");
  }
}
```

## 18.3 事件处理

```typescript
async function beforeTool(input: CarrorActionProposal): Promise<CarrorGateVerdict> {
  assertWriter(input.sessionRole, isStateMutatingTool(input.tool));

  const response = await execa("python3", [
    ".claude/scripts/carros_base.py",
    "gate",
    "--task-id", input.taskId,
    "--proposal-json", JSON.stringify(input),
    "--json"
  ]);

  return JSON.parse(response.stdout).result;
}
```

OpenCode 侧额外要求：

```text
- SQLite 仅用于会话审计；
- prune 前确认工具结果已 Artifact 化；
- hidden 消息不得被包装器重新注入 Capsule；
- retrieve/review 会话只写 Artifact/Proposal，不写 state；
- execute session writer lease 冲突时 fail closed；
-有损摘要必须带 `lossy=true, authoritative=false`。
```

## 18.4 CarrorOS 包装器配置

```json
{
  "carros": {
    "command": "python3 .claude/scripts/carros_base.py",
    "failClosed": true,
    "stateWriterRole": "execute",
    "sessionRoles": {
      "execute": {"stateWrite": true},
      "retrieve": {"stateWrite": false},
      "review": {"stateWrite": false},
      "govern": {"stateWrite": false}
    },
    "context": {
      "rebuildEachTurn": true,
      "includeTranscript": false
    },
    "prune": {
      "beforeSummary": true,
      "nonDestructive": true,
      "preserveRecentTurns": 2,
      "preserveSkillOutputs": true
    },
    "summary": {
      "authoritative": false
    }
  }
}
```

---

# 十九、模型 Profile 与路由接口

模型路由不能绕过 Context 与验证协议。

```python
# models.py
from dataclasses import dataclass

@dataclass(frozen=True)
class RouteDecision:
    profile: str
    reason: str
    isolated_session: bool
    max_disclosure: str


def route_action(action: dict, risk: dict) -> RouteDecision:
    if action["kind"] in {"search", "atomic_edit", "targeted_test"} and risk["level"] != "high":
        return RouteDecision(
            profile="deepseek-v4-flash",
            reason="narrow deterministic action",
            isolated_session=False,
            max_disclosure="D3",
        )

    return RouteDecision(
        profile="opus-4.8",
        reason="cross-module reasoning or high-risk review",
        isolated_session=True,
        max_disclosure="D5",
    )
```

详细路由、Oracle、多 Agent、成本治理放在第 7/8。

---

# 二十、审计与指标

所有治理动作必须写结构化事件：

```json
{
  "schema_version": "carros.audit_event.v1",
  "event_id": "AU-104",
  "task_id": "fix-auth-001",
  "type": "PREACTION_VERDICT",
  "actor": "claude-code/session-abc",
  "state_version": 7,
  "decision": "BLOCK",
  "rule": "G1_DENIED_PATH",
  "target": ".env",
  "created_at": "2026-07-12T10:00:00Z"
}
```

最低指标：

```text
state_conflict_rate
illegal_transition_count
preaction_block_rate_by_rule
hook_fail_closed_count
artifact_before_preview_rate
artifact_hash_mismatch_count
verify_pass_rate_first_attempt
verified_without_verdict_count
resume_without_transcript_success_rate
context_tokens_per_turn
prompt_cache_hit_rate                 # Claude Code
prune_before_summary_rate             # OpenCode
multi_session_writer_conflict_count    # OpenCode
token_$/session
token_$/verified_step
```

不可观测字段不能成为强治理承诺。例如平台无法提供真实 cache hit 指标时，应记录：

```text
cache_metric_availability = unavailable
```

不得用估算值冒充 provider 真实命中率。

---

# 二十一、最小可运行配置

## 21.1 `pyproject.toml`

```toml
[project]
name = "carros-governance"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "jsonschema>=4.22,<5",
  "PyYAML>=6.0,<7",
  "portalocker>=2.8,<4"
]

[project.optional-dependencies]
test = [
  "pytest>=8,<9",
  "pytest-cov>=5,<7"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.coverage.run]
branch = true
source = [".claude/scripts/carros"]
```

## 21.2 安装与测试

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'

python -m pytest tests/unit
python -m pytest tests/integration
python -m pytest tests/conformance
python -m pytest --cov=.claude/scripts/carros --cov-report=term-missing
```

## 21.3 静态检查建议

```bash
python -m ruff check .claude/scripts tests
python -m mypy .claude/scripts/carros
python -m json.tool schemas/task-state.schema.json >/dev/null
python3 .claude/scripts/carros_base.py docs lint --json
```

---

# 二十二、测试目录

```text
tests/
├── fixtures/
│   ├── task-running/
│   ├── task-verified/
│   ├── task-corrupt-artifact/
│   ├── stale-handoff/
│   └── duplicate-doc-id/
├── unit/
│   ├── test_state_machine.py
│   ├── test_task_store.py
│   ├── test_preaction_gate.py
│   ├── test_artifact_store.py
│   ├── test_verify_gate.py
│   ├── test_document_index.py
│   ├── test_context_engine.py
│   └── test_resume.py
├── integration/
│   ├── test_l1_lifecycle.py
│   ├── test_compact_resume.py
│   ├── test_claude_hook.py
│   └── test_opencode_sessions.py
└── conformance/
    ├── test_no_verify_bypass.py
    ├── test_no_transcript_resume.py
    ├── test_review_isolation.py
    └── test_context_non_linear_growth.py
```

## 22.1 关键测试示例

```python
def test_denied_path_wins(manifest, state, step):
    manifest["scope"]["allowed_paths"].append(".env")
    manifest["scope"]["denied_paths"].append(".env")
    verdict = decide_action(manifest, state, step, {
        "step_id": state["current_step"],
        "target": ".env",
    })
    assert verdict["decision"] == "BLOCK"
    assert verdict["rule"] == "G1_DENIED_PATH"


def test_context_engine_cannot_verify():
    import carros.context_engine as module
    assert not hasattr(module, "verify_step")
    assert not hasattr(module, "mark_verified")


def test_archive_requires_verdict(task_running):
    failures = archive_preflight(task_running)
    assert any(item["rule"] == "TASK_NOT_VERIFIED" for item in failures)


def test_state_compare_and_swap(task_running):
    state = load_state(task_running)
    update_state(task_running, state["state_version"], lambda s: None,
                 actor="test", reason="first")
    with pytest.raises(StateConflict):
        update_state(task_running, state["state_version"], lambda s: None,
                     actor="test", reason="stale")
```

---

# 二十三、端到端 L1 示例

```bash
TASK=fix-auth-001

python3 .claude/scripts/carros_base.py init \
  --task-id "$TASK" \
  --manifest request.yaml \
  --json

python3 .claude/scripts/carros_base.py intake \
  --task-id "$TASK" \
  --json

python3 .claude/scripts/carros_base.py plan \
  --task-id "$TASK" \
  --json

python3 .claude/scripts/carros_base.py context compile \
  --task-id "$TASK" \
  --profile deepseek-v4-flash \
  --json

python3 .claude/scripts/carros_base.py gate \
  --task-id "$TASK" \
  --proposal-file action.json \
  --json

# Gate ALLOW 后执行一个 action；完整结果落盘。
python3 .claude/scripts/carros_base.py artifact record \
  --task-id "$TASK" \
  --step S2 \
  --action A1 \
  --kind command_result \
  --input /tmp/test.log \
  --exit-code 0 \
  --json

python3 .claude/scripts/carros_base.py verify step \
  --task-id "$TASK" \
  --step S2 \
  --json

python3 .claude/scripts/carros_base.py archive \
  --task-id "$TASK" \
  --json
```

任何命令失败时，自动化必须检查 `ok=false` 与退出码，不能只搜索 stdout 中的自然语言。

---

# 二十四、L2 扩展方式

`carros_enhance.py` 不复制 L1 代码，只注册增强服务：

```text
research
oracle
multi-judge
knowledge-patch
error-dna
roi
```

结构：

```python
def main(default_level="L2"):
    parser = build_common_parser()
    register_enhance_commands(parser)
    return dispatch(parser.parse_args(), default_level=default_level)
```

L2 扩展硬规则：

```text
- Research Agent 只产 Knowledge Patch；
- Oracle 只产 Review Verdict；
- Meta-Oracle 只聚合已有 verdict；
- 子 Agent 不直接写 state；
- 基础 command/file/user VerifyGate 仍必须通过；
- Oracle ACCEPT 不映射为任务 VERIFIED；
- 所有增强能力都可关闭并降回 L1 Base。
```

---

# 二十五、安全实现要求

## 25.1 命令执行

```text
- 默认使用 argv 数组，不使用 shell=True；
- 命令必须来自 plan 中的 verify 规则或已批准 action；
- 环境变量使用 allowlist；
- stdout/stderr 先脱敏再生成 Preview；
- 原始 Artifact 的访问权限默认 0600；
- shell 命令中的路径必须经过仓库边界检查；
- 超时、退出码和 signal 都写 Evidence。
```

## 25.2 Secret 处理

```text
- Secret 不进入 Capsule、Handoff、Audit、Preview；
- Artifact 若不可避免含 Secret，必须加密或隔离存储；
- Review 文档不能保存真实凭据；
- 日志脱敏规则本身版本化；
- 脱敏后 Preview 与原 Artifact 使用不同 hash。
```

## 25.3 Symlink 与路径逃逸

```text
- `resolve()` 后检查仍在 repo root；
- 写入前拒绝危险 symlink；
- glob 匹配基于规范化 POSIX 相对路径；
- denied 规则在 resolve 前后各检查一次；
- Archive 不跟随指向仓库外的 symlink。
```

---

# 二十六、MCP 配置边界

MCP 工具必须通过同一 PreActionGate，不形成旁路。

CarrorOS 层配置：

```yaml
# .omc/mcp-policy.yaml
schema_version: carros.mcp_policy.v1

servers:
  filesystem:
    enabled: true
    allowed_roots:
      - .
    require_preaction_gate: true

  database:
    enabled: false
    external_side_effect: true
    require_user_confirmation: true
    require_checkpoint: true

  web:
    enabled: true
    read_only: true
    require_artifact_capture: true

policy:
  deny_unknown_server: true
  deny_unknown_tool: true
  record_tool_schema_hash: true
  expose_only_required_tools: true
```

Claude Code：只启用当前 step 需要的 MCP，避免工具 Schema 扩大稳定前缀。

OpenCode：provider/MCP 可插拔，但审计、Artifact 与单一 State Writer 规则不变。

---

# 二十七、实现阶段与验收门

## Phase 0：存储内核

```text
实现：paths、atomic、task_store、state_machine、audit
验收：CAS、非法转换、路径逃逸、原子写入测试通过
```

## Phase 1：执行证据链

```text
实现：preaction_gate、artifact_store、evidence_store
验收：denied 优先；长输出不入 Context；hash 可验证
```

## Phase 2：完成门

```text
实现：verify_gate、verdict Artifact、archive preflight
验收：无 evidence 永不 VERIFIED；Oracle 无法旁路
```

## Phase 3：Memory 与 Context

```text
实现：document_index、working-set、context_engine、receipt
验收：Review 默认隔离；第 30 轮 Context 不线性增长
```

## Phase 4：连续性

```text
实现：checkpoint、handoff、resume、effect reconciliation
验收：删除 transcript 仍可恢复；非幂等 action 不重放
```

## Phase 5：双平台接入

```text
实现：Claude Hook adapter、OpenCode wrapper/session lease
验收：Hook 失败 fail closed；OpenCode 只有 execute 可写 state
```

---

# 二十八、本部分验收矩阵

| ID | 验收项 | 通过标准 |
|---|---|---|
| I-01 | CAS | stale writer 无法覆盖 state |
| I-02 | 状态机 | 非法转换全部拒绝 |
| I-03 | Scope | denied 永远优先于 allowed |
| I-04 | Artifact | 完整结果落盘且 hash 可验证 |
| I-05 | Preview | 同一 Artifact 字节稳定 |
| I-06 | Verify | 无 verdict_id 的 step 不能 VERIFIED |
| I-07 | Context | 不导入完成裁决能力 |
| I-08 | Resume | 最多恢复到 RUNNING |
| I-09 | Archive | 非 VERIFIED 任务不能归档 |
| I-10 | Claude Hook | 失败时拒绝高风险工具 |
| I-11 | OpenCode | 非 execute 会话不能写状态 |
| I-12 | Review | 默认不能进入执行 Capsule |
| I-13 | Secret | 不进入 Handoff/Preview/Audit |
| I-14 | 外部副作用 | UNKNOWN 时禁止重放 |
| I-15 | 成本 | 第 30 轮输入不线性增长 |

---

# 二十九、本部分最终裁决

```text
1. CarrorOS 使用一个领域内核，两套平台适配器；
2. CLI 只路由，Hook 只拦截，平台适配器不制造治理事实；
3. state 写入必须 CAS、原子落盘并记录 audit；
4. 多文件完成事务优先减少真相源数量，再用事务日志补强；
5. denied 优先，路径解析失败和 Hook 失败均 fail closed；
6. 工具完整输出进入 Artifact，Evidence 只存结构化索引；
7. Preview 必须确定性并按 hash 复用，保护 Claude Prompt Cache；
8. VerifyGate 只验证计划声明的 command/file/user 规则；
9. Context Engine 不得依赖 VerifyGate，也不得输出 VERIFIED；
10. Resume 最多恢复到 RUNNING，必须重编译 Capsule 并重跑 Gate；
11. Claude Code 使用独立 Hook adapter，不把版本相关 Schema 写死在领域层；
12. OpenCode 使用 wrapper/plugin 和单一 execute writer，不把 SQLite 当任务状态源；
13. 所有外部副作用必须带 execution ID、幂等或补偿协议；
14. L2 只扩展 Research/Oracle/协同，不复制或绕过 L1 内核；
15. MVP 应按存储→证据→验证→Context→恢复→平台接入的顺序实施。
```

---

# 下一部分：第 7/8 部分

将完整输出 **模型路由、多 Agent、Oracle、成本与审计治理**：

```text
- DeepSeek V4 Flash 原子执行轨
- Opus 4.8 高阶推理与审查轨
- Claude Code subagent 隔离
- OpenCode 多会话隔离
- 单一 State Writer 与 Knowledge Patch
- Research / Oracle / Multi-Judge / Meta-Oracle
- Oracle 与 VerifyGate 的严格边界
- 模型容灾、熔断与 Fallback
- token、cache、compaction、$/session 指标
- 成本归因与预算闸门
- 隐私、SQLite 审计、Artifact 保留
- 可粘贴路由与治理配置
- 多 Agent 并发和故障测试
```
