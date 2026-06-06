/**
 * compact.ts — experimental.session.compacting hook
 * Handoff protection: save context to disk before compact.
 */

import { execSync } from "child_process"
import path from "path"

interface CompactInput {
  sessionID: string
}

interface CompactOutput {
  context: string[]
  prompt?: string
}

/**
 * experimental.session.compacting handler
 * Calls handoff.py before compact to persist session context.
 */
export async function compactHandler(
  input: CompactInput,
  output: CompactOutput,
): Promise<void> {
  const sessionID = input.sessionID

  // Try to find .claude/scripts/handoff.py from cwd
  const handoffPy = path.join(process.cwd(), ".claude", "scripts", "handoff.py")

  let handoffData: string
  try {
    handoffData = execSync(
      `STATE_DIR="${path.join(process.cwd(), ".omc", "state")}" python3 "${handoffPy}" before-compact 2>/dev/null`,
      { encoding: "utf-8", timeout: 5000 },
    ).trim()
  } catch {
    handoffData = JSON.stringify({
      version: "v2",
      sessionID,
      error: "handoff.py not found or failed",
    })
  }

  const jsonMatch = handoffData.match(/\{.*\}/s)
  const parsed = jsonMatch ? JSON.parse(jsonMatch[0]) : {}

  output.context.push(
    `[CarrorOS Handoff] sessionID=${sessionID}`,
    `task_summary=${parsed.task_summary ?? "unknown"}`,
    `task_detail=${parsed.task_detail ?? ""}`,
    `queries=${(parsed.queries ?? []).length}`,
  )
}
