# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-26

### Added

- `wcag-html-audit`: `html_audit.py` for lang, title, alt text (missing, placeholder, file
  names), image buttons, image maps, SVG names, empty and generic links, empty buttons,
  form labels, broken label targets, heading order, duplicate ids, positive tabindex,
  iframe titles, table headers, autoplay media, captions, marquee, zoom-blocking viewport,
  meta refresh and main landmark; a WCAG 2.2 A/AA checklist with all 55 criteria.
- `color-contrast-checker`: `contrast.py` with WCAG 2.2 ratios for pairs, pair files and
  CSS (custom properties, large text from font-size/weight, alpha compositing), AA/AAA and
  non-text thresholds, and nearest passing colour suggestions.
- `aria-review`: `aria_lint.py` for invalid, abstract and deprecated roles, unknown
  attributes, invalid values, broken references, aria-hidden on focusable content,
  redundant and overriding roles, required states and context, unfocusable widgets,
  missing names and unlabelled duplicate landmarks; ARIA rules reference.
- `keyboard-and-focus`: `focus_audit.py` for mouse-only handlers, tabindex problems,
  removed focus outlines in HTML and CSS, sticky headers, skip links and in-page targets,
  autofocus, small targets, dialogs to test, and predicted Tab order; keyboard checklist
  and focus patterns.
- `accessible-forms`: `forms_check.py` with an HTML autofill grammar validator and
  autocomplete suggestions, labels, label in name, fieldsets, error association, required
  state, paste blocking and CAPTCHA detection; token reference and form patterns.
- `accessible-components`: dialog, tabs, menu button and combobox examples that pass every
  audit script, plus disclosure, accordion and toggle patterns with test checklists.
- `screen-reader-testing`: `sr_outline.py` predicting landmarks, headings, links, controls
  with states, images and live regions, and generating Markdown NVDA/VoiceOver test plans;
  NVDA, VoiceOver and TalkBack references, scenarios and a report template.
- `accessibility-statement`: `make_statement.py` generating Markdown/HTML statements and a
  CSV backlog from a JSON config and audit reports; GitHub issue form, accessible feedback
  form and regional context notes.
- Claude Code plugin marketplace manifest, `tools/validate_skills.py`, CI and release workflows.

[Unreleased]: https://github.com/saizul/accessibility-a11y-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saizul/accessibility-a11y-skills/releases/tag/v0.1.0
