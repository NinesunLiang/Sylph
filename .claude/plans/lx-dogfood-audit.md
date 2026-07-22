# lx-dogfood 审计方案

## 当前状态
- 引用: 全部存在 ✅
- dogfood 状态目录: 空（0条记录）
- claude-next.md DG-XX 格式: 从未使用（0条目）
- 16个触发器（过于宽泛）
- 与 error-dna hook（自动采集错误）完全重叠

## 问题
1. **从未被使用** — .omc/state/dogfood/ 空, claude-next.md 无 DG-XX 条目
2. **与 error-dna 重叠** — error-dna.py 已自动采集错误到 error-dna.jsonl
3. **与 RCA 重叠** — lx-root-cause-analysis 已在做根本原因分析
4. **认知负担** — 16个触发词，中低阶模型会困惑该不该调用
5. **复杂度过高** — YAML写入 + claude-next追加 + 升华管道，对Base太重

## 建议: 归档

错误采集能力已由 error-dna hook + claude-next.md 覆盖。狗粮投喂是个好概念但当前实现从未被使用，不应留在 Base 增加认知负担。
