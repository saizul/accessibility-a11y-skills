# Contributing to accessibility-a11y-skills

Thank you for helping! New checks, fewer false positives, new skills, fixture pages and
clearer docs are all welcome. Contributions from people who use assistive technology are
especially valuable: if a pattern here does not work with your setup, please tell us.

- [Ways to contribute](#ways-to-contribute)
- [Good first issues](#good-first-issues)
- [Development setup](#development-setup)
- [Repository layout](#repository-layout)
- [Write a new skill](#write-a-new-skill)
- [Quality bar](#quality-bar)
- [Pull request process](#pull-request-process)

## Ways to contribute

| Size | Idea |
| --- | --- |
| 10 minutes | Fix a typo, clarify a workflow step, add a screen reader command you rely on |
| 30 minutes | Add a fixture page that triggers a false positive or a missed finding |
| 1-2 hours | Add a check to an existing script (see below) |
| Half a day | Write a new skill from the template |

Comment on an issue before you start so nobody else picks the same one.

## Good first issues

Each of these is self-contained and touches one script and its test file.

1. **wcag-html-audit: `aria-describedby` on images.** Report `info` for `<img alt="">`
   that also has `aria-describedby` (decorative image with a description is contradictory).
2. **wcag-html-audit: redundant alt text.** Report `low` when an image inside a link has the
   same alt text as the link's visible text ("Home" image + "Home" text is read twice).
3. **wcag-html-audit: `--baseline` file.** Accept a JSON file of accepted findings
   (rule + file + line) and report only new ones, for gradual adoption in CI.
4. **color-contrast-checker: `--pairs` from CSV with headers.** Accept a CSV export from
   design tools (`foreground,background,name,size,weight`) and use size/weight per row.
5. **color-contrast-checker: dark mode blocks.** Extract pairs from
   `@media (prefers-color-scheme: dark)` separately and label them "dark".
6. **aria-review: `aria-controls` on hidden targets.** Report `info` when `aria-expanded="true"`
   but the element in `aria-controls` has the `hidden` attribute (state out of sync).
7. **keyboard-and-focus: `:focus-within` replacements.** Treat a `:focus-within` rule on
   the parent that adds an outline as a valid replacement for a removed outline.
8. **accessible-forms: `inputmode` hints.** Suggest `inputmode="numeric"` for one-time
   codes, card numbers and postcodes that use `type="number"` (which breaks leading zeros).
9. **accessible-forms: `section-*` consistency.** Warn when two address groups on one page
   use the same tokens without `section-*`, `shipping` or `billing`.
10. **screen-reader-testing: JAWS column.** Add JAWS commands to the generated Markdown
    plan behind a `--readers nvda,jaws,voiceover` option.
11. **accessibility-statement: translations.** Add a `language` option with German, French
    and Spanish statement text (native speakers please).
12. **New skill: `accessible-data-tables`** (see the roadmap in the README).

## Development setup

```bash
git clone https://github.com/saizul/accessibility-a11y-skills.git
cd accessibility-a11y-skills
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

python tools/validate_skills.py   # SKILL.md frontmatter, sections, links, marketplace listing
ruff check . && ruff format --check .
pytest
```

To try your changes in Claude Code, either copy a skill to `~/.claude/skills/` or add your
checkout as a local marketplace:

```bash
claude plugin marketplace add ./accessibility-a11y-skills
claude plugin install accessibility-a11y-skills@accessibility-a11y-skills
```

For Codex, copy the skill folder to `~/.agents/skills/`.

## Repository layout

```
.claude-plugin/
  marketplace.json      marketplace + plugin entry listing every skill
  plugin.json           plugin manifest (name, version, author)
skills/<name>/
  SKILL.md              frontmatter + workflow (the part agents read)
  scripts/*.py          standalone helpers, Python 3.8+ stdlib only
  references/*.md       detail loaded on demand
  assets/               files to copy (HTML examples, templates)
templates/skill/        copy this to start a new skill
tests/
  test_<skill>.py       one test module per skill
  test_shared_helpers.py  keeps the copied DOM helpers identical
  fixtures/html/        good and bad pages
  fixtures/css/         stylesheets and colour pair lists
  fixtures/statement/   statement config and an audit report
tools/validate_skills.py
```

## Write a new skill

1. Open a "New skill proposal" issue first so we can agree on scope.
2. Copy the template:
   ```bash
   cp -r templates/skill skills/my-a11y-skill
   mv skills/my-a11y-skill/scripts/your_script.py skills/my-a11y-skill/scripts/my_check.py
   ```
3. Edit `SKILL.md`:
   - `name` equals the folder name: lowercase letters, digits, single hyphens, max 64 chars.
   - `description` (max 1024 chars) says **what** it does with concrete keywords and **when**
     to use it, starting the second part with "Use when ...". This text decides whether
     the agent picks the skill, so list the phrases users actually type ("tab order",
     "screen reader says nothing").
   - Required sections: `## When to use`, `## When not to use`, `## Workflow`, `## Output`.
   - Workflow steps are imperative and numbered, with exact commands, decision points and
     the point where the agent must ask before changing anything.
   - Keep it under 400 lines; move tables, snippets and long checklists to `references/`.
4. Write the script: `argparse` with a useful `--help`, `--json` output, exit codes
   0 (ok) / 1 (findings) / 2 (error), read-only, no network. If it parses HTML, copy the
   shared DOM helper block from an existing script and add your script to
   `tests/test_shared_helpers.py`.
5. Add `tests/test_my_a11y_skill.py` with fixtures: a bad input, a good input with no
   findings, the "correct pattern is not flagged" cases, and the CLI exit codes.
6. Add the skill to `.claude-plugin/marketplace.json` (`plugins[0].skills`), the README
   skills table, the table in `AGENTS.md`, the bug report dropdown and `CHANGELOG.md`
   under "Unreleased".
7. Run the validator, ruff and pytest.

## Quality bar

- **Grounded in the standards.** Cite the WCAG 2.2 success criterion for every check and
  follow WAI-ARIA 1.2, HTML-AAM and the ARIA Authoring Practices. Link sources in references.
- **Native HTML first.** Fixes must not add ARIA where an HTML element does the job.
- **Low false positives.** A check that is often wrong frustrates developers into ignoring
  all findings. If a check is uncertain, make it `info` or `low`, add a "no false positive"
  test, and document the known false positives in the skill's references.
- **Honest scope.** Never present script output as proof of conformance.
- **Safety first.** A skill must not tell the agent to fetch sites, publish or commit
  without the user's confirmation.

## Pull request process

1. Fork, create a branch, make focused commits.
2. Make sure CI passes locally (validator, ruff, pytest).
3. Fill in the pull request template.
4. A maintainer reviews within a few days. Small, focused pull requests are merged fastest.

By contributing you agree that your contributions are licensed under the MIT License.
