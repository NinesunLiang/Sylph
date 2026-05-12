# Carror OS — 给 AI 装上刹车

> **Carror OS 不是更好的 Cursor，而是 AI 时代的 Unix。**
>
> 当其他工具都在让 AI 跑得更快时，Carror OS 提供了最昂贵的奢侈品——**刹车**。

[![Version](https://img.shields.io/badge/version-v6.1.9-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Tests](https://img.shields.io/badge/tests-98%20PASS%20%2F%200%20FAIL-brightgreen)]()

---

## 问题

AI 编程助手正在进行一场"写出更多更快代码"的军备竞赛。但每个工程师都经历过同样的噩梦：

- AI 在你没注意时执行了 `rm -rf /var/www`
- AI 说"搞定了"——但什么都没做
- AI 读取了你的 `.env` 文件，发给了云端 API
- 对话 30 轮后，AI 开始编辑它不该碰的文件
- 同一个 bug"修复"了 8 次，每次都说"这次应该没问题了"

**现有方案全部失效。** Cursor Rules、Copilot Instructions，甚至 Claude Code Hooks 都在 Prompt 层运作——它们*请求* AI 遵守规则。AI 可以礼貌地无视它们。

---

## 解决方案

Carror OS 选择了不同的路径：**不跟 AI 说话，直接拦截它的工具调用。**

```
正常流程:   用户 → AI → 工具调用 → 执行

Cursor:     用户 → AI → [Prompt 建议] → 工具调用 → 执行

Carror OS:  用户 → AI → [⚠️ Hook 拦截] → 拒绝 / 授权 / 审计
```

### 架构

```
Carror OS
├── harness-kit          ← 内核层：防御与治理
│   └── 32 个注册 Hook，在应用层拦截 AI
└── lx-skills-v5         ← 用户态：能力与工作流
    └── 24 个 Skill，用于任务编排与代码质量
```

### 不同之处

其他工具说：**"请不要这样做。"**

Carror OS 说：**`Exit 2` — 物理阻断。**

---

## 快速开始

```bash
# Base 版 — 32 个 Hook + 10 个门禁 Skill，零学习成本
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base

# Enhanced 版 — 全 24 个 Skill + 任务流水线
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- enhanced
```

30 秒。无需守护进程。无需云端。无需订阅。

---

## 功能一览

### 硬门禁（32 个物理 Hook）

| 域 | Hook | 拦截什么 |
|--------|------|----------------|
| 权限 | `permission-gate.sh` | `rm -rf`, `DROP TABLE`, `git push --force` |
| 隐私 | `privacy-gate.sh` | `.env` 读取、`*.pem`、明文 Token |
| 上下文 | `context-guard.sh` | 上下文 ≥80% 时锁死所有写入（OOM 熔断） |
| 完成验证 | `completion-gate.sh` | 无 VERIFIED 证据声称"完成" |
| 编辑守卫 | `edit-guard.sh` | 编辑 AI 尚未读取的文件 |
| 范围冻结 | `pretool-edit-scope.sh` | 当前任务范围外的文件 |

**全部 32 个注册 Hook 已通过 L1-L4 四层测试（手动验收 + 自动 Hook 校验 + 代码扫描 + 格式门禁）：98 PASS / 0 FAIL，ShellCheck/Bandit 安全扫描：0 真实缺陷，行业标准自评合规对照（OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0）：75/75 覆盖 [内部自评，非第三方认证]。**

### Skill 武器库（24 种能力）

| 类别 | Skill | 功能 |
|----------|--------|--------------|
| 任务流水线 | `lx-rpe`, `lx-task-spec`, `lx-todo` | 全周期：调研 → 规划 → 执行，按复杂度自动伸缩 |
| 代码质量 | `lx-code-review`, `lx-pre-commit`, `lx-pre-push` | 自动审查 + CI 门禁 |
| 安全 | `lx-security-review`, `lx-varlock` | 漏洞扫描 + DLP 透明代理 |
| 深度调试 | `lx-root-cause-analysis`, `lx-debug-spec` | 5-Why 追踪 + 并发调试 |
| 监控 | `lx-status` | 健康面板：Token 节省、错误恢复、任务图谱 |

---

## 行业对比

> **说明**：Carror OS 是运行在 AI CLI 之上的治理层，不是编码工具或 IDE。下表对比的是**原生 CLI 防御能力**与**叠加 Carror OS 治理后的全栈防护能力**。Carror OS 内部版本对比使用不同格式。

| 维度 | Carror OS | Devin | Cursor | Claude Code |
|---|:--:|:--:|:--:|:--:|
| 防御层级 | **Exit 2 物理阻断** | 商业黑盒 | Prompt 建议 | Hook 原语 |
| DLP 脱敏 | **双向代理** | 无 | 无 | 无 |
| 上下文漂移 | **三层自动防御** | 未知 | 无 | 手动 /compact |
| A→B→A 交叉验证 | **对抗性审查** | 无 | 无 | 无 |
| 并发协同 | **文件锁 + MECE** | 内置 | 无 | 无 |
| 价格 | **$0** | $20-500/月 | $20-40/月 | $20/月 |
| 可审计性 | **全开源** | 商业黑盒 | 部分开源 | 闭源 |

### 八维评分

> Carror OS 评分基于源码级深度审计；竞品评分为基于公开资料的团队内部评估，非第三方认证。详见 [行业横评白皮书](industry-benchmark.md)。

| 维度 | Carror OS | Devin | Cursor | Claude Code |
|-----------|:--:|:--:|:--:|:--:|
| **G** 治理深度 | 9.5 | 3.5 | 2.0 | 4.0 |
| **S** 安全防护 | 9.0 | 4.0 | 2.5 | 3.0 |
| **I** 智能协作 | 8.5 | 8.0 | 7.5 | 5.0 |
| **R** 抗衰减 | 9.5 | 2.0 | 1.0 | 2.0 |
| **A** 可审计性 | 8.5 | 3.0 | 1.5 | 2.0 |
| **E** 经济性 | 9.0 | 2.0 | 3.0 | 7.0 |
| **P** 本地主权 | 10.0 | 2.0 | 5.0 | 9.0 |
| **X** 可扩展性 | 8.5 | 2.0 | 4.0 | 7.0 |
| **总分** | **72.5/80** | **26.5** | **26.5** | **39.0** |

---

## 为什么叫 Carror OS？

Carror（腐肉）——腐烂的肉体。一具尸体。

在自然界，腐肉吸引食腐动物。在软件世界，遗留代码吸引 AI 盲目地重写、删除和破坏。Carror OS 是保护你的代码库免受 AI 引起腐烂的免疫系统。

它不是帮 AI 写更快的工具。它是阻止 AI 毁掉你已建东西的那层防护。

---

## 来自真实的痛苦

Carror OS 不是一个架构师设计的。它诞生于六个月真实的 AI 辅助开发：

> **六个月。零 Go 经验。一个完全用 AI 搭建的云平台。**

平台跑起来了。但在这个过程中，AI 在长对话中删除了正常工作的代码，将 `.env` 密钥发给了外部 API，用有问题的代码宣布"完成"，并在 20 轮对话后忘记所有规则。

**Carror OS 的每一个 Hook，都对应着那六个月中真实发生的一场灾难。**

然后我们用 Carror OS 从头搭建了**第二个项目**——同样规模、同样 AI、同样工作流。零数据泄露。零幻觉驱动的删除。零无证据的"完成"声明。

Carror OS 不是我们做好然后请别人测试的框架。**它是我们在建造下一个东西时穿着的盔甲。**

## 适用人群

| ✅ 适合 | ❌ 不适合 |
|-------------|-----------|
| 使用 AI 做生产代码的团队 | 只需要自动补全的个人开发者 |
| 需要审计追溯和合规的企业 | 速度高于安全的项目 |
| 害怕 AI `rm -rf` 的工程师 | 无条件信任 AI 的人 |
| 拥有大型代码库的长期项目 | 一次性原型脚本 |

---

## 理念

> **"先守护，后武装。"**
>
> 大多数 AI 工具竞相赋予模型最大自主权。Carror OS 走相反的方向：**先加固外围，再增加能力。**

三级架构体现了这一点：

1. **仅 Harness** — 32 个静默拦截器。零认知负荷。AI 只是被戴上了手铐。
2. **Base 版** — 增加 10 个自动化审查门禁。被动、隐形、始终开启。
3. **Enhanced 版** — 全 24 个 Skill 武器库。主动编排。需要指挥官。

你可以选择想要的控制程度。刹车永不松懈。

---

## 实战验证

- **L1-L4 四层测试**（手动验收 + 自动 Hook 校验 + 代码扫描 + 格式门禁）— 98 PASS / 0 FAIL
- **ShellCheck / Bandit 安全扫描** — 0 真实缺陷
- **行业标准自评合规对照**（OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0）— 75/75 覆盖 [内部自评，非第三方认证]
- **5 种语言 Profile** — Go、Python、Node、Rust、通用
- **跨平台** — Claude Code + OpenCode + 任何兼容 AGENTS.md 的 IDE

---

## 开始使用

```bash
# 克隆或下载
git clone https://github.com/sylph/carror-os.git
cd carror-os

# 安装到你的项目
bash install.sh base       # 静默守护者
bash install.sh enhanced   # 全武器库
```

安装后：
- `/lx-status` — 查看防御面板
- `/lx-rpe new MyFeature` — 启动任务流水线
- 试试 `rm -rf /tmp/test` — 看 Hook 如何阻止你

---

## 许可证

MIT。Carror OS by Sylph。

---

*"不要用'应该没问题了'——先拿出 VERIFIED 证据。" — Carror OS 宪法，第 6 条*
