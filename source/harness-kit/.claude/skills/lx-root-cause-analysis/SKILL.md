---
name: lx-root-cause-analysis
version: v4.0.0
description: "Trace recurring Go bugs via Five Whys: evidence chains → confidence scoring → immunity defense."
complexity: intermediate
when_to_use: "Use when bug recurs after fix, systematic debugging failed, or user says 'root cause', 'keeps happening'."
argument-hint: "<recurring bug symptom and history>"
harness_version: ">=6.3.0"
status: mature
role: "Five Whys root cause analysis for recurring Go bugs"
execution_mode: stepwise
triggers:
  - "/lx-root-cause-analysis"
  - "root cause"
body_ref: references/body.md
---
