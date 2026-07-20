# 孪生 .sh 文件安全删除分析报告

> 分析范围: `.claude/hooks/`
> 分析日期: 2026-06-07

## 一、废弃可删（.sh 未注册/未引用，.py 单独生效）

这些 .sh 文件有同名 .py 孪生，但 settings.json 中只注册了 .py 版本，.sh 已被废弃且未被任何其他文件调用。

| 文件 | 注册情况 | 理由 |
|------|---------|------|
| `posttool-output-compressor.sh` | .py 和 .sh 均未在 settings.json 注册 | 孪生 .py 也未注册，两者都未被激活。但 .sh 是孪生文件，可安全删除 |
| `pretool-retry-check.sh` | settings.json 仅注册 `pretool-retry-check.py`（line 121） | .sh 未注册，无任何脚本引用 |
| `privacy-gate.sh` | settings.json 仅注册 `privacy-gate.py`（line 151） | .sh 未注册，无任何脚本引用 |
| `subagent-guard.sh` | settings.json 仅注册 `subagent-guard.py`（line 196） | .sh 未注册，无任何脚本引用 |

**共 4 个 .sh 文件可安全删除。**

## 二、双激活不可删（.sh 和 .py 均在 settings.json 中注册）

这些 .sh 文件与同名 .py 文件一起在 settings.json 中被显式注册为 `bash ...sh` 命令，删除会破坏功能。

| 文件 | 注册位置（settings.json line） |
|------|-------------------------------|
| `context-guard.sh` | line 156（.py at line 41） |
| `edit-guard.sh` | line 76（.py at line 21） |
| `fuzzy-block.sh` | line 236（.py at line 231） |
| `lsp-suggest.sh` | line 186（.py at line 181） |
| `meta-oracle-trigger.sh` | line 419（.py at line 413） |
| `permission-gate.sh` | line 141（.py at line 116） |
| `pre-ask-guard.sh` | line 171（.py at line 166） |
| `pre-completion-gate.sh` | line 211（.py at line 206） |
| `pretool-edit-scope.sh` | line 106（.py at line 61） |
| `pretool-oracle-gate.sh` | line 16（.py at line 11） |
| `pretool-plan-gate.sh` | line 81（.py at line 100） |
| `pretool-sensitive-edit.sh` | line 87（.py at line 96） |

**共 12 个 .sh 文件不可删除（双激活状态）。**

## 三、额外发现

- `posttool-output-compressor.sh` 的孪生 `.py` 文件也未注册，两者均处于游离态
- 所有可删除的 .sh 文件均未被 `scripts/`、`.claude/scripts/`、`harness.yaml`、`feature-registry.yaml` 或任何 `.md` 文件引用
- `source/harness-kit/` 镜像目录中不含这些 .sh 文件以外的额外引用

---

**结论**: 4 个 .sh 文件可安全删除，12 个必须保留。
