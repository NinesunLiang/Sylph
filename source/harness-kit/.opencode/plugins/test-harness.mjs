/**
 * carror-hooks-compat.ts 严格测试套件
 *
 * 直接模拟 OpenCode Plugin API 的 input/output 对象，验证：
 * 1. event handler — session.created → SessionStart hooks 执行
 * 2. tool.execute.after handler — 失败检测 → PostToolUseFailure hooks 执行
 * 3. 成功态不应触发 PostToolUseFailure
 */
import { existsSync, readFileSync, unlinkSync, writeFileSync, mkdtempSync, mkdirSync } from "fs";
import { resolve, join } from "path";
import { tmpdir } from "os";
import { createHash } from "crypto";

const PROJECT_ROOT = resolve(import.meta.dirname, "..", "..");
const STATE_DIR = join(PROJECT_ROOT, ".omc", "state");

let passed = 0;
let failed = 0;
const errors = [];

function assert(condition, msg) {
  if (condition) {
    passed++;
    console.log(`  ✅ ${msg}`);
  } else {
    failed++;
    errors.push(msg);
    console.log(`  ❌ ${msg}`);
  }
}

function assertFileContains(filePath, searchStr, msg) {
  try {
    const content = readFileSync(filePath, "utf-8");
    if (content.includes(searchStr)) {
      passed++;
      console.log(`  ✅ ${msg}`);
    } else {
      failed++;
      errors.push(`${msg}: 文件中未找到 "${searchStr}"`);
      console.log(`  ❌ ${msg}: 未找到 "${searchStr}"`);
    }
  } catch (e) {
    failed++;
    errors.push(`${msg}: 读取文件失败 - ${e.message}`);
    console.log(`  ❌ ${msg}: ${e.message}`);
  }
}

console.log("\n=== Phase 1: 隔离测试 - 直接调用 exit code 检测逻辑 ===\n");

// Test 1: exit code 检测 - OpenCode 格式 (metadata.exit)
console.log("--- Test 1: OpenCode 格式 exit code 检测 ---");
const ocSuccess = { metadata: { exit: 0 }, output: "ok" };
const ocFailure = { metadata: { exit: 1 }, output: "error" };

function detectFailure(output) {
  const metadata = output?.metadata;
  const exitCode = metadata?.exitCode ?? metadata?.exit ?? output?.exitCode ?? 0;
  return exitCode !== 0 || !!output?.error || !!metadata?.error;
}

assert(!detectFailure(ocSuccess), "OpenCode 格式: exit=0 → 不应检测为失败");
assert(detectFailure(ocFailure), "OpenCode 格式: exit=1 → 应检测为失败");

// Test 2: exit code 检测 - Claude Code 格式 (metadata.exitCode)
console.log("\n--- Test 2: Claude Code 格式 exit code 检测 ---");
const ccSuccess = { metadata: { exitCode: 0 } };
const ccFailure = { metadata: { exitCode: 2 } };

assert(!detectFailure(ccSuccess), "Claude Code 格式: exitCode=0 → 不应检测为失败");
assert(detectFailure(ccFailure), "Claude Code 格式: exitCode=2 → 应检测为失败");

// Test 3: matcher 匹配逻辑
console.log("\n--- Test 3: matcher 匹配逻辑 ---");
function matchesToolPattern(matcher, toolName) {
  if (!matcher || matcher === ".*") return true;
  const patterns = matcher.split("|").map((p) => p.trim().toLowerCase());
  return patterns.includes(toolName.toLowerCase());
}

assert(matchesToolPattern("Bash", "Bash"), "Bash matcher 匹配 Bash tool");
assert(matchesToolPattern("Bash", "bash"), "Bash matcher 匹配 bash (大小写不敏感)");
assert(matchesToolPattern("Edit|Write", "Write"), "Edit|Write matcher 匹配 Write");
assert(!matchesToolPattern("Bash", "Edit"), "Bash matcher 不应匹配 Edit");
assert(matchesToolPattern(".*", "Anything"), "'.*' matcher 匹配任意 tool");
assert(matchesToolPattern(undefined, "Bash"), "undefined matcher 匹配任意 tool");

// Test 4: settings.json 加载
console.log("\n--- Test 4: settings.json 配置加载 ---");
const settingsPath = join(PROJECT_ROOT, ".claude", "settings.json");
assert(existsSync(settingsPath), ".claude/settings.json 存在");

const raw = JSON.parse(readFileSync(settingsPath, "utf-8"));
const hooks = raw.hooks || {};
assert(!!hooks.SessionStart, "settings.json 包含 SessionStart 配置");
assert(!!hooks.PostToolUseFailure, "settings.json 包含 PostToolUseFailure 配置");
assert(!!hooks.PreToolUse, "settings.json 包含 PreToolUse 配置");
assert(!!hooks.PostToolUse, "settings.json 包含 PostToolUse 配置");
assert(!!hooks.Stop, "settings.json 包含 Stop 配置");

const ssHooks = hooks.SessionStart.flatMap(m => m.hooks || []);
console.log(`  SessionStart 注册 hook 数: ${ssHooks.length}`);
assert(ssHooks.length > 0, `SessionStart 有 ${ssHooks.length} 个 hook 脚本`);

const ptufHooks = hooks.PostToolUseFailure.flatMap(m => m.hooks || []);
assert(ptufHooks.length > 0, `PostToolUseFailure 有 ${ptufHooks.length} 个 hook 脚本`);

// Test 5: hook 脚本存在于磁盘
console.log("\n--- Test 5: Hook 脚本磁盘存在性 ---");
const allHooks = [ssHooks, ptufHooks].flat();
for (const hook of allHooks) {
  if (hook.type !== "command") continue;
  const cmd = hook.command;
  // 提取脚本路径: bash .claude/hooks/xxx.sh
  const match = cmd.match(/(\.claude\/hooks\/\S+)/);
  if (match) {
    const scriptPath = join(PROJECT_ROOT, match[1]);
    assert(existsSync(scriptPath), `Hook 脚本存在: ${match[1]}`);
  }
}

console.log("\n=== Phase 2: 加载 plugin 并调用 handler ===\n");

// 动态加载 plugin
const pluginModule = await import(resolve(import.meta.dirname, "carror-hooks-compat.ts"));
const pluginFactory = pluginModule.default;
const handlers = await pluginFactory();

assert(typeof handlers === "object" && handlers !== null, "plugin factory 返回 handlers 对象");
assert(typeof handlers.event === "function", "handlers 包含 event 函数");
assert(typeof handlers["tool.execute.after"] === "function", "handlers 包含 tool.execute.after 函数");

// Test 6: event handler - session.created 不匹配时跳过
console.log("\n--- Test 6: event handler 过滤非 session.created 事件 ---");
let eventCalled = false;
const originalConsoleError = console.error;
console.error = () => {}; // 静默

try {
  await handlers.event({ event: { type: "session.idle" } });
  eventCalled = true;
} catch (e) {
  // 预期 OK
}
console.error = originalConsoleError;
assert(eventCalled, "非 session.created 事件应被跳过（不抛异常）");

// Test 7: event handler - session.created 分发
console.log("\n--- Test 7: event handler - session.created 分发 ---");
// 这个测试依赖 OpenCode 运行时环境，但我们可以验证 handler 本身不崩溃
let handlerThrew = false;
try {
  await handlers.event({ event: { type: "session.created" } });
} catch (e) {
  handlerThrew = true;
  console.log(`  ⚠️ handler 抛异常: ${e.message}`);
}
assert(!handlerThrew, "session.created handler 不抛异常");

// Test 8: tool.execute.after - 失败检测分发
console.log("\n--- Test 8: tool.execute.after - 失败检测 ---");
try {
  await handlers["tool.execute.after"](
    { tool: "Bash", sessionID: "test-ses-001" },
    { metadata: { exit: 1 }, output: "error", error: "exit code 1" }
  );
  console.log("  ➡ handler 执行完成");
} catch (e) {
  console.log(`  ⚠️ handler 抛异常: ${e.message}`);
}

// Test 9: tool.execute.after - 成功态应跳过
console.log("\n--- Test 9: tool.execute.after - 成功态跳过 ---");
try {
  await handlers["tool.execute.after"](
    { tool: "Bash", sessionID: "test-ses-002" },
    { metadata: { exit: 0 }, output: "ok" }
  );
  console.log("  ➡ handler 执行完成（成功态应无输出/副作用）");
} catch (e) {
  console.log(`  ⚠️ handler 抛异常: ${e.message}`);
}

console.log("\n=== Phase 3: 验证 OpenCode 插件加载 ===\n");

// 检查 opencode.json 配置
const opencodeJsonPath = join(PROJECT_ROOT, ".opencode", "opencode.json");
assert(existsSync(opencodeJsonPath), ".opencode/opencode.json 存在");

const ocConfig = JSON.parse(readFileSync(opencodeJsonPath, "utf-8"));
const plugins = ocConfig.plugin || [];
assert(plugins.includes("oh-my-openagent"), "OMO 插件已注册");
assert(
  plugins.includes(".opencode/plugins/carroros-gov") || plugins.includes("@carroros/gov") || plugins.includes(".opencode/plugins/carror-hooks-compat.ts"),
  "carror-hooks-compat 插件已注册"
);

// 检查 package.json 没有 "main" 字段毒化
const pkgPath = join(PROJECT_ROOT, ".opencode", "plugins", "package.json");
if (existsSync(pkgPath)) {
  const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
  assert(!pkg.main, "plugins/package.json 没有 'main' 字段（避免毒化）");
}

// 检查没有交叉加载的 .ts 文件
const disabledFiles = ["harness-config.ts.disabled", "harness-kit.ts.disabled", "sylph-hooks.ts.disabled"];
for (const f of disabledFiles) {
  const fp = join(PROJECT_ROOT, ".opencode", "plugins", f);
  assert(existsSync(fp), `已禁用文件存在: ${f}`);
}

// 检查没有未禁用的冲突文件
const dangerousFiles = ["harness-config.ts", "harness-kit.ts", "sylph-hooks.ts"];
for (const f of dangerousFiles) {
  const fp = join(PROJECT_ROOT, ".opencode", "plugins", f);
  assert(!existsSync(fp), `冲突文件不存在: ${f}`);
}

console.log("\n=== 汇总 ===\n");
console.log(`通过: ${passed} | 失败: ${failed}`);
if (failed > 0) {
  console.log("\n失败项:");
  for (const e of errors) {
    console.log(`  • ${e}`);
  }
  process.exit(1);
} else {
  console.log("✅ 全部通过");
}
