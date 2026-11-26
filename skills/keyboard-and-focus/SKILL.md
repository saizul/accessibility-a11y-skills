---
name: keyboard-and-focus
description: Make websites fully keyboard accessible and keep focus visible and predictable (WCAG 2.1.1, 2.1.2, 2.4.1, 2.4.3, 2.4.7, 2.4.11, 2.5.8). A static script finds mouse-only click handlers on divs and spans (onclick, @click, v-on:click, (click), ng-click), positive tabindex, tabindex=-1 on visible links, outline:none without a replacement in HTML, style blocks and CSS files, sticky headers that hide focus, missing or broken skip links, autofocus, hover-only and double-click handlers, small targets, and prints the predicted Tab order; then a guided manual walkthrough checks focus traps, dialogs, SPA route changes and focus return, with code for skip links, :focus-visible styles, inert and focus management. Use when the user asks about keyboard navigation, tab order, focus outline or focus ring, skip to content links, focus traps, "can't tab to", or keyboard-only testing.
license: MIT
compatibility: Python 3.8+ standard library only. Static analysis; the manual steps need a browser.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Keyboard and focus

Everything a mouse can do, the keyboard must do, with a visible focus indicator, a logical
order and no traps. The script finds what source code reveals; a Tab-key walkthrough
finds the rest.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "I can't reach the menu with Tab", "focus outline disappeared", "add a skip link"
- Custom clickable divs/cards, modals, off-canvas menus, carousels, SPA navigation
- Keyboard-only testing before launch; reviewing a CSS reset that removes outlines

## When not to use

- Building a specific widget (tabs, menu, combobox, dialog): `accessible-components`
- ARIA attribute correctness: `aria-review`
- Focus indicator colour contrast numbers: `color-contrast-checker --ui`

## Workflow

1. **Collect inputs**: rendered HTML of the page or template, plus the site CSS files
   (resets often hold `outline: none`). For SPAs, save the rendered DOM from devtools.
2. **Run the static audit.**
   ```bash
   python3 scripts/focus_audit.py page.html --css static/css/app.css --css static/css/reset.css
   python3 scripts/focus_audit.py dist/ --json --fail-on high
   python3 scripts/focus_audit.py page.html --order          # predicted Tab sequence
   ```
   Exit 0 = nothing at or above `--fail-on` (default `medium`), 1 = findings, 2 = bad input.
   CSS passed with `--css` is checked once, together with the first HTML file.
3. **Triage.**
   - `click.not_keyboard_accessible` / `click.role_not_focusable` (high): mouse-only
     controls. Replace with `<button type="button">` or `<a href>`; see
     [references/focus-patterns.md](references/focus-patterns.md) for the card pattern.
   - `css.focus_outline_removed` (high): add a `:focus-visible` style with at least 2px
     outline and 3:1 contrast; never remove outlines globally.
   - `link.fragment_target_missing`, `bypass.no_skip_link`: add or fix the skip link.
   - `tabindex.positive`, `tabindex.removed_from_order`: fix DOM order instead.
   - `css.sticky_may_obscure_focus`: `scroll-padding-top` equal to the header height.
   - `dialog.manual_check`: test the dialog by hand (step 4).
4. **Do the keyboard walkthrough** with [references/keyboard-checklist.md](references/keyboard-checklist.md):
   unplug the mouse (or don't touch it), start from the address bar, press Tab through the
   whole page and operate every control. Record: unreachable controls, invisible focus,
   illogical order, traps, focus lost after actions (deleted item, closed dialog, route
   change), content hidden under sticky bars.
5. **Fix with the patterns** in [references/focus-patterns.md](references/focus-patterns.md):
   skip link, `:focus-visible` ring, `inert` for off-canvas and modal backgrounds,
   focus management on SPA route change, returning focus after a dialog, roving tabindex.
   Show diffs; ask before editing files.
6. **Verify**: re-run the script, then repeat the walkthrough for the failed steps. Use
   `--order` output as the expected sequence in the test notes.

## Output

```
Keyboard and focus: product-list.html
HIGH  12 product cards use <div onclick> (line 88...) - not reachable by keyboard
      -> wrap the title in <a href="/p/123" class="card-link"> and stretch it over the card
HIGH  reset.css line 14 "*:focus { outline: none }" - no visible focus anywhere
      -> delete it; add :focus-visible { outline: 3px solid #1a4fd6; outline-offset: 2px }
MED   no skip link; 23 tab stops before <main>
LOW   sticky header (app.css line 40) may cover focused items -> html { scroll-padding-top: 72px }

Manual walkthrough (Chrome, keyboard only):
 1. Filter dialog: focus moves into it and returns to "Filters" on close - PASS
 2. Escape closes the dialog - FAIL (no handler) -> use <dialog> + showModal()
 3. After "Load more", focus stays on the button and new items follow it - PASS
```
