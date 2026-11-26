# Combobox (autocomplete)

APG: <https://www.w3.org/WAI/ARIA/apg/patterns/combobox/>. Working example:
`assets/combobox.html` (editable combobox, list autocomplete, manual selection).

## Before building one

- Fixed short list: native `<select>`.
- Suggestions where free text is also fine: `<input list="x">` + `<datalist id="x">`.
- Search box that shows results on a page: a normal `<input type="search">` + results
  region with a `role="status"` count; no combobox needed.
Build a custom combobox only when you need filtering, rich options or async results.

## Structure (ARIA 1.2)

```html
<label for="assignee">Assign to</label>
<input id="assignee" type="text" role="combobox" autocomplete="off"
       aria-autocomplete="list" aria-expanded="false" aria-controls="assignee-list">
<ul id="assignee-list" role="listbox" aria-label="People" hidden>
  <li role="option" id="person-1">Amina Rahman</li>
</ul>
<div role="status" aria-live="polite" class="visually-hidden"></div>
```

- `role="combobox"` goes on the `<input>` itself (ARIA 1.2; the 1.1 wrapper pattern is obsolete).
- `aria-expanded` reflects whether the listbox is shown; `aria-controls` points at it.
- DOM focus stays in the input; the highlighted option is `aria-activedescendant="person-1"`
  on the input and `aria-selected="true"` on the option.
- `autocomplete="off"` here is correct: browser autofill would cover the listbox. (It is
  not a personal-data field; for address lookups keep a plain field with the right token as a fallback.)
- Announce the number of results in a polite live region, debounced (300-500 ms).

## Keyboard

| Key | Action |
| --- | --- |
| Typing | filter, open the listbox when there are matches |
| Down / Up | open if closed; move the highlight (wraps) |
| Enter | accept the highlighted option, close |
| Escape | close the listbox; second Escape clears the input (optional) |
| Alt+Down | open without moving the highlight (optional) |
| Tab | accept nothing (or the highlighted option, if that is your documented behaviour) and move on |
| Home / End | move the caret in the input (do not hijack them) |

## Async results

- Show "Searching..." in the status region, then "5 results available".
- Do not re-render the input or move focus when results arrive.
- Keep the highlighted option valid when the list changes (reset to none).

## Common bugs

| Bug | Fix |
| --- | --- |
| Options are buttons that take focus | keep focus in the input, use `aria-activedescendant` |
| Highlight only visual (CSS class) | set `aria-selected` and `aria-activedescendant` |
| `aria-activedescendant` points at a removed option | clear it when the list re-renders |
| Listbox closes on mousedown before click registers | `preventDefault` on listbox mousedown |
| No label, placeholder "Search..." only | visible `<label>` |
| Every keystroke announced ("5 results", "4 results"...) | debounce the status message |

## Test checklist

- [ ] Input announced as "Assign to, combo box, collapsed, editable text" (wording varies)
- [ ] Typing announces the result count; Down arrow reads each option name
- [ ] Enter fills the input and closes; Escape closes
- [ ] Works with VoiceOver on iOS (swipe to the list) and with voice control ("click Amina Rahman")
