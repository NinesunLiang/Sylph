# 运行时校验与强制执行机制

## 1. Schema 校验器

```python
# scripts/policy_enforcer.py
"""运行时校验：autofix边界/verifier降级/模式冲突"""

class AutofixPolicyEnforcer:
    def __init__(self, policy_yaml: str):
        self.policy = yaml.safe_load(open(policy_yaml))
    
    def check_safe(self, fix_action: dict) -> tuple[bool, str]:
        """safe级操作校验"""
        if fix_action.get("type") in self.policy["safe"]["forbidden"]["patterns"]:
            return False, f"禁止操作: {fix_action['type']}"
        if fix_action.get("files_changed", 0) > 1:
            return False, "safe级禁止多文件修改"
        if fix_action.get("lines_changed", 0) > 50:
            return False, "safe级禁止大范围修改"
        return True, "ok"
    
    def check_review(self, fix_action: dict) -> tuple[bool, str]:
        """review级前置校验"""
        if not fix_action.get("diff_displayed"):
            return False, "review级必须展示diff"
        if not fix_action.get("user_confirmed"):
            return False, "review级必须用户确认"
        return True, "ok"

class VerifierDegradationEnforcer:
    def __init__(self, rules_yaml: str):
        self.rules = yaml.safe_load(open(rules_yaml))
    
    def can_degrade(self, verifier: str, mode: str) -> bool:
        """判断verifier是否可降级"""
        v = self.rules["verifier_degradation"].get(verifier)
        if not v:
            return False
        if not v["degradable"]:
            return False
        conditions = v.get("conditions", [])
        if "*" in conditions or mode in conditions:
            return True
        return False
    
    def degrade(self, verifier: str, mode: str) -> dict:
        """执行降级并返回效果"""
        if not self.can_degrade(verifier, mode):
            return {"action": "block", "reason": f"{verifier}在当前模式{mode}下不可降级"}
        v = self.rules["verifier_degradation"][verifier]
        return {"action": "degrade", "effect": v["on_degrade"]}

class ModeConflictResolver:
    def __init__(self, modes_yaml: str):
        self.priorities = yaml.safe_load(open(modes_yaml))["mode_priorities"]
    
    def resolve(self, modes: list[str]) -> dict:
        """解析多模式冲突"""
        if "report-only" in modes and any(m in modes for m in ["fix-safe", "fix-with-confirmation"]):
            return {"conflict": True, "resolution": "reject", "reason": "report-only禁止写文件"}
        
        sorted_modes = sorted(modes, key=lambda m: self.priorities.get(m, 0), reverse=True)
        winner = sorted_modes[0]
        if any(self.priorities.get(m, 0) != self.priorities.get(winner, 0) for m in modes):
            return {"conflict": False, "resolution": winner, "suppressed": [m for m in modes if m != winner]}
        return {"conflict": False, "resolution": winner}
```

## 2. 审计日志

```yaml
# references/audit-schema.yaml
audit_log:
  path: .lx-code-review/audit.jsonl
  records:
    - timestamp: ISO8601
      action_type: autofix | degrade | mode_select | review_complete
      rule_id: str
      file: path
      policy_match: pass | fail | override
      override_reason: str | null
      user: str | null
```

## 3. 校验时机

```yaml
# references/enforcement-triggers.yaml
enforcement:
  schema_validation:
    stage: pre_action
    validator: policy_enforcer
    on_violation: halt + audit_log
  runtime_guard:
    check_points:
      - before_file_write
      - before_autofix_apply
      - before_verifier_skip
    enforcer: policy_enforcer
  audit:
    destination: .lx-code-review/audit.jsonl
    record_on:
      - autofix_applied
      - degrade_applied
      - mode_conflict
      - policy_violation
```

## 4. 测试

```python
# tests/test_policy_enforcer.py
def test_safe_rejects_multi_file():
    enforcer = AutofixPolicyEnforcer("references/autofix-policy.yaml")
    ok, reason = enforcer.check_safe({"type": "formatting", "files_changed": 3})
    assert not ok
    assert "多文件" in reason

def test_build_not_degradable():
    enforcer = VerifierDegradationEnforcer("references/verifier-rules.yaml")
    assert not enforcer.can_degrade("build", "fast")

def test_report_only_conflict():
    resolver = ModeConflictResolver("references/mode-rules.yaml")
    result = resolver.resolve(["report-only", "fix-safe"])
    assert result["resolution"] == "reject"
```
