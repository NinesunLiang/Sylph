/**
 * system.ts — chat.system.transform hook
 * Injects compressed CarrorOS governance rules into every system prompt.
 *
 * Reads .claude/AGENTS.compact.md from the project directory.
 * Falls back to embedded minimal governance if file not found.
 */

import path from "path"
import fs from "fs/promises"

const FALLBACK_GOVERNANCE = `# Carror OS — 核心治理（内嵌版）

哲学优先级: #4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)
铁律:
1.禁止编造:断言必有file:line/命令输出
2.用户裁定:验收/选型/冲突由Boss决定
3.证据门禁:无VERIFIED证据禁止说"已完成/已验证"
4.Git门禁:编译→功能→报告→Boss批准→提交
5.范围冻结:一次一Step
6.隐私防线:禁读.env/私钥
7.断言真实:百分比/评分须有来源URL/file:line
8.哲学先行:过程性→直接执行,抉择性→哲学裁决
哲学冲突裁决:#4>#6>#3>#7>#5>#2>#1
权威链:Boss指令>项目宪法>PRD>Skill>设计文档>代码`

const COMPACT_FILE = ".claude/AGENTS.compact.md"

/**
 * Load governance rules from project's compact file.
 * Walk up from worktree to find .claude/AGENTS.compact.md
 */
async function loadGovernanceRules(worktree: string): Promise<string[]> {
  const compactPath = path.join(worktree, COMPACT_FILE)

  let content: string
  try {
    content = await fs.readFile(compactPath, "utf-8")
  } catch {
    // Fallback: try parent directories (in case worktree is subdir)
    try {
      const parentPath = path.join(worktree, "..", COMPACT_FILE)
      content = await fs.readFile(parentPath, "utf-8")
    } catch {
      return [FALLBACK_GOVERNANCE]
    }
  }

  return [content.trim()]
}

interface SystemTransformInput {
  sessionID?: string
  model: unknown
}

interface SystemTransformOutput {
  system: string[]
}

/**
 * chat.system.transform handler
 * Injects CarrorOS governance rules at the start of the system prompt.
 */
export async function systemTransform(
  input: SystemTransformInput,
  output: SystemTransformOutput,
): Promise<void> {
  const sessionID = input.sessionID ?? "unknown"

  // Try to infer worktree from session context (default: cwd)
  // In practice, OpenCode provides model info — but not worktree directly.
  // We use . as a reasonable default; projects have .claude/ in root.
  const worktree = process.cwd()

  const rules = await loadGovernanceRules(worktree)
  output.system.push(...rules)
}
