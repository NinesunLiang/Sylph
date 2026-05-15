/**
 * carror-hooks-compat.ts — Carror OS OpenCode Hooks Compatibility Plugin
 *
 * OMO (oh-my-opencode@3.15.3) 原生从 .claude/settings.json 处理 3/7 事件：
 *   PreToolUse, PostToolUse, PreCompact
 * OMO 不处理（实测 2026-05-15 确认）：
 *   SessionStart, PostToolUseFailure, UserPromptSubmit, Stop
 *
 * 本插件补齐缺失的 4 个事件：
 *   - SessionStart     (event handler, event.type === "session.created")
 *   - PostToolUseFailure (tool.execute.after + exit code ≠ 0 检测)
 *   - UserPromptSubmit (event handler, event.type === "user.prompt.submit")
 *   - Stop             (event handler, event.type === "session.closing")
 *
 * 不修改 OMO node_modules 源码，不替换旧版 sylph-hooks.ts/.disabled。
 * 同一份 .claude/settings.json 在 CC 和 OMO 双平台运行。
 */

import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";
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

      // ── SessionStart ──────────────────────────────────────────
      if (eventType === "session.created" && config.SessionStart) {
        const sessionId = input.sessionID || input.id || "";
        const envExtra: Record<string, string> = {};
        if (sessionId) envExtra.SESSION_ID = sessionId;

        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "SessionStart",
          hook_source: "opencode-plugin",
        };

        const outputs: string[] = [];

        for (const matcher of config.SessionStart) {
          if (!matcher.hooks?.length) continue;
          for (const hook of matcher.hooks) {
            if (hook.type !== "command") continue;
            log("Executing SessionStart hook:", hook.command);
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

        if (outputs.length > 0) {
          const combined = outputs.join("\n---\n");
          try {
            process.stdout.write(combined + "\n");
          } catch {
            // stdout may not be writable at session.created time
          }
          log(`SessionStart: ${outputs.length} hooks executed`);
        }
      }

      // ── UserPromptSubmit ─────────────────────────────────────
      // OpenCode fires events like "user.prompt.submit" / "message.received"
      // when the user sends a message. Try several known patterns.
      const isUserPrompt =
        eventType === "user.prompt.submit" ||
        eventType === "message.received" ||
        eventType === "user.message" ||
        eventType === "prompt.submit";
      if (isUserPrompt && config.UserPromptSubmit) {
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

      // ── Stop ──────────────────────────────────────────────────
      // Fires when session is about to close / compact
      const isStop =
        eventType === "session.closing" ||
        eventType === "session.stop" ||
        eventType === "session.compact" ||
        eventType === "pre-compact";
      if (isStop && config.Stop) {
        const sessionId = input.sessionID || input.id || "";
        const envExtra: Record<string, string> = {};
        if (sessionId) envExtra.SESSION_ID = sessionId;

        const stdinData = {
          session_id: sessionId,
          cwd: PROJECT_ROOT,
          hook_event_name: "Stop",
          hook_source: "opencode-plugin",
        };

        for (const matcher of config.Stop) {
          if (!matcher.hooks?.length) continue;
          for (const hook of matcher.hooks) {
            if (hook.type !== "command") continue;
            log("Executing Stop hook:", hook.command);
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
