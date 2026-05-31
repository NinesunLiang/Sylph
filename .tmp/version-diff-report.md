# Carror OS 线上版 vs 当前版对比报告
**时间**: 2026-05-31 09:40 CST | **版本**: v6.3.27
**对比源**: 开发源(根目录) vs 发行源(source/harness-kit/)

---

## 一、整体差异矩阵

| 文件 | 开发版 | 发行版 | 结论 |
|------|--------|--------|------|
| AGENTS.md | 74行/6.3KB | 1261行/68KB | 开发版=紧凑路由表 ✅ 发行版=38KB百科全书(待压缩) |
| CLAUDE.md | 1行/11B | 1行/11B | ✅ 一致 |
| kernel.md | 173行/8.3KB | 181行/9.6KB | 开发版=数字资产管理内核 ✅ 发行版=旧编码规范(待同步) |
| index.md | 49行/2.5KB | 96行/5.3KB | 开发版=Event:Matcher路由表 ✅ 发行版=项目知识导航(不同用途) |
| context-compressor.sh | 170行/6.5KB | 167行/6.4KB | 开发版=已修复FORCE_REGEN ✅ 发行版=含死循环bug |
| compact-detect.sh | 101行/3.5KB | 101行/3.5KB | ✅ 一致 |
| harness.yaml | 171行/5.2KB | 171行/5.2KB | ✅ 一致 |
| settings.json | 610行/14.7KB | 572行/13.7KB | 开发版多1个hook(pretool-node-reference) |

---

## 二、线上版值得采纳的内容（按优先级排序）

### 🔴 高价值，建议补入

| # | 内容 | 线上版行号 | 开发版现状 | 补入方式 |
|---|------|----------|-----------|---------|
| 1 | **狗粮Triage决策树** | L256-280 | lx-dogfood skill有，路由缺 | AGENTS路由+1行 → Read `.claude/skills/lx-dogfood/SKILL.md` |
| 2 | **三源一致性操作化(A→B→A三重门)** | L91-105 | reference/three-source-consistency.md有 | ✅ 已有路由入口 |
| 3 | **Red Team/Blue Team机制** | L124-133 | 完全缺失 | kernel.md 资产地图加 entry，指向 `.claude/reference/red-team.md`（需创建） |
| 4 | **Source Mirror同步纪律** | L35-51 | 缺失 | 路由+1行 → Read `source/harness-kit/SOURCE-DISCIPLINE.md` |

### 🟡 中等价值，评估后采纳

| # | 内容 | 说明 |
|---|------|------|
| 5 | Oracle选型标准(L941-953) | 选择local/remote/fallback的判断树 |
| 6 | 交接格式模板(L958-1037) | 结构化交接格式，比当前kernel.md的6步更详细 |
| 7 | 证据层级与置信度(L1133-1154) | file:line > 截图 > 日志 > 推理 |

### 🟢 低价值/反模式，不应采纳

| # | 内容 | 为什么不采纳 |
|---|------|-------------|
| 8 | 哲学宣言全文(L57-73) + 哲学如何组织行为(L567-605) | 课堂式冗长，违反哲学#1。开发版已压缩为1行优先级 |
| 9 | 完整开发流程7步详细说明(L337-359) | 重复。开发版"难度分级"4行已覆盖 |
| 10 | 铁律展开每条的详细说明(L641-679) | 重复。开发版铁律已自说明 |
| 11 | 软完成语禁令全部列举(L723-756) | 重复。开发版编码内核1行已覆盖 |
| 12 | 机制→哲学逆向追溯矩阵(L473-506) | 重复。reference/philosophy-mechanism-matrix.md有 |

---

## 三、开发版优于线上版的地方

| 创新 | 说明 |
|------|------|
| **紧凑路由表** | 74行 vs 1261行 → 压缩92.3%，注入从68KB降至6.3KB |
| **三门户分离** | AGENTS(主门户)+kernel(资产)+index(路由)，权责分明 |
| **数字资产管理内核** | kernel.md 从编码规范转型为知识进化引擎（管道5阶段+Compact交接+E1E2） |
| **Read on demand** | 零@展开的路由索引，agent按需read_file |
| **难度分级** | L1-L4 + Oracle/Meta-Oracle触发规则，比线上版的L1/L3更完整 |
| **FORCE_REGEN修复** | context-compressor死循环已修，线上版仍有bug |
| **编码内核集中** | 命名/测试/禁止模式集中在AGENTS.md正文，不在kernel中 |

---

## 四、执行建议

### 即刻执行（本次会话）
1. ~~Skills入口补skills-catalog.md~~ ✅ 已完成
2. ~~发布流水线入口~~ ✅ 已完成
3. AGENTS路由+2行：狗粮Triage + Red Team

### 下次打包同步
4. kernel.md(181行) 替换为 开发版(173行)
5. index.md(96行) → 保持发行版风格（项目知识导航，不是hooks路由表）
6. context-compressor.sh 修复同步到发行版
7. AGENTS.md → 发行版独立压缩（保持1261→~200行精简版，不需要和开发版一样）

### Boss决策
8. 12个孤儿/僵尸hook清理 → 等Boss确认
9. 18个CHANGELOG-6.3.*.md模板复制 → 等Boss确认
