/**
 * session-guardian.ts — OpenCode 专属武器：上下文守护者 v3
 *
 * 利用 OpenCode 独有的能力（TS 插件体系 + 有状态会话 + 原生事件拦截 + 输出追踪），
 * 实现 Claude Code bash hook 永远做不到的事。
 *
 * 核心理念：Plugin 原生执行 > 调用 bash hook — 更快、更可靠、更智能。
 *
 * v3 (2026-05-22):
 *   1. 自适应阈值 — 根据介入频率 + 任务类型自动调整门禁灵敏度
 *   2. 输出后处理 — 追踪 AI 回复质量，下轮注入纠正上下文
 *   3. Pre-Flight Briefing 强化 — 安全 + 反幻觉 + 方向感知
 *   4. 轮次规则刷新强化 — 防 AI 幻觉、欺骗、方向偏离
 *   5. Native 四道防线 — Edit/Permission/Privacy/Context Gate (0 bash spawn)
 *   6. 通用化常量 — 铁律/反模式/禁语集中定义，便于跨平台复用
 */

import { execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, join } from "path";

const PROJECT_ROOT = resolve(
  import.meta.dirname || process.cwd(), "..", ".."
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

// ═══════════════════════════════════════════════════════════════════
// 通用化常量 — 所有规则集中定义，便于跨平台、跨插件复用
// ═══════════════════════════════════════════════════════════════════

const IRON_RULES = [
  "禁止编造：每个技术断言必须有 file:line 来源，找不到则说'需要验证'",
  "证据门禁：说'完成/已验证'前必须提供 VERIFIED 证据（≥60 chars, fresh≤300s）",
  "Git 门禁：commit/push 必须先报告，等用户明确批准，禁止自行提交",
  "范围冻结：只改当前任务涉及的文件，额外发现记 TODO，不顺手修",
  "修复上限：同一问题最多修 3 轮，每轮必须换假设，超限→BLOCKED 升级用户",
  "隐私防线：绝对禁止读取 .env/私钥/凭据文件，禁止 Bash 中使用明文 Token",
  "断言真实：报告中每个百分比/评分必须有行业标准来源 URL 或 file:line，否则标注 [内部自检]",
  "哲学先行：问人前先过哲学 7 条，哲学能裁决→标注 [哲学先行: #N→action] 直接执行",
];

const SOFT_COMPLETION_BAN = [
  "应该没问题了", "应该可以", "基本完成", "大部分完成",
  "理论上", "理论上可行", "看起来正常", "看起来没问题",
  "差不多了", "快好了", "之前验证过", "上次确认过",
  "should be fine", "basically done", "mostly complete",
  "seems to work", "probably works", "theoretically",
];

const HALLUCINATION_SIGNALS = [
  /[\[（(]\s*(?:已验证|已测试|已确认|来源|引用|cf\.?|see)[：:\s]+file:line\s*[\]）)]/i,  // 假引用: [已验证: file:line] 模板占位模式
  /\[已验证: [^\]]*\]/,              // VERIFIED 声明但格式不完整
];

// ── Task Type Detection ────────────────────────────────────────────

type TaskType = "code_change" | "exploration" | "security" | "unknown";

function detectTaskType(message: string): TaskType {
  const lower = message.toLowerCase();
  if (/安全|security|auth|token|密钥|凭据|隐私|permission/i.test(lower)) return "security";
  if (/修|fix|改|refactor|实现|添加|删除|优化|迁移/i.test(lower)) return "code_change";
  if (/看|查|读|浏览|列出|搜索|找|探索|explore|分析|调研|了解|list|是什么/i.test(lower)) return "exploration";
  return "unknown";
}

// ═══════════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════════

interface QualityIssue {
  turn: number;
  type: "soft_completion" | "missing_citation" | "possible_hallucination";
  detail: string;
}

interface ContextState {
  turns: number;
  estimatedTokens: number;
  compactionCount: number;
  dangerMode: boolean;
  lastMessageSize: number;
  sessionStartedAt: string;
  blockedWrites: number;
  knowledgeInjected: boolean;
  // v3: 自适应阈值
  interventionCount: number;
  lastTaskType: TaskType;
  strictnessLevel: number;
  // v3: 输出后处理
  lastTurnIssues: QualityIssue[];
  // v3.1: session-ID tracking (replace session.created/idle hooks)
  _sessionId: string;
  _compactTurn: number;  // turn when last compaction happened
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
    turns: 0, estimatedTokens: 0, compactionCount: 0,
    dangerMode: false, lastMessageSize: 0,
    sessionStartedAt: new Date().toISOString(), blockedWrites: 0,
    knowledgeInjected: false,
    interventionCount: 0, lastTaskType: "unknown", strictnessLevel: 0.5,
    lastTurnIssues: [], _sessionId: "", _compactTurn: 0,
  };
}
function saveState(state: ContextState) {
  ensureStateDir();
  try { writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf-8"); }
  catch (e) { log("Failed to save state", e); }
}

// ═══════════════════════════════════════════════════════════════════
// 自适应阈值引擎 (v3)
// ═══════════════════════════════════════════════════════════════════

function updateStrictness(state: ContextState, taskType: TaskType) {
  // 基准: 介入率越高 → 越严格
  const interventionRate = state.turns > 0
    ? state.interventionCount / state.turns
    : 0;

  let base: number;
  if (interventionRate > 0.3) base = 0.9;        // 高介入 → 高度警戒
  else if (interventionRate > 0.1) base = 0.7;   // 中介入 → 加强
  else base = 0.5;                                // 低介入 → 常规

  // 任务类型调整 (temperature inversion)
  switch (taskType) {
    case "code_change": base += 0.1; break;  // 代码修改 → 更严格
    case "security":    base += 0.2; break;  // 安全相关 → 最严格
    case "exploration": base -= 0.1; break;  // 探索阅读 → 放宽松
  }

  state.strictnessLevel = Math.max(0, Math.min(1.0, base));
  state.lastTaskType = taskType;
  log(`Strictness: ${state.strictnessLevel.toFixed(2)} (intervention_rate=${interventionRate.toFixed(2)}, task=${taskType})`);
}

// ═══════════════════════════════════════════════════════════════════
// 输出后处理引擎 (v3) — 追踪上一轮质量问题，下轮注入纠正
// ═══════════════════════════════════════════════════════════════════

function detectQualityIssues(state: ContextState, tool: string, output: any): QualityIssue[] {
  const issues: QualityIssue[] = [];

  // 检测软完成语 — 扩展到 Edit/Write/Bash 输出 (v3.1: Oracle P1#7)
  if (tool === "Edit" || tool === "Write" || tool === "edit" || tool === "write" ||
      tool === "Bash" || tool === "bash") {
    const content = output?.new_string || output?.content || output?.stdout || "";
    for (const banned of SOFT_COMPLETION_BAN) {
      if (content.includes(banned)) {
        issues.push({
          turn: state.turns,
          type: "soft_completion",
          detail: `检测到软完成语: "${banned}"`,
        });
        break;
      }
    }
  }

  // v3.1 M2: HALLUCINATION_SIGNALS — check for fake citations
  const outputStr = JSON.stringify(output);
  for (const signal of HALLUCINATION_SIGNALS) {
    if (signal.test(outputStr)) {
      issues.push({
        turn: state.turns,
        type: "possible_hallucination",
        detail: `疑似格式空洞: 匹配到 "${signal.source}" 但内容可能不完整`,
      });
      break;
    }
  }

  return issues;
}

function getOutputQualityContext(state: ContextState): string {
  if (state.lastTurnIssues.length === 0) return "";

  let ctx = "\n⚠️ [Carror OS · 上轮质量问题]\n";
  for (const issue of state.lastTurnIssues) {
    switch (issue.type) {
      case "soft_completion":
        ctx += `· 软完成语警告: ${issue.detail}\n  修复: 提供 VERIFIED 证据 + 具体命令输出\n`;
        break;
      case "missing_citation":
        ctx += `· 缺少引用: ${issue.detail}\n  修复: 补充 file:line 或命令输出\n`;
        break;
      case "possible_hallucination":
        ctx += `· 疑似幻觉: ${issue.detail}\n  修复: 重新验证文件是否存在\n`;
        break;
    }
  }

  // 清理上一轮问题（只注入一次）
  state.lastTurnIssues = [];
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════
// Utility
// ═══════════════════════════════════════════════════════════════════

function getTodoQueue(): string {
  const todoFile = join(STATE_DIR, "todo-queue.md");
  try { if (existsSync(todoFile)) return readFileSync(todoFile, "utf-8").slice(0, 500); }
  catch {}
  return "（无待办）";
}

function getGitStatus(): string {
  try {
    const result = execSync("git diff --name-only", {
      cwd: PROJECT_ROOT, encoding: "utf-8", timeout: 3000,
    }).trim();
    if (result) return `修改文件:\n${result.split("\n").slice(0, 15).join("\n")}`;
    return "无未提交修改";
  } catch { return "（无法获取 git 状态）"; }
}

function getKnowledgeInjection(): string {
  const claudeDir = join(PROJECT_ROOT, ".claude");
  const files = [
    ["index.md", "full"], ["kernel.md", "summary"],
    ["anti-patterns.md", "summary"], ["claude-next.md", "summary"],
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

function injectKnowledge(state: ContextState) {
  if (state.knowledgeInjected) return;
  const knowledge = getKnowledgeInjection();
  if (knowledge) {
    const kf = join(STATE_DIR, "injected-knowledge.txt");
    try { writeFileSync(kf, `# Session Knowledge (${state.sessionStartedAt})\n${knowledge}`, "utf-8"); }
    catch {}
  }
  state.knowledgeInjected = true;
  log("Knowledge injected at turn", state.turns);
}

// ═══════════════════════════════════════════════════════════════════
// Native Security Gates (0 bash spawn)
// ═══════════════════════════════════════════════════════════════════

const DANGEROUS_PATTERNS: [RegExp, string][] = [
  [/git\s+push\s+.*--?force/, "git push --force"],
  [/git\s+push\b/, "git push"],
  [/git\s+commit\b/, "git commit"],
  [/\brm\s+-rf\b/, "rm -rf"],
  [/\bsudo\b/, "sudo"],
  [/gh\s+(release|pr|issue|repo)\s+(create|delete|merge|close)/, "gh write"],
  // v3.1 C4: encoding bypass detection (regression fix from bash permission-gate.sh)
  [/base64\s+(-d|--decode).*\|.*\b(bash|sh|dash|zsh)\b/, "encoding bypass (base64 pipe)"],
  [/xxd\s+-r.*\|.*\b(bash|sh)\b/, "encoding bypass (xxd pipe)"],
  [/eval\s+\$\(/, "encoding bypass (eval)"],
  [/printf\s+["']\\x/, "encoding bypass (printf hex)"],
];

function checkDangerousCommand(command: string): string | null {
  for (const [pattern, label] of DANGEROUS_PATTERNS) {
    if (pattern.test(command)) return label;
  }
  return null;
}

// v3.1: anchored patterns to reduce false positives (Oracle P1#3)
const SECRET_FILE_PATTERN = /(^|[\/\\])(\.env|.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.jks|id_rsa|credentials\.(json|ya?ml)|secret[es]?\.ya?ml|auth\.json|kubeconfig)$/i;
// Token pattern: only check in Bash commands, not Read file paths (Oracle P1#4)
const TOKEN_PATTERN = /(sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{36}|xox[bprs]-[a-zA-Z0-9-]+|-----BEGIN\s+(RSA|EC|OPENSSH|DSA)\s+PRIVATE KEY-----)/;

function checkPrivacyLeak(_tool: string, filePath: string, command: string): string | null {
  if (filePath && SECRET_FILE_PATTERN.test(filePath)) return `敏感文件读取: ${filePath}`;
  if (command && TOKEN_PATTERN.test(command)) {
    const match = command.match(TOKEN_PATTERN)?.[0] || "token";
    return `明文凭据: ${match.slice(0, 30)}...`;
  }
  return null;
}

// ═══════════════════════════════════════════════════════════════════
// Pre-Flight Briefing Engine (v3: 自适应 + 反幻觉/欺骗/方向偏离)
// ═══════════════════════════════════════════════════════════════════

function buildBriefing(state: ContextState, userMessage: string): string {
  const taskType = detectTaskType(userMessage);
  updateStrictness(state, taskType);
  const s = state.strictnessLevel;

  // 1. 早期锚定 (≤3 轮) — 根据任务类型注入不同规则侧重点
  if (state.turns <= 3) {
    let anchor = `
🛡️ [Carror OS · 规则锚定] 严格度: ${(s * 100).toFixed(0)}% | 任务类型: ${taskType}
`;

    // 核心铁律 (所有人)
    anchor += "· 铁律: 禁止编造(file:line) | 证据门禁(VERIFIED) | Git门禁 | 范围冻结 | 3轮上限\n";

    // 任务类型特定提醒 — 防方向偏离
    switch (taskType) {
      case "code_change":
        anchor += "· ⚠️ 代码变更模式: 改动前先 Read | 改后提供 VERIFIED | 不要顺手修无关代码\n";
        break;
      case "security":
        anchor += "· 🔒 安全模式: 零信任 | 双法官强制 | 敏感文件零触碰 | 命令全文审计\n";
        break;
      case "exploration":
        anchor += "· 🔍 探索模式: 充分调研 | 官方文档优先 | 不确定时标注 [推断,待确认]\n";
        break;
    }

    // 反幻觉 (所有人)
    anchor += `· 禁语: "${SOFT_COMPLETION_BAN.slice(0, 5).join('" "')}..."
· 置信度: [已验证:file:line] [已测试:cmd+output] [推断,待确认]
`;

    // 输出后处理: 上轮质量问题
    anchor += getOutputQualityContext(state);

    return anchor;
  }

  // 2. 规则刷新 (每 15 轮 — 防规则漂移 + 防欺骗)
  if (state.turns % 15 === 0) {
    let refresh = `
🔋 [Carror OS · 第 ${state.turns} 轮规则刷新] 严格度: ${(s * 100).toFixed(0)}%
`;

    if (s >= 0.7) {
      // 高严格度: 逐条重述全部铁律 (v3.1: slice(0,8) includes #7 #8)
      refresh += IRON_RULES.map((r, i) => `  ${i + 1}. ${r}`).join("\n") + "\n";
    } else {
      // 常规: 摘要
      refresh += "· 铁律: 禁止编造 | 证据门禁 | Git门禁 | 范围冻结 | 3轮上限\n";
    }

    refresh += `· 会话: ${state.turns} 轮 (~${Math.round(state.estimatedTokens / 1000)}K tokens) | 压缩: ${state.compactionCount} | 介入: ${state.interventionCount}\n`;
    refresh += `· ${state.dangerMode ? "⚠️ 危险模式：上下文已压缩，写操作被阻断" : "✅ 正常模式"}\n`;

    // 防 AI 欺骗提醒 (高轮次特有)
    if (state.turns >= 30) {
      refresh += `
🛡️ [防欺骗提醒]
· 每个"已完成"必须有物理证据，不能自说自话
· 文件引用必须有 file:line，不能引用不存在的路径
· 数值必须有来源 URL 或命令输出，不能凭空编造百分比
· 发现额外问题 → 记 TODO，不扩大修改范围
`;
    }
// 输出后处理上下文
    refresh += getOutputQualityContext(state);

    return refresh;
  }

  // 3. 高轮次告警 (≥40 轮，每 10 轮 — 激进防漂移)
  if (state.turns >= 40 && state.turns % 10 === 0) {
    let alert = `
⚠️ [Carror OS · 高轮次告警] 第 ${state.turns} 轮
· ~${Math.round(state.estimatedTokens / 1000)}K tokens | 压缩 ${state.compactionCount} 次 | 阻断写入 ${state.blockedWrites} 次
· 强制: 禁止编造 | 证据门禁 | 软完成语禁令 | 范围冻结
· 建议: /compact 或结束当前阶段后开启新会话
`;

    // 高严重度时注入逐条铁律
    if (s >= 0.8) {
      alert += "\n" + IRON_RULES.map((r, i) => `  ${i + 1}. ${r}`).join("\n") + "\n";
    }

    alert += getOutputQualityContext(state);
    return alert;
  }

  // 4. 常规轮次: 仅注入输出后处理上下文 (如果有问题)
  return getOutputQualityContext(state);
}

// ═══════════════════════════════════════════════════════════════════
// Plugin
// ═══════════════════════════════════════════════════════════════════

export default async () => {
  let state = loadState();
  const startTs = Date.now();

  return {
    // ── chat.message (v3.1: session tracking + briefing + adaptive) ─
    // session.created/idle are NOT valid OpenCode plugin hooks (SDK v1.14).
    // Replaced with session-ID tracking in chat.message.
    "chat.message": async (input: any, output: any) => {
      // v3.1 C3: detect new session by sessionID change → reset state
      const currentSid = input?.sessionID || "";
      if (currentSid && currentSid !== state._sessionId) {
        state = {
          turns: 0, estimatedTokens: 0, compactionCount: 0,
          dangerMode: false, lastMessageSize: 0,
          sessionStartedAt: new Date().toISOString(), blockedWrites: 0,
          knowledgeInjected: false,
          interventionCount: 0, lastTaskType: "unknown", strictnessLevel: 0.5,
          lastTurnIssues: [], _sessionId: currentSid, _compactTurn: 0,
        };
        log("New session detected:", currentSid);
      }

      // v3.1 C3: auto-release dangerMode after 5 turns post-compact
      if (state.dangerMode && state._compactTurn > 0 && state.turns > state._compactTurn + 5) {
        state.dangerMode = false;
        log("Danger mode auto-released after", state.turns - state._compactTurn, "turns");
      }

      state.turns++;
      const msgSize = JSON.stringify(input).length;
      state.lastMessageSize = msgSize;
      state.estimatedTokens += Math.round(msgSize * 0.25);

      // 首次消息注入知识（session.created 回退 + new-session reset）
      injectKnowledge(state);

      // v3.1 C2: extract user text from output.parts (per SDK type)
      const userText = (output?.parts || [])
        .filter((p: any) => p?.type === "text")
        .map((p: any) => p?.text || "")
        .join(" ");
      // Fallback for runtime deviations from SDK type
      const prompt = userText || input?.prompt || input?.message || "";

      // 产生 Pre-Flight Briefing
      const briefing = buildBriefing(state, prompt);
      saveState(state);

      if (briefing && output?.message && typeof output.message === "object") {
        const msg = output.message as Record<string, unknown>;
        const existing = (msg.content as string) || "";
        msg.content = briefing + "\n" + existing;
        log(`Turn ${state.turns}: briefing injected (${briefing.length} chars, strictness=${state.strictnessLevel.toFixed(2)})`);
      }
    },

    // ── experimental.session.compacting ──────────────────────────
    "experimental.session.compacting": async (_input: any, output: any) => {
      state.compactionCount++;
      state.dangerMode = true;
      state._compactTurn = state.turns;  // v3.1: track when compaction happened
      saveState(state);

      const todo = getTodoQueue();
      const git = getGitStatus();

      if (output && Array.isArray(output.context)) {
        output.context.push(
          `## Carror OS 铁律（压缩后必须保留）\n` +
          IRON_RULES.map((r, i) => `${i + 1}. ${r}`).join("\n") +
          `\n\n## 会话状态\n` +
          `轮次: ${state.turns} | 压缩: ${state.compactionCount} | Tokens: ~${Math.round(state.estimatedTokens / 1000)}K | 严格度: ${(state.strictnessLevel * 100).toFixed(0)}%\n` +
          `\n## Todo\n${todo}\n\n## Git\n${git}\n` +
          `\n## 压缩指令\n` +
          `⚠️ 仅总结进度+下一步，不展开细节。保留铁律+Todo+活跃文件。`
        );
      }
    },

    // ── tool.execute.before (v3.1: 四道原生防线, args from output per SDK) ─
    // SDK: tool.execute.before args are in OUTPUT (not input like tool.execute.after)
    "tool.execute.before": async (input: any, output: any) => {
      const tool = input?.tool || "";
      // Per SDK type: output.args for tool.execute.before
      const args = output?.args || input?.args || {};

      // [1] Read 追踪
      if (tool === "read" || tool === "Read") {
        const filePath = args?.filePath || args?.file_path || "";
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

      // v3.1 M1: force-override check (escape hatch when context dangerously low)
      const OVERRIDE_FILE = join(STATE_DIR, "context-force-override");
      if (state.dangerMode && existsSync(OVERRIDE_FILE)) {
        try { execSync(`rm -f "${OVERRIDE_FILE}"`, { timeout: 1000 }); } catch {}
        state.dangerMode = false;
        log("Danger mode cleared by force-override");
      }

      // [2] Edit Guard — Read-before-Edit (v3.1: strictnessLevel drives behavior)
      if (tool === "Edit" || tool === "Write" || tool === "edit" || tool === "write") {
        const filePath = args?.filePath || args?.file_path || "";
        // Low strictness: skip edit guard for safe file types (exploration mode)
        if (state.strictnessLevel <= 0.4 && !filePath.match(/\.(sh|py|ts|tsx|js|go)$/)) {
          // Allow direct edits for non-code files in exploration mode
        } else if (filePath && existsSync(READ_TRACKER)) {
          try {
            const readLog = readFileSync(READ_TRACKER, "utf-8");
            const absPath = filePath.startsWith("/") ? filePath : resolve(PROJECT_ROOT, filePath);
            if (!readLog.includes(absPath)) {
              state.interventionCount++;
              updateStrictness(state, state.lastTaskType);
              throw new Error(
                `⛔ [Edit Guard] 未读即编: ${filePath}\n` +
                `请先 Read 此文件再编辑。铁律 #1: 每个技术断言必须有 file:line 来源。`
              );
            }
          } catch (e: any) {
            if (e.message?.includes("[Edit Guard]")) throw e;
            // v3.1: log unexpected errors instead of silently swallowing (Oracle P1#6)
            log("Edit Guard error (non-blocking):", e.message);
          }
        }
      }

      // [3] Permission Gate — 危险命令拦截
      if (tool === "Bash" || tool === "bash") {
        const command = args?.command || args?.cmd || "";
        if (command) {
          const danger = checkDangerousCommand(command);
          if (danger) {
            state.interventionCount++;
            throw new Error(
              `🚫 [Permission Gate] 危险命令已拦截: ${danger}\n` +
              `命令: ${command.slice(0, 200)}\n` +
              `请在终端中手动执行，或创建 .omc/state/sensitive-approved 后重试。`
            );
          }
        }
      }

      // [4] Privacy Gate — 凭据泄露拦截 (零信任，不接受降级)
      {
        const filePath = args?.filePath || args?.file_path || "";
        const command = args?.command || args?.cmd || "";
        const leak = checkPrivacyLeak(tool, filePath, command);
        if (leak) {
          state.interventionCount++;
          throw new Error(
            `🔒 [Privacy Gate] 凭据泄露已拦截: ${leak}\n` +
            `禁止读取敏感文件或在命令中使用明文凭据。请在终端手动操作。`
          );
        }
      }

      // [5] Context Danger Gate — 压缩后阻断写操作
      if (!state.dangerMode) return;
      if (tool === "Edit" || tool === "Write" || tool === "edit" || tool === "write") {
        state.blockedWrites++;
        state.interventionCount++;
        saveState(state);
        throw new Error(
          `🛑 [Context Guard] 上下文已压缩 ${state.compactionCount} 次（${state.turns} 轮，~${Math.round(state.estimatedTokens / 1000)}K tokens）。\n` +
          `写入操作已被阻断以防止低上下文幻觉损毁代码。\n` +
          `· 使用 Read/Grep/Bash 诊断\n` +
          `· 等待 /compact 刷新上下文\n` +
          `· 或创建 .omc/state/context-force-override 后重试`
        );
      }
    },

    // ── tool.execute.after (v3: 输出后处理 — 追踪质量问题) ────────
    "tool.execute.after": async (input: any, output: any) => {
      const tool = input?.tool || "";

      // Token 追踪
      if (tool === "Bash" || tool === "bash") {
        const stdout = output?.stdout || "";
        const stderr = output?.stderr || "";
        state.estimatedTokens += Math.round((stdout.length + stderr.length) * 0.25);
      }

      // v3: 输出质量检测 — 追踪 Edit/Write 结果中的质量问题
      const issues = detectQualityIssues(state, tool, output);
      if (issues.length > 0) {
        state.lastTurnIssues = issues;
        log(`Turn ${state.turns}: ${issues.length} quality issue(s) detected`);

        // 质量问题已存储在 state.lastTurnIssues，下轮 briefing 自动注入
      }

      saveState(state);
    },

    // session.idle removed (not a valid OpenCode plugin hook per SDK v1.14).
    // dangerMode auto-release handled in chat.message (5 turns post-compact).
  };
};
