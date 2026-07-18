**GPT-5.6 Sol 补充审核结论**

Kimi v3.0 已经吸收了我上一轮的主要阻断项。我的总体判断是：

> **架构可以 Sign-off；执行规格尚不能称为“修复项全部定型”。**  
> Grok 提出的 R1、R2、R3、R4、R6 基本成立，但 R5 的状态枚举方案不应原样采纳。除此之外，我再补 4 个更底层的问题：**信任边界、manifest 摘要自引用、finalize 时序循环、基线不可重现。**

当前仍应是 **v3.0-rc2 / Execution No-Go**。下面的问题落地并取得 smoke 证据后，才是单页 Conditional GO。

**一、对 Grok R1–R6 的裁决**

### R1 门禁权威链：接受，但“优先级”还不够

Grok 正确指出：如果模型能直接修改 `token.json`，再由 `finalize-page.sh` 相信 token，P0-4 只是把伪造入口从 summary 移到了 token。

应明确：

```text
manifest         = 人类签署的 desired state
gate-results     = 门禁产生的 observed facts
token.json       = carros_base 根据 observed facts 推导的进度缓存
machine-summary  = finalize 根据 observed facts 重算的结果
acceptance_report = 展示产物
```

因此不是简单的：

```text
gate-results > machine-summary > token
```

而是：

```text
final_status = reduce(manifest, gate-results, execution-events)
```

`token.json` 不能作为最终结论输入，只能作为恢复提示。恢复时也必须重新校验对应 gate result，而不能看到 `*_VERIFIED` 就直接续跑。

### R2 C6 失败回退：完全接受

这是 Kimi v3.0 的真实状态机缺口。C6 失败后必须允许进入修复态，否则“VISUAL_VERIFIED 后禁写”容易被错误实现为永久禁写。

建议不要把失败页伪装成已验证态回退，而是增加明确状态：

```text
VISUAL_FIXING
```

进入该状态时：

1. 撤销当前 `code_sha` 的证据资格；
2. 清除或隔离该 SHA 的 artifacts；
3. 允许受限源码修改；
4. 修改完成后从 C1 全链重跑；
5. 旧 gate-results 标为 `SUPERSEDED`，不得删除。

所有影响 `src/`、`tests/`、构建配置和依赖锁的改动，都必须使 C1–C7 后续结果失效。

### R3 静态原型分型：接受

Kimi 的“逐一触发所有交互元素”只适用于可交互原型。静态图不能承担交互发现职责。

应加入：

```yaml
prototype:
  kind: interactive | static | mixed
  interaction_scan_required: true | false
```

静态输入下缺失浮层契约应走 `BLOCKED_INPUT`，不能归因于夜间 research 失职。`overlays: []` 也有歧义，应改为：

```yaml
overlay_contract:
  status: declared | confirmed_none | unknown
  items: []
```

只有 `declared` 或 `confirmed_none` 才能冻结 plan；`unknown` 必须在 Phase 0 解决或阻塞。

### R4 权威链攻击 smoke：完全接受

现有“五类 smoke”必须包含这些攻击场景。尤其要测：

- 伪造 token；
- 伪造 gate result；
- 伪造 summary；
- 替换 evidence；
- 弱化测试；
- 修改门禁脚本自身；
- 门禁进程被 kill；
- gate 输出只写了一半；
- exit 0 但结果文件缺失；
- 结果文件 PASS 但进程 exit 非 0。

退出码和结果文件冲突时必须 fail-closed。

### R5 状态与码表正交：接受问题，拒绝其具体方案

Grok 发现 `FAILED_INVARIANT` 被塞进“七阻塞码”是对的，但不应把：

```text
CRASHED / NOT_STARTED
```

扩进 `final_status`。Kimi 已经定义它们是晨报派生态，应该保持这一点，否则再次破坏“三值终局”。

建议：

```yaml
execution_status:
  NOT_STARTED | RUNNING | CRASHED | TERMINATED

final_status:
  DONE | BLOCKED | FAILED | null

blocked_code:
  BLOCKED_INPUT | BLOCKED_SCOPE | BLOCKED_ENV |
  BLOCKED_BUDGET | BLOCKED_HUMAN | BLOCKED_VISUAL_P0 | null

failed_code:
  FAILED_INVARIANT | FAILED_TOOLCHAIN |
  FAILED_FIX_LOOP | FAILED_UNKNOWN | null
```

`final_status` 只有任务真正终结后才非空。晨报用 `execution_status` 表达崩溃和未启动。

### R6 机器化 scorecard：接受

“控制面 8 问”不能只存在于 Markdown。建议同时输出：

```text
control-plane-scorecard.yaml
control-plane-scorecard.md
```

其中 YAML 是机器事实，Markdown 是展示。晋级规则只读取 YAML。

但 `control_plane_green` 也不能作为手填字段，应由固定 reducer 根据各计数推导。

---

**二、我新增的 4 个阻断项**

### S1 同一执行身份下，“模型物理上无权写结论”并不成立

这是当前最重要的剩余问题。

如果 DeepSeek 所在进程能够：

- 修改 `scripts/finalize-page.sh`；
- 修改 `gate-results/*.json`；
- 修改 `token.json`；
- 修改 `.git/hooks` 或 PreToolUse hook；
- 直接执行任意 Shell；

那么“禁止模型写 machine-summary”只是工作流约定，不是物理权限。模型完全可以先改门禁，再让门禁替它写 DONE。

必须建立真正的信任边界，至少满足以下一种：

1. 门禁由 CarrorOS 外层 supervisor 运行，执行模型无权修改；
2. 门禁脚本来自只读目录或独立治理仓库；
3. gate-results 写入模型无权限的目录；
4. 每个结果由 supervisor 使用会话密钥签名，finalize 验签；
5. 任务工作树与治理控制目录分离。

推荐最小实现：

```text
repo worktree                    模型可写受控范围
$CARROS_HOME/policies            模型只读
$CARROS_RUN_DIR/gate-results     仅 supervisor 可写
$CARROS_RUN_DIR/final            仅 supervisor 可写
```

否则“篡改 smoke”测过一次，也不能证明真实夜跑时模型不能篡改控制器。

### S2 `manifest_digest` 存在自引用问题，必须定义规范化算法

manifest 内含：

```yaml
human_signoff:
  manifest_digest: "sha256:..."
```

如果摘要覆盖完整 manifest，那么填写 digest 本身会改变被摘要内容，无法稳定验证。

必须明确定义摘要对象，例如：

```text
digest = SHA256(canonical_yaml(
  manifest excluding:
    human_signoff.manifest_digest
))
```

还要明确：

- key 排序；
- 换行规范；
- 字符编码；
- 注释是否参与；
- YAML anchor/alias 如何展开；
- 时间字段是否纳入。

更稳妥的方案是 detached signoff：

```text
night-manifest.yaml
night-manifest.signoff.yaml
```

这不构成“双契约”：前者是唯一任务契约，后者只是签署证明。签署文件记录 manifest 原始字节的 SHA-256，避免 YAML canonicalization 差异。

### S3 `finalize-page.sh` 与 Draft PR URL 存在时序循环

v3.0 同时规定：

- `finalize-page.sh` 生成 machine-summary；
- `draft_pr_url` 唯一来源是 `gh pr create`；
- Draft PR 在 finalize/archive 之后创建；
- summary 是门禁生成且不可手改。

那么第一次 finalize 时还没有 PR URL；创建 PR 后再回填 summary，又会改变交付产物和可能改变 evidence commit。

需要两阶段交付：

```text
finalize-page verify
  → 生成 immutable verification-summary.yaml
  → 若 DONE，创建 Draft PR
  → 生成 delivery-receipt.yaml
  → 渲染 acceptance_report.md
```

其中：

```yaml
verification-summary.yaml:
  final_status
  completion
  gates
  code_sha
  evidence

delivery-receipt.yaml:
  delivery_status
  draft_pr_url
  delivered_at
  evidence_commit_sha
```

不要让 PR URL 进入验证结论文件。GitHub 失败只影响 delivery receipt，不改写 DONE/BLOCKED/FAILED。

### S4 `page_start_sha` 不足以保证依赖与运行环境可重现

`PAGE_BOUNDARY_RESET` 目前主要检查 Git 工作树，但以下状态不一定被 Git 捕获：

- `node_modules` 与锁文件不一致；
- Playwright 浏览器版本变化；
- dev server 使用旧进程；
- service worker/cache/localStorage 残留；
- 环境变量变化；
- mock server 内存状态；
- 端口被上一页进程占用；
- untracked 文件位于 ignored 目录。

首夜至少记录环境指纹：

```yaml
environment_fingerprint:
  node_version:
  pnpm_version:
  lockfile_sha256:
  playwright_version:
  browser_version:
  env_allowlist_digest:
  dev_server_pid:
  dev_server_started_at:
```

`PAGE_BOUNDARY_RESET` 还应清理 browser context、storage state、mock state 和任务级测试产物。否则“工作树干净”不等于“页面基线干净”。

---

**三、对 Kimi 文本本身的三处修订**

1. §4.4 的“阻塞码七枚举”改成阻塞码与失败码两组，不再把 `FAILED_INVARIANT` 算作阻塞码。

2. §5 的禁写时间点应改为“成功进入 `VISUAL_VERIFIED` 后禁写”。C6 FAIL 时不能先进入该状态；进入 `VISUAL_FIXING` 后按受控流程重新开放。

3. §6 的 C8 不应同时承担“验证结论”和“远程交付”。拆为：
   - C8a Finalization；
   - C8b Delivery。
   
   C8b 失败不推翻 C1–C8a 的 DONE，只产生 `DRAFT_PR_FAILED`。

---

**最终结论**

Kimi v3.0 可以作为唯一架构正本；不需要再重新设计整个体系。Grok 的 R1、R2、R3、R4、R6 应纳入，R5 应按“三值终局 + 独立 execution_status”修正。

GA 前还必须补上：

1. 门禁与执行模型之间的真实权限隔离；
2. manifest digest 的非自引用定义；
3. verification summary 与 delivery receipt 的两阶段交付；
4. 环境指纹和非 Git 状态清理；
5. 状态回退及证据失效传播；
6. 权威链攻击 smoke 和机器化 scorecard。

因此我的签署状态是：

> **Architecture: SIGNED OFF**  
> **Execution specification: CONDITIONAL ACCEPT**  
> **v3.0-GA: NO-GO**  
> **首夜：NO-GO，直到上述补丁落盘并取得五类 smoke 的实际输出。**

补丁与 smoke 全绿后，我支持：

> **1 页、Patch A、全 mock、K3=0、仅 DONE 建 Draft PR 的 Conditional GO。**

最关键的补充不是再加一道 grep，而是把“谁有权宣布成功”做成真正的进程与文件权限边界。只要实现模型和裁判仍使用同一写权限，任何“模型不能自己给自己填 DONE”的规则都只是约定。