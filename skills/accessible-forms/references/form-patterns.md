# Accessible form patterns

## Field with label, hint and error

```html
<div class="field">
  <label for="email">Email address</label>
  <p id="email-hint" class="hint">We only use it to send your receipt.</p>
  <p id="email-error" class="error" hidden>
    <span class="visually-hidden">Error:</span> Enter an email address like name@example.com
  </p>
  <input id="email" name="email" type="email" autocomplete="email" spellcheck="false"
         required aria-describedby="email-hint">
</div>
```

On error (from JS or server render):

```js
function showError(input, message) {
  const err = document.getElementById(`${input.id}-error`);
  err.lastChild.textContent = " " + message;
  err.hidden = false;
  input.setAttribute("aria-invalid", "true");
  input.setAttribute("aria-describedby", `${err.id} ${input.id}-hint`);
}
function clearError(input) {
  document.getElementById(`${input.id}-error`).hidden = true;
  input.removeAttribute("aria-invalid");
  input.setAttribute("aria-describedby", `${input.id}-hint`);
}
```

- Error text says what is wrong and how to fix it; no "Invalid input".
- Do not rely on red colour or an icon only (1.4.1): use the word "Error" and text.
- Put the error above the input (or between label and input) so screen magnifier users see it.

## Error summary on submit

```html
<div id="error-summary" class="error-summary" role="alert" tabindex="-1" hidden>
  <h2>There is a problem</h2>
  <ul>
    <li><a href="#email">Enter an email address like name@example.com</a></li>
    <li><a href="#card-number">Enter the 16 digits on the front of your card</a></li>
  </ul>
</div>
```

```js
form.addEventListener("submit", (e) => {
  const errors = validate(form);           // [{id, message}]
  if (!errors.length) return;
  e.preventDefault();
  renderSummary(errors);
  summary.hidden = false;
  summary.focus();                          // also announced via role=alert
  document.title = "Error: " + baseTitle;
});
```

Use either the focus move or `role="alert"`; both together may announce twice on some
screen readers. Moving focus is the most robust choice; drop `role="alert"` if you do.

## Required and optional

```html
<p>Fields marked <span aria-hidden="true">*</span><span class="visually-hidden">with an asterisk</span> are required.</p>
<label for="name">Full name <span aria-hidden="true">*</span></label>
<input id="name" name="name" autocomplete="name" required>
```

`required` gives the "required" announcement and native validation; use `novalidate` on
the form if you render your own messages (keep `required` for the semantics).

## Groups

```html
<fieldset>
  <legend>How should we contact you?</legend>
  <div><input type="radio" id="c-email" name="contact" value="email"><label for="c-email">Email</label></div>
  <div><input type="radio" id="c-phone" name="contact" value="phone"><label for="c-phone">Phone</label></div>
</fieldset>

<fieldset>
  <legend>Date of birth</legend>
  <label for="bd-d">Day</label>   <input id="bd-d" name="bday-day" inputmode="numeric" autocomplete="bday-day" size="2">
  <label for="bd-m">Month</label> <input id="bd-m" name="bday-month" inputmode="numeric" autocomplete="bday-month" size="2">
  <label for="bd-y">Year</label>  <input id="bd-y" name="bday-year" inputmode="numeric" autocomplete="bday-year" size="4">
</fieldset>
```

## Validation timing

- Validate on submit. Inline validation on blur is fine for format errors once the user
  has left the field; never on every keystroke, never before the user typed.
- Do not disable the submit button until the form is valid: users cannot discover why.
- Keep all entered data after an error (including passwords where security allows).
- Time limits on forms: warn and allow extending (2.2.1).

## Redundant entry (3.3.7)

- Offer "Billing address is the same as delivery address" (checked by default where sensible).
- Pre-fill data the user gave earlier in the same flow; allow selecting it.
- Exceptions: re-entering for security (password confirmation) or when the earlier data is no longer valid.

## Accessible authentication (3.3.8)

Not allowed as the only way to log in: remembering or transcribing a code without paste,
solving puzzles, identifying images the user did not provide. Allowed / good:

- Password field that accepts paste and password managers (`autocomplete="current-password"`)
- Passkeys / WebAuthn (`autocomplete="username webauthn"`)
- Email magic links, OAuth sign-in
- One-time codes with `autocomplete="one-time-code"` and paste allowed (do not split the
  code into 6 inputs that block paste; if split, support pasting the whole code)
- CAPTCHA only with an alternative (object recognition is allowed at AA, but offer audio
  and a non-CAPTCHA route where possible)

## Things to avoid

| Pattern | Why |
| --- | --- |
| Placeholder as label | disappears on typing, low contrast, not reliably announced |
| Floating labels that start inside the field | OK only if the label element stays programmatically associated and visible |
| `<select onchange="submit()">` | unexpected context change (3.2.2) |
| Custom checkboxes with `display:none` on the input | keyboard and screen reader cannot use them; hide visually with opacity instead |
| `autocomplete="off"` on login forms | breaks password managers; 3.3.8 and usability |
| Error messages in a toast that disappears | not perceivable or persistent |
