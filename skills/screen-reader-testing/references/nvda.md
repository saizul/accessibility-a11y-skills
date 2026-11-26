# NVDA (Windows)

Free, open source: <https://www.nvaccess.org/download/>. User guide:
<https://www.nvaccess.org/files/nvda/documentation/userGuide.html>.

## Setup

1. Install NVDA (or run the portable copy). Choose the keyboard layout: **Desktop** uses
   Insert as the NVDA key; **Laptop** uses Caps Lock. Below, `NVDA` = that key.
2. Tools > **Speech viewer**: shows everything spoken, so you can copy exact announcements.
3. Optional: lower speech rate while learning (NVDA+Ctrl+Down to adjust in the synth ring).
4. Use Chrome or Firefox (both well supported); test the browser your users use most.

## Modes

- **Browse mode**: arrow keys read the page; single letters jump (H headings, K links...).
- **Focus mode**: keys go to the control (typing in fields, widgets with arrow keys).
  NVDA switches automatically when you Tab or press Enter on a field; a sound plays.
  `NVDA+Space` toggles manually. Custom widgets with `role="application"` force focus mode.

## Essential commands

| Task | Keys |
| --- | --- |
| Stop speech | Ctrl |
| Read from here / say all | NVDA+Down Arrow |
| Next / previous line | Down / Up |
| Window title (page title) | NVDA+T |
| Elements list (headings, links, landmarks, form fields, buttons) | NVDA+F7 |
| Next heading / heading level 1-6 | H / 1-6 (Shift = previous) |
| Next landmark | D |
| Next link / unvisited link | K / U |
| Next form field / button / edit field | F / B / E |
| Next table / move by cell | T / Ctrl+Alt+arrows |
| Next list / list item | L / I |
| Next graphic | G |
| Toggle browse / focus mode | NVDA+Space |
| Read current focus | NVDA+Tab |
| Activate | Enter (Space for buttons/checkboxes) |
| Next / previous focusable | Tab / Shift+Tab |
| Read current line / character | NVDA+Up / arrow left-right |

## Notes for testers

- Announcements read roughly as "name, role, state, value, description", e.g.
  "Email address, edit, required, invalid entry, Enter an email address like ...".
- NVDA reads `aria-describedby` after the name and role; long descriptions are noisy.
- Live regions: `role="status"`/`aria-live="polite"` are spoken after the current speech;
  `role="alert"` interrupts.
- Check both browse mode (arrowing) and Tab navigation: content reachable only by one
  of them is a finding.
- Record the version (NVDA menu > Help > About) and the browser version in reports.
