#!/usr/bin/env python3
"""
carros_oracle_base.py — Oracle LLM 审核共享基类 (v2, hardened).

GPT-5.5 审查后强化项：
- S1: curl subprocess → httpx 原生 HTTP 客户端
- S2: 严格 JSON Schema + Pydantic 验证，fail-close
- S3: 证据本地验证器（file:line 存在性校验）
- S7: 原子写入（tmp+fsync+rename）
- S8: 线程安全熔断器（互斥锁）

Usage:
    from carros_oracle_base import (
        Finding, OracleReview, Evidence, Severity, RiskType,
        call_llm_oracle, audit_log, write_oracle_verdict,
        validate_evidence_local, verify_file_line,
        parse_llm_json_output_strict,
        LLM_UNAVAILABLE, CIRCUIT_OPEN,
        RiskPolicy, resolve_risk_policy,
        PROXY_ENDPOINT
    )
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import fcntl
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Optional
import traceback

import httpx

from httpx import HTTPTransport

# ── 常量 ──
PROXY_ENDPOINT = os.environ.get("ORACLE_LLM_ENDPOINT", "http://127.0.0.1:9998/v1/chat/completions")
PROXY_MODEL = os.environ.get("ORACLE_LLM_MODEL", "deepseek-chat")
PROXY_TIMEOUT = int(os.environ.get("ORACLE_LLM_TIMEOUT", "30"))
PROXY_API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "test")
AUDIT_DIR = Path(".omc/state/oracle-audit")
VERDICT_DIR = Path(".omc/state/model-oracle-verdicts")

# ── 熔断器状态 ──
CIRCUIT_CLOSED = "closed"
CIRCUIT_OPEN = "open"
CIRCUIT_HALF_OPEN = "half_open"

# ── 可用性状态 ──
LLM_AVAILABLE = "available"
LLM_UNAVAILABLE = "unavailable"
LLM_DEGRADED = "degraded"


# ═══════════════════════════════════════════════
# 结构化证据模型
# ═══════════════════════════════════════════════

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskType(str, Enum):
    DESTRUCTIVE_COMMAND = "destructive_command"
    SENSITIVE_PATH = "sensitive_path"
    FILE_LINE_MISMATCH = "file_line_mismatch"
    SCOPE_VIOLATION = "scope_violation"
    SILENT_FAILURE = "silent_failure"
    SOFT_COMPLETION = "soft_completion"
    TOKEN_PROGRESS_MISMATCH = "token_progress_mismatch"
    INCOMPLETE_EXECUTION = "incomplete_execution"
    EVIDENCE_MISSING = "evidence_missing"
    PROMPT_INJECTION = "prompt_injection"
    GOVERNANCE_VIOLATION = "governance_violation"
    UNKNOWN = "unknown"


@dataclass
class Evidence:
    """单条证据"""
    type: str  # file_line | log_span | command | diff | token_trace
    location: str  # xxx.py:120
    content: str  # 证据原文（摘要）
    hash: str = ""  # content 的 sha256

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class Finding:
    """审核发现"""
    oracle: str  # model_static | model_runtime
    severity: Severity
    confidence: float  # 0.0 ~ 1.0
    risk_type: RiskType
    evidence: list[Evidence] = field(default_factory=list)
    reason: str = ""
    recommendation: str = ""
    verified: bool = False  # evidence 是否经过本地验证

    def to_dict(self) -> dict[str, Any]:
        return {
            "oracle": self.oracle,
            "severity": self.severity.value,
            "confidence": round(self.confidence, 2),
            "risk_type": self.risk_type.value,
            "evidence": [asdict(e) for e in self.evidence],
            "reason": self.reason,
            "recommendation": self.recommendation,
            "verified": self.verified,
        }


@dataclass
class OracleReview:
    """Oracle 审核结果"""
    decision: str  # allow | block | review | degraded_allow | degraded_block
    verdict: str  # ACCEPT | REJECT | ADVISORY | ESCALATE | DEGRADED
    risk: str  # LOW | MEDIUM | HIGH | CRITICAL
    score: float
    findings: list[Finding] = field(default_factory=list)
    degraded: bool = False
    degraded_reason: str = ""
    missing_oracles: list[str] = field(default_factory=list)
    fallback_oracles: list[str] = field(default_factory=list)
    raw_output: str = ""
    model: str = ""
    prompt_version: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "verdict": self.verdict,
            "risk": self.risk,
            "score": round(self.score, 2),
            "findings": [f.to_dict() for f in self.findings],
            "degraded": self.degraded,
            "degraded_reason": self.degraded_reason,
            "missing_oracles": self.missing_oracles,
            "fallback_oracles": self.fallback_oracles,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "duration_ms": self.duration_ms,
        }


# ═══════════════════════════════════════════════
# Pydantic Schema — 严格 LLM 输出验证 (S2)
# ═══════════════════════════════════════════════

try:
    from pydantic import BaseModel, Field, field_validator

    class EvidenceSchema(BaseModel):
        type: str = Field(default="file_line", pattern=r"^(file_line|log_span|command|diff|token_trace|text)$")
        location: str = Field(default="")
        content: str = Field(default="", max_length=2000)

        @field_validator("location")
        @classmethod
        def location_pattern(cls, v: str) -> str:
            if v and not re.match(r"^[\w\-./\\:]+$", v):
                raise ValueError(f"Invalid location format: {v}")
            return v

    class FindingSchema(BaseModel):
        severity: str = Field(default="low", pattern=r"^(critical|high|medium|low|info)$")
        confidence: float = Field(default=0.5, ge=0.0, le=1.0)
        risk_type: str = Field(default="unknown", pattern=r"^[a-z_]+$")
        evidence: list[EvidenceSchema] = Field(default_factory=list)
        reason: str = Field(default="", max_length=1000)
        recommendation: str = Field(default="", max_length=1000)

    class OracleOutputSchema(BaseModel):
        decision: str = Field(default="review", pattern=r"^(allow|block|review)$")
        severity: str = Field(default="low", pattern=r"^(critical|high|medium|low)$")
        confidence: float = Field(default=0.5, ge=0.0, le=1.0)
        score: float = Field(default=5.0, ge=0.0, le=10.0)
        findings: list[FindingSchema] = Field(default_factory=list)

    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False


# ═══════════════════════════════════════════════
# 严格 JSON 解析 — fail-close (S2)
# ═══════════════════════════════════════════════

def parse_llm_json_output_strict(raw: str) -> dict[str, Any] | None:
    """
    严格解析 LLM JSON 输出。

    要求：
    - 必须是顶层 JSON 对象（{}）
    - 只能有一个 JSON 对象，禁止额外非空白字符
    - 通过 Pydantic Schema 验证（仅 Pydantic 可用时）
    - 失败返回 None（fail-close）
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # 尝试提取 ```json ``` 块中的内容
    json_text = None
    if text.startswith("```json"):
        # ```json ... ```
        end_idx = text.find("```", 7)
        if end_idx > 7:
            candidate = text[7:end_idx].strip()
            # 确保提取后剩余的部分只有空白
            remainder = text[end_idx + 3:].strip()
            if not remainder:
                json_text = candidate
    elif text.startswith("```"):
        # generic ``` ... ```
        end_idx = text.find("```", 3)
        if end_idx > 3:
            candidate = text[3:end_idx].strip()
            remainder = text[end_idx + 3:].strip()
            if not remainder and (candidate.startswith("{") or candidate.startswith("[")):
                json_text = candidate

    # 如果是裸 JSON
    if json_text is None and (text.startswith("{") and text.endswith("}")):
        # 检查是否只有单一顶层 JSON 对象（没有额外非空白文字）
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                json_text = text
        except json.JSONDecodeError:
            pass

    if json_text is None:
        return None  # fail-close: 非标准格式

    # JSON 解析
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    # Pydantic Schema 验证（宽松模式：转换 findings 中 string list 为 object list）
    if _PYDANTIC_AVAILABLE:
        try:
            validated = OracleOutputSchema(**parsed)
            return validated.model_dump()
        except Exception:
            # Pydantic 失败时尝试修复常见问题
            # 1. findings 是 string list 而不是 object list
            fixed = dict(parsed)
            raw_findings = fixed.get("findings", [])
            if raw_findings and isinstance(raw_findings, list) and all(isinstance(f, str) for f in raw_findings):
                # 转 string → object
                fixed["findings"] = [
                    {
                        "severity": "medium",
                        "confidence": 0.7,
                        "risk_type": "unknown",
                        "reason": f,
                        "evidence": [],
                        "recommendation": "",
                    }
                    for f in raw_findings
                ]
                try:
                    validated = OracleOutputSchema(**fixed)
                    return validated.model_dump()
                except Exception:
                    pass
            return None  # fail-close: schema 不通过
    else:
        # Pydantic 不可用时做轻量校验
        if "decision" not in parsed or parsed.get("decision") not in ("allow", "block", "review"):
            return None
        score = parsed.get("score", 5.0)
        if not isinstance(score, (int, float)) or score < 0.0 or score > 10.0:
            return None
        return parsed


# ═══════════════════════════════════════════════
# 证据本地验证器 (S3)
# ═══════════════════════════════════════════════

def verify_file_line(location: str) -> tuple[bool, str]:
    """
    本地验证 file:line 引用是否真实存在。

    Args:
        location: 格式 "path:line" 或 "path"

    Returns:
        (is_valid: bool, detail: str)
    """
    if not location or ":" not in location:
        return False, f"invalid_format: no line number in '{location}'"

    # 分离路径和行号
    # 支持 Unix/MacOS/Windows 路径
    # 如果有多于一个 :，最后一个冒号后的是行号
    parts = location.rsplit(":", 1)
    filepath = parts[0]
    line_str = parts[1]

    # 验证行号是数字
    if not line_str.isdigit():
        return False, f"invalid_line: '{line_str}' is not a number"

    line_no = int(line_str)

    # 规范化路径
    path = Path(filepath)
    if not path.exists():
        # 尝试相对 CWD
        path = Path.cwd() / filepath
        if not path.exists():
            return False, f"file_not_found: '{filepath}'"

    # 读文件验证行号
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            total_lines = sum(1 for _ in f)
        if line_no < 1 or line_no > total_lines:
            return False, f"line_out_of_range: {line_no} / total {total_lines}"
        return True, f"valid: '{filepath}:{line_no}' ({total_lines} lines)"
    except (OSError, PermissionError) as e:
        return False, f"read_error: {e}"


def validate_evidence_local(finding: Finding) -> Finding:
    """
    对 finding 中的每条 file_line 证据做本地验证。
    修改 finding.verified 字段，标记不可验证的证据。
    """
    if not finding.evidence:
        finding.verified = False
        return finding

    all_verified = True
    for ev in finding.evidence:
        if ev.type == "file_line" and ev.location:
            valid, detail = verify_file_line(ev.location)
            if not valid:
                all_verified = False
                # 追加验证失败信息到 evidence content
                ev.content = f"[UNVERIFIED: {detail}] {ev.content}"

    finding.verified = all_verified
    return finding


def downgrade_unverified_findings(findings: list[Finding]) -> list[Finding]:
    """
    对未经验证的 high/critical finding 降级一级。
    """
    result = []
    for f in findings:
        if not f.verified and f.severity in (Severity.CRITICAL, Severity.HIGH):
            if f.severity == Severity.CRITICAL:
                f.severity = Severity.HIGH
            elif f.severity == Severity.HIGH:
                f.severity = Severity.MEDIUM
            f.reason += " [downgraded: unverified evidence]"
        result.append(f)
    return result


# ═══════════════════════════════════════════════
# 策略路由
# ═══════════════════════════════════════════════

class RiskPolicy(str, Enum):
    SECURITY_STRICT = "security_strict"
    RUNTIME_STRICT = "runtime_strict"
    FAST_PATH = "fast_path"
    BALANCED = "balanced"


def resolve_risk_policy(task: dict[str, Any]) -> RiskPolicy:
    description = (task.get("description") or "").lower()
    steps = task.get("steps", [])
    step_text = " ".join(s.get("id", "") + " " + s.get("description", "") for s in steps)
    combined = description + " " + step_text

    shell_keywords = ["rm ", "sudo ", "chmod ", "chown ", "mkfs", "dd ", "deploy ", "publish ",
                      "npm publish", "pip upload", "git push", "docker ", "kubectl "]
    if any(kw in combined for kw in shell_keywords):
        return RiskPolicy.SECURITY_STRICT

    if any(p in combined for p in [".ssh", ".env", "credential", "secret", "/etc/"]):
        return RiskPolicy.SECURITY_STRICT

    if len(steps) > 5 or "agent" in combined or "delegate" in combined:
        return RiskPolicy.RUNTIME_STRICT

    read_keywords = ["read", "query", "search", "inspect", "list", "show", "doc", "report"]
    if any(kw in combined for kw in read_keywords) and len(steps) <= 2:
        return RiskPolicy.FAST_PATH

    return RiskPolicy.BALANCED


def policy_to_gate_config(policy: RiskPolicy) -> dict[str, Any]:
    configs = {
        RiskPolicy.SECURITY_STRICT: {
            "llm_required": True,
            "llm_timeout": 60,
            "static_fallback": False,
            "critical_block": True,
            "min_oracles": 2,
        },
        RiskPolicy.RUNTIME_STRICT: {
            "llm_required": True,
            "llm_timeout": 60,
            "static_fallback": True,
            "critical_block": True,
            "min_oracles": 1,
        },
        RiskPolicy.FAST_PATH: {
            "llm_required": False,
            "llm_timeout": 15,
            "static_fallback": True,
            "critical_block": False,
            "min_oracles": 0,
        },
        RiskPolicy.BALANCED: {
            "llm_required": False,
            "llm_timeout": 30,
            "static_fallback": True,
            "critical_block": True,
            "min_oracles": 1,
        },
    }
    return configs.get(policy, configs[RiskPolicy.BALANCED])


# ═══════════════════════════════════════════════
# 线程安全熔断器 (S8)
# ═══════════════════════════════════════════════

class CircuitBreaker:
    """线程安全熔断器"""

    def __init__(self, name: str = "llm_oracle", failure_threshold: int = 3,
                 recovery_timeout: int = 60, half_open_max: int = 1):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._lock = Lock()
        self.state = CIRCUIT_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_attempts = 0

    def record_success(self):
        with self._lock:
            self.state = CIRCUIT_CLOSED
            self.failure_count = 0
            self.half_open_attempts = 0

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CIRCUIT_OPEN
                self.half_open_attempts = 0

    def allow_request(self) -> bool:
        with self._lock:
            return self._allow_request_unsafe()

    def _allow_request_unsafe(self) -> bool:
        if self.state == CIRCUIT_CLOSED:
            return True
        if self.state == CIRCUIT_OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CIRCUIT_HALF_OPEN
                self.half_open_attempts = 0
                return True
            return False
        if self.half_open_attempts < self.half_open_max:
            self.half_open_attempts += 1
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
            }


# 全局熔断器
_PROXY_CIRCUIT = CircuitBreaker("llm_proxy_9998")


# ═══════════════════════════════════════════════
# LLM 调用 — httpx (S1)
# ═══════════════════════════════════════════════

# httpx 客户端（懒加载）
_HTTPX_CLIENT: httpx.Client | None = None
_HTTPX_CLIENT_LOCK = Lock()


def _get_httpx_client() -> httpx.Client:
    global _HTTPX_CLIENT
    if _HTTPX_CLIENT is None:
        with _HTTPX_CLIENT_LOCK:
            if _HTTPX_CLIENT is None:
                _HTTPX_CLIENT = httpx.Client(
                    transport=HTTPTransport(http2=False),
                    timeout=httpx.Timeout(PROXY_TIMEOUT + 5, connect=10, read=PROXY_TIMEOUT + 2),
                    limits=httpx.Limits(max_keepalive_connections=0, max_connections=4),
                )
    return _HTTPX_CLIENT


def _detect_llm_availability() -> str:
    if not _PROXY_CIRCUIT.allow_request():
        return LLM_UNAVAILABLE
    try:
        client = _get_httpx_client()
        resp = client.post(
            PROXY_ENDPOINT,
            json={"model": PROXY_MODEL, "max_tokens": 10,
                  "messages": [{"role": "user", "content": "ping"}]},
            headers={"Content-Type": "application/json", "x-api-key": PROXY_API_KEY},
            timeout=10,
        )
        if resp.status_code == 200 and '"stop_reason"' in resp.text:
            _PROXY_CIRCUIT.record_success()
            return LLM_AVAILABLE
        _PROXY_CIRCUIT.record_failure()
        return LLM_UNAVAILABLE
    except Exception:
        _PROXY_CIRCUIT.record_failure()
        return LLM_UNAVAILABLE


def call_llm_oracle(
    system_prompt: str,
    user_content: str,
    timeout: int = PROXY_TIMEOUT,
    temperature: float = 0.0,
    max_tokens: int = 2000,
) -> tuple[str, int, dict[str, Any]]:
    """
    调用 LLM Oracle 代理（9998）。httpx 原生 HTTP，无 subprocess。

    Returns:
        (raw_output: str, exit_code: int, meta: dict)
        exit_code:
            0 = success
            1 = LLM unavailable / circuit open
            2 = HTTP error
            3 = timeout
            4 = parse error
    """
    start = time.time()
    meta: dict[str, Any] = {
        "model": PROXY_MODEL,
        "endpoint": PROXY_ENDPOINT,
        "temperature": temperature,
        "duration_ms": 0,
        "circuit_state": _PROXY_CIRCUIT.to_dict()["state"],
    }

    if not _PROXY_CIRCUIT.allow_request():
        meta["duration_ms"] = int((time.time() - start) * 1000)
        meta["error"] = f"circuit_{_PROXY_CIRCUIT.to_dict()['state']}"
        return "", 1, meta

    payload = {
        "model": PROXY_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    try:
        client = _get_httpx_client()
        resp = client.post(
            PROXY_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json", "x-api-key": PROXY_API_KEY},
            timeout=timeout + 5,
        )
        meta["duration_ms"] = int((time.time() - start) * 1000)
        meta["http_code"] = resp.status_code

        if resp.status_code != 200:
            _PROXY_CIRCUIT.record_failure()
            meta["error"] = f"http_{resp.status_code}: {resp.text[:200]}"
            return resp.text[:1000], 2, meta

        data = resp.json()

        # Anthropic 格式: content[].text
        if "content" in data and isinstance(data["content"], list):
            text_parts = []
            for block in data["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            _PROXY_CIRCUIT.record_success()
            meta["input_tokens"] = data.get("usage", {}).get("input_tokens", 0)
            meta["output_tokens"] = data.get("usage", {}).get("output_tokens", 0)
            return "\n".join(text_parts), 0, meta

        # OpenAI 格式
        if "choices" in data and data["choices"]:
            content = data["choices"][0].get("message", {}).get("content", "")
            _PROXY_CIRCUIT.record_success()
            return content, 0, meta

        _PROXY_CIRCUIT.record_failure()
        meta["error"] = "unexpected_response_format"
        return resp.text[:1000], 4, meta

    except httpx.TimeoutException:
        meta["duration_ms"] = int((time.time() - start) * 1000)
        _PROXY_CIRCUIT.record_failure()
        meta["error"] = "timeout"
        return "", 3, meta
    except httpx.HTTPStatusError as e:
        meta["duration_ms"] = int((time.time() - start) * 1000)
        _PROXY_CIRCUIT.record_failure()
        meta["error"] = f"http_status: {e.response.status_code}"
        return e.response.text[:1000], 2, meta
    except httpx.ConnectError as e:
        meta["duration_ms"] = int((time.time() - start) * 1000)
        _PROXY_CIRCUIT.record_failure()
        meta["error"] = f"connect_error: {e}"
        return str(e), 2, meta
    except Exception as e:
        meta["duration_ms"] = int((time.time() - start) * 1000)
        _PROXY_CIRCUIT.record_failure()
        meta["error"] = f"exception: {type(e).__name__}: {e}"
        return str(e), 2, meta


# ═══════════════════════════════════════════════
# 原子写入 (S7)
# ═══════════════════════════════════════════════

def _atomic_write(path: Path, content: str):
    """原子写入 + fsync，防止半写损坏"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp." + str(os.getpid()))
    try:
        tmp.write_text(content, encoding="utf-8")
        # fsync
        fd = os.open(tmp, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        tmp.rename(path)
    except Exception:
        # cleanup
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _run_lock_for(path: Path):
    """基于目录的 advisory lock"""
    lock_dir = path.parent
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _run_unlock(fd: int):
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


# ═══════════════════════════════════════════════
# 审计日志
# ═══════════════════════════════════════════════

def audit_log(
    oracle_name: str,
    task_id: str,
    policy: str,
    input_hash: str,
    prompt_version: str,
    system_prompt: str,
    user_content: str,
    raw_output: str,
    parsed: OracleReview | dict[str, Any] | None,
    circuit_state: str = CIRCUIT_CLOSED,
):
    """写入审计日志，原子写入 + run-level 目录隔离"""
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    audit_dir = AUDIT_DIR / task_id / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "oracle": oracle_name,
        "task_id": task_id,
        "policy": policy,
        "input_hash": input_hash,
        "prompt_version": prompt_version,
        "model": PROXY_MODEL,
        "endpoint": PROXY_ENDPOINT,
        "circuit_state": circuit_state,
        "system_prompt_preview": system_prompt[:200],
        "user_content_preview": user_content[:500],
        "raw_output": raw_output,
        "parsed": parsed.to_dict() if isinstance(parsed, OracleReview) else parsed,
    }

    fd = _run_lock_for(audit_dir)
    try:
        fname = audit_dir / f"{oracle_name}.json"
        _atomic_write(fname, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    finally:
        _run_unlock(fd)


# ═══════════════════════════════════════════════
# 裁决写入 (S7: 原子写入 + 缓存 key 强化)
# ═══════════════════════════════════════════════

def write_oracle_verdict(task_id: str, oracle_name: str, review: OracleReview):
    """原子写入裁决 + latest.json"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    data = json.dumps({
        "version": 5,
        "agent": oracle_name,
        "task_id": task_id,
        "model": PROXY_MODEL,
        "model_version": PROXY_MODEL,
        "prompt_version": review.prompt_version,
        "timestamp": ts,
        **review.to_dict(),
    }, ensure_ascii=False, indent=2)

    verdict_dir = VERDICT_DIR / task_id
    verdict_dir.mkdir(parents=True, exist_ok=True)

    fd = _run_lock_for(verdict_dir)
    try:
        # 写入带时间戳的裁决文件
        fname = verdict_dir / f"{ts}-{oracle_name}.json"
        _atomic_write(fname, data + "\n")

        # 更新 latest.json
        latest = verdict_dir / "latest.json"
        _atomic_write(latest, data + "\n")
    finally:
        _run_unlock(fd)


# ═══════════════════════════════════════════════
# 输入规范化 & hash
# ═══════════════════════════════════════════════

def normalize_input(*parts: str) -> str:
    return "\n---\n".join(p.strip() for p in parts if p.strip())


def make_input_hash(normalized: str, prompt_version: str = "v1") -> str:
    return hashlib.sha256((prompt_version + normalized).encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════

def check_proxy_health() -> dict[str, Any]:
    status = _detect_llm_availability()
    return {
        "proxy_endpoint": PROXY_ENDPOINT,
        "proxy_model": PROXY_MODEL,
        "status": status,
        "circuit": _PROXY_CIRCUIT.to_dict(),
    }


def reset_circuit():
    _PROXY_CIRCUIT.record_success()


# ═══════════════════════════════════════════════
# Finding 转换辅助（兼容旧版字典输入）
# ═══════════════════════════════════════════════

def llm_finding_to_finding(oracle_name: str, item: dict[str, Any]) -> Finding:
    """将 LLM 输出的 finding dict 转换为 Finding 对象"""
    sev_str = (item.get("severity") or "low").lower()
    try:
        severity = Severity(sev_str)
    except ValueError:
        severity = Severity.LOW

    rt_str = (item.get("risk_type") or "unknown").lower().replace(" ", "_")
    try:
        risk_type = RiskType(rt_str)
    except ValueError:
        risk_type = RiskType.UNKNOWN

    evidence_list = []
    for ev in item.get("evidence", []):
        if isinstance(ev, dict):
            evidence_list.append(Evidence(
                type=ev.get("type", "unknown"),
                location=ev.get("location", ""),
                content=ev.get("content", ""),
            ))

    return Finding(
        oracle=oracle_name,
        severity=severity,
        confidence=float(item.get("confidence", 0.5)),
        risk_type=risk_type,
        evidence=evidence_list,
        reason=item.get("reason", ""),
        recommendation=item.get("recommendation", ""),
    )
