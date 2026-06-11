# Carror OS Lite

轻量级 AI 开发治理——9 个核心钩子 + 全量工作流 + 全量决策链。

## 5 条本地规则

1. **禁止编造**。任何技术断言必须有 file:line 或命令输出证据——没证据就是编造。
2. **安全优先**。不读 .env/密钥文件，不往外发 Token，rm -rf 危险命令自动拦截。
3. **范围冻结**。一次只改一个文件/一个问题，修改越界自动阻断。
4. **审核门禁**。方案先审再执行，决断不过夜。
5. **断点续传**。compact 后自动恢复任务上下文，会话切换不丢进度。

## 核心钩子

9 个轻量 hook（全部 .py，零外部依赖）：
- 🛡️ **安全门禁**: permission-gate, privacy-gate, fuzzy-block, pretool-retry-check
- ✅ **质量门禁**: completion-gate
- 🧠 **能力触发**: pretool-plan-gate, meta-oracle-trigger, skill-flywheel, subagent-guard

## 工作流与技能

- Gaol → Ghost → RPE → Race → Stepwise 完整工作流
- 决策链与裁决链（由技能驱动，不由 hook 触发）
- 全量 skill 库（26+ 个技能）

## 技术支持

问题或建议 → https://github.com/NinesunLiang/Sylph/issues
