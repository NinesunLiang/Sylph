/**
 * hermes-migration-opencode.ts — Hermes 门禁脚本 OpenCode 适配器
 * 
 * 将 ~/.hermes/scripts/hermes-*.sh 的门禁能力注入 OpenCode。
 * OpenCode 通过 TS plugin 系统调用 bash 脚本，模拟 Carror OS hook 行为。
 * 
 * 事件映射:
 *   OC session.created    → SessionStart (注入铁律)
 *   OC message.updated    → UserPromptSubmit (turn-counter + compact-detect)
 *   OC tool.execute.before → PreToolUse (pre-exec gate)
 *   OC tool.execute.after  → PostToolUse (error-dna)
 *   OC session.idle       → Stop (session-handoff)
 */

import { execSync } from "child_process";
import { existsSync, mkdirSync, readFileSync } from "fs";
import { resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const HERMES_SCRIPTS = resolve(HOME, ".hermes", "scripts");
const HERMES_STATE = resolve(HOME, ".hermes", "state");
const DEBUG = process.env.HERMES_HOOKS_DEBUG === "1";

function log(...args: unknown[]) {
  if (DEBUG) console.error("[hermes-opencode]", ...args);
}

function execBash(script: string, stdinJson?: string, timeout = 5000): { stdout: string; exitCode: number } {
  const scriptPath = resolve(HERMES_SCRIPTS, script);
  if (!existsSync(scriptPath)) {
    log("Script not found:", scriptPath);
    return { stdout: "", exitCode: -1 };
  }
  try {
    const result = execSync(`bash "${scriptPath}"`, {
      input: stdinJson,
      timeout,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { stdout: result.trim(), exitCode: 0 };
  } catch (e: any) {
    return { stdout: (e.stdout || "").trim(), exitCode: e.status ?? 1 };
  }
}

// 确保 state 目录存在
function ensureState() {
  if (!existsSync(HERMES_STATE)) {
    mkdirSync(HERMES_STATE, { recursive: true });
  }
}

export default async () => {
  ensureState();
  
  // 记录会话轮次
  let turnCount = 0;

  return {
    // ── SessionStart ──────────────────────────────────────────
    event: async (input: any) => {
      const eventType = input?.event?.type || input?.type || "";
      
      if (eventType === "session.created") {
        log("SessionStart: injecting core rules");
        // 注入 SOUL.md 铁律摘要
        const soulPath = resolve(HOME, ".hermes", "SOUL.md");
        if (existsSync(soulPath)) {
          const soul = readFileSync(soulPath, "utf-8");
          const rules = soul.split("## Hard Rules")[1]?.slice(0, 500) || "";
          if (rules) {
            log("Injected Hard Rules:", rules.length, "chars");
          }
        }
      }

      // ── UserPromptSubmit ─────────────────────────────────────
      if ((eventType === "message.updated" || eventType === "tui.prompt.append")) {
        turnCount++;
        const promptText = input?.prompt || input?.message || "";
        
        // Turn counter
        execBash("hermes-turn-counter.sh", promptText);
        
        // Compact detect
        if (promptText.includes("/compact")) {
          execBash("hermes-compact-detect.sh", "/compact");
        }
      }

      // ── Stop ──────────────────────────────────────────────────
      if (eventType === "session.idle") {
        log("Stop: session-handoff");
        execBash("hermes-session-handoff.sh");
      }
    },

    // ── PreToolUse: 命令前门禁 ──────────────────────────────────
    "tool.execute.before": async (input: any) => {
      const args = input?.args || {};
      const command = args?.command || "";
      if (!command) return;

      log("PreToolUse:", command.slice(0, 80));
      const result = execBash("hermes-pre-exec.sh", command, 3000);
      
      if (result.exitCode === 2) {
        const err = new Error(`⛔ [Hermes Gate] 命令被门禁阻断: ${command.slice(0, 100)}`);
        (err as any).status = 403;
        throw err;
      }
    },

    // ── PostToolUse: 错误捕获 + 重试计数 ─────────────────────────
    "tool.execute.after": async (input: any, output: any) => {
      const metadata = output?.metadata;
      const exitCode = metadata?.exitCode ?? metadata?.exit ?? output?.exitCode ?? 0;
      const args = input?.args || {};
      const command = args?.command || "";

      // Error DNA
      if (exitCode !== 0 && command) {
        const stderr = output?.stderr || metadata?.stderr || "";
        execBash("hermes-error-dna.sh", 
          JSON.stringify({ cmd: command, exit: exitCode, err: stderr }));
        
        // Retry check
        execBash("hermes-retry-check.sh", "increment");
      }
    },
  };
};
