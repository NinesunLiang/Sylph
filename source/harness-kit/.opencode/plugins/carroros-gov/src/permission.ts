/**
 * permission.ts — permission.ask hook
 * Maps CarrorOS approval flow to OpenCode's native permission system.
 *
 * Low-risk operations → auto-allow
 * High-risk operations → ask user
 */

interface PermissionAskInput {
  type: string
  tool: string
  args: Record<string, unknown>
}

interface PermissionAskOutput {
  status: "ask" | "deny" | "allow"
}

// Tools/types that auto-allow (low risk)
const AUTO_ALLOW_TOOLS = new Set([
  "Read",
  "Grep",
  "ListFiles",
  "Glob",
  "search_files",
])

/**
 * permission.ask handler
 * Decide ask/deny/allow based on CarrorOS risk assessment.
 *
 * This is a PLUGIN-level permissions hook — the agent itself also has
 * OpenCode's own permission system (opencode.json). This hook is
 * CarrorOS specific overrides.
 */
export async function permissionAsk(
  input: PermissionAskInput,
  output: PermissionAskOutput,
): Promise<void> {
  const { tool } = input

  // Read operations: auto-allow
  if (AUTO_ALLOW_TOOLS.has(tool)) {
    output.status = "allow"
    return
  }

  // Sensitive file writes: ask
  if (tool === "Write" || tool === "Edit") {
    const filePath = String(input.args?.path ?? input.args?.file ?? "")
    const sensitivePatterns = [
      ".env",
      "id_rsa",
      "config.json",
      ".pem",
      ".key",
      "credentials",
      "secrets",
    ]
    if (sensitivePatterns.some((p) => filePath.includes(p))) {
      output.status = "ask"
      return
    }
  }

  // Default: allow for everything else (OpenCode's own permission system
  // already handles general approval).
  output.status = "allow"
}
