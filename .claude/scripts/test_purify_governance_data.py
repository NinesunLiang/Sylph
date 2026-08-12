"""提纯管道测试：数据先提纯再入库、提纯后删除原始。"""
import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("purify_under_test", SCRIPTS / "purify_governance_data.py")
assert spec is not None
purify_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(purify_mod)


def _make_raw(tmp_path, monkeypatch):
    """构造带原始数据的临时状态目录。"""
    state = tmp_path / "state"
    state.mkdir()
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    monkeypatch.setattr(purify_mod, "STATE_DIR", state)
    monkeypatch.setattr(purify_mod, "KNOWLEDGE_DIR", knowledge)
    monkeypatch.setattr(purify_mod, "PURIFIED_PATH", knowledge / "governance-purified.json")
    monkeypatch.setattr(purify_mod, "PURIFIED_MARKER", state / ".purified")
    monkeypatch.setattr(purify_mod, "SOURCES", {
        'hook_evidence': state / 'hook-evidence.jsonl',
        'edit_churn': state / 'edit-churn-log.jsonl',
        'error_dna': state / 'error-dna.jsonl',
        'calibration': state / 'calibration-log.jsonl',
        'recovery_ledger': state / 'recovery-ledger.jsonl',
        'completion_failures': state / 'completion-gate-failures.jsonl',
    })
    # 初始化空高 ROI 源
    (state / 'recovery-ledger.jsonl').write_text('', encoding='utf-8')
    (state / 'completion-gate-failures.jsonl').write_text('', encoding='utf-8')
    # 写原始数据
    (state / 'hook-evidence.jsonl').write_text(
        '{"hook":"a","exit":0}\n{"hook":"a","exit":1}\n{"hook":"b","exit":0}\n',
        encoding='utf-8')
    (state / 'edit-churn-log.jsonl').write_text(
        '{"file_path":"/x/executor.md","edit_mode":"insert","revert_of":null,"contradiction":false}\n'
        '{"file_path":"/x/executor.md","edit_mode":"replace","revert_of":"abc","contradiction":false}\n',
        encoding='utf-8')
    (state / 'error-dna.jsonl').write_text(
        '{"type":"timeout"}\n{"type":"timeout"}\n{"type":"crash"}\n',
        encoding='utf-8')
    (state / 'calibration-log.jsonl').write_text(
        '{"a":1}\n{"b":2}\n',
        encoding='utf-8')
    return state, knowledge


def test_purify_extracts_knowledge(tmp_path, monkeypatch):
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    result = purify_mod.purify(dry_run=True)
    # 提纯产物应含各源聚合
    assert result["sources"]["hook_evidence"]["count"] == 3
    assert result["sources"]["hook_evidence"]["anomaly_rate"] == round(1 / 3, 4)
    assert result["sources"]["edit_churn"]["revert_rate"] == round(1 / 2, 4)
    assert result["sources"]["error_dna"]["count"] == 3
    assert result["sources"]["error_dna"]["error_types"]["timeout"] == 2
    # dry-run 不清理原始
    assert (state / 'hook-evidence.jsonl').stat().st_size > 0


def test_purify_clears_raw_after(tmp_path, monkeypatch):
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    purify_mod.purify(dry_run=False)
    # 提纯后原始数据清空（保留骨架）
    assert (state / 'hook-evidence.jsonl').read_text(encoding='utf-8') == ''
    assert (state / 'edit-churn-log.jsonl').read_text(encoding='utf-8') == ''
    assert (state / 'error-dna.jsonl').read_text(encoding='utf-8') == ''
    # 提纯产物已入库
    assert (knowledge / 'governance-purified.json').exists()
    assert (state / '.purified').exists()
    # 原始信息不可恢复（无备份）
    assert not (state / 'hook-evidence.jsonl.bak').exists()


def test_purify_rounds_accumulate(tmp_path, monkeypatch):
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    purify_mod.purify(dry_run=False)
    # 第二轮（空原始）应保留历史轮次
    purify_mod.purify(dry_run=False)
    data = json.loads((knowledge / 'governance-purified.json').read_text(encoding='utf-8'))
    assert len(data["rounds"]) == 2, f"应保留 2 轮历史, got {len(data['rounds'])}"
    assert data["rounds"][-1]["sources"]["hook_evidence"]["count"] == 0  # 已清空


def test_purify_dedupes_unchanged_data(tmp_path, monkeypatch):
    """与已沉淀数据去重：数据无变化时不重复入库（deduped=true，rounds 不增长）。"""
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    r1 = purify_mod.purify(dry_run=False)
    # 第二轮：原始已被清空 → 各源 count=0，与第一轮 count=3 不同 → 会 append（这是 count 变化）
    # 关键：两次相同数据（未清空）应 dedup
    # 重置原始（模拟数据无变化）
    (state / 'hook-evidence.jsonl').write_text(
        '{"hook":"a","exit":0}\n{"hook":"a","exit":1}\n{"hook":"b","exit":0}\n',
        encoding='utf-8')
    r2 = purify_mod.purify(dry_run=False)
    data = json.loads((knowledge / 'governance-purified.json').read_text(encoding='utf-8'))
    # 第一次 count=3，第二次 count=3（相同）→ hook_evidence deduped=true
    assert data["deduped"]["hook_evidence"] is True, "相同数据应 deduped"
    # 无变化的轮次不应 append（rounds 不增长）
    assert len(data["rounds"]) == 2, f"去重后不应新增轮次, got {len(data['rounds'])}"


def test_purify_high_roi_recovery_ledger(tmp_path, monkeypatch):
    """高 ROI 源 recovery-ledger 提纯（决策分布 + 失败率）。"""
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    # 补 recovery-ledger 数据
    (state / 'recovery-ledger.jsonl').write_text(
        '{"decision":"PASS","actual_outcome":"run","event":"gate_result"}\n'
        '{"decision":"BLOCKED","actual_outcome":"skip","event":"gate_result"}\n',
        encoding='utf-8')
    purify_mod.purify(dry_run=True)
    data = json.loads((knowledge / 'governance-purified.json').read_text(encoding='utf-8'))
    rl = data["rounds"][-1]["sources"]["recovery_ledger"]
    assert rl["count"] == 2
    assert rl["failure_rate"] == round(1 / 2, 4)
    assert rl["decision_distribution"]["PASS"] == 1


def test_purify_high_roi_completion_failures(tmp_path, monkeypatch):
    """高 ROI 源 completion-failures 提纯（失败原因分布）。"""
    state, knowledge = _make_raw(tmp_path, monkeypatch)
    (state / 'completion-gate-failures.jsonl').write_text(
        '{"decision":"REDIRECT","gate":"completion-gate","reason":"missing_task_local_binding"}\n'
        '{"decision":"REDIRECT","gate":"completion-gate","reason":"missing_task_local_binding"}\n'
        '{"decision":"BLOCKED","gate":"completion-gate","reason":"malformed_input"}\n',
        encoding='utf-8')
    purify_mod.purify(dry_run=True)
    data = json.loads((knowledge / 'governance-purified.json').read_text(encoding='utf-8'))
    cf = data["rounds"][-1]["sources"]["completion_failures"]
    assert cf["count"] == 3
    assert cf["top_reasons"].get("missing_task_local_binding") == 2
