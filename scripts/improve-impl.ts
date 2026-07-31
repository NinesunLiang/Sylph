/* Consolidated implementation improvements based on prototype analysis.
   Run: pnpm exec tsc scripts/improve-impl.ts --noEmit 2>/dev/null; echo "Design reference only" */

/* Prototype measurements (from Playwright extraction):
   - 64px sidebar (44px icon buttons, 10-12px padding)
   - Avatar: 40x40 circle @ (12,16)
   - 5 icon buttons: 44x44 @ y=72,124,176,228,280 (spacing 52px)
   - SVG icons: 24x24 centered in button
   - Brand color: #0072f5 (rgb(0,114,245))
   - Text primary: #080808 (rgb(8,8,8))
   - Text secondary: #999 (rgb(153,153,153))
   - Main font: HarmonyOS Sans, 14px default
   - Input bar at bottom, antd-styled
   - RSC streaming: Next.js SSR */
