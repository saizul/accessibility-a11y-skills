# accessibility-a11y-skills

[![CI](https://github.com/saizul/accessibility-a11y-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/saizul/accessibility-a11y-skills/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/saizul/accessibility-a11y-skills?sort=semver)](https://github.com/saizul/accessibility-a11y-skills/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/saizul/accessibility-a11y-skills?style=social)](https://github.com/saizul/accessibility-a11y-skills/stargazers)

**Agent Skills that help Claude Code and Codex make websites and web apps accessible (WCAG 2.2 AA) - with tested, offline scripts that check your HTML and CSS instead of guessing.**

Eight skills that cover an accessibility project end to end: audit the HTML, check colour
contrast, lint ARIA, fix keyboard and focus, build accessible forms and components, test
with screen readers, and publish an honest accessibility statement. Seven of them ship a
standard-library-only Python script; the components skill ships working examples that
pass all of those scripts.

- **Deterministic checks.** Scripts parse HTML with Python's `html.parser` and report rule
  id, WCAG success criterion, line, element and fix, as text or JSON, with CI exit codes.
- **WCAG 2.2.** Includes the new criteria: focus not obscured (2.4.11), target size (2.5.8),
  redundant entry (3.3.7), accessible authentication (3.3.8); 4.1.1 Parsing is gone.
- **Native HTML first.** Fixes prefer `<button>`, `<label>`, `<dialog>`, `<details>` over
  ARIA, following the five rules of ARIA and the WAI-ARIA Authoring Practices.
- **Honest about limits.** Every skill says what automation cannot find and walks through
  the manual keyboard, zoom and screen reader checks.
- **Tested.** 300+ tests with good and bad fixture pages, run on Python 3.11-3.13 in CI.

## Skills

| Skill | What it does | Try asking |
| --- | --- | --- |
| [wcag-html-audit](skills/wcag-html-audit/SKILL.md) | Audits HTML files/folders: alt text, empty links and buttons, labels, heading order, lang, title, duplicate ids, positive tabindex, iframe titles, table headers, autoplay, captions, zoom blocking; full WCAG 2.2 A/AA checklist for the manual part | "Audit our built site in dist/ for WCAG 2.2 AA" |
| [color-contrast-checker](skills/color-contrast-checker/SKILL.md) | Exact contrast ratios for pairs, pair lists or CSS (resolves `var(--token)`, large text from font-size/weight, alpha compositing); AA/AAA and 3:1 non-text; suggests the nearest passing colour | "Do our brand colours pass AA? Here is theme.css" |
| [aria-review](skills/aria-review/SKILL.md) | ARIA lint: invalid/abstract roles, misspelled attributes, invalid values, broken id references, aria-hidden on focusable content, redundant roles, missing states and parents, unfocusable widgets | "Review the ARIA in this dropdown component" |
| [keyboard-and-focus](skills/keyboard-and-focus/SKILL.md) | Finds mouse-only click handlers, removed focus outlines in HTML and CSS, skip link problems, positive tabindex, sticky headers hiding focus; predicted Tab order; manual walkthrough and focus patterns | "Users say they can't tab to our product cards" |
| [accessible-forms](skills/accessible-forms/SKILL.md) | Validates `autocomplete` tokens against the HTML grammar and suggests the right one, plus labels, label-in-name, fieldsets, error association, required state, paste blocking, reset buttons; error summary patterns | "Make our checkout form accessible" |
| [accessible-components](skills/accessible-components/SKILL.md) | Complete dialog, tabs, menu button and combobox examples (HTML/CSS/JS) plus disclosure and accordion, with keyboard tables, ARIA states, bugs and test checklists | "Build an accessible autocomplete for assigning users" |
| [screen-reader-testing](skills/screen-reader-testing/SKILL.md) | Predicts what NVDA/VoiceOver will announce (landmarks, headings, controls with name/role/state) and writes a pre-filled test plan; command references and scenarios | "Give me a VoiceOver test plan for this page" |
| [accessibility-statement](skills/accessibility-statement/SKILL.md) | Generates an accessibility statement (Markdown/HTML) from JSON, imports audit findings as known limitations, exports a CSV backlog; GitHub issue form and feedback form | "Write our accessibility statement from the audit results" |

## Install

### Claude Code: plugin marketplace (recommended)

```text
/plugin marketplace add saizul/accessibility-a11y-skills
/plugin install accessibility-a11y-skills@accessibility-a11y-skills
```

Or from your shell:

```bash
claude plugin marketplace add saizul/accessibility-a11y-skills
claude plugin install accessibility-a11y-skills@accessibility-a11y-skills
```

Plugin skills are namespaced, e.g. `/accessibility-a11y-skills:wcag-html-audit`. Claude
also picks them up automatically when your request matches a skill's description. Update
later with `/plugin marketplace update accessibility-a11y-skills`.

### Claude Code: copy the skills

```bash
git clone https://github.com/saizul/accessibility-a11y-skills.git
# all projects (personal skills)
mkdir -p ~/.claude/skills && cp -r accessibility-a11y-skills/skills/* ~/.claude/skills/
# or just one project
mkdir -p .claude/skills && cp -r accessibility-a11y-skills/skills/wcag-html-audit .claude/skills/
```

Each release also has one zip per skill and an all-skills zip under
[Releases](https://github.com/saizul/accessibility-a11y-skills/releases).

### Codex CLI

Codex reads skills from `~/.agents/skills` (all repositories) and `.agents/skills` in a
repository (from the current directory up to the repository root):

```bash
git clone https://github.com/saizul/accessibility-a11y-skills.git
mkdir -p ~/.agents/skills && cp -r accessibility-a11y-skills/skills/* ~/.agents/skills/
# or per repository
mkdir -p .agents/skills && cp -r accessibility-a11y-skills/skills/wcag-html-audit .agents/skills/
```

Codex also ships a `$skill-installer` skill that can install skills from a GitHub
repository; ask it to install from `saizul/accessibility-a11y-skills`. Skill locations and
the installer are described in the [Codex skills documentation](https://developers.openai.com/codex/skills);
check it if your Codex version behaves differently. [AGENTS.md](AGENTS.md) explains how
Codex and other agents should use these skills.

### Any other agent

The skills follow the open [Agent Skills format](https://agentskills.io/specification):
a folder with `SKILL.md` (YAML frontmatter + instructions), `scripts/`, `references/` and
`assets/`. Point your agent at the folder, or run the scripts yourself; every script has `--help`.

## Usage examples

```text
> Audit dist/ for accessibility before we launch.
  (Runs html_audit.py, aria_lint.py and focus_audit.py: 14 icon-only buttons without
   names in the shared header, a reset.css that removes all focus outlines, skipped
   heading levels in the blog template. Fixes the header component once, then lists the
   manual checks left: contrast, 320px reflow, a screen reader pass.)

> Our designer wants #9ca3af for helper text on white. OK?
  (contrast.py: 2.53:1, fails AA even for large text; suggests #6d7787, the same blue-grey
   darkened just enough to reach 4.5:1.)

> The checkout form: can you check autocomplete and errors?
  (forms_check.py flags autocomplete="surname" and "zip" as invalid, suggests
   family-name and postal-code, finds radios without a fieldset and an aria-invalid field
   with no message, and adds an error summary that receives focus on submit.)
```

Run the scripts directly too:

```bash
python3 skills/wcag-html-audit/scripts/html_audit.py dist/ --fail-on high
python3 skills/color-contrast-checker/scripts/contrast.py "#767676" "#ffffff"
python3 skills/color-contrast-checker/scripts/contrast.py --css src/theme.css --json
python3 skills/aria-review/scripts/aria_lint.py component.html
python3 skills/keyboard-and-focus/scripts/focus_audit.py page.html --css css/site.css --order
python3 skills/accessible-forms/scripts/forms_check.py signup.html
python3 skills/accessible-forms/scripts/forms_check.py --token "shipping postal-code"
python3 skills/screen-reader-testing/scripts/sr_outline.py page.html --format markdown > sr-plan.md
python3 skills/accessibility-statement/scripts/make_statement.py statement.json --findings audit.json
```

For single-page apps, save the rendered DOM (devtools > Elements > Copy outerHTML) and
audit that file: the scripts do not run JavaScript.

## How skills work

At startup the agent loads only each skill's `name` and `description` (about 100 tokens
each). When your request matches a description, it reads that skill's `SKILL.md`: the
workflow, decision points and output format. Longer material lives in `references/` and is
read only when a step needs it; `assets/` holds files to copy (component examples, issue
forms). Scripts run as normal commands, so their output is exact and repeatable.

```
skills/<skill-name>/
  SKILL.md          frontmatter (name, description) + workflow
  scripts/          standalone Python 3 helpers (stdlib only, --help, --json)
  references/       checklists, patterns, rule explanations
  assets/           files to copy (HTML examples, templates)
```

## FAQ

**Does this make my site WCAG compliant?**
No tool can. Automated checks find a minority of WCAG issues (often quoted as 30-40%).
These skills find the mechanical ones reliably and then guide the manual checks; real
conformance needs testing by people, ideally including disabled users.

**Do the scripts fetch my site or send data anywhere?**
No. They read local files (or stdin) and print results. No network calls, no telemetry.

**React, Vue, Angular, Svelte?**
Audit rendered HTML (SSR output, a static build, or the DOM saved from devtools). The
component patterns include notes for porting to frameworks.

**What about axe-core, Lighthouse, Pa11y?**
Use them too: they run in a real browser with CSS and JavaScript. These skills add
explanations, fixes in context, checks they do not cover (autocomplete grammar, statement
generation, screen reader plans) and a workflow that does not need a browser.

**Can I use the scripts in CI?**
Yes: every checker supports `--json`, `--fail-on` and exits 1 on findings.

**Are accessibility overlays a fix?**
No. Overlay widgets do not repair the underlying code and often interfere with assistive
technology. Fix the source.

## Roadmap

Ideas for new skills (great first contributions; see [CONTRIBUTING.md](CONTRIBUTING.md)):

- `accessible-data-tables` - complex headers, sortable and responsive tables, a checker for `headers`/`scope`
- `accessible-media` - captions (WebVTT linting), transcripts, audio description, accessible players
- `reflow-and-zoom` - 320px reflow, text spacing and 200% zoom checks with a CSS scanner
- `accessible-charts` - data visualisation alternatives, patterns and contrast for series
- `accessible-pdf-and-docs` - tagged PDFs and Word documents from the web workflow
- `mobile-app-accessibility` - iOS (UIAccessibility, SwiftUI) and Android (Compose) checks
- `motion-and-animation` - prefers-reduced-motion, flashing thresholds, carousels
- `a11y-ci-pipeline` - axe-core/Playwright setup combined with these scripts and a baseline file

## Contributing

Contributions are welcome: new checks, fewer false positives, new skills, fixture pages
from real projects (anonymised), and clearer docs. Read [CONTRIBUTING.md](CONTRIBUTING.md)
for the skill template, the quality bar and how to run the validator and tests:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python tools/validate_skills.py && ruff check . && ruff format --check . && pytest
```

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues
privately as described in [SECURITY.md](SECURITY.md).

WCAG and WAI-ARIA are W3C standards. This project is independent and not affiliated with
the W3C, NV Access, Apple or Google.

## License

[MIT](LICENSE) (c) Saizul Amin
