# AGENTS.md

Guidance for Codex CLI and other coding agents that use or work on this repository.

## Using the skills

The skills live in `skills/<name>/SKILL.md` and follow the Agent Skills format. Codex
discovers them when they are copied to `~/.agents/skills/` or `.agents/skills/` (see
README "Install"). If you are reading this file inside the repository instead:

1. Pick the skill whose `description` matches the user's request:

   | Request is about | Skill |
   | --- | --- |
   | accessibility / WCAG / ADA / EAA audit of HTML, templates or a built site | `wcag-html-audit` |
   | colour contrast, palettes, design tokens, dark mode, focus ring colours | `color-contrast-checker` |
   | ARIA roles and attributes, screen reader announcements of custom widgets | `aria-review` |
   | keyboard navigation, tab order, focus outline, skip links, focus traps | `keyboard-and-focus` |
   | form labels, errors, validation, autocomplete, login and checkout forms | `accessible-forms` |
   | building a modal, tabs, dropdown menu, autocomplete/combobox, accordion | `accessible-components` |
   | NVDA, VoiceOver, TalkBack test plans and what a screen reader will say | `screen-reader-testing` |
   | accessibility statement, feedback form, a11y issue template, backlog | `accessibility-statement` |

2. Read that `SKILL.md` completely and follow its Workflow section in order.
3. Paths such as `scripts/x.py`, `references/y.md` and `assets/z.html` are relative to the
   skill folder. `${CLAUDE_SKILL_DIR}` in the text means that folder; Codex does not expand it.
4. Read files in `references/` only when a workflow step points to them.

## Rules (apply to every skill)

- The scripts are read-only and work on local files; they never fetch URLs. Do not crawl
  or fetch the user's live site unless they ask; prefer files they provide.
- Show proposed code changes as a diff and wait for confirmation before editing the
  user's files, publishing a statement or committing.
- Prefer native HTML over ARIA in every fix. Never recommend accessibility overlays.
- Do not invent content you cannot know (what an image or chart shows, legal facts,
  audit dates); ask the user.
- Always say that automated checks cover only part of WCAG and list the manual checks
  still needed. Do not claim a site "is compliant" based on script output.
- Accessibility statements are not legal advice: recommend review by the person who owns
  compliance.

## Working on this repository

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python tools/validate_skills.py   # frontmatter, sections, links, assets, marketplace listing
ruff check . && ruff format --check .
pytest
```

- Scripts: Python 3.8+ standard library only, `#!/usr/bin/env python3`, `argparse` with
  `--help`, `--json` where output is structured, exit 0/1/2 (ok / findings / error).
- Scripts must stay standalone (one file each) so a skill folder can be copied on its own.
  The HTML scripts share a block between `# --- begin shared dom helpers` and
  `# --- end shared dom helpers ---`; when you change it, copy it to all five scripts
  (`tests/test_shared_helpers.py` fails if the copies differ).
- Every script needs tests in `tests/test_<skill_with_underscores>.py`. HTML fixtures are
  in `tests/fixtures/html/`, CSS in `tests/fixtures/css/`. Add a fixture for every new check,
  and a "no false positive" case for the correct pattern.
- The component examples in `skills/accessible-components/assets/` must stay clean under
  every audit script (enforced by tests).
- Keep each `SKILL.md` under 400 lines; move detail to `references/`.
- A new skill must be added to `.claude-plugin/marketplace.json` (`plugins[0].skills`), the
  README table, the table above and `CHANGELOG.md`. The validator enforces the manifest.
