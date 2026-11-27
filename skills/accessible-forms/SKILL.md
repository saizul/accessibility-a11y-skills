---
name: accessible-forms
description: Build and fix accessible HTML forms - visible labels, hints, required fields, grouped radios and checkboxes, inline errors tied with aria-describedby, error summaries, autocomplete for personal data (WCAG 1.3.5), redundant entry (3.3.7) and accessible authentication without paste blocking or puzzles (3.3.8). A script validates every autocomplete value against the HTML autofill grammar (section-*, shipping/billing, home/work/mobile, field names, webauthn), suggests the right token for name, email, phone, address, postcode, card and password fields, and flags missing labels, placeholder-as-label, aria-label that hides the visible label (2.5.3), radio groups without fieldset/legend, aria-invalid without a message, required shown only by an asterisk, and blocked paste. Use when the user builds or reviews a signup, login, checkout, contact or settings form, asks about form labels, error messages, form validation accessibility, or autocomplete attributes.
license: MIT
compatibility: Python 3.8+ standard library only. Works offline on HTML files.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Accessible forms

Forms are where accessibility failures cost money: abandoned checkouts and sign-ups.
Check the markup with the script, then fix labels, errors and autofill with the patterns.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- New or existing login, sign-up, checkout, address, contact, search or settings forms
- "What autocomplete value do I use for ...?", "is `autocomplete="zip"` valid?"
- Error messages that screen readers do not announce, placeholder-only fields
- A WCAG audit flagged 1.3.1, 1.3.5, 2.5.3, 3.3.1, 3.3.2, 3.3.3, 3.3.7 or 3.3.8

## When not to use

- Custom select/autocomplete widgets: `accessible-components` (combobox pattern)
- Whole-page audit: `wcag-html-audit`; keyboard-only behaviour: `keyboard-and-focus`
- Server-side validation logic or security of authentication (not an accessibility topic)

## Workflow

1. **Get the rendered form HTML**, ideally in two states: initial, and after a failed
   submit (errors shown). Save both from devtools if it is a client-rendered form.
2. **Run the checker.**
   ```bash
   python3 scripts/forms_check.py signup.html
   python3 scripts/forms_check.py checkout-errors.html --json
   python3 scripts/forms_check.py --token "shipping postal-code" --token "zip"   # validate values
   ```
   Exit 0 = nothing at or above `--fail-on` (default `medium`), 1 = findings (or an invalid
   `--token`), 2 = bad input. Token list and grammar:
   [references/autocomplete-tokens.md](references/autocomplete-tokens.md).
3. **Fix labels and structure first** (high impact):
   - Every field has a visible `<label for>`; placeholder is only an example.
   - Radio/checkbox groups in `<fieldset><legend>`; the legend is the question.
   - Hints and format instructions are visible and referenced with `aria-describedby`.
   - Required fields: `required` attribute plus a visible marker explained once
     ("Fields marked * are required"); or mark the optional ones instead.
   - `aria-label` must start with the visible label text (voice control users say it).
4. **Autofill (1.3.5).** Add the token the script suggests for every field that collects
   the user's own data; never `autocomplete="off"` on those. Use `type="email"`, `tel`,
   `url` so phones show the right keyboard. Use `new-password` on sign-up and password
   change, `current-password` on login, `one-time-code` for SMS/email codes.
5. **Errors (3.3.1, 3.3.3).** Follow [references/form-patterns.md](references/form-patterns.md):
   - Validate on submit (not on every keystroke); keep the entered values.
   - Each message names the field and how to fix it: "Enter a date like 21/03/1990".
   - Message next to the field, linked with `aria-describedby`, field gets `aria-invalid="true"`.
   - On submit with errors: an error summary at the top with links to the fields,
     focused, plus the page title prefixed "Error: ".
6. **Authentication and multi-step (3.3.7, 3.3.8).** Allow paste and password managers,
   offer passkeys or email links instead of puzzles, show "Same as billing address",
   never ask again for information already given in the same process.
   Remove reset buttons (`form.reset_button`): one mis-click next to Submit wipes the form.
7. **Re-run** the script on both states and do a keyboard plus screen reader submit
   (`screen-reader-testing`): fill wrongly, submit, hear the errors, fix, submit.

## Output

```
Form check: checkout.html - 4 high, 4 medium, 3 low

HIGH  autocomplete="surname" (line 11) is not a token -> autocomplete="family-name"
HIGH  "shipping mobile street-address" (line 17): mobile only before tel/email
      -> autocomplete="shipping street-address"
HIGH  password field blocks paste (line 21) -> remove onpaste (3.3.8)
HIGH  coupon input has only a placeholder (line 22) -> <label for="coupon">Coupon code</label>
MED   first name has no autocomplete -> autocomplete="given-name"
MED   radios "speed" not in a fieldset -> <fieldset><legend>Delivery speed</legend>
MED   card number aria-invalid without message -> <p id="cc-error">Enter the 16 digits on the front of your card</p>
Corrected form markup: (attached, labels and ids unchanged where possible)
```
