## What does this pull request do?

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Type

- [ ] New skill
- [ ] New check or option in an existing script
- [ ] Workflow / reference improvement
- [ ] Bug fix (false positive / missed finding / crash)
- [ ] Repository tooling (validator, CI)

## Checklist

- [ ] `python tools/validate_skills.py` passes
- [ ] `ruff check . && ruff format --check .` passes
- [ ] `pytest` passes; new behaviour has tests with fixtures in `tests/fixtures/`, including
      a "correct pattern is not flagged" case
- [ ] Scripts use only the Python standard library, support `--help`, have a `--json`
      option where output is structured, and exit non-zero on findings
- [ ] Scripts are read-only and make no network calls
- [ ] If the shared DOM helper block changed, it is identical in all scripts
- [ ] New checks cite a WCAG success criterion (or are marked as best practice)
- [ ] New skills: listed in `.claude-plugin/marketplace.json`, the README skills table,
      `AGENTS.md` and CHANGELOG.md
