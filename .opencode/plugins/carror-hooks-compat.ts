/**
 * carror-hooks-compat.ts — Carror OS OpenCode Hooks Compatibility Plugin
 *
 * 为 OMO claude-code-hooks 补充缺失的 SessionStart 和 PostToolUseFailure 事件映射。
 * OMO 处理 PreToolUse, PostToolUse, UserPromptSubmit, Stop, PreCompact 五个事件。
 * 本插件处理：
 *   - SessionStart (session.created) — 会话启动 hook
 *   - PostToolUseFailure (tool.execute.after + 失败检测) — 工具执行失败 hook
 *
 * 不修改 OMO 源码，不替换旧版 sylph-hooks.ts，保持 Claude Code 已验证的行为不变。
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
  cwd: string
): { stdout: string; stderr: string; exitCode: number } {
  try {
    const result = execSync(command, {
      input: stdinJson,
      timeout,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      cwd,
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
    "session.created": async (input: any) => {
      const config = loadClaudeHooksConfig();
      if (!config?.SessionStart) return;

      const sessionId = input.sessionID || input.id || "";

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
            PROJECT_ROOT
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
    },

    "tool.execute.after": async (input: any, output: any) => {
      // Detect tool failure: non-zero exit code, error field, or metadata.error
      const metadata = output?.metadata;
      const exitCode = metadata?.exitCode ?? output?.exitCode ?? 0;
      const toolFailed =
        exitCode !== 0 ||
        !!output?.error ||
        !!metadata?.error;

      if (!toolFailed) return;

      const config = loadClaudeHooksConfig();
      if (!config?.PostToolUseFailure) return;

      const toolName = input?.tool || "";

      for (const matcher of config.PostToolUseFailure) {
        if (!matcher.hooks?.length) continue;
        if (!matchesToolPattern(matcher.matcher, toolName)) continue;

        const stdinData = {
          session_id: input.sessionID || "",
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
            PROJECT_ROOT
          );
        }
      }
    },
  };
};
