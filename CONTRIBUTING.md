# Contributing to Carror OS

Thank you for considering contributing to Carror OS — the AI Native Developer Operating System.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

- Check the [issue tracker](https://github.com/sylph/carror-os/issues) for existing reports
- Provide a clear title and detailed reproduction steps
- Include the Carror OS version (`cat VERSION.json`), platform, and AI model used
- Attach relevant log output from `.omc/state/`

### Suggesting Features

- Describe the problem you're solving, not just the solution
- Explain how your feature fits Carror OS's "Guard First, Arm Later" philosophy
- Provide example usage scenarios

### Pull Requests

1. Fork the repository and create a branch from `main`
2. Run the full test suite before submitting:
   ```bash
   bash .claude/scripts/harness-smoke-test.sh
   bash .claude/scripts/hook-production-verify.sh
   ```
3. Update documentation (`docs/`, `AGENTS.md`, `README.md`) as needed
4. Ensure your PR description clearly describes the change and its motivation
5. Reference any related issues

### Development Setup

```bash
# Clone the repository
git clone https://github.com/sylph/carror-os.git
cd carror-os

# Install in development mode
bash install.sh enhanced
```

### Commit Guidelines

- Follow the existing commit style (imperative mood, short subject line)
- Keep commits focused on a single change
- Include `Co-Authored-By: ...` for AI-assisted contributions

## Questions?

Open a [discussion](https://github.com/sylph/carror-os/discussions) or reach out via the repository issue tracker.
