# Focus patterns

## Skip link

```html
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <header>...</header>
  <main id="main" tabindex="-1">...</main>
</body>
```

```css
.skip-link {
  position: absolute;
  left: 1rem;
  top: -100px;
  padding: 0.75rem 1rem;
  background: #fff;
  color: #1a1a1a;
  z-index: 1000;
}
.skip-link:focus {
  top: 1rem;
}
main:focus {
  outline: none; /* main is a target, not a control; the ring would be distracting */
}
```

`tabindex="-1"` on `<main>` makes focus (not just scroll) move there in all browsers.

## Visible focus with :focus-visible

```css
/* Never: *:focus { outline: none } */
:focus-visible {
  outline: 3px solid #1a4fd6;
  outline-offset: 2px;
}
/* Works on light and dark backgrounds */
.on-image :focus-visible {
  outline: 2px solid #fff;
  box-shadow: 0 0 0 5px #1a1a1a;
}
/* Only hide the ring for mouse clicks, if the design insists */
:focus:not(:focus-visible) {
  outline: none;
}
```

Rules: at least 2px thick, 3:1 against adjacent colours, not hidden by `overflow: hidden`
on a parent (use `outline-offset: -3px` inside clipped containers). Windows High Contrast
mode / forced colours: use `outline` (box-shadow disappears); a transparent outline
`outline: 2px solid transparent` shows up in forced-colours mode.

## Sticky headers and focus not obscured (2.4.11)

```css
html {
  scroll-padding-top: 5rem;    /* header height + a little */
  scroll-padding-bottom: 4rem; /* sticky footer / cookie bar */
}
```

Cookie banners and chat launchers count too: make banners non-modal and small, or move
focus into them and keep them out of the way after dismissal.

## Clickable cards without div onclick

```html
<article class="card">
  <img src="/p/1.jpg" alt="">
  <h3><a class="card-link" href="/products/1">Linen shirt</a></h3>
  <p>EUR 49</p>
  <button type="button">Add to cart</button>
</article>
```

```css
.card { position: relative; }
.card-link::after { content: ""; position: absolute; inset: 0; } /* whole card clickable */
.card button { position: relative; z-index: 1; }                  /* keep inner button usable */
```

One tab stop per card (plus real buttons), the link name is the product name.

## Custom button (only if a native button is impossible)

```html
<div role="button" tabindex="0" class="btn">Save</div>
<script>
  document.querySelectorAll('[role="button"]').forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") el.click();
      if (e.key === " ") e.preventDefault(); // stop page scroll
    });
    el.addEventListener("keyup", (e) => {
      if (e.key === " ") el.click();       // buttons activate on Space keyup
    });
  });
</script>
```

A `<button type="button">` does all of this for free, plus form behaviour and disabled state.

## Off-canvas menus and modal backgrounds: inert

```js
const menu = document.getElementById("mobile-menu");
function setMenu(open) {
  menu.inert = !open;              // closed menu: no focus, no screen reader access
  toggle.setAttribute("aria-expanded", String(open));
  if (open) menu.querySelector("a, button").focus();
  else toggle.focus();
}
```

`inert` is supported in all current browsers. For a modal built without `<dialog>`, set
`inert` on the page siblings of the dialog container while it is open.

## Return focus after an action

```js
// Delete a row: move focus to the next row's first control, or the table heading.
function removeRow(row) {
  const next = row.nextElementSibling || row.previousElementSibling;
  row.remove();
  (next?.querySelector("button, a") || document.getElementById("orders-heading")).focus();
}
```

Headings used as focus targets need `tabindex="-1"`.

## SPA route changes

```js
// After the new view renders:
document.title = `${pageTitle} - Example Shop`;
const h1 = document.querySelector("main h1");
h1.setAttribute("tabindex", "-1");
h1.focus();
```

Optionally announce "Loaded: page title" in a polite live region. Do not move focus on
filter changes within the same page; announce the result count instead (`role="status"`).

## Roving tabindex (toolbars, tabs, radio-like groups)

```js
function roving(container, selector) {
  const items = [...container.querySelectorAll(selector)];
  items.forEach((el, i) => (el.tabIndex = i === 0 ? 0 : -1));
  container.addEventListener("keydown", (e) => {
    const i = items.indexOf(document.activeElement);
    if (i < 0) return;
    const keys = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: items.length - 1 };
    if (!(e.key in keys)) return;
    e.preventDefault();
    const next = items[(keys[e.key] + items.length) % items.length];
    items[i].tabIndex = -1;
    next.tabIndex = 0;
    next.focus();
  });
}
```

One Tab stop for the group, arrows move inside it.
