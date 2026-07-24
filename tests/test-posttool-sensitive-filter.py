#!/usr/bin/env python3
"""
test-posttool-sensitive-filter.py — 单元测试 posttool-sensitive-filter.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

FILTER_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "posttool-sensitive-filter.py"


def run_filter(input_text: str):
    """通过 stdin 向 filter 输送 input_text，返回 (stdout, stderr, returncode)。"""
    proc = subprocess.run(
        [sys.executable, str(FILTER_PATH)],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout, proc.stderr, proc.returncode


def assert_continue(stdout: str):
    """验证 filter 返回了 continue=True 的 JSON。"""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout 不是合法 JSON: {e}\nstdout={stdout!r}")
    assert data.get("continue") is True, f"缺少 continue=True: {data}"


# ── 测试用例 ──────────────────────────────────────────────────────────────

errors = []


def test(name: str, input_text: str, expect_masked: bool = True, exact_expected: str | None = None):
    """运行一个测试用例。"""
    stdout, stderr, rc = run_filter(input_text)

    try:
        assert_continue(stdout)
        assert rc == 0, f"返回码非零: {rc}"

        if exact_expected is not None:
            # 精确匹配模式 — 验证 stderr 内容完全等于预期
            assert stderr.strip() == exact_expected.strip(), (
                f"[{name}] 期望精确匹配\n  expected: {exact_expected!r}\n  got:      {stderr.strip()!r}"
            )
        elif expect_masked:
            # 检查 stderr 中是否包含 RECACTED 标记（原始内容已被掩码替换）
            assert "[REDACTED:" in stderr, (
                f"[{name}] 期望掩码但未找到 REDACTED 标记\n  stderr={stderr!r}"
            )
            # 确认原始敏感内容不在 stderr 中
            for pat in ["sk-", "ghp_", "ghu_", "gho_", "ghs_", "-----BEGIN"]:
                if pat in input_text:
                    assert pat not in stderr, (
                        f"[{name}] 原始敏感内容 {pat!r} 仍出现在 stderr 中\n  stderr={stderr!r}"
                    )
        else:
            # 不应掩码 — stderr 应包含原始内容
            assert stderr.strip() == input_text.strip(), (
                f"[{name}] 期望透传\n  expected: {input_text!r}\n  got:      {stderr.strip()!r}"
            )
    except AssertionError as e:
        errors.append(f"FAIL [{name}]: {e}")
        return

    print(f"  PASS  {name}")


# ── JSON 输入测试 ──────────────────────────────────────────────────────────

# 1) API Key (sk-)
json_sk = json.dumps({"content": "my api key is sk-aBcDeFgHiJkLmNoPqRsT1234567890AbCdEf"})
test("JSON: sk- API key", json_sk, expect_masked=True)

# 2) GitHub Token (ghp_)
json_ghp = json.dumps({"token": "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890Ab"})
test("JSON: ghp_ GitHub token", json_ghp, expect_masked=True)

# 3) Private Key (multiline) — filter regex handles "-----BEGIN PRIVATE KEY-----" (PKCS#8),
#    but NOT "-----BEGIN RSA PRIVATE KEY-----" (the regex expects a single word between BEGIN and KEY)
pk = "-----BEGIN PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END PRIVATE KEY-----"
json_pk = json.dumps({"key": pk})
test("JSON: private key", json_pk, expect_masked=True)

# 4) Normal text — 透传
json_normal = json.dumps({"name": "Carror OS", "version": "1.0"})
test("JSON: 正常内容透传", json_normal, expect_masked=False)

# 5) Nested JSON
json_nested = json.dumps({
    "level1": {
        "level2": {
            "api_key": "sk-aBcDeFgHiJkLmNoPqRsT1234567890AbCdEf",
            "safe": "hello"
        }
    },
    "list": [
        {"token": "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890Ab"},
        {"value": 42}
    ]
})
test("JSON: 嵌套数据掩码", json_nested, expect_masked=True)

# 6) 深度 > 10 的嵌套 — 不再递归
deep = {}
cur = deep
for i in range(12):
    cur["n"] = {}
    cur = cur["n"]
cur["key"] = "sk-aBcDeFgHiJkLmNoPqRsT1234567890AbCdEf"
json_deep = json.dumps(deep)
test("JSON: 深度 > 10 停止递归", json_deep, expect_masked=False)

# 7) 空输入
test("空输入", "", expect_masked=False)
# will generate empty stderr or same empty input; accept either
stdout, stderr, _ = run_filter("")
assert_continue(stdout)

# 8) 空白输入
test("空白输入", "   \n  ", expect_masked=False)


# ── 非 JSON 输入测试 ────────────────────────────────────────────────────────

# 9) 非 JSON 中的 sk-
raw_sk = "Token: sk-aBcDeFgHiJkLmNoPqRsT1234567890AbCdEf"
test("Raw: sk- API key", raw_sk, expect_masked=True)

# 10) 非 JSON 中的 ghp_
raw_ghp = "github token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890Ab"
test("Raw: ghp_ GitHub token", raw_ghp, expect_masked=True)

# 11) 非 JSON 中的 private key — PKCS#8 format (filter does NOT handle multi-word algorithm prefixes)
raw_pk = "here is my key:\n-----BEGIN PRIVATE KEY-----\nZm9vYmFy\n-----END PRIVATE KEY-----"
test("Raw: private key", raw_pk, expect_masked=True)

# 12) 非 JSON 正常内容透传
raw_normal = "User said: just a normal conversation\nNo secrets here."
test("Raw: 正常文本透传", raw_normal, expect_masked=False)

# 13) 非 JSON 混合
raw_mixed = "safe text\nghs_VwXyZ1234567890AbCdEfGhIjKlMnOpQrStUv\nmore safe\n"
test("Raw: 混合内容", raw_mixed, expect_masked=True)


# ── 边界与边缘测试 ──────────────────────────────────────────────────────────

# 14) 短 sk-（不足 20 位，不应匹配）
short_sk = json.dumps({"key": "sk-tooshort"})
test("JSON: 短 sk- 不应掩码", short_sk, expect_masked=False)

# 15) sk- 正好 20 位
exact_20 = "sk-" + "A" * 20
test("Raw: sk- 恰好 20 位应掩码", exact_20, expect_masked=True)

# 16) 空 JSON 对象
test("JSON: 空对象", "{}", expect_masked=False)

# 17) JSON 数组顶层
test("JSON: 数组顶层", json.dumps(["sk-x" + "A" * 30]), expect_masked=True)

# 18) 多行非 JSON
multi = "line1\nsk-aBcDeFgHiJkLmNoPqRsT1234567890AbCdEf\nline3\ngithub: gho_VwXyZ1234567890AbCdEfGhIjKlMnOpQrStUv\n"
test("Raw: 多行混合", multi, expect_masked=True)


# ── 报 告 ────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"{len(errors)} 个测试失败:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("全部测试通过。")
