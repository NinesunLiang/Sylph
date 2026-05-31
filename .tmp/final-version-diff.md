# Carror OS 线上版(发行版) vs 线下版(开发版) 对比报告
**时间**: 2026-05-31 | **版本**: v6.3.27+

---

## 一、文件级差异

对比 26 个核心治理文件：

| 状态 | 数量 | 说明 |
|------|------|------|
| 🟢 完全相同 | 17 | hooks/skills/scripts 已通过 package-release.sh 同步 |
| 🔴 有差异 | 9 | 见下文 |

| 文件 | DEV行数 | PKG行数 | Δ | 差异原因 |
|------|---------|---------|---|---------|
| AGENTS.md | 77 | 1261 | +1184 | 刻意不同：DEV=紧凑路由表，PKG=完整百科全书 |
| index.md | 49 | 96 | +47 | 刻意不同：DEV=hooks路由，PKG=项目知识导航 |
| harness.yaml | 168 | 171 | +3 | DEV新增：knowledge_condenser/build_validator/error_dna_auto_fix=true |
| settings.json | 640 | 572 | +68 | DEV新增：4个hook注册 + 幽灵清理 |
| harness-smoke-test.sh | 2139 | 1994 | +145 | DEV新增：R37-R39测试(知识管道+构建卫士) |
| capability-matrix-test.sh | 835 | 694 | +141 | DEV更新：更多测试覆盖 |
| context-compressor.sh | 170 | 167 | +3 | DEV修复：FORCE_REGEN死循环修复 |
| claude-next.md | 577 | 563 | +14 | DEV新增：本次会话教训 |
| philosophy-mechanism-matrix.md | 400 | 399 | +1 | 微小差异 |

**结论：所有9个有差异的地方，DEV > PKG。开发版领先。**

---

## 二、线上版独有价值（可采纳）

PKG AGENTS.md (1261行) 中有但 DEV 缺失的内容：

### 🔴 已采纳（前次会话）
| 内容 | 采纳方式 |
|------|---------|
| Source Mirror同步纪律 | +source-mirror-discipline.md + 路由条目 |
| 狗粮Triage决策树 | +路由条目 → lx-dogfood/SKILL.md |
| Red Team/Blue Team | +red-team.md + 路由条目 |

### 🟡 建议采纳（本次）
| # | 内容 | PKG行号 | 价值 | 建议方式 |
|---|------|---------|------|---------|
| 1 | **机制保留/删除判定原则** (意图不对 vs 实现不对) | L295-319 | 高——反映ED-01教训，与本次hook接线直接相关 | 创建 `.claude/reference/mechanism-lifecycle.md` + 路由条目 |
| 2 | **狗粮反馈循环6步操作协议** | L282-293 | 中——已通过lx-dogfood覆盖，但6步协议更具体 | 补充到 lx-dogfood SKILL.md 或单独 reference |
| 3 | **置信度标注格式** (已验证/已测试/推断) | index.md L47-50 | 中——当前编码内核有L1/L2证据但缺格式模板 | 补入 AGENTS.md 编码内核 |
| 4 | **维护操作表** (install/update/uninstall) | index.md L9-20 | 低——面向用户而非AI | 保留在PKG版即可 |

### 🟢 不采纳（已在DEV以更好形式存在）
| PKG内容 | DEV已有 |
|---------|--------|
| 铁律速查表(index.md) | AGENTS.md 铁律8条 (更紧凑) |
| 记忆系统表(index.md) | kernel.md 资产生命周期 (更详细) |
| 哲学宣言全文 | AGENTS.md 1行优先级锁链 (更高效) |
| Meta-Oracle详解 | reference/meta-oracle.md |
| 三源一致性详解 | reference/three-source-consistency.md |

---

## 三、执行建议

| 优先级 | 操作 |
|--------|------|
| 🔴 | 创建 mechanism-lifecycle.md (机制生命周期判定) + 路由条目 |
| 🟡 | 补置信度格式到编码内核 |
| 🟢 | 下次 package-release 同步时，PKG AGENTS.md 压缩为精简版(~200行) |
