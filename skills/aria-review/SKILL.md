---
name: aria-review
description: Review and lint WAI-ARIA usage in HTML with a deterministic script - invalid, misspelled, abstract and deprecated roles; unknown aria-* attributes (aria-labeledby typos); invalid values (aria-expanded="yes"); aria-labelledby, aria-describedby and aria-controls pointing at missing ids; aria-hidden="true" on focusable elements or the body; redundant roles (button role="button"); roles overriding native semantics; missing required states (role=checkbox without aria-checked) and required parents (role=tab outside tablist); interactive roles that cannot be focused; unnamed dialogs; aria-label on generic divs; duplicate unlabelled landmarks. Then applies the five rules of ARIA to replace ARIA with native HTML where possible. Use when the user asks to review ARIA, fix screen reader announcements, check role or aria attribute usage, audit a custom widget or component library markup, or when axe/Lighthouse reports ARIA errors.
license: MIT
compatibility: Python 3.8+ standard library only. Works offline on HTML files.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# ARIA review

ARIA changes what assistive technology announces, never what the browser does. Bad ARIA
is worse than none. Lint the markup, then remove or fix ARIA, preferring native HTML.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "Review the ARIA in this component", "screen reader says 'clickable' / nothing"
- Custom widgets: tabs, menus, accordions, comboboxes, toggles, dialogs
- axe / Lighthouse / WAVE reports `aria-*` errors and the user wants them understood
- Reviewing a design system's rendered HTML (Storybook "show code", SSR output)

## When not to use

- Building a widget from scratch: `accessible-components` has complete patterns
- General page audit (alt text, labels, headings): `wcag-html-audit`
- Keyboard behaviour and focus styles: `keyboard-and-focus`

## Workflow

1. **Get rendered HTML** (component output, not JSX source): save the DOM from devtools,
   Storybook's HTML panel, or a server-rendered page. Include the widget in its open and
   closed states if they differ (two files).
2. **Run the linter.**
   ```bash
   python3 scripts/aria_lint.py widget.html
   python3 scripts/aria_lint.py dist/ --json
   python3 scripts/aria_lint.py page.html --fail-on high --ignore role.redundant
   ```
   Exit 0 = nothing at or above `--fail-on` (default `medium`), 1 = findings, 2 = bad input.
   Rules and the reasoning behind each: [references/aria-rules.md](references/aria-rules.md).
3. **Fix in this order.**
   1. `aria_hidden.focusable`, `aria_hidden.body`: content keyboard users reach but screen
      readers cannot perceive. Remove `aria-hidden` or make the content inert.
   2. `role.not_focusable`, `role.missing_required`, `role.missing_context`: the widget
      announces a role it does not implement. Usually replace with a native element.
   3. `aria.broken_reference`, `aria.unknown_attribute`, `aria.invalid_value`: silently
      ignored attributes (typos such as `aria-labeledby` are common).
   4. `role.invalid`, `role.abstract`, `name.missing`, `name.prohibited_on_generic`.
   5. `role.redundant`, duplicate landmarks: tidy-ups.
4. **Apply the five rules of ARIA** ([references/aria-rules.md](references/aria-rules.md)):
   - Native first: `<button>` not `div role=button`, `<a href>` not `span role=link`,
     `<input type=checkbox>` not `div role=checkbox`, `<dialog>` not `div role=dialog`.
   - Do not change native semantics (`<h2 role=tab>`: wrap instead).
   - Every interactive ARIA control must be keyboard operable.
   - No `role="presentation"` or `aria-hidden="true"` on focusable elements.
   - Every interactive element has an accessible name.
   Show the replacement markup and the states the JavaScript must keep in sync
   (`aria-expanded`, `aria-selected`, `aria-checked`, `aria-pressed`, `aria-current`).
5. **Check what ARIA cannot express statically.** States must change at runtime: open the
   widget, toggle it, and confirm attribute updates in devtools, then listen with a screen
   reader (`screen-reader-testing`). Live regions must exist in the DOM before content is
   inserted into them.
6. **Re-run** the linter on the fixed markup.

## Output

```
ARIA review: settings-panel.html - 4 high, 2 medium, 3 low

HIGH aria_hidden.focusable line 17: <div aria-hidden="true"> contains <a href="/secret">
     -> the off-canvas menu is hidden from screen readers but still in Tab order:
        add the inert attribute while closed (and drop aria-hidden)
HIGH role.not_focusable line 13: <div role="button">Save</div>
     -> <button type="button">Save</button> (Enter/Space and focus for free)
HIGH role.missing_required line 12: role="checkbox" without aria-checked
     -> <input type="checkbox" id="remember"><label for="remember">Remember me</label>
MED  aria.invalid_value line 15: aria-expanded="yes" -> "true"/"false", toggled in JS
LOW  role.redundant: <main role="main">, <ul role="list"> (keep role=list only if
     list-style:none removes list semantics in Safari and you need them)

Runtime checks to do: open/close the menu and watch aria-expanded; tab order while closed.
```
