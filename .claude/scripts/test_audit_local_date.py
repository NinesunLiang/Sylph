"""TDD 回归: 审计分片日期用本地日期而非 UTC(M1 修复, index21 双法官发现)。

缺陷: helpers.py:387 与 carros_utils.py:95 用 datetime.now(timezone.utc)
做审计分片名。UTC+8 时区 00:00-08:00 运行 → 审计落到昨日分片, 全部
ON 运行(01:20-01:30 CST)审计文件命名为前一日 → 双法官 B 判 P1, 审计
证据链日期错位。

修复: 审计分片(文件名)改用本地日期; 时间戳字段(ts/timestamp)保持 UTC。
与 index20 F2(任务目录日期)同一修复原则。
"""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import carros_utils  # noqa: E402


def _monkey_now_utc_plus8(monkeypatch):
    """模拟 UTC+8 时区(本地时间比 UTC 早 8 小时)下 01:xx 本地时刻。

    让本地日期 = UTC 日期 + 1 天, 复现「晚 8 小时运行 → 审计落昨日分片」。
    用独立的假 datetime 类(非子类), 避免 datetime.now() C 实现歧义。
    """

    class _FakeDT:
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                # UTC 调用点: 前一日 17:30 (与本地 08-14 01:30 对应)
                return datetime(2026, 8, 13, 17, 30, 0, tzinfo=tz)
            # 本地调用点(now() 无参): 08-14 01:30
            return datetime(2026, 8, 14, 1, 30, 0)

        @classmethod
        def strftime(cls, fmt):
            return cls.now().strftime(fmt)

    monkeypatch.setattr(carros_utils, "datetime", _FakeDT)


def test_audit_shard_uses_local_date(monkeypatch):
    """carros_utils.write_audit 分片名必须用本地日期(本地 08-14 不应落 08-13)。"""
    _monkey_now_utc_plus8(monkeypatch)
    with tempfile.TemporaryDirectory() as td:
        ad = Path(td)
        carros_utils.write_audit(ad, "verify", {"step": "S1", "result": "PASS"})
        files = [p.name for p in ad.iterdir()]
        assert "20260814.jsonl" in files, (
            f"审计分片应用本地日期 20260814, 实际: {files} "
            "(UTC 日期会错误落 20260813.jsonl)"
        )


def test_audit_timestamp_keeps_utc_iso(monkeypatch):
    """ts 时间戳字段保持 UTC ISO(不因分片改本地而改)。"""
    _monkey_now_utc_plus8(monkeypatch)
    with tempfile.TemporaryDirectory() as td:
        ad = Path(td)
        carros_utils.write_audit(ad, "verify", {"step": "S1", "result": "PASS"})
        f = ad / "20260814.jsonl"
        line = json.loads(f.read_text(encoding="utf-8").strip())
        assert line["ts"].startswith("2026-08-13T17:30"), (
            "ts 时间戳应保持 UTC(2026-08-13T17:30), 分片名才用本地日期"
        )


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
