# ARIA rules and lint reference

Sources: WAI-ARIA 1.2 (<https://www.w3.org/TR/wai-aria-1.2/>), ARIA in HTML
(<https://www.w3.org/TR/html-aria/>), Using ARIA (<https://www.w3.org/TR/using-aria/>),
ARIA Authoring Practices Guide (<https://www.w3.org/WAI/ARIA/apg/>).

## The five rules of ARIA use

1. **Use native HTML** if an element with the semantics and behaviour exists.
2. **Do not change native semantics** unless you really must (`<h2><button>` instead of
   `<h2 role="button">`).
3. **All interactive ARIA controls must be keyboard operable** (focusable, Enter/Space,
   arrows where the pattern expects them).
4. **Do not use `role="presentation"`/`none` or `aria-hidden="true"` on focusable elements.**
5. **All interactive elements must have an accessible name.**

## Lint rules

| Rule | Sev | Meaning | Fix |
| --- | --- | --- | --- |
| `role.invalid` | high (low if a valid fallback follows) | not a WAI-ARIA 1.2 role (typo, made-up) | valid role or native element |
| `role.abstract` | high | abstract roles (`widget`, `landmark`, `input`, `section`...) are for the spec only | concrete role |
| `role.deprecated` | low | `directory` | `list` |
| `role.empty` | medium | `role=""` | remove |
| `role.redundant` | low | role equals the implicit role | remove (exception: `<ul role="list">` restores list semantics that Safari drops with `list-style: none`) |
| `role.overrides_native` | medium/low | role replaces native interactive semantics (`<button role="heading">`; low for `<a role="button">`) | use the matching element |
| `role.presentation_conflict` | medium | `role=none` on a focusable element or one with global ARIA: browsers ignore the role | remove the role or the focusability |
| `role.missing_required` | high | e.g. checkbox/radio/switch/menuitemcheckbox without `aria-checked`, slider without `aria-valuenow`, combobox without `aria-expanded`, scrollbar without `aria-controls` | add the state and update it in JS |
| `role.missing_context` | high | owned roles outside their container: `tab` outside `tablist`, `option` outside `listbox`, `menuitem` outside `menu`, `listitem` outside `list`, `row` outside `table/grid/rowgroup`, cells outside `row` | wrap in the container (or `aria-owns`) |
| `role.not_focusable` | high | `button`, `link`, `checkbox`, `slider`... on an element that cannot receive focus | native element, or `tabindex="0"` + key handlers |
| `role.roving_tabindex` | medium | composite items (tab, option, menuitem, treeitem, radio) with no tabindex at all | roving tabindex or `aria-activedescendant` |
| `aria.unknown_attribute` | high | attribute is not in WAI-ARIA 1.2 (`aria-labeledby`, `aria-role`, `aria-hiden`) | correct spelling |
| `aria.deprecated` | low | `aria-grabbed`, `aria-dropeffect` | remove; describe drag and drop with instructions |
| `aria.invalid_value` | medium | wrong token/number (`aria-expanded="yes"`, `aria-live="loud"`, `aria-level="two"`) | allowed value |
| `aria.broken_reference` | high/medium | id reference to nothing (labels, descriptions, error messages: high) | fix or remove |
| `aria.empty_label` | medium | `aria-label=""` | text or remove |
| `aria_hidden.focusable` | high | `aria-hidden="true"` subtree contains focusable elements | remove aria-hidden, or `inert` / `tabindex="-1"` / `disabled` |
| `aria_hidden.body` | high | `aria-hidden` on `<body>`/`<html>` hides everything | use `inert` on background siblings of a modal |
| `name.missing` | medium | dialog, alertdialog, img, progressbar, meter, tabpanel, tree, grid, listbox, menu, radiogroup, form, region without a name | `aria-labelledby` to the visible heading |
| `name.prohibited_on_generic` | medium | `aria-label` on `div`/`span` without a role: prohibited in ARIA 1.2, ignored by some screen readers | give a role, or put the text in the content |
| `landmark.duplicate_unlabelled` | low (medium for main) | several `nav`/`aside`/... without labels | `aria-label="Primary"`, `"Breadcrumb"`, `"Footer"` |

## Common misuse and the fix

| Seen | Problem | Use instead |
| --- | --- | --- |
| `<div role="button" onclick>` | no focus, no Enter/Space | `<button type="button">` |
| `<a href="#" role="button">` for actions | announced as button, but Space does not activate | `<button>` |
| `<span role="link" onclick>` | no focus, no href, no "open in new tab" | `<a href>` |
| `<div aria-hidden="true">` around an off-canvas menu that still has links | ghost tab stops | `inert` while closed |
| `aria-label` repeating visible text | double announcements or name mismatch | remove it |
| `aria-label` on a `<div>` card | ignored | heading inside the card, or `role="group"`/`region` with label |
| `role="menu"` for site navigation | menu pattern expects arrow keys and changes screen reader mode | `<nav><ul><li><a>`, disclosure buttons for submenus |
| `role="tooltip"` holding essential text | only some AT read it | `aria-describedby` to visible text |
| `aria-live` added at the same time as the content | first message not announced | render the empty live region at page load, then update it |
| `role="alert"` on every validation message | interrupts constantly | `aria-describedby` + one summary or `role="status"` |
| `role="application"` on a page section | disables screen reader browse keys | remove it |
| `tabindex="0"` on every element | dozens of useless tab stops | only on interactive elements |

## States the JavaScript must keep in sync

| Widget | Attribute | Values |
| --- | --- | --- |
| Disclosure / menu button / accordion header | `aria-expanded` | `true`/`false` on the button |
| Toggle button | `aria-pressed` | `true`/`false` (do not change the label too) |
| Tab | `aria-selected` | `true` on one tab; `tabindex="0"` on it, `-1` on others |
| Custom checkbox / switch | `aria-checked` | `true`/`false`/`mixed` |
| Current page link | `aria-current` | `page` (step, date, location also allowed) |
| Combobox | `aria-expanded`, `aria-activedescendant` | expanded while listbox shows; id of highlighted option |
| Invalid field | `aria-invalid` + `aria-describedby` | `true` only after validation fails |
| Busy region | `aria-busy` | `true` while loading, then `false` |
