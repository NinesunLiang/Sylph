/**
 * privacy.ts — tool.execute.before hook
 * Privacy Gate: intercepts tool calls attempting to read sensitive files/paths.
 *
 * Equivalent to CC privacy-gate.py — blocks access to:
 *   - Environment variables (.env, .env.local, .env.*)
 *   - SSH keys (id_rsa, id_ed25519, .ssh/)
 *   - Certificates (.pem, .key, .crt, .p12)
 *   - Credentials (credentials, secret, .netrc, .pgpass)
 *   - Tokens (.npmrc, .npmtoken, api-key, api_key)
 *   - Cloud config (.aws/, .gcp/, .azure/, kube/config)
 *   - General privacy (.git-credentials, .docker/config.json, passwd)
 */

interface PrivacyGateInput {
  tool: string
  sessionID: string
  callID: string
  args: any
}

interface PrivacyGateOutput {
  args: any
}

/**
 * Sensitive path patterns — matched as case-insensitive substrings.
 * Each pattern is checked against extracted path/file/directory arguments
 * and Bash command strings.
 */
const SENSITIVE_PATTERNS: string[] = [
  // Environment variable files
  ".env",
  ".env.local",
  ".env.production",
  ".env.development",
  ".env.test",

  // SSH keys
  "id_rsa",
  "id_ed25519",
  "id_dsa",
  "id_ecdsa",
  ".ssh/",

  // Certificates / TLS
  ".pem",
  ".key",
  ".crt",
  ".p12",
  ".pfx",
  ".cert",

  // Credentials
  "credentials",
  ".netrc",
  ".pgpass",
  "_netrc",

  // Secrets
  "secret",
  ".secret",

  // Tokens
  ".npmrc",
  ".npmtoken",
  "api-key",
  "api_key",
  "apiToken",
  "api_token",
  "token.json",

  // Cloud provider configs
  ".aws/",
  ".gcp/",
  ".azure/",
  "kube/config",
  "kubeconfig",
  "gcloud",
  ".kube/",

  // Git credentials
  ".git-credentials",
  ".gitconfig",

  // Docker
  ".docker/config.json",

  // System password files
  "passwd",
  "shadow",
  "sudoers",

  // Service account keys
  "service-account",
  "service_account",
  "application_default_credentials",

  // Config files with potential secrets
  ".config/gh",
  ".config/git",

  // IDEs / Editors (may contain tokens)
  ".vscode/settings.json",
  ".cursor/config",
]

/**
 * Privacy Gate — intercept tool.execute.before to block sensitive path access.
 *
 * Strong blocking via throw Error — not a soft warning.
 * Messages are in Chinese with 🔒 prefix.
 */
export async function privacyGate(
  input: PrivacyGateInput,
  _output: PrivacyGateOutput,
): Promise<void> {
  const { tool, args } = input
  const extractedPaths = extractSensitivePaths(tool, args)

  if (extractedPaths.length > 0) {
    const matched = extractedPaths.map((p) => `"${p}"`).join(", ")
    throw new Error(
      `🔒 Privacy Gate 已阻断: 检测到敏感路径访问 (${matched})`,
    )
  }
}

/**
 * Extract path-like strings from tool call arguments.
 * Supports Bash/Read/Write/Edit tools and any tool with path/file/directory params.
 */
function extractSensitivePaths(tool: string, args: any): string[] {
  const found: string[] = []

  if (typeof args !== "object" || args === null) return found

  const values: string[] = []

  // Collect all string values from known path-bearing keys
  for (const [key, value] of Object.entries(args)) {
    const keyLower = key.toLowerCase()

    // Direct path/file/directory parameters
    if (["path", "file", "directory", "dir", "folder"].includes(keyLower)) {
      if (typeof value === "string") values.push(value)
    }

    // Bash command: extract paths from the command string
    if (keyLower === "command" && tool === "Bash") {
      if (typeof value === "string") values.push(value)
    }

    // Recursive check for nested objects (e.g., { location: { path: "..." } })
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      values.push(...extractSensitivePaths(tool, value))
    }

    // Arrays of strings (e.g., files: ["a.txt", "b.txt"])
    if (Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === "string") {
          values.push(item)
        }
        if (typeof item === "object" && item !== null) {
          values.push(...extractSensitivePaths(tool, item))
        }
      }
    }

    // Content parameter might contain paths too (Read file content)
    if (keyLower === "content" && typeof value === "string") {
      values.push(value)
    }
  }

  // Check each collected value against sensitive patterns
  for (const val of values) {
    const valLower = val.toLowerCase()

    for (const pattern of SENSITIVE_PATTERNS) {
      const patternLower = pattern.toLowerCase()

      // For simple filenames (no path separator), check word boundaries
      if (
        !pattern.includes("/") &&
        !pattern.startsWith(".") &&
        valLower === patternLower
      ) {
        if (!found.includes(pattern)) found.push(pattern)
        break
      }

      // For patterns with dots/slashes, do substring match
      if (valLower.includes(patternLower)) {
        if (!found.includes(pattern)) found.push(pattern)
        break
      }
    }
  }

  return found
}
