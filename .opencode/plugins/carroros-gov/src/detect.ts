/**
 * detect.ts — Anti-pattern detection engine
 * Based on CarrorOS anti-patterns.md (A1-L1, 18 patterns)
 */

export interface AntiPatternViolation {
  name: string
  severity: "low" | "medium" | "high"
  message: string
}

interface ToolCallArgs {
  command?: string
  [key: string]: unknown
}

/**
 * Detect anti-patterns in tool output and call arguments.
 */
export function detectAntiPatterns(
  tool: string,
  output: string,
  args: ToolCallArgs,
): AntiPatternViolation[] {
  const violations: AntiPatternViolation[] = []

  // A2: 虚假完成 — 软完成语
  const softCompleteWords = [
    "应该没问题",
    "应该可以",
    "基本完成",
    "理论上",
    "看起来正常",
    "差不多了",
    "之前验证过",
    "should be fine",
    "basically done",
  ]
  for (const word of softCompleteWords) {
    if (output.includes(word)) {
      violations.push({
        name: "A2: 虚假完成",
        severity: "high",
        message: `输出包含软完成语「${word}」，必须替换为具体证据`,
      })
      break
    }
  }

  // D1: 断连后上下文丢失 — 要求用户重述
  if (output.includes("继续上次") || output.includes("什么任务") || output.includes("之前做过什么")) {
    violations.push({
      name: "D1: 断连后上下文丢失",
      severity: "medium",
      message: "不要要求用户重新解释背景。检查 session-handoff-v2.json 恢复上下文",
    })
  }

  // E2: 执行假死 — 长时间无反馈
  if (tool === "Bash" && args.command) {
    const cmd = String(args.command)
    if (cmd.includes("sleep") && !output.trim()) {
      violations.push({
        name: "E2: 执行假死",
        severity: "medium",
        message: "Bash sleep 可能产生假死，考虑拆分子任务",
      })
    }
  }

  // F1: 假设驱动 — 不看代码先猜
  if (output.match(/应该是|通常|一般来说/) && !output.match(/file:line|L\d+/)) {
    violations.push({
      name: "F1: 假设驱动",
      severity: "high",
      message: "技术断言应引用 file:line，无引用标记为 [推断, 待确认]",
    })
  }

  // H1: 语义编造 — 百分比/评分无来源
  if (output.match(/\d+%/)) {
    const hasSource = output.includes("file:line") || output.includes("URL") || output.includes("来源")
    if (!hasSource) {
      violations.push({
        name: "H1: 语义编造",
        severity: "high",
        message: "百分比数据缺少来源 URL 或 file:line，需标注 [内部自检]",
      })
    }
  }

  // L1: 静默失败 — 空输出但预期有内容
  if (tool === "Bash" && !output.trim()) {
    violations.push({
      name: "L1: 静默失败",
      severity: "medium",
      message: "Bash 输出为空，验证 exit code 和副作用",
    })
  }

  return violations
}
