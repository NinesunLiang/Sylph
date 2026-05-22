/**
 * carror-hooks-compat.ts — Carror OS OpenCode Hooks Compatibility Plugin
 *
 * OMO (oh-my-opencode) 原生从 .claude/settings.json 处理 3/7 事件：
 *   PreToolUse, PostToolUse, PreCompact
 * OMO 不处理（实测 2026-05-15 确认）：
 *   SessionStart, PostToolUseFailure, UserPromptSubmit, Stop
 *
 * OpenCode 事件体系 vs Claude Code hook 事件：
 *   CC UserPromptSubmit → OC message.updated / tui.prompt.append
 *   CC Stop              → OC session.idle
 *   CC PreCompact        → OC session.compacted (OMO 已处理)
 *
 * 本插件补齐缺失的 4 个事件：
 *   - SessionStart         (双路径: session.created + message.updated 回退)
 *   - PostToolUseFailure   (tool.execute.after + exit code ≠ 0 检测)
 *   - UserPromptSubmit     (event handler, message.updated)
 *   - Stop                 (三路径: session.idle + message.updated 定时 + session.compacted 兜底)
 *
 * SessionStart 回退机制 (2026-05-22):
 *   session.created 在 OpenCode SDK v1.14.28 实测不触发。
 *   首次 message.updated → 检查 .omc/state/.session-start-marker
 *   → 不同 session ID 则执行 SessionStart hooks → 写入 marker 防重复。
 *
 * Stop 回退机制 (2026-05-22):
 *   session.idle 在 OpenCode SDK v1.14.28 实测不触发。
 *   message.updated 时检查距上次 Stop > 10 分钟 → 执行 Stop hooks。
 *   session.compacted 作为额外兜底（OMO 确认该事件有效）。
 *
 * 不修改 OMO node_modules 源码，不替换旧版 sylph-hooks.ts/.disabled。
 * 同一份 .claude/settings.json 在 CC 和 OMO 双平台运行。
 */

import { execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve } from "path";

const PROJECT_ROOT = resolve(
  import.meta.dirname || process.cwd(),
  "..",
  ".."
);

const DEBUG = process.env.CARROR_HOOKS_DEBUG === "1";

function log(...args: unknown[]) {
  if (DEBUG) console.error("[carror-hooks-compat]", ...args);
}

interface HookEntry {
  type: string;
  command: string;
  timeout?: number;
}

interface HookMatcher {
  matcher?: string;
  hooks: HookEntry[];
}

interface HooksConfig {
  SessionStart?: HookMatcher[];
  PostToolUseFailure?: HookMatcher[];
  UserPromptSubmit?: HookMatcher[];
  Stop?: HookMatcher[];
}

function loadClaudeHooksConfig(): HooksConfig | null {
  const paths = [
    resolve(PROJECT_ROOT, ".claude", "settings.json"),
    resolve(PROJECT_ROOT, ".claude", "settings.local.json"),
  ];
  for (const p of paths) {
    if (existsSync(p)) {
      try {
        const raw = JSON.parse(readFileSync(p, "utf-8"));
        return raw.hooks || null;
      } catch (e) {
        log("Failed to parse", p, e);
      }
    }
  }
  log("No .claude/settings.json found");
  return null;
}

function execHook(
  command: string,
  stdinJson: string,
  timeout: number,
  cwd: string,
  env?: Record<string, string>
): { stdout: string; stderr: string; exitCode: number } {
  try {
    const result = execSync(command, {
      input: stdinJson,
      timeout,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      cwd,
      env: env ? { ...process.env, ...env } : undefined,
    });
    return { stdout: result.trim(), stderr: "", exitCode: 0 };
  } catch (e: any) {
    return {
      stdout: (e.stdout || "").trim(),
      stderr: (e.stderr || "").trim(),
      exitCode: e.status ?? 1,
    };
  }
}

function matchesToolPattern(
  matcher: string | undefined,
  toolName: string
): boolean {
  if (!matcher || matcher === ".*") return true;
  const patterns = matcher.split("|").map((p) => p.trim().toLowerCase());
  return patterns.includes(toolName.toLowerCase());
}

export default async () => {
  return {
    event: async (input: any) => {
      const eventType = input?.event?.type || input?.type || "";
      log("event received:", eventType);

      const config = loadClaudeHooksConfig();
      if (!config) return;

      // ── SessionStart (双路径: session.created + message.updated 回退) ──
      // session.created 在 OpenCode SDK v1.14.28 实测不触发 (2026-05-22)。
      // 回退方案：首次 chat.message → 检查 marker 文件 → 执行 SessionStart hooks。
      const sessionId = input.sessionID || input.id || "";
      const markerPath = resolve(PROJECT_ROOT, ".omc", "state", ".session-start-marker");

      const trySessionStart = (triggerEvent: string) => {
        if (!config.SessionStart) return;

        // 检查 marker：同 session 已执行过则跳过
        if (existsSync(markerPath) && sessionId) {
          try {
            const prevId = readFileSync(markerPath, "utf-8").trim();
            if (prevId === sessionId) {
              log("SessionStart: already executed for session", sessionId);
              return;
            }
          } catch { /* marker corrupt, re-run */ }
        }

        const envExtra: Record<string, string> = {};
        if (sessionId) envExtra.SESSION_ID = sessionId;

        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "SessionStart",
          hook_source: `opencode-plugin:${triggerEvent}`,
        };

        const outputs: string[] = [];

        for (const matcher of config.SessionStart) {
          if (!matcher.hooks?.length) continue;
          for (const hook of matcher.hooks) {
            if (hook.type !== "command") continue;
            log("Executing SessionStart hook:", hook.command, `(via ${triggerEvent})`);
            const result = execHook(
              hook.command,
              JSON.stringify(stdinData),
              hook.timeout || 10000,
              PROJECT_ROOT,
              envExtra
            );
            if (result.stdout) {
              outputs.push(result.stdout);
              log("SessionStart hook output:", result.stdout.slice(0, 200));
            }
            if (result.exitCode === 2) {
              log("SessionStart hook blocked:", hook.command, result.stderr);
            }
          }
        }

        // 写入 marker 防重复执行
        try {
          const stateDir = resolve(PROJECT_ROOT, ".omc", "state");
          mkdirSync(stateDir, { recursive: true });
          writeFileSync(markerPath, sessionId || `fallback-${Date.now()}`, "utf-8");
        } catch { /* best-effort marker write */ }

        log(`SessionStart: ${outputs.length} hooks executed via ${triggerEvent}`);
      };

      // 主路径：session.created（OpenCode 原生事件，未来 SDK 修复后生效）
      if (eventType === "session.created") {
        trySessionStart("session.created");
      }

      // 回退路径：首次 message.updated（SDK v1.14.28 实测 session.created 不触发）
      if (eventType === "message.updated") {
        trySessionStart("message.updated");
      }

      // ── UserPromptSubmit ─────────────────────────────────────
      // CC UserPromptSubmit ≈ OC message.updated / tui.prompt.append
      if ((eventType === "message.updated" || eventType === "tui.prompt.append") && config.UserPromptSubmit) {
        const sessionId = input.sessionID || input.id || "";
        const envExtra: Record<string, string> = {};
        if (sessionId) envExtra.SESSION_ID = sessionId;

        const promptText = input?.prompt || input?.message || "";
        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "UserPromptSubmit",
          prompt: promptText,
          hook_source: "opencode-plugin",
        };

        for (const matcher of config.UserPromptSubmit) {
          if (!matcher.hooks?.length) continue;
          for (const hook of matcher.hooks) {
            if (hook.type !== "command") continue;
            log("Executing UserPromptSubmit hook:", hook.command);
            const result = execHook(
              hook.command,
              JSON.stringify(stdinData),
              hook.timeout || 5000,
              PROJECT_ROOT,
              envExtra
            );
            log("UserPromptSubmit hook exit:", result.exitCode);
            if (result.exitCode === 2) {
              log("UserPromptSubmit hook blocked:", hook.command, result.stderr);
            }
          }
        }
      }

      // ── Stop (双路径: session.idle + 定时回退) ────────────────
      // session.idle 在 OpenCode SDK v1.14.28 实测不触发 (2026-05-22)。
      // 回退方案：距上次 Stop 执行 > 10 分钟时，在 message.updated 上触发。
      const stopMarkerPath = resolve(PROJECT_ROOT, ".omc", "state", ".stop-marker");

      const tryStop = (triggerEvent: string) => {
        if (!config.Stop) return;

        // 防抖：距上次执行 < 10 分钟则跳过 (仅回退路径生效)
        if (triggerEvent !== "session.idle" && existsSync(stopMarkerPath)) {
          try {
            const lastRun = parseInt(readFileSync(stopMarkerPath, "utf-8").trim(), 10);
            if (Date.now() - lastRun < 600_000) { // 10 min
              return;
            }
          } catch { /* marker corrupt, re-run */ }
        }

        const envExtra: Record<string, string> = {};
        if (sessionId) envExtra.SESSION_ID = sessionId;

        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "Stop",
          hook_source: `opencode-plugin:${triggerEvent}`,
        };

        for (const matcher of config.Stop) {
          if (!matcher.hooks?.length) continue;
          for (const hook of matcher.hooks) {
            if (hook.type !== "command") continue;
            log("Executing Stop hook:", hook.command, `(via ${triggerEvent})`);
            const result = execHook(
              hook.command,
              JSON.stringify(stdinData),
              hook.timeout || 10000,
              PROJECT_ROOT,
              envExtra
            );
            log("Stop hook exit:", result.exitCode);
            if (result.exitCode === 2) {
              log("Stop hook blocked:", hook.command, result.stderr);
            }
          }
        }

        // 写入防抖 marker
        try {
          const stateDir = resolve(PROJECT_ROOT, ".omc", "state");
          mkdirSync(stateDir, { recursive: true });
          writeFileSync(stopMarkerPath, String(Date.now()), "utf-8");
        } catch { /* best-effort */ }

        log(`Stop: hooks executed via ${triggerEvent}`);
      };

      // 主路径：session.idle（OpenCode 原生事件，未来 SDK 修复后生效）
      if (eventType === "session.idle") {
        tryStop("session.idle");
      }

      // 回退路径：message.updated 时检查距上次 Stop > 10 分钟则触发
      if (eventType === "message.updated") {
        tryStop("message.updated");
      }

      // 兜底路径：session.compacted（压缩时触发，OMO 确认该事件有效）
      if (eventType === "session.compacted") {
        tryStop("session.compacted");
      }
    },

    "tool.execute.after": async (input: any, output: any) => {
      // Detect tool failure: non-zero exit code, error field, or metadata.error
      // Claude Code: metadata.exitCode; OpenCode: metadata.exit
      const metadata = output?.metadata;
      const exitCode =
        metadata?.exitCode ??
        metadata?.exit ??
        output?.exitCode ??
        0;
      const toolFailed =
        exitCode !== 0 ||
        !!output?.error ||
        !!metadata?.error;

      if (!toolFailed) return;

      const config = loadClaudeHooksConfig();
      if (!config?.PostToolUseFailure) return;

      const toolName = input?.tool || "";
      const sessionId = input?.sessionID || "";
      const envExtra: Record<string, string> = {};
      if (sessionId) envExtra.SESSION_ID = sessionId;

      for (const matcher of config.PostToolUseFailure) {
        if (!matcher.hooks?.length) continue;
        if (!matchesToolPattern(matcher.matcher, toolName)) continue;

        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "PostToolUseFailure",
          tool_name: toolName,
          tool_input: input.args || {},
          error: output?.error || metadata?.error || `exit code ${exitCode}`,
          is_interrupt: !!(metadata?.isInterrupt || output?.isInterrupt),
          tool_use_id: input.callID || "",
          hook_source: "opencode-plugin",
        };

        for (const hook of matcher.hooks) {
          if (hook.type !== "command") continue;
          log("Executing PostToolUseFailure hook:", hook.command);
          execHook(
            hook.command,
            JSON.stringify(stdinData),
            hook.timeout || 5000,
            PROJECT_ROOT,
            envExtra
          );
        }
      }
    },
  };
};
