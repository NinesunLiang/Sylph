# 0019. frontend-overnight 迁出治理域（能力保留）

**日期**: 2026-10-23
**来源**: 用户裁决「C 档：整体归档 frontend-overnight，不接入 CarrorOS 的治理，保留能力」

## 上下文

`frontend-overnight` 是 UI 还原隔夜自动工作流（C0–C8a 门禁链），长期占 `.claude/` 体量
（非测试 Python 9,057 行 + Markdown 3,270 行），且通过 `carroros-night-deny.py`
注册在 `settings.json` 的 PreToolUse 链上，使「产品域能力」与「CarrorOS 治理」耦合。

轻量化阶段 2 需要把治理域体量降下来；但该工作流仍有真实使用价值（XSimpleChat UI 还原
探针即由它驱动），不能删除。

## 决策

1. **能力迁移**：`git mv .claude/workflows/frontend-overnight → capabilities/frontend-overnight/`
   （保 git 历史），从治理路由移除。
2. **解绑治理**：`settings.json` 的 PreToolUse launcher 参数去掉 `carroros-night-deny.py`
   （注册 hook 12 → 11）；hook 文件保留在 `.claude/hooks/`（能力内部 `install_night_hook.py`
   与 `common_lib.py` 依赖它定位仓库根；需要夜跑时由能力侧自行安装）。
3. **路径修正**：hook 内控制面路径 `.claude/workflows/frontend-overnight/**`
   → `capabilities/frontend-overnight/**`。
4. **路由指针**：`.claude/workflows/index.md`、`.claude/index.md`、`README.md` 同步。

## 替代方案

- **直接删除**：否决，用户明确「保留能力」。
- **留在 `.claude/` 仅加注释**：否决，不算「不接入治理」，体量仍在。
- **移到 `apps/`**：否决，`apps/` 是宿主 App 工作区（gitignore），会丢版本历史。

## 后果

- 治理域少 9,057 行 Python + 3,270 行 Markdown；`test_line_budget.py` 的 workflows 预算降至 100。
- CarrorOS 治理不再默认加载夜跑 hook（白天零影响；夜间能力需显式安装后才有 hook 保护）。
- 历史 ADR0018/scorecard 中的旧路径保留为历史记录，不回改。
