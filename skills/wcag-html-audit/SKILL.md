---
name: wcag-html-audit
description: Audit HTML pages and templates for WCAG 2.2 Level A/AA failures with a deterministic, offline script - missing or placeholder alt text, empty links and icon-only buttons, unlabelled form fields, skipped heading levels, missing lang and title, duplicate ids, positive tabindex, iframes without title, data tables without th, autoplaying audio/video, missing captions, zoom-blocking viewport, meta refresh, marquee. Reports rule id, WCAG success criterion, line and fix, as text or JSON with CI exit codes, then guides the manual checks a script cannot do. Use when the user asks for an accessibility audit, a11y review, WCAG or ADA/EAA compliance check of HTML, a template, a static site build or saved page source, or wants an accessibility gate in CI.
license: MIT
compatibility: Python 3.8+ standard library only. Works offline on HTML files; never fetches URLs.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# WCAG HTML audit

Find the mechanical WCAG 2.2 A/AA failures in HTML source quickly and reliably, then
direct the human (or browser) checks that decide real conformance. Read-only: the script
never changes files and never fetches pages.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "Audit this page for accessibility", "is this WCAG 2.2 AA compliant?", "a11y review"
- HTML files, templates (Blade, Jinja, Twig, JSX output), a static site `dist/` or `_site/`
- Before a launch, after a redesign, or as a CI gate on built HTML
- Preparing input for an accessibility statement (`accessibility-statement` skill)

## When not to use

- Colour contrast: `color-contrast-checker` (this script cannot see CSS colours)
- ARIA widget semantics in depth: `aria-review`; keyboard traps and focus styles: `keyboard-and-focus`
- Form autocomplete and error handling in depth: `accessible-forms`
- PDFs, native mobile apps, Word documents: different standards and tools
- A legal opinion on compliance: the output supports one, it is not one

## Workflow

1. **Get the HTML that users actually receive.**
   - Static or server-rendered: the built files (`dist/`, `public/`, `_site/`) or the source templates.
   - Single-page apps (React, Vue, Angular): the script cannot run JavaScript. Ask the user to
     save the rendered DOM: browser devtools > Elements > right-click `<html>` > Copy > Copy
     outerHTML, into `page.html`. Or build with SSR/prerendering and audit that.
   - Never fetch the live site yourself unless the user asks; prefer files they provide.
2. **Run the audit.**
   ```bash
   python3 scripts/html_audit.py page.html
   python3 scripts/html_audit.py dist/ --json > a11y-report.json
   python3 scripts/html_audit.py dist/ --fail-on high          # CI: fail only on high
   python3 scripts/html_audit.py page.html --ignore link.new_window
   cat page.html | python3 scripts/html_audit.py -
   ```
   Exit 0 = nothing at or above `--fail-on` (default `medium`), 1 = findings, 2 = bad input.
   Each finding has `rule`, `severity`, `wcag`, `line`, `element`, `message`, `fix`.
   Rule meanings and known false positives: [references/rules.md](references/rules.md).
3. **Triage.** Fix in this order:
   1. `high`: blocks a user outright (no alt, unnamed links/buttons/fields, no lang, zoom
      blocked, sound autoplay, iframes without title, tables without headers).
   2. `medium`: degrades navigation or comprehension (skipped headings, duplicate ids,
      positive tabindex, placeholder alt, missing captions).
   3. `low`/`info`: best practice; mention but do not block a release on them.
   Group repeated findings by template or component: one fix in a shared header often
   clears 40 findings across pages.
4. **Write fixes that keep the design.** For each high/medium finding, give the corrected
   markup. Rules of thumb:
   - Alt text describes purpose, not appearance; decorative images get `alt=""`. Ask the
     user for content you cannot know (what a chart shows) instead of inventing it.
   - Icon-only buttons and links: visible text is best; otherwise `aria-label` or a
     visually hidden `<span class="visually-hidden">`.
   - Prefer native elements (`<button>`, `<a href>`, `<label>`, `<th scope>`) over ARIA.
   - Fix heading levels in markup and keep the look with CSS classes.
   Show the diff and wait for confirmation before editing project files.
5. **Do the checks the script cannot.** Walk the page with the
   [WCAG 2.2 AA checklist](references/wcag-22-aa-checklist.md), at minimum:
   keyboard-only pass (`keyboard-and-focus`), contrast (`color-contrast-checker`), 200%
   zoom and 320px reflow, text spacing, captions/transcripts content, error messages, and a
   short screen reader pass (`screen-reader-testing`).
6. **Re-run** the script on the fixed files and report before/after counts.

## Output

```
WCAG 2.2 AA audit: checkout.html - 6 high, 3 medium, 2 low

HIGH  img.alt_missing (1.1.1) line 42 <img src="/badges/secure.png">
      -> alt="Secure checkout: 256-bit SSL" (or alt="" if purely decorative)
HIGH  button.empty (4.1.2) line 57 button.icon-close -> <button aria-label="Close cart">
HIGH  form.label_missing (1.3.1, 4.1.2) line 80 input[name=coupon] (placeholder only)
      -> <label for="coupon">Coupon code</label>
MED   heading.skipped_level (1.3.1) line 33 h2 -> h4: use h3, keep .small-heading class
...
Not checked by the script (manual, see checklist): contrast, keyboard traps, focus
visibility, reflow at 320px, error messages, live regions, media content.
Next: apply the 9 fixes above (diff attached), then run keyboard and contrast checks.
```

Always state that automated checks find only part of WCAG issues (commonly cited as
30-40%), so "no findings" is not "conformant".
