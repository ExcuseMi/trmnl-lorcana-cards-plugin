---
name: defense-svg-fill
description: defense/willpower icon uses dark bg + white number; fill:white on shield paths hides the number
metadata:
  type: feedback
---

The `w` (defense/willpower) SYMBOL uses hardcoded `fill:black;stroke:white` on all paths (no `currentcolor`), matching `assets/icons/defense.svg`. No background circle is rendered for it in `makeStat` (`dark` flag skips the bg div).

**Why:** The defense icon is a self-contained black shield with white stroke and white number — it doesn't need a colored circle behind it. Using `currentcolor` or `fill:white` caused number readability issues on various backgrounds.

**How to apply:** Keep the `w` SVG paths as `fill:black;stroke:white` (hardcoded, not currentcolor). In `makeStat`, the bg div is only appended when `!dark`. The strength (`s`) symbol still uses `fill:white;stroke:currentcolor` with a white bg circle.
