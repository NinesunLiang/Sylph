/**
 * session-guardian.ts — OpenCode 专属武器：上下文守护者
 *
 * 利用 OpenCode 独有的能力（TS 插件体系 + experimental.session.compacting + 丰富事件模型），
 * 实现 Claude Code 无法做到的上下文防护。三个核心能力：
 *
 *   1. Compaction Protector — 压缩前注入铁律+状态，防止关键上下文丢失
 *   2. Context Danger Gate — 压缩后禁止 Edit/Write，防止低上下文幻觉损毁代码
 *   3. Knowledge Injector — session.created 时注入项目知识（替代不可靠的 shell stdout）
 *
 * 写入状态文件供 shell hook (context-guard.sh / lsp-suggest.sh) 读取，
 * 实现 TS ↔ Shell 双向通信。
 */

import { execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync, statSync } from "fs";
import { resolve, join } from "path";

const PROJECT_ROOT = resolve(
  import.meta.dirname || process.cwd(),
  "..",
  ".."
);

const STATE_DIR = join(PROJECT_ROOT, ".omc", "state");
const STATE_FILE = join(STATE_DIR, "context-guard-opencode.json");
const READ_TRACKER = join(STATE_DIR, "read-tracker.txt");
const DEBUG = process.env.CARROR_HOOKS_DEBUG === "1";

function log(...args: unknown[]) {
  if (DEBUG) console.error("[session-guardian]", ...args);
}

function ensureStateDir() {
  if (!existsSync(STATE_DIR)) mkdirSync(STATE_DIR, { recursive: true });
}

interface ContextState {
  turns: number;
  estimatedTokens: number;
  compactionCount: number;
  dangerMode: boolean;
  lastMessageSize: number;
  sessionStartedAt: string;
  blockedWrites: number;
}

function loadState(): ContextState {
  try {
    if (existsSync(STATE_FILE)) {
      return JSON.parse(readFileSync(STATE_FILE, "utf-8"));
    }
  } catch (e) {
    log("Failed to load state, using defaults", e);
  }
  return {
    turns: 0,
    estimatedTokens: 0,
    compactionCount: 0,
    dangerMode: false,
    lastMessageSize: 0,
    sessionStartedAt: new Date().toISOString(),
    blockedWrites: 0,
  };
}

function saveState(state: ContextState) {
  ensureStateDir();
  try {
    writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf-8");
  } catch (e) {
    log("Failed to save state", e);
  }
}

function getTodoQueue(): string {
  const todoFile = join(STATE_DIR, "todo-queue.md");
  try {
    if (existsSync(todoFile)) {
      return readFileSync(todoFile, "utf-8").slice(0, 500);
    }
  } catch {}
  return "（无待办）";
}

function getGitStatus(): string {
  try {
    const result = execSync("git diff --name-only", {
      cwd: PROJECT_ROOT,
      encoding: "utf-8",
      timeout: 3000,
    }).trim();
    if (result) return `修改文件:\n${result.split("\n").slice(0, 15).join("\n")}`;
    return "无未提交修改";
  } catch {
    return "（无法获取 git 状态）";
  }
}

function getKnowledgeInjection(): string {
  const claudeDir = join(PROJECT_ROOT, ".claude");
  const files = [
    ["index.md", "full"],
    ["kernel.md", "summary"],
    ["anti-patterns.md", "summary"],
    ["claude-next.md", "summary"],
  ];

  let injected = "";
  for (const [name, mode] of files) {
    const fp = join(claudeDir, name);
    if (!existsSync(fp)) continue;
    try {
      if (mode === "full") {
        injected += `\n[.claude/${name}]\n${readFileSync(fp, "utf-8").slice(0, 2000)}\n`;
      } else {
        const content = readFileSync(fp, "utf-8");
        const headers = content.split("\n").filter((l) => l.startsWith("##"));
        injected += `\n[.claude/${name} 章节]\n${headers.slice(0, 20).join("\n")}\n--- 完整内容请 Read .claude/${name}\n`;
      }
    } catch {}
  }
  return injected;
}

// ── Plugin ────────────────────────────────────────────────────────

export default async () => {
  let state = loadState();
  const startTs = Date.now();

  return {
    // ═══════════════════════════════════════════════════════════
    // session.created — 知识注入 + 状态初始化
    // ═══════════════════════════════════════════════════════════
    "session.created": async (input: any, _output: any) => {
      state = {
        turns: 0,
        estimatedTokens: 0,
        compactionCount: 0,
        dangerMode: false,
        lastMessageSize: 0,
        sessionStartedAt: new Date().toISOString(),
        blockedWrites: 0,
      };
      saveState(state);
      log("Session created, state reset");

      // 注入项目知识到 state（供 context-guard.sh 读取）
      const knowledge = getKnowledgeInjection();
      if (knowledge) {
        const kf = join(STATE_DIR, "injected-knowledge.txt");
        try {
          writeFileSync(kf, `# Session Knowledge (${state.sessionStartedAt})\n${knowledge}`, "utf-8");
        } catch {}
      }
    },

    // ═══════════════════════════════════════════════════════════
    // chat.message — 上下文追踪（每次用户消息计数）
    // ═══════════════════════════════════════════════════════════
    "chat.message": async (input: any, output: any) => {
      state.turns++;
      const msgSize = JSON.stringify(input).length;
      state.lastMessageSize = msgSize;
      // 粗略估算：平均 1 char ≈ 0.25 tokens
      state.estimatedTokens += Math.round(msgSize * 0.25);
      saveState(state);

      // 轮次铁律注入（每 15 轮提醒）
      if (state.turns > 0 && state.turns % 15 === 0) {
        log(`Turn ${state.turns} — injecting rule anchor`);
        const reminder = `
【铁律提醒·第 ${state.turns} 轮】
1. 禁止编造：每个技术断言必须有 file:line 来源
2. 证据门禁：说"完成"前必须有 VERIFIED 证据
3. Git 门禁：commit/push 必须先报告，等用户批准
4. 范围冻结：只改当前任务文件，顺手发现的记 TODO
5. 修复上限：同一问题最多修 3 轮，第 3 轮失败→BLOCKED
`;
        // 注入到输出消息中
        if (output && output.message && typeof output.message === "object") {
          const msg = output.message as Record<string, unknown>;
          const existing = (msg.content as string) || "";
          msg.content = existing + reminder;
        }
      }

      // 高风险告警（50 轮）
      if (state.turns >= 50 && state.turns % 10 === 0) {
        if (output && output.message && typeof output.message === "object") {
          const msg = output.message as Record<string, unknown>;
          const existing = (msg.content as string) || "";
          msg.content = existing + `\n⚠️ [Context Guard] 已 ${state.turns} 轮（估计 ${Math.round(state.estimatedTokens / 1000)}K tokens），请考虑 /compact`;
        }
      }
    },

    // ═══════════════════════════════════════════════════════════
    // experimental.session.compacting — 压缩守护（OpenCode 独有能力！）
    // Claude Code 只能阻止压缩，OpenCode 可以注入内容到压缩提示词
    // ═══════════════════════════════════════════════════════════
    "experimental.session.compacting": async (input: any, output: any) => {
      state.compactionCount++;
      state.dangerMode = true;
      saveState(state);

      const todo = getTodoQueue();
      const git = getGitStatus();

      // 注入 Carror OS 铁律 + 任务状态到压缩提示词
      if (output && Array.isArray(output.context)) {
        output.context.push(
          `## Carror OS 铁律（压缩后必须保留）` +
          `\n1. 禁止编造：每个技术断言必须有 file:line 来源` +
          `\n2. 证据门禁：声明完成前必须提供 VERIFIED 证据` +
          `\n3. Git 门禁：任何 git 写操作必须先报告，等用户批准` +
          `\n4. 范围冻结：只改当前任务文件，额外发现记 TODO` +
          `\n5. 修复上限：同一问题最多修 3 轮，超限 BLOCKED` +
          `\n6. 禁用词：禁止"应该是/可能/通常"作为技术断言` +
          `\n7. 软完成语禁令：禁止"应该没问题了/基本完成/理论上"等` +
          `\n` +
          `\n## 当前任务状态` +
          `\n会话轮次: ${state.turns} | 压缩次数: ${state.compactionCount} | 估计 tokens: ${Math.round(state.estimatedTokens / 1000)}K` +
          `\n` +
          `\n## Todo 队列` +
          `\n${todo}` +
          `\n` +
          `\n## ${git}` +
          `\n` +
          `\n## 压缩前指令` +
          `\n⚠️ 上下文已达限制，请：` +
          `\n- 仅总结当前进度和下一步，不展开细节` +
          `\n- 保留上述铁律完整内容` +
          `\n- 保留 Todo 队列和活跃文件路径` +
          `\n- 不要丢失"正在进行中"的任务上下文`
        );
      }

      log(`Compaction #${state.compactionCount}: injected ${output?.context?.length || 0} context items`);
    },

    // ═══════════════════════════════════════════════════════════
    // tool.execute.before — 上下文危险模式：禁止写操作
    // ═══════════════════════════════════════════════════════════
    "tool.execute.before": async (input: any, _output: any) => {
      const tool = input?.tool || "";

      // Read 追踪：记录所有读取的文件路径供 edit_guard 使用
      if (tool === "read" || tool === "Read") {
        const filePath = input?.args?.filePath || input?.args?.file_path || "";
        if (filePath) {
          ensureStateDir();
          try {
            const existing = existsSync(READ_TRACKER) ? readFileSync(READ_TRACKER, "utf-8") : "";
            const absPath = filePath.startsWith("/") ? filePath : resolve(PROJECT_ROOT, filePath);
            if (!existing.includes(absPath)) {
              writeFileSync(READ_TRACKER, existing + absPath + "\n", "utf-8");
            }
          } catch {}
        }
      }

      // 上下文危险模式：禁止 Edit/Write
      if (!state.dangerMode) return;

      const isWrite = tool === "Edit" || tool === "Write" ||
                      tool === "edit" || tool === "write";
      if (!isWrite) return;

      state.blockedWrites++;
      saveState(state);

      const msg = `🛑 [Context Guard] 上下文已压缩 ${state.compactionCount} 次（${state.turns} 轮，~${Math.round(state.estimatedTokens / 1000)}K tokens）。
写入操作已被阻断以防止低上下文幻觉损毁代码。

你可以：
- 使用 Read/Grep/Bash 诊断当前状态
- 等待会话自动 /compact 刷新上下文
- 如果确认安全，创建 .omc/state/context-force-override 文件后重试`;

      throw new Error(msg);
    },

    // ═══════════════════════════════════════════════════════════
    // session.idle — 危险模式在空闲时自动解除
    // ═══════════════════════════════════════════════════════════
    "session.idle": async () => {
      // 空闲超过 30s 且压缩过 → 解除危险模式（上下文已刷新）
      if (state.dangerMode && Date.now() - startTs > 30000) {
        state.dangerMode = false;
        saveState(state);
        log("Danger mode cleared after idle");
      }
    },

    // ═══════════════════════════════════════════════════════════
    // tool.execute.after — 追踪 Bash 输出大小（token 估算）
    // ═══════════════════════════════════════════════════════════
    "tool.execute.after": async (input: any, output: any) => {
      const tool = input?.tool || "";
      if (tool === "Bash" || tool === "bash") {
        const stdout = output?.stdout || "";
        const stderr = output?.stderr || "";
        state.estimatedTokens += Math.round((stdout.length + stderr.length) * 0.25);
        saveState(state);
      }
    },
  };
};
