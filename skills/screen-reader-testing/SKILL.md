---
name: screen-reader-testing
description: Plan and run manual screen reader tests with NVDA (Windows), VoiceOver (macOS and iOS) and TalkBack (Android) - setup, the essential keyboard and gesture commands, step-by-step test scripts for page structure, links, forms and errors, dialogs, menus, tabs, live regions and single-page app navigation, and how to write findings developers can reproduce. A script predicts what a screen reader exposes from the HTML (title, language, landmarks, heading outline, links, controls with name/role/state, images, live regions), flags unnamed controls, and generates a pre-filled Markdown test script with expected announcements per step. Use when the user asks how to test with a screen reader, wants an NVDA or VoiceOver test plan, says "what will a screen reader say", needs to verify ARIA fixes, or prepares assistive technology testing for an accessibility audit.
license: MIT
compatibility: Script needs Python 3.8+ (standard library). Manual testing needs NVDA on Windows, VoiceOver on macOS/iOS or TalkBack on Android.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Screen reader testing

Automated tools cannot tell you whether a page makes sense when heard. A focused 30-minute
session with one or two screen readers catches what audits miss. Prepare expectations
from the markup, test, and record reproducible findings.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "How do I test this with NVDA/VoiceOver?", "what will a screen reader announce here?"
- Verifying fixes from `aria-review`, `accessible-components`, `accessible-forms`
- The assistive-technology part of an audit or a release checklist

## When not to use

- Finding mechanical failures (alt, labels, ARIA typos): run `wcag-html-audit` and
  `aria-review` first; they are faster and exact
- Native mobile app testing in depth (this skill covers mobile web)
- You cannot run a screen reader yourself: you can still generate the plan with the script
  and hand it to a tester

## Workflow

1. **Pick the combinations** (most used pairs per the WebAIM screen reader surveys):
   NVDA + Chrome or Firefox (Windows), VoiceOver + Safari (macOS), VoiceOver + Safari (iOS),
   optionally JAWS + Chrome and TalkBack + Chrome (Android). One desktop and one mobile pair
   is the minimum for a release.
2. **Predict the announcements from the markup.**
   ```bash
   python3 scripts/sr_outline.py page.html                       # outline
   python3 scripts/sr_outline.py page.html --format markdown > sr-test-plan.md
   python3 scripts/sr_outline.py dist/ --json
   ```
   Exit 1 means basics are missing (unnamed controls or images, no title, lang or main):
   fix those first, they will dominate the session. The Markdown plan has one row per task
   with NVDA and VoiceOver keys and the expected result, plus a table of every control.
3. **Set up** using [references/nvda.md](references/nvda.md) and
   [references/voiceover.md](references/voiceover.md) (install, speech viewer / caption
   panel to read along, browse vs focus mode, rotor). Turn on speech viewer (NVDA) or the
   caption panel (VoiceOver) so you can copy exact announcements.
4. **Run the scenarios** in [references/test-scenarios.md](references/test-scenarios.md)
   that apply: structure, links, images, forms with errors, dialogs, menus/tabs/disclosures,
   live regions and status messages, SPA navigation, tables, media. Compare what you hear
   with the "Expected" column; anything different, missing, duplicated or confusing is a
   finding.
5. **Record findings** in [assets/test-report-template.md](assets/test-report-template.md):
   AT + browser + versions, steps, what was announced (quote it), what was expected,
   WCAG criterion, severity. Screen reader output differs between products; report
   behaviour that blocks or confuses users, not wording differences.
6. **Retest** after fixes with the same combination and steps.

## Output

```
Screen reader test: checkout (NVDA 2025.3 + Firefox, VoiceOver macOS 15 + Safari)
| Step | Expected | NVDA | VoiceOver | Result |
| Title on load | "Checkout - Example Shop" | ok | ok | pass |
| Landmarks | banner, navigation 'Primary', main, contentinfo | main missing | main missing | FAIL 1.3.1 |
| Coupon field | "Coupon code, edit text" | "edit text" | "edit text, blank" | FAIL 4.1.2 |
| Submit with errors | focus to summary, "There is a problem" read | nothing announced | nothing | FAIL 3.3.1 |
| Card added toast | "Card saved" announced politely | ok | not announced | FAIL 4.1.3 (Safari) |
Findings: 4 (2 high). Repro steps and fixes in the attached report.
```
