# VoiceOver (macOS, iOS) and TalkBack (Android)

Apple VoiceOver guide: <https://support.apple.com/guide/voiceover/welcome/mac>.
TalkBack: <https://support.google.com/accessibility/android/answer/6283677>.

## VoiceOver on macOS

Setup:

1. Turn on: Cmd+F5 (or hold Cmd and press Touch ID three times). `VO` = Control+Option
   (or Caps Lock if set as the VoiceOver modifier).
2. Use **Safari** (the best supported pairing).
3. Safari > Settings > Advanced: "Press Tab to highlight each item on a webpage".
4. VoiceOver Utility > Visuals > Caption panel shows what is spoken.

| Task | Keys |
| --- | --- |
| Stop speech | Control |
| Read from here | VO+A |
| Next / previous item | VO+Right / VO+Left |
| Rotor (headings, links, landmarks, form controls, tables) | VO+U, then Left/Right to switch lists, type to filter |
| Next heading | VO+Cmd+H (Shift for previous) |
| Next link / form control / table / graphic | VO+Cmd+L / VO+Cmd+J / VO+Cmd+T / VO+Cmd+G |
| Window title | VO+F2 twice |
| Activate | VO+Space |
| Interact with a group / stop | VO+Shift+Down / VO+Shift+Up |
| Tab through focusable items | Tab / Shift+Tab |
| Quick Nav (arrows only; then H, L, J with single-key on) | Left+Right arrows together |

## VoiceOver on iOS (Safari)

- Turn on: Settings > Accessibility > VoiceOver, or triple-click the side button after
  setting the Accessibility Shortcut.
- Swipe right / left: next / previous item. Double-tap: activate. Two-finger swipe up: read all.
- Rotor: rotate two fingers on the screen; choose Headings, Links, Form Controls, Landmarks;
  then swipe down/up to move by that type.
- Two-finger double tap: magic tap; three-finger swipe: scroll.
- Check: touch targets reachable by swiping in a logical order, dialogs keep focus inside,
  custom widgets operable with double-tap, no content hidden off-screen but still read.

## TalkBack on Android (Chrome)

- Turn on: Settings > Accessibility > TalkBack (or hold both volume keys if enabled).
- Swipe right / left: next / previous. Double-tap: activate. Swipe up then down / reading
  controls (TalkBack menu: swipe down then right, or three-finger tap) to choose headings,
  links, controls.
- Explore by touch: drag a finger to hear what is under it.

## Notes for testers

- VoiceOver reads "name, value, role/state" (e.g. "Email address, edit text, required,
  invalid data"). Wording differs from NVDA; compare meaning, not words.
- Safari exposes `aria-describedby` after a pause; check that hints are read.
- `role="status"` and `aria-live` updates may be skipped if the region is created at the
  same time as the text: create it at page load.
- Record macOS/iOS and Safari versions in reports.
