/**
 * oracle-post.ts — tool.execute.after hook
 * Meta-Oracle post-review + anti-pattern detection.
 */

import { detectAntiPatterns } from "./detect"

interface OracleAfterInput {
  tool: string
  sessionID: string
  callID: string
  args: any
}

interface OracleAfterOutput {
  title: string
  output: string
  metadata: any
}

/**
 * Meta-Oracle post-tool review:
 * Audit tool output for compliance, anti-patterns, and quality issues.
 */
export async function metaOraclePostReview(
  input: OracleAfterInput,
  output: OracleAfterOutput,
): Promise<void> {
  const { tool, args } = input
  const toolOutput = output.output ?? ""

  // Detect anti-patterns in tool output
  const violations = detectAntiPatterns(tool, toolOutput, args)

  if (violations.length > 0) {
    // Log violations to output metadata
    output.metadata = {
      ...(output.metadata ?? {}),
      carror_anti_patterns: violations,
    }

    // Prefix output with warning for severe violations
    const severe = violations.filter((v) => v.severity === "high")
    if (severe.length > 0) {
      output.output = `⚠️ [CarrorOS] 反模式检测警告:\n${severe.map((v) => `  - ${v.name}: ${v.message}`).join("\n")}\n\n${toolOutput}`
    }
  }
}

/**
 * Anti-pattern detection on tool output (runs in parallel with Meta-Oracle).
 */
export async function antiPatternDetect(
  input: OracleAfterInput,
  output: OracleAfterOutput,
): Promise<void> {
  // Delegated to detectAntiPatterns in metaOraclePostReview
  // This is a separate hook entry point for clarity.
  return metaOraclePostReview(input, output)
}
