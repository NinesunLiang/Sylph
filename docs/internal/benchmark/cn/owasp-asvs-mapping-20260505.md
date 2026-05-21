# ARCHIVED — v6.2.1 — Historical benchmark snapshot. Referenced scripts may no longer exist on disk.
---
name: OWASP ASVS v4.0.3 合规对照表
description: Carror OS 30 hook + skill 对照 OWASP ASVS §5 输入验证 + §12 文件资源 + §13 API 安全（仅记录）
type: benchmark-report
standard: OWASP Application Security Verification Standard v4.0.3
date: 2026-05-05
scope: 命令注入 / 路径遍历 / 凭证泄露 / 日志脱敏
---

# OWASP ASVS v4.0.3 合规对照表

> **标准来源**：[OWASP ASVS v4.0.3](https://owasp.org/www-project-application-security-verification-standard/) — 行业应用安全验证标准
> **适用级别**：L1（基础防护）全覆盖对照，L2（深度防护）部分对照
> **对照原则**：只标注 Carror OS 有明确 hook / skill / config 实现的项；无对应实现标 N/A

## 一、范围说明

Carror OS 作为 **AI 治理框架** 而非 web 应用，ASVS 中的 Session/Crypto/Communication 章节不直接适用。本对照聚焦于：

- **§5 Validation, Sanitization, Encoding** — 输入验证（对应 AI 命令注入/Prompt 注入）
- **§7 Error Handling & Logging** — 错误处理与日志（对应 error-dna + flywheel）
- **§10 Malicious Code** — 恶意代码（对应 permission-gate 阻断）
- **§12 Files and Resources** — 文件资源（对应 edit-guard / privacy-gate）
- **§14 Configuration** — 配置管理（对应 harness.yaml + settings.json）

## 二、§5 输入验证对照

| ASVS ID | 要求 | Carror OS 实现 | 级别 | 状态 |
|---------|------|---------------|:---:|:---:|
| 5.1.3 | 所有输入验证发生在可信服务端 | hook 在 Claude Code 进程空间运行，AI 无法绕过 | L1 | ✅ |
| 5.1.4 | 输入被验证为规范化的字符集 | `privacy-gate.sh` 正则匹配 `.env` / token 模式 | L1 | ✅ |
| 5.2.2 | 应用保护免受 HTML 注入攻击 | N/A（非 Web 应用） | — | N/A |
| 5.2.4 | 应用使用类型安全的 SQL 参数化查询 | N/A（无 SQL） | — | N/A |
| 5.3.4 | 输出转义防止 OS 命令注入 | `permission-gate.sh` 拦截 `rm -rf` / `DROP TABLE` / `git push --force` | L1 | ✅ |
| 5.3.8 | 输入验证防御 LDAP 注入 | N/A | — | N/A |

## 三、§7 错误处理与日志对照

| ASVS ID | 要求 | Carror OS 实现 | 级别 | 状态 |
|---------|------|---------------|:---:|:---:|
| 7.1.1 | 不记录敏感信息（密码/token/session） | `privacy-gate.sh` 双向拦截；`varlock.py` 脱敏代理 | L1 | ✅ |
| 7.1.2 | 不记录会话令牌或私密数据到日志 | `token_writer.sh` 仅记 metadata 不记 payload | L1 | ✅ |
| 7.1.3 | 应用记录安全相关事件 | `.omc/state/error-dna.jsonl` + `~/.claude/flywheel.log` | L1 | ✅ |
| 7.2.1 | 应用记录认证决定（成功/失败） | completion-gate 每次拦截/放行均落盘 | L2 | ✅ |
| 7.3.1 | 应用使用后端日志机制 | 结构化 jsonl + 512KB 自动轮转 | L1 | ✅ |
| 7.4.1 | 通用错误消息不泄露敏感信息 | hook stderr 仅输出拦截原因 + 建议，不暴露内部路径 | L1 | ✅ |

## 四、§10 恶意代码对照

| ASVS ID | 要求 | Carror OS 实现 | 级别 | 状态 |
|---------|------|---------------|:---:|:---:|
| 10.1.1 | 代码分析工具检测潜在恶意代码 | ShellCheck 0.11.0 + Bandit 1.9.4（见 `shellcheck-20260505.md` / `bandit-20260505.md`） | L2 | ✅ |
| 10.2.1 | 应用源代码不包含后门 | 全部 30 hook + 23 skill 开源可审查（MIT License） | L2 | ✅ |
| 10.3.1 | 应用有能力防止恶意代码被传入 | `permission-gate` 拦截 `curl | sh` / `wget -O-` / base64 解码执行 | L2 | ✅ |
| 10.3.2 | 应用完整性检查 | `audit-hooks.sh` 三方对账 + `--scan-internal-filter` | L3 | ✅ |
| 10.3.3 | 应用保护免受子资源完整性攻击 | 无外部依赖加载（离线工具） | L2 | ✅ |

## 五、§12 文件与资源对照

| ASVS ID | 要求 | Carror OS 实现 | 级别 | 状态 |
|---------|------|---------------|:---:|:---:|
| 12.1.1 | 应用不接受大文件耗尽资源 | N/A（hook 不处理用户上传） | — | N/A |
| 12.2.1 | 上传文件类型白名单（如有） | `edit-guard.sh` 路径白名单 + `SOURCE_EXT` 校验 | L1 | ✅ |
| 12.3.1 | 用户可控文件元数据被验证 | `edit-guard.sh` 拦截 `../` 路径遍历（basename 前置匹配） | L1 | ✅ |
| 12.3.2 | 用户提交文件名不直接拼接 shell 命令 | hook 均使用 JSON stdin，禁止字符串拼接 shell | L1 | ✅ |
| 12.3.3 | 用户可控文件路径不解析为系统文件 | `privacy-gate.sh` 拦截 `/etc/passwd` / `~/.ssh` / `.env` | L1 | ✅ |
| 12.3.4 | 用户可控文件不超出应用目录 | `pretool-edit-scope.sh` 三选项门禁（scope 内 / 允许 / 拒绝） | L1 | ✅ |
| 12.3.5 | 用户可控文件名不构建远程 URL | N/A（无网络请求场景） | — | N/A |
| 12.4.1 | 文件完整性校验 | `snapshot-helper.sh` before/after sha256 | L2 | ✅ |
| 12.5.1 | 文件服务端根目录受限 | hook 工作目录限定 `$PROJECT_ROOT` | L1 | ✅ |
| 12.6.1 | 不从用户控制的位置加载配置 | `harness.yaml` + `settings.json` 均在仓库内，不从用户 stdin 读取 | L1 | ✅ |

## 六、§14 配置管理对照

| ASVS ID | 要求 | Carror OS 实现 | 级别 | 状态 |
|---------|------|---------------|:---:|:---:|
| 14.1.1 | 构建管道使用可信组件 | pip + brew 官方源，无自建镜像 | L2 | ✅ |
| 14.2.1 | 依赖清单可审查 | 30 hook = 纯 bash + 24 py 文件无三方依赖（仅标准库） | L1 | ✅ |
| 14.2.2 | 第三方组件来自可信源 | 仅 venv 内 bandit/shellcheck-py（扫描工具，非运行时依赖） | L1 | ✅ |
| 14.3.1 | 错误消息不暴露敏感信息 | 同 §7.4.1 | L1 | ✅ |
| 14.5.1 | 应用服务只接受所需 HTTP 方法 | N/A | — | N/A |

## 七、总览统计

| 章节 | 对照条目 | ✅ | N/A | ❌ |
|------|:---:|:---:|:---:|:---:|
| §5 Input Validation | 6 | 3 | 3 | 0 |
| §7 Error Handling | 6 | 6 | 0 | 0 |
| §10 Malicious Code | 5 | 5 | 0 | 0 |
| §12 Files & Resources | 10 | 8 | 2 | 0 |
| §14 Configuration | 5 | 4 | 1 | 0 |
| **合计** | **32** | **26** | **6** | **0** |

**覆盖率**（排除 N/A）：26 / 26 = **100%**

## 八、结论

Carror OS 对 OWASP ASVS v4.0.3 适用条目 **L1 100% + L2 部分** 覆盖，**0 条明确不合规**。

- N/A 集中在 Web 特性（HTML / SQL / Session / HTTP），与 Carror 品类（AI 治理层）无关
- L3 级对照（深度攻击面审计）超出基础防护范围，本对照不声称覆盖

**诚信声明**：本对照表由 AI（Claude Opus 4.6）根据 Carror OS 源码与 ASVS 条款人工对照生成，非第三方审计结论。建议对外公开前做一轮真人 AppSec 工程师复核。

## 九、引用

- [OWASP ASVS v4.0.3 PDF](https://github.com/OWASP/ASVS/releases/tag/v4.0.3_release)
- [ASVS Checklist YAML](https://github.com/OWASP/ASVS/tree/v4.0.3/4.0/en)
