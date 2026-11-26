# Keyboard walkthrough checklist

Setup: desktop browser at 100% zoom. On macOS enable "Keyboard navigation" (System
Settings > Keyboard) and in Safari "Press Tab to highlight each item" (Settings > Advanced),
or use Chrome/Firefox. Do not use the mouse after the page loads.

## Keys to use

| Key | Expected |
| --- | --- |
| Tab / Shift+Tab | next / previous interactive element |
| Enter | activate links and buttons, submit forms |
| Space | activate buttons, toggle checkboxes, open selects; scrolls the page otherwise |
| Arrow keys | inside radio groups, tabs, menus, listboxes, sliders, grids |
| Escape | close dialogs, menus, tooltips, comboboxes |
| Home / End | first / last item in composite widgets |

## Checklist

| # | Check | WCAG | Pass when |
| --- | --- | --- | --- |
| 1 | First Tab shows a skip link that moves focus to the main content | 2.4.1 | link visible on focus, next Tab continues inside main |
| 2 | Every link, button, field and custom control receives focus | 2.1.1 | nothing interactive is skipped |
| 3 | Nothing non-interactive receives focus | 2.4.3 | no empty tab stops (wrappers, headings with tabindex=0) |
| 4 | Focus is always visible, with enough contrast | 2.4.7, 1.4.11 | you can see where you are on every stop, in light and dark mode |
| 5 | Order follows the visual and logical order | 2.4.3 | no jumps between columns, no jump to footer and back |
| 6 | Focused element is not hidden by sticky headers, footers, cookie banners or chat buttons | 2.4.11 | at least part of it is visible; ideally all |
| 7 | Every control works with Enter/Space (and arrows where expected) | 2.1.1 | custom buttons, cards, toggles, sliders, date pickers |
| 8 | Menus and dropdowns open with keyboard and close with Escape; focus returns to the trigger | 2.1.1, 2.4.3 | |
| 9 | Dialogs: focus moves inside on open, Tab stays inside, Escape closes, focus returns to the opener | 2.1.2, 2.4.3 | |
| 10 | No keyboard trap: you can always Tab out of embeds, editors, maps, video players | 2.1.2 | if a trap is intentional (editor), the way out is documented on screen |
| 11 | Tooltips and popovers appear on focus too, can be dismissed with Escape without moving focus | 1.4.13 | |
| 12 | Actions do not lose focus: after deleting a row, closing a toast, "load more", focus lands somewhere sensible | 2.4.3 | not on `<body>` |
| 13 | SPA route change moves focus to the new page heading (or main) and updates the title | 2.4.3, 2.4.2 | screen reader announces the new page |
| 14 | Single-key shortcuts can be turned off or remapped | 2.1.4 | |
| 15 | Focus does not trigger changes (no navigation or submit on focus) | 3.2.1 | |
| 16 | Drag-and-drop has a keyboard / single-pointer alternative | 2.5.7, 2.1.1 | e.g. "Move up/down" buttons |
| 17 | Targets are at least 24x24 CSS px or spaced apart | 2.5.8 | icon buttons, pagination, close buttons |
| 18 | Forms: Enter submits, errors move focus to an error summary or first invalid field | 3.3.1 | |
| 19 | Carousels/auto-playing content can be paused from the keyboard | 2.2.2 | pause button reachable before the slides |
| 20 | Zoom to 200%: focus still visible and order still logical | 1.4.4, 1.4.10 | |

## Recording results

```
| # | Step | Result | Notes |
| 1 | Skip link | FAIL | no skip link; 23 stops before main |
| 9 | Newsletter dialog | FAIL | Tab escapes to page behind; no Escape |
```
