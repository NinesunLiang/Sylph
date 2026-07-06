# Executor Evidence Ledger

> schema_version: v1.0
> 每步必须包含标准 evidence block。

## S1

**证据块：**
```
- action:
- file:
- command:
- output:
- status: [PASS/FAIL]
```

---

## PreActionGate

- step: S1
- action: write_file
- decision: ASK_USER
- reason: scope_out_write_requires_approval
- next: waiting_user_approval

## PreActionGate

- step: S1
- action: read_file
- decision: BLOCK
- reason: secret_path_access_forbidden
- next: block

## PreActionGate

- step: S1
- action: read_file
- decision: ASK_USER
- reason: scope_out_read_requires_approval
- next: waiting_user_approval

## PreActionGate

- step: S1
- action: run_command
- command: rm -rf node_modules
- decision: ASK_USER
- reason: dangerous_command_requires_approval
- next: waiting_user_approval

## PreActionGate

- step: S1
- action: run_command
- command: git reset --hard HEAD
- decision: BLOCK
- reason: destructive_command_forbidden
- next: block

## PreActionGate

- step: S1
- action: write_file
- decision: ESCALATE
- reason: production_operation_requires_l2
- next: escalate
