# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## What counts as a vulnerability

These skills are run by AI agents on real projects, so unsafe behaviour or guidance is
treated like a code vulnerability:

- A script that makes network calls, writes outside the paths it was given, or executes
  content from the files it reads (crafted HTML, CSS or JSON that runs code)
- A generated statement or HTML output that allows script injection from config values
  (all values must be escaped)
- A `SKILL.md` workflow that tells the agent to fetch or crawl sites, publish, commit or
  change files without asking the user first
- Guidance that is wrong in a way that harms users, e.g. a component pattern that traps
  keyboard focus or hides content from screen readers while presenting it as accessible

A check that misses an accessibility problem (false negative) or flags correct code (false
positive) is a normal bug: please open an issue.

## Reporting

Please **do not** open a public issue. Use
[GitHub private vulnerability reporting](https://github.com/saizul/accessibility-a11y-skills/security/advisories/new)
with the affected skill, version, impact and steps to reproduce. Remove private URLs and
personal data from examples.

You will get an answer within 5 working days. Fixes are released as soon as possible and
credited in the changelog unless you prefer otherwise.
