# Screen reader test scenarios

Run the scenarios that apply. "Expected" describes behaviour; exact wording varies by
screen reader. Keys: NVDA / VoiceOver macOS (VO = Control+Option).

## 1. Page load and structure

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Load the page | (automatic) | (automatic) | page title read, then the first content | 2.4.2 |
| Title is specific | NVDA+T | VO+F2 twice | "Topic - Site", unique per page/state | 2.4.2 |
| Language | listen | listen | correct voice/pronunciation; passages in other languages switch voice | 3.1.1, 3.1.2 |
| Landmarks list | NVDA+F7 > Landmarks / D | VO+U > Landmarks | banner, navigation (labelled if several), main, contentinfo | 1.3.1 |
| Headings list | NVDA+F7 > Headings / H | VO+U > Headings | one h1 that names the page; levels follow the structure; no fake headings | 1.3.1, 2.4.6 |
| Read all | NVDA+Down | VO+A | order matches the visual order; no hidden/duplicated/garbage text (icon fonts, "image", file names) | 1.3.2 |
| Skip link | Tab once, Enter | Tab once, VO+Space | moves to main; next item read is the main content | 2.4.1 |

## 2. Links and images

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Links list | NVDA+F7 > Links | VO+U > Links | every link name makes sense out of context; no "click here", no URLs | 2.4.4 |
| Image links | K | VO+Cmd+L | announced by purpose ("Home", not "logo.png") | 1.1.1 |
| Images | G | VO+Cmd+G | informative images described; decorative ones not announced | 1.1.1 |
| Icon buttons | B / Tab | Tab | "Close, button", not "button" or "times" | 4.1.2 |

## 3. Forms and errors

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Tab through fields | Tab | Tab | each field: label, role, required, hint | 1.3.1, 3.3.2 |
| Radio/checkbox groups | Tab into group | Tab into group | group question (legend) read with the first option | 1.3.1 |
| Submit empty | Enter | VO+Space | focus moves to an error summary or first error; errors read | 3.3.1 |
| Field with error | Tab | Tab | "invalid entry" plus the error text | 3.3.1, 3.3.3 |
| Autocomplete/combobox | type, Down | type, VO+Down | result count announced; options read; selection confirmed | 4.1.2, 4.1.3 |
| Success | submit valid | submit valid | confirmation read (new page title or status message) | 4.1.3 |

## 4. Dialogs, menus, tabs, disclosures

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Open a dialog | Enter on trigger | VO+Space | "Dialog name, dialog" and first focusable or content read | 4.1.2, 2.4.3 |
| Stay inside | Tab and Down arrow at end | VO+Right at end | cannot reach the page behind | 2.1.2 |
| Close | Escape | Escape | dialog gone; focus back on the trigger and announced | 2.4.3 |
| Disclosure/accordion | Enter | VO+Space | "expanded"/"collapsed" announced and correct | 4.1.2 |
| Menu button | Enter, arrows | VO+Space, arrows | "menu", items read with position; Escape returns | 4.1.2 |
| Tabs | arrows in tablist | arrows | "Tab name, tab, 2 of 3, selected"; panel content follows | 4.1.2 |

## 5. Dynamic content

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Add to cart / save | activate | activate | status read ("Added to cart") without moving focus | 4.1.3 |
| Filter results | change filter | change filter | "24 results" announced; focus stays | 4.1.3 |
| Loading | trigger | trigger | "Loading" then content or status; no silence | 4.1.3 |
| SPA navigation | follow a link | follow a link | new page title read; focus at the new h1 or main | 2.4.2, 2.4.3 |
| Toasts / timeouts | wait | wait | messages remain long enough or are logged; session timeout warning is read and can be extended | 2.2.1 |

## 6. Tables and media

| Step | NVDA | VoiceOver | Expected | WCAG |
| --- | --- | --- | --- | --- |
| Data table | T, Ctrl+Alt+arrows | VO+Cmd+T, VO+arrows | caption read; column/row headers announced when moving between cells | 1.3.1 |
| Layout table | T | VO+Cmd+T | not announced as a table | 1.3.1 |
| Video player | Tab through controls | Tab | play, mute, captions, fullscreen buttons named and state announced | 4.1.2, 1.2.2 |

## Severity for findings

| Severity | Meaning | Example |
| --- | --- | --- |
| Blocker | task cannot be completed | checkout button not announced or not activatable |
| High | task completed only with great effort or guesswork | error not announced; unnamed icon buttons |
| Medium | confusing or slow | missing landmarks, heading level jumps, verbose descriptions |
| Low | polish | redundant "link" text, minor order issue |
