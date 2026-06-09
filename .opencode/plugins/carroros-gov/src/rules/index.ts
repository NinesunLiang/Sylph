/**
 * rules/index.ts — Dynamic governance rule loader
 * Reads from .claude/rules/ directory at plugin startup.
 */

import path from "path"
import fs from "fs/promises"

export interface GovernanceRules {
  philosophy: string[]
  antiPatterns: string[]
  ironRules: string[]
}

/**
 * Load governance rules from .claude/rules/ directory.
 * Falls back gracefully if directory doesn't exist.
 */
export async function loadRules(worktree: string): Promise<GovernanceRules> {
  const rulesDir = path.join(worktree, ".claude", "rules")
  const rules: GovernanceRules = {
    philosophy: [],
    antiPatterns: [],
    ironRules: [],
  }

  try {
    await fs.access(rulesDir)
  } catch {
    return rules
  }

  const files = await fs.readdir(rulesDir)
  for (const file of files) {
    if (!file.endsWith(".md")) continue
    const content = await fs.readFile(path.join(rulesDir, file), "utf-8")

    if (file.includes("philosophy")) {
      rules.philosophy.push(content.trim())
    } else if (file.includes("anti-pattern")) {
      rules.antiPatterns.push(content.trim())
    } else if (file.includes("iron")) {
      rules.ironRules.push(content.trim())
    }
  }

  return rules
}
