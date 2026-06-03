---
name: lx-varlock

version: v1.1.0

description: "隐私脱敏代理管理器。处理包含敏感信息（密码、API Key、Token）的文件读写或命令执行，确保明文绝不泄露在 AI 上下文中。"

when_to_use: "Use when user provides a password, api key, token, or when you need to read/write a sensitive configuration file like .env or secret.yml."


argument-hint: "[set | list | rm | run | read | write]"

harness_version: ">=6.3.0"
status: stable
role: "Privacy desensitization proxy manager for sensitive data"
execution_mode: stepwise

triggers:
  - "/lx-varlock"
body_ref: references/body.md
---
