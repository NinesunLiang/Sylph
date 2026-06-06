/**
 * @carroros/gov — CarrorOS governance plugin for OpenCode
 *
 * Exports the `server()` function returning an `@opencode-ai/plugin` Hooks object.
 * Registers hooks at:
 *   - chat.system.transform → inject governance rules
 *   - tool.execute.before → Oracle pre-review
 *   - tool.execute.after → Meta-Oracle post-review + anti-pattern detection
 *   - permission.ask → approval flow mapping
 *   - experimental.session.compacting → handoff protection
 */

import type { Plugin, Hooks } from "@opencode-ai/plugin"
import { systemTransform } from "./system"
import { oraclePreReview } from "./oracle"
import { privacyGate } from "./privacy"
import { metaOraclePostReview, antiPatternDetect } from "./oracle-post"
import { permissionAsk } from "./permission"
import { compactHandler } from "./compact"

/**
 * Composite tool.execute.before handler.
 * OC only allows one handler per event, so we compose multiple concerns:
 *   1. privacyGate — sensitive path/secret file access blocking
 *   2. oraclePreReview — high-risk command blocking + arg sanitization
 *
 * Order matters: privacy gate runs first (cheaper, broader catch),
 * then the Oracle review (heavier analysis of remaining calls).
 */
async function compositeBefore(input: any, output: any): Promise<void> {
  // Phase 1: Privacy Gate — block sensitive file/path access
  await privacyGate(input, output)

  // Phase 2: Oracle — block high-risk commands + sanitize args
  await oraclePreReview(input, output)
}

export const server: Plugin = async (_input, _options) => {
  const hooks: Hooks = {
    "experimental.chat.system.transform": systemTransform,
    "tool.execute.before": compositeBefore,
    "tool.execute.after": metaOraclePostReview,
    "permission.ask": permissionAsk,
    "experimental.session.compacting": compactHandler,
  }
  return hooks
}

export type { Hooks } from "@opencode-ai/plugin"
