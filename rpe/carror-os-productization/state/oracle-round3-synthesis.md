# Oracle Round 3 合成报告 — 最终验证

> 日期: 2026-05-04 | 状态: ✅ 已完成 (12/12 全部裁决, RPE-015/Mirror 已删除)
> 方法: 每个特性独立 Oracle 专家代理, 全量代码审查 + 结构化作答

---

## 裁决总览

| # | 特性 | 裁决 | 关键条件 | 执行建议 |
|---|------|------|---------|---------|
| 1 | Error DNA 重写 | ⏳ 部分完成 (orphaned) | 4 bug 确认, 重写方案已定 | 需重新验证或沿用 Round 2 方案 |
| 2 | Loading Benchmark | ⏳ 部分完成 (orphaned) | 方法论已设计, 无最终 GO/NO-GO | 需重新验证或沿用 Round 2 方案 |
| 3 | Audit Trail 修复 | ✅ GO (条件) | 5 缺陷全部确认, 修复方案清晰 | 正常执行 |
| 4 | 统一特性注册表 | ✅ GO (条件) | Schema + skills_enabled + probe 三件套 | 正常执行 |
| 5 | Agentic UI 菜单 | ❌ NO-GO | O7/O8 测试→钩子不匹配, 需扩展覆盖全部 4 钩子 | **必须扩展 AC 后重审** |
| 6 | Lecture 系列 | ✅ GO | 8 篇 + 7 模板 + Mermaid + sync_check | 正常执行 |
| 7 | Docs BIMODAL 重构 | ✅ GO (条件) | 6 子目录 + 3 入口 + sync 检查 | 正常执行 |
| 8 | Error DNA 共享库 | ⏳ 依赖 RPE-001 | 等 RPE-001 完成 | 正常排队 |
| 9 | Feature Probe 增强 | ✅ GO (条件) | **AC 需重新分配至 RPE-004/005/012** | 见下方 AC 重分配 |
| 10 | Marketing 重写 | ❌ NO-GO (3 阻塞) | 12% 验收覆盖 + 12 "分析"框残留 + 零 launch asset | **Phase 2 完成后重审** |
| 11 | Launch Asset 补全 | ❌ NO-GO (0 进展) | 截图/视频/dogfooding/外部审查全部为零 | **Phase 2 完成后重审** |
| 12 | lx-status 升级 | ✅ GO | Token 趋势 + Error DNA + Flywheel 三面板 | 提前至 Phase 1.5 |
| 13 | Audit 统一仪表盘 | ✅ GO | 5 源聚合 + SHA256 防篡改 | 提前至 Phase 1.5 |
| 14 | OMA Lock 增强 | ✅ GO | mkdir 锁 + .stealing + 300s 超时 + meta.json | Phase 5 正常执行 |
| 16 | Race 调度增强 | ✅ GO (条件) | **删除 RPE-014 依赖 (独立执行)** | 修正后正常执行 |
| 17 | Flywheel 增强 | ✅ GO | 空日志防护 + 月度趋势 + 桌面通知 | 正常执行 |

---

## 关键发现

### 1. 实锤 Bug: posttool-write-lock.sh 嵌入式换行符 Bug

OMA Lock Round 3 代理通过 `cat -e` 发现:
- `.claude/hooks/posttool-write-lock.sh` 中 TOOL_NAME 比较字符串包含字面换行符
- `[[ "$TOOL_NAME" != "edit" ]]` 条件永不为真 → posttool 永不调用 `release_lock()`, 产生孤儿锁
- 同样存在于 `source/harness-kit/.claude/hooks/posttool-write-lock.sh`

**修复**: RPE-014 AC-14.1 包含此修复 (mkdir 锁替代方案自动解决)

### 2. 僵尸代码: Context Monitor 系统

plan.md 多处引用 `context_monitor.py` 和 `token-tracking-index.json`:
- `context_monitor.py` → **磁盘上不存在** (仅存在于 plan.md 和 context_guard.md 文档中)
- `token-tracking-index.json` → **无写入者** (没有任何代码写入此文件)
- 整个 Context Guard 系统围绕不存在的文件构建

**修正**: RPE-003 AC-3.3 删除 `context_monitor.py` 引用, 改为创建写入者或移除功能

### 3. RPE-009 AC 重分配

Feature Verification Round 3 代理裁定:

| 原 AC | 目标 | 原因 |
|-------|------|------|
| AC-9.1: completion-gate 使用 registry | RPE-005 (新 AC-5.6) | 这是 Agentic UI 的增强, 不是 probe 功能 |
| AC-9.2: feature-probe.sh L1-L4 证据报告 | RPE-004 (合并到 AC-4.4) | feature-probe.sh 是 AC-4.4 的产物, 同属一个交付 |
| AC-9.3: lx-status 集成 | RPE-012 (新 AC-12.4) | lx-status 集成自然属于可视化阶段 |

**RPE-009 删除** (全部 AC 已分配至其他 Task)

### 4. RPE-005 AC 扩展 (Agentic UI)

Agentic UI Round 3 代理发现 O7/O8 测试期望正则 `^\s+[123]\.`, 但仅 permission-gate 和 pretool-edit-scope 有阻塞消息 (非 numbered 菜单). 需要:

| 新增 AC | 描述 |
|---------|------|
| AC-5.4 | permission-gate.sh 增加 numbered-choice 菜单 (1. 写入标记文件 / 2. 取消操作) |
| AC-5.5 | pretool-edit-scope.sh 增加 numbered-choice 菜单 (1. 强制编辑 / 2. 取消 / 3. 切换到新分支) |
| AC-5.6 (原 AC-9.1) | completion-gate 使用 feature-registry.yaml 作为证据预期来源 |
| O9/O10 测试 | 新增 permission-gate 和 pretool-edit-scope 的 numbered 菜单验收测试 |

### 5. Phase 1.5: Observability 阶段

Agentic UI Round 3 代理建议 RPE-012 + RPE-013 提前至 Phase 1.5 (Phase 1 之后立即执行), 理由:
- RPE-012 (lx-status 升级) 的 Token 趋势面板在 Phase 2-5 全程可复用
- RPE-013 (Audit 统一仪表盘) 的 5 源聚合在 Phase 2-5 全程可复用
- Phase 4 原本就需要可视化, 提前可在开发过程中获得反馈

**新 Phase 结构**:
- Phase 1: 高优先级修复 (RPE-001~005)
- **Phase 1.5: 可观测性 (RPE-012, RPE-013)**
- Phase 2: 文档化 (RPE-006~008)
- Phase 3: 对外化 (RPE-010, RPE-011)
- Phase 5: 增强 (RPE-014~017)

**Phase 4 删除** (RPE-012/013 移至 Phase 1.5)

### 6. RPE-016 依赖修正

Race 调度 Round 3 代理确认 Race 模式与 OMA Lock 是**正交功能**:
- Race 模式是"任意顺序编排"而非真并发
- Race 不需要 OMA 锁 — 它使用目录隔离 (`.omc/race/{id}/`)
- 删除 RPE-016 对 RPE-014 的依赖

### 7. Loading Benchmark & Error DNA

两个特性因上下文压缩而 orphaned, 但其 Round 2 方案已足够成熟:
- **Error DNA**: Round 2 已确定 Sentinel File + JSONL 双格式 + 轮转方案
- **Loading Benchmark**: Round 2 已确定 tiktoken cl100k_base 基线测量法
- Round 3 代理读取了大量文件但未输出最终裁决
- **建议**: 沿用 Round 2 方案直接进入执行, 或单独重新 Round 3

---

## 执行顺序建议

```
Phase 1: RPE-001 → RPE-002 → RPE-003 → RPE-004 → RPE-005 (扩展版)
     ↓
Phase 1.5: RPE-012 → RPE-013
     ↓
Phase 2: RPE-006 → RPE-007 → RPE-008 (依赖 RPE-001)
     ↓
Phase 3: RPE-010 → RPE-011 (依赖 Phase 2 完成)
     ↓
Phase 5: RPE-014 → RPE-016 (无依赖) → RPE-017
```

**RPE-009 已删除** (AC 分配至 RPE-004, RPE-005, RPE-012)

---

## 未解决问题

1. **Error DNA (RPE-001)**: Round 3 未出明确裁决 — 需要沿用 Round 2 方案或重新咨询
2. **Loading Benchmark (RPE-002)**: 同上, Round 3 未出明确裁决
3. **Productization (RPE-010, RPE-011)**: NO-GO 但可通过 — 只需填充 manual-acceptance-test-log.md 和删除"分析"框即可突破阻塞
4. **Marketing 与 Lecture 的同步**: RPE-010 AC-10.3 要求引用 manual-acceptance-test.md, 该文件需在 Phase 2 完成后才有完整数据
