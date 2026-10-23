# 根因置信度评分

## 评分标准（满分 25 分）

每个维度的评分锚点：

| 维度 | 5分（强） | 3分（中） | 1分（弱） |
|------|----------|----------|----------|
| **证据强度** | 有 grep/ast-grep/LSP 直接证据 | 间接证据（日志/推断） | 仅代码推测 |
| **可复现性** | 已创建最小复现脚本（稳定≥3/5次） | 间歇复现（<3/5次） | 仅理论/一次性 |
| **跨系统一致性** | 多个模块/服务确认一致 | 2个模块受影响 | 仅单点 |
| **设计可追溯性** | 定位到确切PR/架构决策 | 找到相关commit | 无记录 |
| **防御可行性** | 完整防护（interface+context+sync等） | 部分防御（单层） | 仅"加强培训" |

## 计算公式

总分 = (ES + RP + CS + DT + AF) / 25 × 25

其中 ES=证据强度, RP=可复现性, CS=跨系统一致性, DT=设计可追溯性, AF=防御可行性
每维最高5分，最低1分。总分范围 5-25 分。

## 分数阈值
| 分数 | 动作|
|------|------|
|≥ 18 | 进入 Phase 4|
|18-20（边界区） | 必须有 2 个独立证据来源交叉验证|
|13-17 | 升级至 Oracle 咨询|
|< 13 | 调查终止——证据不足 |

## 评分模板
Phase 3 完成后填写：

```Confidenc
e
: [X]/25- Evidence strength: [N]/5 (source: [tool])- Reproducibility: [N]/5 (repro script: yes/no)- Cross-system: [N]/5 (modules affected: [list])- Traceability: [N]/5 (source: [commit/PR/doc])- Actionability: [N]/5 (defense: [mechanism])Boundary zone (18-20): Source 1: [tool] | Source 2: [tool]
Confidence: [X]/25- Evidence strength: [N]/5 (source: [tool])- Reproducibility: [N]/5 (repro script: yes/no)- Cross-system: [N]/5 (modules affected: [list])- Traceability: [N]/5 (source: [commit/PR/doc])- Actionability: [N]/5 (defense: [mechanism])Boundary zone (18-20): Source 1: [tool] | Source 2: [tool]
```

## 截断输出惩罚
若任意维度的证据使用了截断的工具输出（包含 `...`、`truncated`、`> N lines`、`output omitted`）：- 该维度自动扣 **-2 分**- 必须以更大的输出限制重新执行工具，再使用该证据
