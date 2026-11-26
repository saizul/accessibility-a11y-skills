# Modal dialog

APG: <https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/>. Working example:
`assets/dialog.html`.

## Use native `<dialog>` with `showModal()`

`showModal()` gives you, in all current browsers: top layer rendering, `::backdrop`, the
rest of the page made inert (no focus, no screen reader access), Escape to close, and the
`dialog` role with `aria-modal` semantics. You still need to:

- Name it: `aria-labelledby` pointing at the dialog heading.
- Optionally describe it: `aria-describedby` for a short message (confirm dialogs).
- Decide initial focus: `autofocus` on the least destructive control (Cancel) for
  confirmations; on the first field for forms; on the heading (with `tabindex="-1"`) when
  the dialog starts with long text.
- Return focus to the opener on close (most browsers do; do it explicitly).
- Provide a visible close button (`aria-label="Close"`), at least 24x24px (44px is better).

```html
<button type="button" id="open-filters">Filters</button>
<dialog id="filters" aria-labelledby="filters-title">
  <h2 id="filters-title">Filter products</h2>
  <form method="dialog">...<button value="apply">Apply</button></form>
</dialog>
<script>
  const d = document.getElementById("filters");
  document.getElementById("open-filters").onclick = () => d.showModal();
  d.addEventListener("close", () => document.getElementById("open-filters").focus());
</script>
```

## Keyboard

| Key | Action |
| --- | --- |
| Tab / Shift+Tab | cycle through focusable elements inside the dialog (browser handles it with showModal) |
| Escape | close (fires `cancel` then `close`); do not block it unless data would be lost, then ask |
| Enter | activates the focused button; `form method="dialog"` submits and closes |

## Without `<dialog>` (legacy component libraries)

`role="dialog"` + `aria-modal="true"` + `aria-labelledby`, then all of: move focus in,
trap Tab inside (wrap first/last), close on Escape, set `inert` on every sibling of the
dialog container, restore focus, prevent background scroll. Missing any one is a bug.

## Non-modal dialogs and popovers

`dialog.show()` (non-modal) or the `popover` attribute for lightweight overlays (menus,
toggletips). No focus trap, Escape still closes, focus stays in the page flow. Do not use
`aria-modal="true"` for these.

## Common bugs

| Bug | Effect |
| --- | --- |
| `display:none` dialog opened by toggling a class, focus not moved | screen reader users do not know it opened |
| Background not inert | Tab and the virtual cursor wander behind the overlay |
| `aria-hidden="true"` on `<body>` or the app root while the dialog is inside it | the dialog is hidden too |
| Close button is an `×` character in a div | unnamed and not focusable |
| Focus lands on `<body>` after close | users must start from the top |
| Dialog opened on page load (newsletter, cookie wall) | disorienting; prefer non-modal banners |
| Scroll locked with `overflow:hidden` on body, iOS jumps | test on iOS; use `overscroll-behavior` and keep the position |

## React notes

Render `<dialog ref={ref}>` and call `ref.current.showModal()` in an effect when `open`
becomes true, `close()` when false; listen to `onClose` to sync state (Escape closes it
natively). Keep the opener in a ref to restore focus.

## Test checklist

- [ ] Opening moves focus into the dialog; the heading/name is announced with "dialog"
- [ ] Tab and Shift+Tab never leave the dialog; the page behind is not reachable by the
      screen reader virtual cursor either (NVDA: arrow down at the end of the dialog)
- [ ] Escape closes; the close button works; focus returns to the opener
- [ ] At 200% zoom and 320px width the dialog content scrolls and buttons are reachable
- [ ] Destructive confirm dialogs focus Cancel first
