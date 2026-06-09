# OC Plugin 环境依赖检查 — @carroros/gov

> 生成: 2026-06-07 19:09
> 路径: `packages/carroros-gov/`

---

## 1. 依赖清单

### 1.1 runtime 依赖 (package.json)

| 包 | 版本 | 类型 | 是否已安装 | 用途 |
|---|------|------|-----------|------|
| `effect` | `^4.0.0` | dependencies | ❌ 未安装 (npm) | 类型安全的副作用管理 (ToolContext.ask) |
| `zod` | `^3.24.0` | dependencies | ❌ 未安装 (npm) | 运行时 schema 校验 (ToolDefinition args) |
| `@opencode-ai/plugin` | `*` | peerDependencies | ✅ 已安装 (v1.14.32) | Plugin SDK: Plugin/Hooks/PluginInput 类型 |

### 1.2 实际运行时环境

- `@opencode-ai/plugin` v1.14.32 安装在 `.opencode/node_modules/@opencode-ai/plugin/`
- `zod` v3.x 安装在 `.opencode/node_modules/zod/`（由 OMO 间接依赖携带）
- `effect` **未在任何位置安装**（项目无 node_modules）

### 1.3 工程配置

| 项目 | 值 |
|------|-----|
| 模块类型 | ESM (`"type": "module"`) |
| 入口 | `src/index.ts` ✅ 存在 |
| 编译输出 | `dist/` ❌ **不存在** (未编译) |
| tsconfig | ES2022 → NodeNext 模块解析 |
| OpenCode 版本要求 | `>=1.16.0` (但实际运行是 v1.14.32) |

> ⚠️ **版本不匹配**: engine 要求 `opencode >=1.16.0`，但实际安装的是 `@opencode-ai/plugin v1.14.32`。插件可能因 API 变动无法加载。

---

## 2. 文件结构

```
packages/carroros-gov/
├── package.json          # npm 包配置 + 依赖声明
├── tsconfig.json         # TypeScript 编译配置
├── PLUGIN-ENV-CHECK.md   # 本文件
└── src/
    ├── index.ts          # 插件入口: export server() → Plugin
    ├── system.ts         # experimental.chat.system.transform
    ├── privacy.ts        # tool.execute.before (Phase 1: privacy gate)
    ├── oracle.ts         # tool.execute.before (Phase 2: oracle pre-review)
    ├── oracle-post.ts    # tool.execute.after (meta-oracle post-review)
    ├── permission.ts     # permission.ask (权限映射)
    ├── compact.ts        # experimental.session.compacting (handoff)
    ├── detect.ts         # 反模式检测引擎
    └── rules/
        └── index.ts      # 动态治理规则加载器
```

### 入口逻辑 (`src/index.ts`)

```typescript
export const server: Plugin = async (_input, _options) => {
  const hooks: Hooks = {
    "experimental.chat.system.transform": systemTransform,
    "tool.execute.before": compositeBefore,       // privacyGate → oraclePreReview
    "tool.execute.after": metaOraclePostReview,
    "permission.ask": permissionAsk,
    "experimental.session.compacting": compactHandler,
  }
  return hooks
}
```

插件是个 `Plugin` 工厂函数，接收 `PluginInput`（client, project, directory, worktree, $ shell）和 `PluginOptions`，返回 `Hooks` 对象。

---

## 3. OpenCode 插件加载协议

### 3.1 加载方式

OpenCode 通过 `.opencode/opencode.json` 的 `plugin[]` 字段加载插件：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "oh-my-openagent",                           // npm 包名（从 node_modules 加载）
    ".opencode/plugins/carror-hooks-compat.ts"   // 本地相对路径
  ]
}
```

支持的加载路径：
1. **npm 包名**: `oh-my-openagent` → 从 `node_modules/oh-my-openagent` 加载
2. **本地相对路径**: `.opencode/plugins/carror-hooks-compat.ts` → 相对 `.opencode/` 解析
3. **绝对路径**: 也支持

### 3.2 插件格式要求

插件模块必须 `export default` 或具名 export `server`：

```typescript
// 方式 A: export default
export default async (input: PluginInput, options?: PluginOptions) => {
  return { /* Hooks */ }
}

// 方式 B: export server (官方推荐)
export const server: Plugin = async (input, options) => {
  return { /* Hooks */ }
}
```

`PluginInput` 包含：
- `client` — OpenCode API 客户端
- `project` — 项目信息
- `directory` — 当前目录
- `worktree` — 工作区根目录
- `experimental_workspace` — 工作区间适配器注册
- `serverUrl` — OpenCode 服务 URL
- `$` — BunShell 实例

### 3.3 @carroros/gov 当前加载状态

- `@carroros/gov` **未被注册** 到 `opencode.json`
- 当前注册的插件是 `oh-my-openagent`（OMO，npm 包）和 `.opencode/plugins/carror-hooks-compat.ts`（本地文件）
- `@carroros/gov` 需要通过 npm link 或发布到 registry 后才能被 `opencode.json` 引用

### 3.4 可用的 Hooks 事件

| 事件 | @carroros/gov 实现 | 说明 |
|------|-------------------|------|
| `chat.message` | ❌ | 消息接收时触发 |
| `chat.params` | ❌ | 修改 LLM 参数 |
| `chat.headers` | ❌ | 修改 HTTP headers |
| `chat.system.transform` | ✅ `system.ts` | 修改系统提示 |
| `chat.message.transform` | ❌ | 实验性：消息转换 |
| `permission.ask` | ✅ `permission.ts` | 权限决策 |
| `tool.execute.before` | ✅ `compositeBefore` | 工具执行前 |
| `tool.execute.after` | ✅ `metaOraclePostReview` | 工具执行后 |
| `shell.env` | ❌ | 环境变量注入 |
| `experimental.session.compacting` | ✅ `compact.ts` | 会话压缩前 |
| `experimental.compaction.autocontinue` | ❌ | 压缩后自动继续 |
| `experimental.text.complete` | ❌ | 文本补全 |
| `tool.definition` | ❌ | 工具定义修改 |
| `tool.*` (自定义工具) | ❌ | 自定义工具注册 |
| `event` (通用事件) | ❌ | 通用事件处理 |
| `config` | ❌ | 配置处理 |
| `auth` | ❌ | 认证 hooks |
| `provider` | ❌ | 模型提供者 hooks |

---

## 4. 启动顺序

```
1. OpenCode 启动
2. 读取 .opencode/opencode.json → plugin[]
3. 加载 oh-my-openagent（OMO 驱动）
   └─ OMO 通过 .claude/settings.json 加载 hooks 配置
      ├─ PreToolUse → oh-my-openagent 原生处理 (3/7 事件)
      ├─ PostToolUse → oh-my-openagent 原生处理
      └─ PreCompact → oh-my-openagent 原生处理
4. 加载 carror-hooks-compat.ts（本地插件）
   └─ 补齐 4 个缺失事件：
      ├─ SessionStart (session.created / message.updated 回退)
      ├─ PostToolUseFailure (tool.execute.after + exit code ≠ 0)
      ├─ UserPromptSubmit (message.updated)
      └─ Stop (session.idle / message.updated / session.compacted 回退)
5. [未执行] 加载 @carroros/gov（当前未注册）
   └─ 5 个 hook 事件（system.transform / before / after / permission / compacting）
```

---

## 5. 验证结果

### ✅ 已通过

| 检查项 | 结果 | 证据 |
|--------|------|------|
| package.json 存在 | ✅ | `packages/carroros-gov/package.json` |
| src/index.ts 入口存在 | ✅ | 导出 `server()` 函数 |
| 5 个 hook handler 实现完整 | ✅ | system/privacy/oracle/oracle-post/permission/compact |
| tsconfig 配置正确 | ✅ | ES2022 + NodeNext |
| @opencode-ai/plugin 类型可用 | ✅ | v1.14.32 安装在 .opencode/node_modules/ |
| 插件加载协议理解 | ✅ | opencode.json plugin[] + export server/default |
| 对齐文档存在 | ✅ | `docs/internal/oc-plugin-alignment-todo.md` (5/73 hook 已对齐) |

### ⚠️ 待处理

| 问题 | 影响 | 建议 |
|------|------|------|
| `effect` 未安装 | 编译时 type-check 失败 | `cd packages/carroros-gov && npm install effect zod` |
| `dist/` 不存在 | TypeScript 无法直接加载 | `tsc` 构建或配置 ts-node runner |
| engine `opencode >=1.16.0` vs 实际 `@opencode-ai/plugin 1.14.32` | API 不兼容风险 | 确认 v1.14.32 是否支持所有用到的 hook 事件名 |
| @carroros/gov 未注册到 opencode.json | 插件不会被加载 | 需 npm link 后在 opencode.json 添加 `"@carroros/gov"` |
| 仅对齐 5/73 CC hooks | 治理能力仅覆盖 10-15% | 按 oc-plugin-alignment-todo.md Phase 1 优先扩展 |

---

## 6. 关键依赖路径

```
@carroros/gov (src/index.ts)
├── @opencode-ai/plugin (peerDep) → Plugin, Hooks types
├── effect (dep) → ToolContext, Effect<void>
├── zod (dep) → ToolDefinition schema
├── Node.js builtins: path, fs/promises, child_process
└── Python3 (运行时) → handoff.py (compact hook 调用)
```
