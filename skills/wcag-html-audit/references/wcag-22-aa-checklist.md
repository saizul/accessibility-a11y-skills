# WCAG 2.2 Level A and AA checklist

All 55 success criteria at levels A and AA (4.1.1 Parsing was removed in WCAG 2.2).
"Auto" = what the scripts in this repository detect; everything else needs a person.
Normative text: <https://www.w3.org/TR/WCAG22/>. Understanding docs:
<https://www.w3.org/WAI/WCAG22/Understanding/>.

## 1 Perceivable

| SC | Name | Lvl | How to check | Auto |
| --- | --- | --- | --- | --- |
| 1.1.1 | Non-text Content | A | Every meaningful image, icon, chart, CAPTCHA has a text alternative; decorative ones are hidden | partly (`html_audit.py`) |
| 1.2.1 | Audio-only and Video-only (Prerecorded) | A | Transcript for audio-only; transcript or audio track for silent video | no |
| 1.2.2 | Captions (Prerecorded) | A | Accurate, synchronised captions on videos with speech | track presence only |
| 1.2.3 | Audio Description or Media Alternative | A | Visual-only information described or in a transcript | no |
| 1.2.4 | Captions (Live) | AA | Live streams have captions | no |
| 1.2.5 | Audio Description (Prerecorded) | AA | Audio description for important visual content | no |
| 1.3.1 | Info and Relationships | A | Headings, lists, tables, labels, groups are in markup, not just styling | partly |
| 1.3.2 | Meaningful Sequence | A | DOM/reading order matches the visual meaning (check with CSS off or a screen reader) | no |
| 1.3.3 | Sensory Characteristics | A | Instructions do not rely only on shape, position, colour or sound ("click the green button") | no |
| 1.3.4 | Orientation | AA | Works in portrait and landscape | no |
| 1.3.5 | Identify Input Purpose | AA | Personal-data fields have correct `autocomplete` | yes (`forms_check.py`) |
| 1.4.1 | Use of Color | A | Colour is not the only cue (links in text, errors, charts, required fields) | no |
| 1.4.2 | Audio Control | A | Audio over 3 s can be paused/stopped or muted | autoplay only |
| 1.4.3 | Contrast (Minimum) | AA | Text 4.5:1, large text 3:1 | yes (`contrast.py`) |
| 1.4.4 | Resize Text | AA | 200% zoom without loss of content or function | zoom blocking only |
| 1.4.5 | Images of Text | AA | No text baked into images (logos excepted) | no |
| 1.4.10 | Reflow | AA | 320 CSS px wide (1280px at 400%) without horizontal scrolling | no |
| 1.4.11 | Non-text Contrast | AA | UI component boundaries, states, icons and focus indicators 3:1 | yes, given colours (`contrast.py --ui`) |
| 1.4.12 | Text Spacing | AA | Line height 1.5, paragraph 2x, letter 0.12em, word 0.16em without clipping | no |
| 1.4.13 | Content on Hover or Focus | AA | Tooltips/popovers dismissable (Esc), hoverable, persistent | hover-only handlers |

## 2 Operable

| SC | Name | Lvl | How to check | Auto |
| --- | --- | --- | --- | --- |
| 2.1.1 | Keyboard | A | Everything works with Tab, Shift+Tab, Enter, Space, arrows, Esc | partly (`focus_audit.py`) |
| 2.1.2 | No Keyboard Trap | A | Focus can always leave a component (dialogs, embeds, editors) | no |
| 2.1.4 | Character Key Shortcuts | A | Single-key shortcuts can be turned off or remapped, or only work on focus | accesskey hint |
| 2.2.1 | Timing Adjustable | A | Time limits can be turned off, adjusted or extended (20 s warning) | meta refresh |
| 2.2.2 | Pause, Stop, Hide | A | Carousels, animations, auto-updating content over 5 s can be paused | marquee, autoplay |
| 2.3.1 | Three Flashes or Below Threshold | A | Nothing flashes more than 3 times per second | no |
| 2.4.1 | Bypass Blocks | A | Skip link or landmarks/headings to bypass repeated blocks | yes (`focus_audit.py`) |
| 2.4.2 | Page Titled | A | Unique, descriptive `<title>`; SPA updates it on route change | static title only |
| 2.4.3 | Focus Order | A | Tab order follows meaning; dialogs get focus, return it on close | tabindex, autofocus |
| 2.4.4 | Link Purpose (In Context) | A | Link text (plus its sentence/list item) tells where it goes | empty/generic links |
| 2.4.5 | Multiple Ways | AA | Two ways to find pages (nav + search or sitemap) | no |
| 2.4.6 | Headings and Labels | AA | Headings and labels describe topic or purpose | empty headings |
| 2.4.7 | Focus Visible | AA | Keyboard focus is always visible | `outline:none` detection |
| 2.4.11 | Focus Not Obscured (Minimum) | AA | Focused item not fully hidden by sticky headers, cookie banners, chat widgets | sticky hint |
| 2.5.1 | Pointer Gestures | A | Multipoint or path gestures (pinch, swipe) have a single-pointer alternative | no |
| 2.5.2 | Pointer Cancellation | A | Actions fire on up-event or can be aborted | no |
| 2.5.3 | Label in Name | A | Accessible name contains the visible label text | yes (`forms_check.py`, inputs) |
| 2.5.4 | Motion Actuation | A | Shake/tilt features have a UI alternative and can be disabled | no |
| 2.5.7 | Dragging Movements | AA | Drag and drop has a single-pointer alternative (buttons, menus) | no |
| 2.5.8 | Target Size (Minimum) | AA | Targets at least 24x24 CSS px or spaced (inline text links excepted) | inline styles only |

## 3 Understandable

| SC | Name | Lvl | How to check | Auto |
| --- | --- | --- | --- | --- |
| 3.1.1 | Language of Page | A | `<html lang>` correct | yes |
| 3.1.2 | Language of Parts | AA | Passages in other languages have `lang` | validity only |
| 3.2.1 | On Focus | A | Focus alone does not submit, open windows or move focus | autofocus hint |
| 3.2.2 | On Input | A | Changing a field does not cause unexpected context change (auto-submit selects) | forms without submit |
| 3.2.3 | Consistent Navigation | AA | Repeated navigation in the same order across pages | no |
| 3.2.4 | Consistent Identification | AA | Same function, same name and icon across pages | no |
| 3.2.6 | Consistent Help | A | Help/contact links in the same relative place on every page | no |
| 3.3.1 | Error Identification | A | Errors are described in text and tied to the field | aria-invalid association |
| 3.3.2 | Labels or Instructions | A | Labels, formats, required fields are explained up front | labels, required |
| 3.3.3 | Error Suggestion | AA | Error text says how to fix it | no |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | AA | Review, confirm or undo for submissions with consequences | no |
| 3.3.7 | Redundant Entry | A | Do not ask for the same information twice in a process (offer "same as billing") | no |
| 3.3.8 | Accessible Authentication (Minimum) | AA | No cognitive test to log in unless there is an alternative; allow paste and password managers | paste blocking, CAPTCHA |

## 4 Robust

| SC | Name | Lvl | How to check | Auto |
| --- | --- | --- | --- | --- |
| 4.1.2 | Name, Role, Value | A | Custom controls expose name, role, state and update them | yes (`aria_lint.py`, `html_audit.py`) |
| 4.1.3 | Status Messages | AA | Status messages (saved, 3 results, errors) announced without focus change via `role=status`/`alert` | live region listing (`sr_outline.py`) |

## Minimum manual pass (30 minutes per template)

1. Keyboard only: Tab through everything, operate every control, open and close dialogs.
2. Zoom to 200% and set the window to 320px wide: nothing lost, no sideways scrolling.
3. Apply text spacing (bookmarklet or devtools CSS) and check for clipped text.
4. Check colour contrast of text, icons, borders, focus rings and states.
5. Screen reader: headings list, landmarks, a form submission with an error, one dialog.
6. Media: captions accurate, transcript present, nothing autoplays with sound.
7. Content: link text, headings and error messages make sense on their own.
