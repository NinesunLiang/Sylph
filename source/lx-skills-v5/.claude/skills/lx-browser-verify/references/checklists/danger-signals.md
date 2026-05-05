# Browser Visual Verification — Danger Signal Self-Check

Before outputting the final report, check every item below. Any unchecked item -> go back to the corresponding step and correct.

## Accuracy Checks

- [ ] Did I actually start a dev server (or confirm one was running) before attempting screenshots? (Step 3 prerequisite)
- [ ] Did I use the correct viewport dimensions for each resolution tier (desktop 1920x1080, tablet 768x1024, mobile 375x812)?
- [ ] Did I wait for page load completion (networkidle or domcontentloaded) before capturing screenshots?
- [ ] Did I verify the correct URL/route was loaded, not a 404 or error page?
- [ ] Did I confirm dark mode is actually supported before reporting dark mode issues? (Check for `dark:` classes, `prefers-color-scheme`, or theme toggle)

## Evidence Completeness Checks

- [ ] Does every verification claim have an actual screenshot file or tool output as evidence?
- [ ] Were all requested resolutions actually captured (not just desktop)?
- [ ] Did I provide pixel-level or region-level comparison data for visual regression claims (not just "looks different")?
- [ ] Is every interactive flow step backed by a navigation/click/type command + resulting screenshot?
- [ ] Did I record the actual page URL in the screenshot metadata (not assumed)?

## False Positive Prevention

- [ ] Did I account for intentional design changes before flagging visual regressions? (Check git history for deliberate CSS/layout changes)
- [ ] Did I distinguish between rendering variance (anti-aliasing, subpixel) and actual layout shifts?
- [ ] Did I confirm font loading completed before flagging typography differences?
- [ ] Did I check whether a "missing element" is simply hidden at that viewport via responsive classes (e.g., `hidden md:block`)?
- [ ] Did I account for dynamic content (timestamps, avatars, random data) that naturally differs between captures?

## Tool & Environment Checks

- [ ] If Playwright was unavailable, did I clearly state the degradation and switch to manual checklist mode?
- [ ] Did I verify the dev server port matches the project configuration (not hardcoded to 3000)?
- [ ] Did I check that the browser context was clean (no cached state from previous runs)?

## Uncertainty Handling

- [ ] Are visual differences I cannot explain marked as "pending confirmation" rather than definitively flagged?
- [ ] Are cross-browser rendering differences within acceptable tolerance marked appropriately (not P0)?
- [ ] Did I avoid claiming "pixel-perfect match" without actual pixel-diff evidence?
