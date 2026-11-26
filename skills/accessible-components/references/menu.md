# Menu button (actions menu)

APG: <https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/>. Working example:
`assets/menu-button.html`.

## Menu or not?

`role="menu"` means "application-style menu of commands". Screen readers switch to focus
mode and users expect arrow keys, type-ahead and Escape. Use it for **actions** (Edit,
Duplicate, Archive, Sort by). For **site navigation** (a dropdown of links) use a
disclosure: a `<button aria-expanded>` that shows a plain `<ul>` of `<a>` links
(see `references/disclosure.md`). Most website "mega menus" are disclosures.

## Structure

```html
<button type="button" id="actions-button" aria-haspopup="true" aria-expanded="false" aria-controls="actions-menu">
  Actions
</button>
<ul role="menu" id="actions-menu" aria-labelledby="actions-button" hidden>
  <li role="menuitem" tabindex="-1">Rename</li>
  <li role="menuitem" tabindex="-1">Duplicate</li>
  <li role="separator"></li>
  <li role="menuitemcheckbox" aria-checked="true" tabindex="-1">Show hidden files</li>
</ul>
```

- `aria-haspopup="true"` (= menu) and `aria-expanded` on the button, kept in sync.
- Items are not in the Tab order; focus moves to them with arrow keys (roving focus).
- Checkable items use `menuitemcheckbox` / `menuitemradio` with `aria-checked`.
- Disabled items: `aria-disabled="true"` (stay focusable so they are discoverable).

## Keyboard

| Key | On the button | In the menu |
| --- | --- | --- |
| Enter / Space | open, focus first item | activate item, close, focus button |
| Down / Up | open, focus first / last item | next / previous item (wraps) |
| Home / End | | first / last item |
| Escape | | close, focus button |
| Tab | | close, move on (do not trap) |
| Character | | focus next item starting with it (type-ahead) |

## Common bugs

| Bug | Fix |
| --- | --- |
| `role="menu"` on navigation links | disclosure pattern |
| Menu opens on hover only | open on click/Enter; hover is an extra |
| Items are `<a href="#">` with menuitem role, Tab moves through them | `tabindex="-1"` and arrow-key handling |
| Focus stays on the button while items are "highlighted" visually | move real focus (or use `aria-activedescendant` consistently) |
| Menu does not close on outside click or Tab | close it |
| `aria-expanded` on the menu instead of the button | it belongs on the button |

## Test checklist

- [ ] Button announced as "Actions, menu button, collapsed" (wording varies by reader)
- [ ] Enter/Down opens and focuses the first item; arrows, Home/End and type-ahead work
- [ ] Escape closes and returns focus; Tab closes and moves on
- [ ] `aria-expanded` toggles; checkable items announce checked state
