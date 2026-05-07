# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| v6.1.x  | :white_check_mark: |
| < 6.1   | :x:                |

## Reporting a Vulnerability

Carror OS takes security seriously. The privacy-gate, context-guard, and permission-gate hooks are designed to protect your development environment — but no software is perfect.

If you discover a security vulnerability, please **do not** open a public issue.

Instead, send a private report to the maintainers:

1. **GitHub**: Open a security advisory at [github.com/sylph/carror-os/security/advisories](https://github.com/sylph/carror-os/security/advisories)
2. **Email**: Contact the repository owner via GitHub

We will respond within 48 hours with a plan for triage and remediation.

### What to include

- Carror OS version and installation mode (`harness` / `base` / `enhanced`)
- Description of the vulnerability and potential impact
- Steps to reproduce (config files, commands, screenshots)
- Any bypass attempts against the harness-kit hooks

### Our commitment

- We will acknowledge receipt within 48 hours
- We will provide an estimated timeline for a fix
- We will credit you in the release notes (unless you prefer anonymity)

## Security Features

Carror OS includes the following built-in security measures:

- **Privacy Gate**: Physical blocking of `.env` / secret file reads
- **Context Guard**: Hard OOM protection at 80% context usage
- **Permission Gate**: `rm -rf` / `git push --force` requires explicit user approval
- **DLP Transparent Proxy** (`lx-varlock`): Bidirectional masking of sensitive data
- **A→B→A Cross-Verification**: Adversarial review across different AI models
