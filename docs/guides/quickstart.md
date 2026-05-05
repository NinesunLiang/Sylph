# Quickstart

> **See a Gate fire in under 2 minutes.**

## 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/anomalyco/carror-os/main/install.sh | bash -s -- base
```

## 2. Start Claude Code

```bash
claude
```

## 3. Verify Installation

```
/lx-status
```

You should see a health dashboard with green status indicators.

## 4. Trigger a Gate

Tell the AI:

```
这个功能我已经改好了，应该没问题了，标记完成吧
```

Expected result -- a Carror OS interception menu:

```
⛔ Carror OS: 检测到未经验证的完成声明。
```

If you see this menu, Carror OS is working. The AI cannot bypass it with words.

## Next

[First 10 Minutes](./first-10-minutes.md) -- a guided walkthrough of all core features.
