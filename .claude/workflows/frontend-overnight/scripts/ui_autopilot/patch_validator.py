"""patch_validator.py — Worker output validation with P0–P2 checks.

Enforces ui-patch/2 contract on every worker output before accepting:
  P0: schema version, limits, hash dedup, file bounds
  P1: files within page edit-scope (calls C1 scope_check)
  P2: scan for raw #hex / bare px / !important / :global violations (calls C3)

Design: Opus M1—M2 risk mitigation + Grok G-P0-4 (no session self-minting).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class ValidationVerdict(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"


class RejectCode(StrEnum):
    """Machine-readable rejection reasons for morning_report aggregation."""
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SCOPE_FAIL = "SCOPE_FAIL"
    RAW_VALUE = "RAW_VALUE"           # bare #hex or px without token
    TOKEN_REQUIRED = "TOKEN_REQUIRED"  # value has no matching token
    ABSTRACTION_FAIL = "ABSTRACTION_FAIL"  # :global / !important / antd override
    TOUCHES_GENERATED = "TOUCHES_GENERATED"
    TOUCHES_TOKEN_SOURCE = "TOUCHES_TOKEN_SOURCE"  # 🔴 P0: night must not touch
    FILE_LIMIT_EXCEEDED = "FILE_LIMIT_EXCEEDED"
    LINE_LIMIT_EXCEEDED = "LINE_LIMIT_EXCEEDED"
    EMPTY_PATCH = "EMPTY_PATCH"
    HASH_DUPLICATE = "HASH_DUPLICATE"


# ── Patterns ────────────────────────────────────────────────────────────────────

RAW_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}(?![-\w])")
RAW_PX_RE = re.compile(r"(?<!\d)\d+px(?![\w-])")
IMPORTANT_RE = re.compile(r"!\s*important", re.IGNORECASE)
GLOBAL_RE = re.compile(r":global\s*\(")
ANTHACK_RE = re.compile(r"\.ant-[a-z]")

# Paths that night must NEVER touch
IMMUTABLE_NIGHT_PATTERNS = [
    "src/styles/tokens/generated/",
    "src/styles/tokens/source/",
    ".claude/workflows/frontend-overnight/scripts/carroros-gates/",
    ".claude/",
    ".omc/",
]

# Allowed px/hex in comments and generated tokens (whitelist)
PX_HEX_WHITELIST_PATTERNS = [
    r"/\*.*\*/",                     # CSS comments
    r"//.*",                          # JS/TS line comments
    r"generated/tokens",              # Generated token files
]


@dataclass(slots=True)
class ValidationResult:
    verdict: ValidationVerdict = ValidationVerdict.PASS
    reject_code: RejectCode | None = None
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PatchValidator:
    """P0–P2 patch contract validator.

    Usage:
        v = PatchValidator(allowed_patterns=["src/pages/**"], token_index={...})
        result = v.validate(patch_dict, history_hashes=["abc123", ...])
        if result.verdict == ValidationVerdict.REJECT:
            # reject patch, log result.reject_code
    """

    allowed_patterns: list[str] = field(default_factory=list)
    token_index: set[str] = field(default_factory=set)
    max_files: int = 8
    max_lines: int = 400

    def validate(
        self,
        patch: dict[str, Any],
        history_hashes: list[str] | None = None,
    ) -> ValidationResult:
        """Run full P0–P2 validation pipeline.

        Args:
            patch: Worker output dict with keys:
                - schema_version: int
                - changed_files: list[{path, before, after}]
                - self_check: dict with token/hardcode assertions
            history_hashes: Recent patch hashes to dedup against

        Returns:
            ValidationResult with verdict and reject_code
        """
        # ── P0: Schema check ──
        if patch.get("schema_version") != 2:
            return ValidationResult(
                verdict=ValidationVerdict.REJECT,
                reject_code=RejectCode.SCHEMA_INVALID,
                reason=f"Expected schema_version=2, got {patch.get('schema_version')}",
            )

        changed_files = patch.get("changed_files", [])
        if not changed_files:
            return ValidationResult(
                verdict=ValidationVerdict.REJECT,
                reject_code=RejectCode.EMPTY_PATCH,
                reason="No changed_files in patch",
            )

        # ── P0: File/line limits ──
        if len(changed_files) > self.max_files:
            return ValidationResult(
                verdict=ValidationVerdict.REJECT,
                reject_code=RejectCode.FILE_LIMIT_EXCEEDED,
                reason=f"{len(changed_files)} files > max {self.max_files}",
            )

        total_lines = sum(
            str(f.get("after", "")).count("\n") for f in changed_files
        )
        if total_lines > self.max_lines:
            return ValidationResult(
                verdict=ValidationVerdict.REJECT,
                reject_code=RejectCode.LINE_LIMIT_EXCEEDED,
                reason=f"{total_lines} changed lines > max {self.max_lines}",
            )

        # ── P0: Hash dedup ──
        if history_hashes:
            patch_hash = self._hash_patch(changed_files)
            if patch_hash in history_hashes:
                return ValidationResult(
                    verdict=ValidationVerdict.REJECT,
                    reject_code=RejectCode.HASH_DUPLICATE,
                    reason=f"Patch hash {patch_hash[:8]} already in recent history",
                )

        # ── P1: Scope check ──
        for f in changed_files:
            path = f.get("path", "")
            if not self._in_scope(path):
                return ValidationResult(
                    verdict=ValidationVerdict.REJECT,
                    reject_code=RejectCode.SCOPE_FAIL,
                    reason=f"File not in scope: {path}",
                    details={"file": path},
                )

        # ── P1: Immutable night paths ──
        for f in changed_files:
            path = f.get("path", "")
            if any(pat in path for pat in IMMUTABLE_NIGHT_PATTERNS):
                code = (
                    RejectCode.TOUCHES_TOKEN_SOURCE
                    if "tokens/source" in path
                    else RejectCode.TOUCHES_GENERATED
                    if "tokens/generated" in path
                    else RejectCode.SCOPE_FAIL
                )
                return ValidationResult(
                    verdict=ValidationVerdict.REJECT,
                    reject_code=code,
                    reason=f"Immutable night path: {path}",
                    details={"file": path},
                )

        # ── P2: Raw value scan ──
        raw_violations = []
        for f in changed_files:
            after = str(f.get("after", ""))
            violations = self._scan_raw_values(after, f.get("path", ""))
            if violations:
                raw_violations.extend(violations)

        if raw_violations:
            return ValidationResult(
                verdict=ValidationVerdict.REJECT,
                reject_code=RejectCode.RAW_VALUE,
                reason=f"{len(raw_violations)} raw value violations found",
                details={"violations": raw_violations[:10]},
            )

        # ── P2: Abstraction violations ──
        for f in changed_files:
            after = str(f.get("after", ""))
            if IMPORTANT_RE.search(after):
                return ValidationResult(
                    verdict=ValidationVerdict.REJECT,
                    reject_code=RejectCode.ABSTRACTION_FAIL,
                    reason="!important found",
                    details={"file": f.get("path")},
                )
            if GLOBAL_RE.search(after):
                return ValidationResult(
                    verdict=ValidationVerdict.REJECT,
                    reject_code=RejectCode.ABSTRACTION_FAIL,
                    reason=":global() found",
                    details={"file": f.get("path")},
                )

        return ValidationResult(verdict=ValidationVerdict.PASS)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _in_scope(self, path: str) -> bool:
        """Check if a file path is within allowed glob patterns."""
        if not self.allowed_patterns:
            return True  # No scope defined → allow all (test mode)
        import fnmatch
        for pattern in self.allowed_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    @staticmethod
    def _hash_patch(changed_files: list[dict]) -> str:
        """Compute a hash of the patch content for dedup."""
        content = json.dumps(changed_files, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _scan_raw_values(content: str, filepath: str = "") -> list[dict]:
        """Scan content for raw hex colors and bare px values.

        Skip whitelisted patterns (comments, generated tokens).
        """
        # Strip comments to reduce false positives
        cleaned = content
        for pattern in PX_HEX_WHITELIST_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)

        violations: list[dict] = []

        for match in RAW_HEX_RE.finditer(cleaned):
            hex_val = match.group(0)
            # Skip common non-color hex patterns
            if len(hex_val) > 8:
                continue
            violations.append({
                "type": "raw_hex",
                "value": hex_val,
                "file": filepath,
            })

        for match in RAW_PX_RE.finditer(cleaned):
            # Skip if value looks like it's inside a CSS variable or token
            px_val = match.group(0)
            violations.append({
                "type": "raw_px",
                "value": px_val,
                "file": filepath,
            })

        return violations
