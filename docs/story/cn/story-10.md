# 工具匠人 — 从脚本军团到钩子进化

claim-lint.sh 沉默地扫描着每一份营销文档。它不关心文采——它只关心一件事：有没有人写"行业独创"？有没有人说"100%"？有没有人称"没有对手"？

高风险关键词的名单不长——但每一条都是因果的产物。对外宣称"行业首创"被事实核查打脸的那一天，名单上多了"首创"。写"自评分"让 Oracle 发现评分虚高的那一天，名单上多了"自评分"。

工具匠人不靠灵感——靠前车之鉴。

---

## 旧军团的消逝

曾经，审计军团有六位成员。三位审计师：audit-hooks.sh（三方一致性），harness-smoke-test.sh（回归烟雾），hook-production-verify.sh（全场景覆盖）。三位事务官：pre-commit-self-review.sh（反自矛盾），doc-sync-check.sh（文档引用），score-self-check.sh（AI vs 实际配置）。

他们全部消逝了。

不是被删除的——是被进化吸收的。

三方一致性审计？现在的 completion-gate 家族（completion-gate + posttool-completion-audit + pre-completion-gate）在每次 TaskUpdate 时实时检查，不再需要手动运行 audit-hooks.sh。

回归烟雾测试？Dogfood 模式（lx-dogfood skill + flywheel-report）在持续运行中覆盖了所有 hook 的功能验证，不再需要独立的 harness-smoke-test.sh。

全场景门禁覆盖？posttool-anti-pattern-detect 和 fuzzy-block 在生产环境中实时检测反模式，不再需要模拟测试的 hook-production-verify.sh。

反自矛盾检查？Oracle 终审（lx-oracle）在每次关键决策时交叉验证，不再需要 pre-commit 脚本。文档引用验证？inject-project-knowledge 在每次 SessionStart 时注入最新状态，不再需要 doc-sync-check.sh。

**不是"被废弃了"。是被更高效的机制替代了。** 每一个消逝的脚本，其因果逻辑都没有消失——只是从手动脚本层进化到了 hook 实时层和 skill 智能层。

脚本层变薄了。但覆盖更密了。

---

## 现在：工具匠人工坊

如今站在 scripts/ 目录里的，是六位不同性格的手艺人：

| 匠人 | 工具 | 职责 | 触发 |
|------|------|------|------|
| 真言匠人 | claim-lint.sh | 营销文档关键词扫描 | 文档变更时 |
| 安装大师 | install.sh | 一键安装 Carror OS | 新环境部署 |
| 工具箱匠人 | harness-kit-install.sh | 导入 harness 套件 | 项目初始化 |
| 工具箱卸手 | harness-kit-uninstall.sh | 安全卸载 harness | 清理迁移 |
| 打包师 | package.sh | 生成发布包 | 版本构建 |
| 发布官 | package-release.sh | 版本发布全流程 | Release 门禁 |

---

## 真言匠人：claim-lint.sh — 不夸大是一种纪律

claim-lint.sh 是唯一和"审计"沾边的留存者。它做的事简单却致命：扫描 docs/marketing/ 下所有 Markdown 文件，检测是否出现被禁的关键词。

名单不长。每条都有故事：

- **"行业独创"** —— 被事实核查发现同类产品早在 2025 年就发布了
- **"首创"** —— 和"独创"类似的过度声明
- **"100%"** —— "100% 可见"被 Oracle 审计发现存在盲区
- **"完全可见"** —— 同上
- **"自评分"** —— R30：AI 自评分在 Enhanced 环境下与 Base 文档基准错位
- **"毫无疑问"** —— 因为永远有疑问
- **"军工级"** —— 未经任何军工认证的浮夸比喻
- **"满分"** —— 因为永远不是

真言匠人的逻辑不是"删除所有营销语言"。它的逻辑是：**每一个夸张的断言，都是未来被打脸的因果种子。** 此刻省下的真实，是未来积攒的信用。

---

## 从"审计事后"到"实时进化"

回看旧审计军团的消逝和工具匠人工坊的现状，折射的是 Carror OS 自身的一个进化规律：

**好的治理不是事后审计——是实时融入。**

当治理从脚本（手动运行）进化到 hook（自动触发）再进化到 skill（智能决策），每一次跳跃都在提高信噪比、降低心智负担。脚本层从 15 个工具减少到 6 个——不是功能变少了，是功能找到更高效的存在形态了。

而工具匠人工坊的存在，恰好说明：**总有一些事情不适合 hook 化或 skill 化。** 营销措辞检查不需要每次 commit 都触发。安装部署不需要注入到 AI 上下文中。它们是独立任务，独立触发，独立验收。

这就是 因果 的智慧：不预设什么应该是 hook、什么应该是 script。让实际需求决定生长方向。

---

## 相关故事

- [证据裁判庭](story-04.md) — completion-gate 家族：吸收了三方一致性审计的实时验证
- [双生判官](story-16.md) — Oracle 终审：吸收了 pre-commit 自检的交叉验证
- [飞轮回响](story-12.md) — Dogfood 模式：吸收了回归烟雾测试的持续验证
- [反面镜宫](story-09.md) — posttool-anti-pattern-detect：吸收了全场景门禁覆盖
