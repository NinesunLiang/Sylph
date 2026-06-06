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
import { metaOraclePostReview, antiPatternDetect } from "./oracle-post"
import { permissionAsk } from "./permission"
import { compactHandler } from "./compact"

export const server: Plugin = async (_input, _options) => {
  const hooks: Hooks = {
    "experimental.chat.system.transform": systemTransform,
    "tool.execute.before": oraclePreReview,
    "tool.execute.after": metaOraclePostReview,
    "permission.ask": permissionAsk,
    "experimental.session.compacting": compactHandler,
  }
  return hooks
}

export type { Hooks } from "@opencode-ai/plugin"
