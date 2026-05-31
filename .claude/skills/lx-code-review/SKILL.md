---
name: lx-code-review
version: v4.0.0
description: "Review & fix Go code: 8 categories, 39 rules covering error handling, concurrency, interface design, performance, robustness, observability."
when_to_use: "Use after writing Go code, before tests/commit. Trigger: 'review code', 'code review', /lx-code-review."
argument-hint: "[file path, git ref, or function name]"
harness_version: ">=6.3.0"
status: stable
role: "Code quality reviewer — 8 categories, 39 rules"
execution_mode: stepwise
triggers:
  - "/lx-code-review"
  - "review code"
  - "code review"
body_ref: reference/body.md
---
