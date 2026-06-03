---
name: lx-test-gen
version: v1.0.0
description: "Language-agnostic test code generator. Auto-detects project language (Go/TS/Python/etc.), routes to appropriate test patterns: table-driven, mocks, HTTP handlers, benchmarks, fuzz, property-based."
complexity: intermediate
when_to_use: "Use when user needs test code for functions, interfaces, HTTP handlers, or when user says 'generate tests', 'test this function', '/lx-test-gen'."
argument-hint: "<function/handler/module name> [test type]"
harness_version: ">=6.3.0"
status: stable
role: "Language-agnostic test code generator — pattern-based test scaffolding"
execution_mode: stepwise
triggers:
  - "/lx-test-gen"
body_ref: references/body.md
---
