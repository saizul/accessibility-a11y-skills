---
name: color-contrast-checker
description: Compute exact WCAG 2.2 contrast ratios with a tested script - single colour pairs, a list of pairs, or color/background pairs extracted from simple CSS (resolves var(--token) from :root, reads font-size and font-weight to apply the large-text threshold, composites rgba/hsla transparency). Reports AA and AAA results for normal and large text plus the 3:1 non-text threshold (1.4.11) for icons, borders and focus rings, and suggests the nearest passing foreground or background of the same hue. Accepts hex, rgb(), hsl() and named colours; never rounds 4.49:1 up. Use when the user asks whether colours are accessible, gives a palette, brand colours, design tokens, a Tailwind/CSS theme or a dark mode to check, or when an audit needs WCAG 1.4.3, 1.4.6 or 1.4.11 contrast checks.
license: MIT
compatibility: Python 3.8+ standard library only. Offline.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Colour contrast checker

Give exact contrast numbers instead of eyeballing, and propose the smallest colour change
that passes. The script is read-only and works on colours, pair lists and CSS files.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "Is #8a8a8a on white accessible?", "check our brand palette", "does this pass AA?"
- Design tokens, CSS custom properties, a theme file, a dark mode palette
- Button, link, placeholder, disabled-looking, focus-ring and icon colours
- A WCAG audit that needs 1.4.3 (text), 1.4.6 (AAA text) or 1.4.11 (non-text) results

## When not to use

- Text over photos, gradients or video: the ratio varies per pixel; sample the worst area
  in a design tool or browser colour picker, then check that pair here
- Complex CSS (cascade, inheritance, Tailwind classes in HTML): get the computed colours
  from the browser (devtools > Elements > Computed, or the contrast info in the colour picker)
  and check them with `--pairs`
- APCA / WCAG 3 contrast: not normative; this skill implements WCAG 2.x only

## Workflow

1. **Collect the pairs and their use.** For each pair know: text or non-text (icon,
   border, focus ring, chart line), font size and weight, and all states (default, hover,
   focus, visited, disabled, error, dark mode). Logos, inactive (disabled) controls and pure
   decoration are exempt; placeholder text is not.
2. **Run the checker.**
   ```bash
   python3 scripts/contrast.py "#767676" "#ffffff"
   python3 scripts/contrast.py "rgb(0 0 0 / 60%)" white          # transparency composited
   python3 scripts/contrast.py "#9ca3af" "#ffffff" --large        # >=24px, or >=18.66px bold
   python3 scripts/contrast.py "#94a3b8" "#ffffff" --ui           # icons, borders, focus rings: 3:1
   python3 scripts/contrast.py --pairs pairs.txt --level AAA      # "fg, bg, label" per line
   python3 scripts/contrast.py --css src/styles/theme.css --json
   ```
   Exit 0 = every pair passes the requested level, 1 = at least one fails, 2 = bad input.
   CSS mode checks rules that set `color`; a missing background falls back to the `body`
   background (or `--default-bg`) and is flagged "assumed"; gradients and images are skipped.
3. **Interpret.** Thresholds, exemptions and edge cases:
   [references/contrast-guide.md](references/contrast-guide.md). Key points:
   - AA text 4.5:1, large text 3:1; AAA 7:1 and 4.5:1; non-text 3:1 against adjacent colours.
   - Ratios are truncated, never rounded: 4.47:1 fails even if a tool shows "4.5".
   - Links inside text that are distinguished only by colour also need 3:1 against the
     surrounding text, or an underline (1.4.1).
   - Focus indicators need 3:1 against the background they sit on (1.4.11).
4. **Propose fixes.** Use the suggested colour (same hue and saturation, only lightness
   changed) or the suggested background. Present a small table: old, new, ratio. For design
   systems, change the token once rather than overriding per component. Ask before editing
   the user's files.
5. **Re-run** with the new values (and in dark mode if the site has one) and report.

## Output

```
Contrast (WCAG 2.2 AA)
| Pair                         | Ratio  | Needs | Result | Fix                         |
| .muted #9a9a9a on #ffffff    | 2.81:1 | 4.5   | FAIL   | #767676 (4.54:1)            |
| .btn-primary #fff on #1a4fd6 | 6.70:1 | 4.5   | pass   |                             |
| .badge #fff on #f59e0b       | 2.14:1 | 4.5   | FAIL   | text #424242 or bg #a36a00  |
| focus ring #93c5fd on #fff   | 1.80:1 | 3.0   | FAIL   | #3b82f6 or thicker 2-colour ring |
Skipped: .banner (gradient) - sample the lightest area and check it with --pairs.
```
