/**
 * oracle.ts — tool.execute.before hook
 * Oracle pre-review: assess tool call risk and block high-risk operations.
 */

interface OracleBeforeInput {
  tool: string
  sessionID: string
  callID: string
}

interface OracleBeforeOutput {
  args: any
}

// High-risk tools that need blocking
const HIGH_RISK_TOOLS = new Set([
  "Bash",        // shell access
  "Write",       // file write
  "Edit",        // file edit
])

// Tools that always require explicit permission
const PERMISSION_REQUIRED_TOOLS = new Set([
  "Bash",
])

/**
 * Assess tool risk and block high-risk operations.
 * CarrorOS principle: guard before excite — prevent damage before it happens.
 *
 * This is an "Oracle" gate — it runs BEFORE the tool executes.
 */
export async function oraclePreReview(
  input: OracleBeforeInput,
  output: OracleBeforeOutput,
): Promise<void> {
  const { tool, args } = input

  // Block known dangerous patterns
  if (HIGH_RISK_TOOLS.has(tool)) {
    // Check for dangerous args
    if (isDangerousToolCall(tool, args)) {
      throw new CarrorBlockedError(
        `[CarrorOS Oracle] 高风险操作已阻断: ${tool}`,
      )
    }
  }

  // Sanitize args: strip sensitive values
  output.args = sanitizeArgs(args)
}

function isDangerousToolCall(tool: string, args: any): boolean {
  if (tool === "Bash" && typeof args === "object" && args !== null) {
    const cmd = String(args.command ?? args.Command ?? "")
    const dangerous = [
      "rm -rf /",
      "rm -rf ~",
      "sudo ",
      "chmod 777 ",
      ":(){ :|:& };:", // fork bomb
      "dd if=/dev/zero",
      "> /dev/sda",
      "> /dev/nvme",
      "git push --force",
      "git reset --hard HEAD",
    ]
    return dangerous.some((d) => cmd.includes(d))
  }
  return false
}

function sanitizeArgs(args: any): any {
  if (typeof args !== "object" || args === null) return args
  const sanitized = { ...args }

  // Strip environment variables that may contain secrets
  if (sanitized.env) {
    const safeEnv: Record<string, string> = {}
    for (const [key, val] of Object.entries(sanitized.env as Record<string, string>)) {
      if (!key.toLowerCase().includes("key") &&
          !key.toLowerCase().includes("token") &&
          !key.toLowerCase().includes("secret") &&
          !key.toLowerCase().includes("password")) {
        safeEnv[key] = val
      }
    }
    sanitized.env = safeEnv
  }

  return sanitized
}

export class CarrorBlockedError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "CarrorBlockedError"
  }
}
