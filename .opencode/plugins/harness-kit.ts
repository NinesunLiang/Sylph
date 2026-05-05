/**
 * harness-kit.ts — Carror OS OpenCode Plugin
 *
 * 版本：v1.0.0 | 对应 Claude Code harness-kit v6.0.1
 *
 * 覆盖 22 个 Claude Code hook 的 OpenCode 等价实现：
 *
 * - 19 个通过 tool.execute.before/after 完全对齐
 * - 3 个通过 message.updated / tui.prompt.append 变通实现
 *
 * 安装：将此文件放入 .opencode/plugins/ 目录，OpenCode 自动加载
 * 配置：读取项目根 .claude/harness.yaml（与 Claude Code 共享配置）
 */

import type { Plugin } from "@opencode-ai/plugin";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { loadHarnessConfig } from "./harness-config.js";

// ── 工具函数 ───────────────────────────────────────────────────

function getStateDir(root: string) {
  const dir = join(root, ".omc", "state");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

function readState(root: string, key: string, def = ""): string {
  try {
    return readFileSync(join(getStateDir(root), key), "utf-8").trim();
  } catch {
    return def;
  }
}

function writeState(root: string, key: string, value: string) {
  try {
    writeFileSync(join(getStateDir(root), key), value, "utf-8");
  } catch {}
}

function matchRegex(pattern: string, text: string): boolean {
  try {
    return new RegExp(pattern, "i").test(text);
  } catch {
    return false;
  }
}

function hasVerifiedEvidence(root: string, keyword: string, minChars: number): boolean {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const evFile = `/tmp/.completion-evidence-${today}`;
  try {
    const content = readFileSync(evFile, "utf-8");
    return content.includes(keyword) && content.length >= minChars;
  } catch {
    return false;
  }
}

// ── Plugin 主体 ────────────────────────────────────────────────

export const HarnessKitPlugin: Plugin = async ({ project, $, directory, worktree }) => {
  const root = worktree ?? directory ?? process.cwd();
  const cfg = loadHarnessConfig(root);
  const stateDir = getStateDir(root);

  // 轮次计数器（turn-counter 变通）
  let turnCount = parseInt(
    readState(root, "session-turns.json").replace(/.*"count":\s*(\d+).*/, "$1") || "0", 10
  );
  if (isNaN(turnCount)) turnCount = 0;

  return {
    // ══════════════════════════════════════════════════════════
    // tool.execute.before — PreToolUse 等价
    // ══════════════════════════════════════════════════════════
    "tool.execute.before": async (input: any, output: any) => {
      const tool = input.tool ?? "";

      // ── One-Man Army 并发锁挂起 (OMA) ──────────────────────
      if (["edit", "write", "replace", "str_replace"].includes(tool)) {
        const filePath = (output.args?.filePath ?? output.args?.file_path ?? "") as string;
        if (filePath) {
          const { promisify } = require("util");
          const { exec } = require("child_process");
          const execAsync = promisify(exec);
          try {
            // 唤起底层的 Python 微内核锁，Node.js 侧优雅挂起 (await)，不阻塞 UI
            await execAsync(`python3 ${join(root, ".claude/scripts/oma_lock_manager.py")} acquire "${filePath}" opencode-session`);
          } catch (e) {
            throw new Error("🚫 [OMA 并发锁] 致命错误：微内核锁引擎抛出异常，请检查环境！\n" + (e as Error).message);
          }
        }
      }

      // ── privacy-gate：隐私防线拦截 (DLP) ────────────────────
      if ((tool === "read" || tool === "grep") && cfg.hooks_enabled.privacy_gate) {
        const filePath = (output.args?.filePath ?? output.args?.file_path ?? "") as string;
        if (/\.(env|pem|key)$|id_rsa|credentials\.json|secret\.ya?ml|auth\.json/i.test(filePath)) {
          throw new Error(
            `🚫 harness-kit [privacy-gate]: 隐私防线触发，禁止读取敏感凭据文件(${filePath})。\n` +
            `请通过 lx-varlock 或系统环境变量脱敏执行。`
          );
        }
      }

      if (tool === "bash" && cfg.hooks_enabled.privacy_gate) {
        const cmd = (output.args?.command ?? "") as string;
        if (/sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|xoxb-[0-9]{10,}-[0-9]{10,}|Bearer\s+[A-Za-z0-9_\-+/\\]+={0,2}/i.test(cmd)) {
          throw new Error(
            `🚫 harness-kit [privacy-gate]: 隐私防线触发，检测到命令中包含明文 Token/密码。\n` +
            `这是严重的数据泄露风险。请立即停止，配置 varlock，并使用 "varlock.py run" 来安全执行。`
          );
        }
      }

      // ── permission-gate：危险命令拦截 ───────────────────────
      if (tool === "bash" && cfg.hooks_enabled.permission_gate) {
        const cmd = (output.args?.command ?? "") as string;

        if (matchRegex(cfg.permission_gate.git_push_force_regex, cmd)) {
          throw new Error(
            `🚫 harness-kit [permission-gate]: git push --force 被拦截\n` +
            `当前任务: ${readState(root, "current-task.txt", "未知")}\n` +
            `如需 force push，请先向用户说明原因并获得明确批准。`
          );
        }
        if (matchRegex(cfg.permission_gate.git_push_regex, cmd)) {
          throw new Error(
            `🚫 harness-kit [permission-gate]: git push 被拦截\n` +
            `必须先报告变更内容 → 等待用户明确批准 → 再执行 push\n` +
            `当前任务: ${readState(root, "current-task.txt", "未知")}`
          );
        }
        if (matchRegex(cfg.permission_gate.git_commit_regex, cmd)) {
          throw new Error(
            `🚫 harness-kit [permission-gate]: git commit 被拦截\n` +
            `必须先报告：文件清单 + commit message + 影响范围 → 等待用户批准`
          );
        }
        if (matchRegex(cfg.permission_gate.destructive_regex, cmd)) {
          throw new Error(
            `🚫 harness-kit [permission-gate]: 破坏性操作被拦截: ${cmd.slice(0, 60)}\n` +
            `DROP/TRUNCATE/rm -rf 需要用户明确确认后才能执行。`
          );
        }
        if (matchRegex(cfg.permission_gate.sudo_regex, cmd)) {
          throw new Error(
            `🚫 harness-kit [permission-gate]: sudo 命令被拦截\n` +
            `请说明：需要权限 + 当前任务 + 申请理由，获得用户批准后再执行。`
          );
        }
      }

      // ── pretool-edit-scope：范围控制（写文件前警告）──────────
      if ((tool === "edit" || tool === "write") && cfg.hooks_enabled.pretool_edit_scope) {
        const filePath = (output.args?.filePath ?? output.args?.file_path ?? "") as string;
        const scopeFile = join(stateDir, "current-scope.txt");
        if (existsSync(scopeFile)) {
          const scope = readFileSync(scopeFile, "utf-8").trim();
          if (scope && !filePath.includes(scope)) {
            // 注入警告但不阻断（与 Claude Code 版本行为一致）
            Object.assign(output, {
              _harness_warning: `⚠️ harness-kit [edit-scope]: 文件 ${filePath} 不在当前任务范围 (${scope})。如非必要请停止，额外改动记 TODO。`,
            });
          }
        }
      }

      // ── subagent-guard：子 Agent 管控 ──────────────────────
      if (tool === "task" && cfg.hooks_enabled.subagent_guard) {
        const agentType = (output.args?.subagent_type ?? "") as string;
        const dangerTypes = cfg.hooks_enabled.subagent_guard
          ? "executor designer scientist".split(" ")
          : [];
        const maxTurns = output.args?.max_turns;

        if (dangerTypes.includes(agentType) && !maxTurns) {
          throw new Error(
            `🚫 harness-kit [subagent-guard]: 危险 Agent 类型 "${agentType}" 缺少 max_turns 限制\n` +
            `请指定 max_turns 防止无限循环。`
          );
        }
      }

      // ── pretool-rule-anchor：长对话铁律锚定（写文件前）──────
      if ((tool === "write" || tool === "edit") && cfg.hooks_enabled.rule_anchor) {
        const { turn_threshold, interval } = cfg.rule_anchor;
        const offset = turnCount - turn_threshold;
        if (turnCount >= turn_threshold && offset >= 0 && offset % interval === 0) {
          const lastPrompt = readState(root, ".last-user-prompt");
          const driftWords = ["顺手", "顺便", "顺带", "捎带", "另外也", "同时也"];
          const isDrift = driftWords.some((w) => lastPrompt.includes(w));
          const driftWord = driftWords.find((w) => lastPrompt.includes(w));

          const msg = isDrift
            ? `⚠️ [第${turnCount}轮·漂移预警] 检测到范围扩展词「${driftWord}」。` +
              `铁律：①禁止编造(需file:line) ②完成前需VERIFIED ③git需用户批准 ④只改当前任务范围 ⑤最多3轮→BLOCKED`
            : `📌 [第${turnCount}轮·规则锚定] 铁律提醒：` +
              `①禁止编造 ②完成前需VERIFIED ③git需用户批准 ④范围冻结 ⑤最多3轮修复→BLOCKED`;

          // 注入到 output（OpenCode 的变通方式）
          console.warn(`\n${msg}\n`);
        }
      }

      // ── plan-gate：计划门禁（写 plan.md/executor.md 前）──────
      if (tool === "edit" && cfg.hooks_enabled.plan_gate) {
        const filePath = (output.args?.filePath ?? "") as string;
        if (filePath.includes("plan.md") || filePath.includes("executor.md")) {
          const docRoot = "rpe";
          // 检查是否有 rpe/ 目录和活跃 executor.md
          const rpeDir = join(root, docRoot);
          if (existsSync(rpeDir)) {
            // 软阻断：注入提醒
            Object.assign(output, {
              _harness_plan_gate: `⚠️ harness-kit [plan-gate]: 编辑 ${filePath}，请确认 Research Gate 已通过。`,
            });
          }
        }
      }
    },

    // ══════════════════════════════════════════════════════════
    // tool.execute.after — PostToolUse 等价
    // ══════════════════════════════════════════════════════════
    "tool.execute.after": async (input: any, output: any) => {
      const tool = input.tool ?? "";

      // ── One-Man Army 释放并发锁 (OMA) ──────────────────────
      if (["edit", "write", "replace", "str_replace"].includes(tool)) {
        const filePath = (input.args?.filePath ?? input.args?.file_path ?? "") as string;
        if (filePath) {
          try {
            const { promisify } = require("util");
            const { exec } = require("child_process");
            const execAsync = promisify(exec);
            await execAsync(`python3 ${join(root, ".claude/scripts/oma_lock_manager.py")} release "${filePath}"`);
          } catch (e) {
            // 静默释放
          }
        }
      }

      // ── posttool-bash-audit + error-dna + build-validator ──
      if (tool === "bash" && cfg.hooks_enabled.posttool_bash_audit) {
        const exitCode = output.exitCode ?? 0;
        const cmd = (input.args?.command ?? "") as string;
        const stdout = (output.stdout ?? "") as string;
        const stderr = (output.stderr ?? "") as string;

        // build-validator：构建失败记录
        if (exitCode !== 0 && cfg.hooks_enabled.build_validator) {
          const logFile = join(stateDir, "build-errors.log");
          const entry = `[${new Date().toISOString()}] CMD: ${cmd}\nSTDERR: ${stderr.slice(0, 500)}\n---\n`;
          try {
            const existing = existsSync(logFile) ? readFileSync(logFile, "utf-8") : "";
            writeFileSync(logFile, entry + existing, "utf-8");
          } catch {}
        }

        // error-dna：记录错误模式
        if (exitCode !== 0 && cfg.hooks_enabled.error_dna) {
          const dnaFile = join(stateDir, "error-dna.jsonl");
          const entry = JSON.stringify({ ts: Date.now(), cmd, exitCode, stderr: stderr.slice(0, 200) }) + "\n";
          try {
            writeFileSync(dnaFile, entry, { flag: "a", encoding: "utf-8" });
          } catch {}
        }
      }

      // ── read-tracker：读文件追踪 ────────────────────────────
      if (tool === "read" && cfg.hooks_enabled.read_tracker) {
        const filePath = (input.args?.filePath ?? input.args?.file_path ?? "") as string;
        if (filePath) {
          const trackFile = join(stateDir, "read-tracker.txt");
          try {
            const existing = existsSync(trackFile) ? readFileSync(trackFile, "utf-8") : "";
            if (!existing.includes(filePath)) {
              writeFileSync(trackFile, existing + filePath + "\n", "utf-8");
            }
          } catch {}
        }
      }

      // ── posttool-edit-quality：编辑质量提示 ────────────────
      if ((tool === "edit" || tool === "write") && cfg.hooks_enabled.posttool_edit_quality) {
        // OpenCode 中无 LSP 直接 hook，记录到日志供后续
        const filePath = (input.args?.filePath ?? input.args?.file_path ?? "") as string;
        if (filePath) {
          writeState(root, "last-edited-file.txt", filePath);
        }
      }
    },

    // ══════════════════════════════════════════════════════════
    // session.created — SessionStart 等价
    // ══════════════════════════════════════════════════════════
    "session.created": async () => {
      // ── inject-project-knowledge ────────────────────────────
      if (cfg.hooks_enabled.inject_project_knowledge) {
        const claudeDir = join(root, ".claude");
        const injectFiles = cfg.knowledge.inject_files;

        // 读取 index.md / kernel.md / claude-next.md 等
        const injected: string[] = [];
        for (const fileSpec of injectFiles) {
          const [fileName] = fileSpec.split(":");
          const filePath = join(claudeDir, fileName);
          if (existsSync(filePath)) {
            injected.push(`@${filePath}`);
          }
        }

        if (injected.length) {
          // 写入会话知识注入记录（供 AI 参考）
          writeState(root, "injected-knowledge.txt", injected.join("\n"));
        }
      }

      // 重置轮次计数
      turnCount = 0;
      writeState(root, "session-turns.json", JSON.stringify({ count: 0, updated: new Date().toISOString() }));

      // flywheel-report：加载飞轮报告
      if (cfg.hooks_enabled.skill_flywheel) {
        const flywheelFile = join(stateDir, "skill-flywheel.json");
        if (existsSync(flywheelFile)) {
          writeState(root, "flywheel-loaded.txt", new Date().toISOString());
        }
      }
    },

    // ══════════════════════════════════════════════════════════
    // session.idle — Stop 等价
    // ══════════════════════════════════════════════════════════
    "session.idle": async () => {
      // ── auto-snapshot：会话快照 ─────────────────────────────
      if (cfg.hooks_enabled.auto_snapshot) {
        const snapshotFile = join(stateDir, "session-handoff.md");
        const todoFile = join(stateDir, "todo-queue.md");
        const todoContent = existsSync(todoFile) ? readFileSync(todoFile, "utf-8") : "（无待办）";

        const snapshot = `# 会话快照 ${new Date().toISOString()}\n\n## Todo 状态\n${todoContent.slice(0, 500)}\n\n## 轮次\n${turnCount}\n`;
        try {
          writeFileSync(snapshotFile, snapshot, "utf-8");
        } catch {}
      }

      // skill-flywheel：记录使用的 skill
      if (cfg.hooks_enabled.skill_flywheel) {
        // 更新时间戳
        writeState(root, "flywheel-updated.txt", new Date().toISOString());
      }
    },

    // ══════════════════════════════════════════════════════════
    // message.updated — UserPromptSubmit 变通（轮次计数）
    // ══════════════════════════════════════════════════════════
    "message.updated": async ({ event }: any) => {
      // 仅统计用户消息
      if (event?.role === "user" || event?.type === "message.updated") {
        turnCount++;
        writeState(root, "session-turns.json", JSON.stringify({ count: turnCount, updated: new Date().toISOString() }));

        // 保存最后用户消息内容（供 pretool-rule-anchor 的漂移词检测使用）
        const content = event?.content ?? event?.text ?? "";
        if (typeof content === "string" && content) {
          writeState(root, ".last-user-prompt", content.slice(0, 500));
        }

        // turn-counter：每 N 轮注入铁律摘要
        const interval = cfg.turn_counter.todo_refresh_interval;
        if (turnCount > 0 && turnCount % interval === 0) {
          // 在 OpenCode 里通过 console.warn 输出（显示在 debug 日志）
          console.warn(
            `\n【铁律提醒·第 ${turnCount} 轮·始终生效】\n` +
            ` 1. 禁止编造：技术断言必须引用 file:line\n` +
            ` 2. 证据门禁：说"完成"前必须有 VERIFIED 证据\n` +
            ` 3. Git 门禁：commit/push 必须先报告，等用户批准\n` +
            ` 4. 范围冻结：只改当前任务文件，顺手发现的记 TODO\n` +
            ` 5. 修复上限：同一问题最多修 3 轮，第 3 轮失败→BLOCKED\n` +
            ` 6. 禁用词：禁止用"应该是/可能/通常"做技术断言\n`
          );
        }
      }
    },

    // ══════════════════════════════════════════════════════════
    // permission.asked — 权限申请透明（pretool-user-correction 变通）
    // ══════════════════════════════════════════════════════════
    "permission.asked": async ({ event }: any) => {
      if (!cfg.hooks_enabled.user_correction_detector) return;

      // 记录权限申请，供审计
      const entry = JSON.stringify({ ts: Date.now(), tool: event?.tool, description: event?.description }) + "\n";
      try {
        const logFile = join(stateDir, "permission-log.jsonl");
        writeFileSync(logFile, entry, { flag: "a", encoding: "utf-8" });
      } catch {}
    },

    // ══════════════════════════════════════════════════════════
    // experimental.session.compacting — 上下文压缩注入
    // ══════════════════════════════════════════════════════════
    "experimental.session.compacting": async (input: any, output: any) => {
      // 注入 harness-kit 铁律到压缩摘要，确保压缩后规则不丢失
      const ironLaw =
        `## harness-kit 铁律（压缩后保留）\n` +
        `1. 禁止编造：每个技术断言必须有 file:line 来源\n` +
        `2. 证据门禁：声明完成前必须提供 VERIFIED 证据\n` +
        `3. Git 门禁：任何 git 写操作必须先报告，等用户批准\n` +
        `4. 范围冻结：只改当前任务文件，额外发现记 TODO\n` +
        `5. 修复上限：同一问题最多修 3 轮，超限 BLOCKED\n` +
        `6. 禁用词：禁止"应该是/可能/通常"作为技术断言\n` +
        `7. 软完成语禁令：禁止"应该没问题了/基本完成/理论上"等\n` +
        `当前 Todo 状态：${readState(root, "todo-queue.md", "（无）").slice(0, 300)}`;

      if (output && Array.isArray(output.context)) {
        output.context.push(ironLaw);
      }
    },
  };
};

export default HarnessKitPlugin;
