---
name: accessibility-statement
description: Write an honest accessibility statement and set up an accessibility issue process. A script generates the statement (Markdown or accessible HTML) from a JSON config - conformance status against WCAG 2.2 AA (full, partial, non), known limitations with WCAG references, workarounds and fix dates, content out of scope, feedback contact and response time, enforcement procedure, compatible browsers and assistive technology, assessment method and dates - and can import findings from this repository's audit scripts as known limitations and export them as a CSV backlog. Ships a GitHub issue form for accessibility barriers and an accessible feedback form. Covers what EU (Web Accessibility Directive, European Accessibility Act), UK and US contexts typically expect, without giving legal advice. Use when the user needs an accessibility statement, accessibility page, conformance statement, VPAT-style summary for a website, an accessibility feedback form or an a11y issue template.
license: MIT
compatibility: Python 3.8+ standard library only. Offline; writes files only with --out and --issues-csv.
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Accessibility statement

A statement tells users how accessible the site is, what does not work yet, and how to
get help. Honest "partially conforms" with a real contact beats a claim of full
compliance. The statement is generated from data so it stays current after each audit.

Paths below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

## When to use

- "Write an accessibility statement / accessibility page for our site"
- After an audit, to publish known limitations and a fix plan
- Setting up how users report barriers (feedback form, issue template, response time)
- An organisation preparing for EU Web Accessibility Directive or European Accessibility
  Act requirements, UK public sector regulations, or US procurement questions

## When not to use

- A formal VPAT / ACR for procurement: use the ITI VPAT template; this statement can feed it
- Legal advice on whether the organisation must comply, or exemptions: refer to counsel
- Running the audit itself: `wcag-html-audit`, `color-contrast-checker`, `aria-review`,
  `keyboard-and-focus`, `accessible-forms`, `screen-reader-testing`

## Workflow

1. **Gather facts** from the user (do not invent them): organisation and site, standard
   and level (default WCAG 2.2 AA), audit method (self-evaluation or external), dates,
   contact channels and response time, known problems with planned fix dates, content out
   of scope, and which regime applies (EU member state, UK public sector, none).
   Context per region: [references/legal-context.md](references/legal-context.md).
2. **Create the config.**
   ```bash
   python3 scripts/make_statement.py --init > statement.json   # same as assets/statement-config.example.json
   ```
   Edit it with the user's facts. `conformance` is `full` only when there are no known
   failures at the chosen level after a full audit (automated plus manual).
3. **Import audit findings (optional).**
   ```bash
   python3 ../wcag-html-audit/scripts/html_audit.py dist/ --json > audit.json
   python3 ../aria-review/scripts/aria_lint.py dist/ --json > aria.json
   python3 scripts/make_statement.py statement.json --findings audit.json --findings aria.json \
     --issues-csv a11y-backlog.csv
   ```
   High/medium findings become plain-language known limitations grouped by rule (with
   counts); `--min-severity high` keeps only blockers. Imported findings switch `full` to
   `partial`. Rewrite imported titles if the user's audience needs more context, and add
   workarounds.
4. **Generate the statement.**
   ```bash
   python3 scripts/make_statement.py statement.json                         # Markdown to stdout
   python3 scripts/make_statement.py statement.json --format html --out public/accessibility.html
   ```
   Exit 1 lists config problems (missing contact, "full" with known issues, partial with
   none listed). The HTML output itself passes `wcag-html-audit`.
5. **Set up feedback and tracking.**
   - Website: adapt [assets/feedback-form.html](assets/feedback-form.html) (labels,
     fieldset, autocomplete, optional fields) and link it from the statement and footer.
   - Repository: copy [assets/accessibility-issue.yml](assets/accessibility-issue.yml) to
     `.github/ISSUE_TEMPLATE/`. Import `a11y-backlog.csv` into the tracker.
6. **Review and publish.** Ask the user to have the owner of legal compliance review the
   text, publish it at a stable URL (`/accessibility`), link it from every page footer,
   and set a review date (at least yearly and after major changes). Do not publish or
   commit for the user without confirmation.

## Output

The statement (Markdown or HTML), the backlog CSV when requested, and a short summary:

```
Accessibility statement for Example shop: partial conformance with WCAG 2.2 AA
Known limitations: 9 (6 from audit.json, 3 from the config), 2 with planned fix dates
Missing before publishing: enforcement procedure text for your member state,
  workaround for "Some videos have no captions", review by legal/compliance owner
Files: public/accessibility.html, a11y-backlog.csv
```
