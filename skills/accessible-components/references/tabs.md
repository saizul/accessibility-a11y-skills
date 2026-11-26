# Tabs

APG: <https://www.w3.org/WAI/ARIA/apg/patterns/tabs/>. Working example: `assets/tabs.html`.

## Structure

```html
<div role="tablist" aria-labelledby="settings-title">        <!-- or aria-label -->
  <button role="tab" id="tab-a" aria-selected="true"  aria-controls="panel-a">Profile</button>
  <button role="tab" id="tab-b" aria-selected="false" aria-controls="panel-b" tabindex="-1">Security</button>
</div>
<div role="tabpanel" id="panel-a" aria-labelledby="tab-a" tabindex="0">...</div>
<div role="tabpanel" id="panel-b" aria-labelledby="tab-b" tabindex="0" hidden>...</div>
```

- Tabs are `<button>` elements: focusable, clickable, no extra key code for Enter/Space.
- Exactly one tab has `aria-selected="true"` and `tabindex="0"`; the others `tabindex="-1"`
  (roving tabindex): the tablist is one Tab stop.
- `tabindex="0"` on a panel lets keyboard users reach panels that start with plain text;
  drop it if the panel's first content is focusable.
- Inactive panels use `hidden` (not just CSS) so they are out of the accessibility tree.

## Keyboard

| Key | Action |
| --- | --- |
| Tab | into the tablist (selected tab), then out to the panel |
| Left / Right | previous / next tab (wraps); Up / Down for `aria-orientation="vertical"` |
| Home / End | first / last tab |
| Enter / Space | select the focused tab (manual activation only) |
| Delete | optional: close a closable tab |

**Automatic activation** (example): arrows select immediately. Use when panels render
instantly. **Manual activation**: arrows only move focus; Enter/Space select. Use when
switching loads data or is slow.

## Common bugs

| Bug | Fix |
| --- | --- |
| Tabs are links that change the URL and reload the page | that is navigation: use `<nav>` links with `aria-current="page"`, not tab roles |
| All tabs in the Tab order | roving tabindex |
| `aria-selected` never updated | update on every selection |
| Panels hidden with `opacity:0` | screen readers still read them; use `hidden` |
| Tab roles on a mobile accordion layout | switch the whole pattern (accordion) at small widths, not just the styling |
| Heading inside each tab button | allowed but noisy; put headings in panels instead |

## Test checklist

- [ ] One Tab stop for the tablist; arrows move and select; Home/End work
- [ ] Screen reader announces "Security, tab, 2 of 3, selected/not selected"
- [ ] Tab from the selected tab reaches the panel content
- [ ] Only the active panel is in the accessibility tree
