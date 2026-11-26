# Disclosure, accordion, navigation dropdowns and toggles

APG: <https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/>,
<https://www.w3.org/WAI/ARIA/apg/patterns/accordion/>,
<https://www.w3.org/WAI/ARIA/apg/patterns/button/>.

## Native first: details/summary

```html
<details>
  <summary>What is your returns policy?</summary>
  <p>You can return items within 30 days.</p>
</details>
```

Keyboard, state and announcements for free. Style the marker with `summary::marker` or
`list-style: none` plus your own icon.

## Disclosure button

```html
<button type="button" aria-expanded="false" aria-controls="more-filters">More filters</button>
<div id="more-filters" hidden>...</div>
<script>
  document.querySelectorAll("button[aria-expanded][aria-controls]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      document.getElementById(btn.getAttribute("aria-controls")).hidden = open;
    });
  });
</script>
```

Do not change the button label when it opens ("Show"/"Hide") and also toggle
`aria-expanded`; pick one (prefer `aria-expanded`).

## Accordion

```html
<h3>
  <button type="button" id="acc-1" aria-expanded="true" aria-controls="acc-panel-1">Shipping</button>
</h3>
<div id="acc-panel-1" role="region" aria-labelledby="acc-1">...</div>
<h3>
  <button type="button" id="acc-2" aria-expanded="false" aria-controls="acc-panel-2">Returns</button>
</h3>
<div id="acc-panel-2" role="region" aria-labelledby="acc-2" hidden>...</div>
```

- The button sits inside a heading of the right level (headings navigation still works).
- `role="region"` only for a few large panels (more than about 6 regions is landmark noise).
- Optional keys: Up/Down between headers, Home/End. Tab must work without them.

## Navigation dropdown (disclosure navigation)

```html
<nav aria-label="Primary">
  <ul>
    <li>
      <button type="button" aria-expanded="false" aria-controls="nav-products">Products</button>
      <ul id="nav-products" hidden>
        <li><a href="/products/shirts">Shirts</a></li>
        <li><a href="/products/shoes">Shoes</a></li>
      </ul>
    </li>
    <li><a href="/pricing" aria-current="page">Pricing</a></li>
  </ul>
</nav>
```

- No `role="menu"`/`menuitem`: links stay links, Tab moves through them.
- Escape closes the open submenu and returns focus to its button; opening one closes others.
- If the top-level item must also be a link, use a link plus a separate small toggle
  button labelled "Products submenu" (`aria-label`) next to it.
- Hover may open it as an extra, with a small delay, but never only on hover.

## Toggle button vs switch

```html
<button type="button" aria-pressed="false">Mute</button>                     <!-- toggle button -->
<input type="checkbox" role="switch" id="wifi"><label for="wifi">Wi-Fi</label> <!-- switch -->
```

Toggle buttons keep a constant label and flip `aria-pressed`. Switches are for settings
that apply immediately (on/off). Do not use both a changing label and a state.

## Test checklist

- [ ] Enter and Space toggle; state announced ("expanded"/"collapsed", "pressed")
- [ ] Hidden content is out of Tab order and the accessibility tree when collapsed
- [ ] Navigation dropdowns: Escape closes and returns focus; Tab never gets stuck
