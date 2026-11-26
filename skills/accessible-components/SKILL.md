---
name: accessible-components
description: Build or fix accessible interactive components with complete, tested code following the WAI-ARIA Authoring Practices - modal dialog (native dialog with showModal, focus return, inert background), tabs (roving tabindex, arrow keys, automatic vs manual activation), menu button (actions menu with arrow keys, Escape, type-ahead) versus disclosure navigation, combobox / autocomplete (aria-activedescendant, listbox, result count announcements), plus accordion and toggle buttons. Each pattern lists the required roles, states and keyboard interactions, common bugs, React/Vue notes and a test checklist; the HTML examples pass this repository's audit scripts. Use when the user builds or reviews a modal, popup, drawer, tabs, dropdown menu, navigation submenu, autocomplete, typeahead, select replacement, accordion or toggle, or asks how to make a custom widget accessible.
license: MIT
compatibility: Plain HTML, CSS and JavaScript examples for current browsers (dialog, inert); adaptable to React, Vue, Svelte and Angular.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Accessible components

Pick the right pattern first (most "menus" are disclosures, most "custom selects" should
be native), then implement the roles, states and keyboard model completely. Half an ARIA
pattern is worse than plain HTML.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- Building a modal, drawer, confirmation dialog, tabs, dropdown, autocomplete, accordion
- Reviewing a component library or a third-party widget for keyboard and screen reader support
- An audit found `role.not_focusable`, `role.missing_context`, broken focus in a widget

## When not to use

- Checking existing markup mechanically: run `aria-review` and `keyboard-and-focus` first
- Plain forms: `accessible-forms`; data tables, carousels, date pickers, drag and drop,
  trees and grids are not covered here yet (see the WAI-ARIA APG for those)

## Workflow

1. **Choose the pattern** with this table (ask what the widget does, not what it looks like):

   | The user wants | Use | Reference | Example |
   | --- | --- | --- | --- |
   | content on top that blocks the page (confirm, form, image) | modal dialog | [references/dialog.md](references/dialog.md) | [assets/dialog.html](assets/dialog.html) |
   | switch between panels in place | tabs | [references/tabs.md](references/tabs.md) | [assets/tabs.html](assets/tabs.html) |
   | a list of actions (Rename, Delete) | menu button | [references/menu.md](references/menu.md) | [assets/menu-button.html](assets/menu-button.html) |
   | navigation links in a dropdown, FAQ, "show more" | disclosure / accordion | [references/disclosure.md](references/disclosure.md) | in the reference |
   | type to filter and pick a value | combobox | [references/combobox.md](references/combobox.md) | [assets/combobox.html](assets/combobox.html) |
   | pick one of a few fixed values | native `<select>` or radio buttons | `accessible-forms` | |
   | on/off setting | `<button aria-pressed>` or `<input type="checkbox" role="switch">` | [references/disclosure.md](references/disclosure.md) | |

2. **Check native options first**: `<dialog>`, `<details>/<summary>`, `<select>`,
   `<input list>` + `<datalist>`, `popover` attribute. Use them when the design allows.
3. **Implement from the example.** Copy the asset, keep its roles, states and key
   handlers, then restyle. When porting to a framework, keep ids stable (React `useId`),
   update ARIA states from component state, and manage focus in effects after render.
   Ask before replacing an existing component in the user's codebase; show the diff.
4. **Verify mechanically** with the sibling skills on the rendered HTML (open and closed):
   ```bash
   python3 ../aria-review/scripts/aria_lint.py widget-open.html
   python3 ../keyboard-and-focus/scripts/focus_audit.py widget-open.html
   ```
5. **Test by hand** with the checklist at the end of each reference: keyboard only, then
   NVDA + Firefox/Chrome and VoiceOver + Safari (`screen-reader-testing`). Test with the
   page zoomed to 200% and on a phone with VoiceOver/TalkBack for touch.

## Output

For a build request: the component code (HTML/CSS/JS or the user's framework), a table of
keyboard interactions and ARIA states it implements, and the manual test checklist.
For a review:

```
Component review: <ProductFilterDropdown>
Pattern: it shows links to category pages -> disclosure, not role="menu"
Problems:
 1. role="menu" + role="menuitem" on links: screen readers switch to application mode and
    users expect arrow keys that are not implemented -> remove the roles (plain list of links)
 2. Trigger is a <div>: not focusable -> <button type="button" aria-expanded aria-controls>
 3. Escape does not close; focus not returned -> add keydown handler (code below)
Fixed code: ...
Test checklist: Tab to button, Enter/Space opens, Tab moves through links, Escape closes
and focus returns to the button, aria-expanded flips true/false.
```
