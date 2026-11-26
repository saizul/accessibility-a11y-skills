#!/usr/bin/env python3
"""Generate an accessibility statement (Markdown or HTML) and an issue list from a JSON config.

  make_statement.py --init > statement.json          write an example config to edit
  make_statement.py statement.json                    Markdown statement to stdout
  make_statement.py statement.json --format html --out accessibility.html
  make_statement.py statement.json --findings audit.json --issues-csv issues.csv

--findings reads JSON reports from the audit scripts in this repository
(html_audit.py, aria_lint.py, focus_audit.py, forms_check.py with --json) and turns
high/medium findings into "known limitations", grouped by rule, merged with the
config's own known_issues. Nothing is sent anywhere; files are written only with --out
and --issues-csv.

Exit codes: 0 = written, 1 = config has problems (listed on stderr), 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import sys
from pathlib import Path

EXAMPLE = {
    "organization": "Example Ltd",
    "site_name": "Example shop",
    "site_url": "https://www.example.com",
    "standard": "WCAG 2.2",
    "level": "AA",
    "conformance": "partial",
    "statement_date": "2026-11-01",
    "last_reviewed": "2026-11-01",
    "assessment": {
        "method": "self-evaluation",
        "details": "Automated checks, keyboard-only testing and screen reader testing with NVDA + Firefox "
        "and VoiceOver + Safari on the 12 most used page templates.",
    },
    "contact": {
        "email": "accessibility@example.com",
        "phone": "",
        "form_url": "https://www.example.com/accessibility-feedback",
        "response_days": 5,
    },
    "technologies": ["HTML", "CSS", "JavaScript", "WAI-ARIA"],
    "compatible_with": [
        "recent versions of Chrome, Firefox, Safari and Edge",
        "NVDA and JAWS on Windows, VoiceOver on macOS and iOS, TalkBack on Android",
    ],
    "known_issues": [
        {
            "title": "Product image carousel cannot be paused",
            "wcag": "2.2.2",
            "impact": "Moving content distracts some users and screen readers re-announce slides.",
            "workaround": "All product images are also listed on the product details tab.",
            "fix_by": "2027-01-31",
        }
    ],
    "exemptions": [
        {
            "title": "Archived PDF newsletters published before 2024",
            "reason": "Archived content not needed for current services; accessible versions on request.",
        }
    ],
    "enforcement": "",
}
CONFORMANCE = {
    "full": "fully conforms with {std} level {lvl}. Fully conforms means that the content fully conforms to the "
    "accessibility standard without any exceptions.",
    "partial": "partially conforms with {std} level {lvl}. Partially conforms means that some parts of the "
    "content do not fully conform to the accessibility standard.",
    "non": "does not conform with {std} level {lvl}. Non-conformance means that the content does not conform "
    "to the accessibility standard yet. We are working on it; see the known limitations below.",
}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}


def validate(cfg: dict) -> list[str]:
    problems = []
    for key in ("organization", "site_url", "standard", "level", "conformance", "statement_date"):
        if not cfg.get(key):
            problems.append(f"missing '{key}'")
    if cfg.get("conformance") and cfg["conformance"] not in CONFORMANCE:
        problems.append("conformance must be one of: full, partial, non")
    if cfg.get("level") and cfg["level"] not in ("A", "AA", "AAA"):
        problems.append("level must be A, AA or AAA")
    contact = cfg.get("contact") or {}
    if not any(contact.get(k) for k in ("email", "phone", "form_url")):
        problems.append("contact needs at least one of email, phone, form_url (users must be able to report problems)")
    if cfg.get("conformance") == "full" and cfg.get("known_issues"):
        problems.append("conformance is 'full' but known_issues is not empty: use 'partial'")
    if cfg.get("conformance") in ("partial", "non") and not cfg.get("known_issues"):
        problems.append("conformance is partial/non but no known_issues are listed")
    for i, issue in enumerate(cfg.get("known_issues") or []):
        if not issue.get("title"):
            problems.append(f"known_issues[{i}] needs a title")
    return problems


def issues_from_findings(reports: list[dict], min_severity: str = "medium") -> list[dict]:
    """Group findings from the audit scripts' --json output into known issues."""
    floor = SEVERITY_RANK[min_severity]
    grouped: dict = {}
    for rep in reports:
        for file_entry in rep.get("files", []):
            for f in file_entry.get("findings", []):
                if SEVERITY_RANK.get(f.get("severity"), 0) < floor:
                    continue
                g = grouped.setdefault(
                    f["rule"],
                    {
                        "title": f.get("message", f["rule"]),
                        "wcag": f.get("wcag", ""),
                        "severity": f.get("severity"),
                        "count": 0,
                        "pages": set(),
                        "fix": f.get("fix", ""),
                        "rule": f["rule"],
                    },
                )
                g["count"] += 1
                g["pages"].add(file_entry.get("file", ""))
                if SEVERITY_RANK[f["severity"]] > SEVERITY_RANK[g["severity"]]:
                    g["severity"] = f["severity"]
    out = []
    for g in sorted(grouped.values(), key=lambda x: (-SEVERITY_RANK[x["severity"]], -x["count"])):
        pages = sorted(p for p in g["pages"] if p)
        out.append(
            {
                "title": RULE_TITLES.get(g["rule"], g["title"]),
                "wcag": g["wcag"],
                "impact": f"{g['count']} occurrence(s) on {len(pages)} page(s)",
                "workaround": "",
                "fix_by": "",
                "severity": g["severity"],
                "rule": g["rule"],
                "pages": pages,
                "fix": g["fix"],
            }
        )
    return out


RULE_TITLES = {
    "img.alt_missing": "Some images have no text alternative",
    "img.alt_placeholder": "Some images have unhelpful text alternatives",
    "link.empty": "Some links have no accessible name",
    "button.empty": "Some buttons have no accessible name",
    "form.label_missing": "Some form fields have no label",
    "label.missing": "Some form fields have no label",
    "heading.skipped_level": "Heading levels are skipped on some pages",
    "html.lang_missing": "The page language is not set",
    "document.title_missing": "Some pages have no title",
    "id.duplicate": "Duplicate ids break some labels and descriptions",
    "tabindex.positive": "The keyboard focus order is changed on some pages",
    "iframe.title_missing": "Embedded frames have no title",
    "table.no_headers": "Some data tables have no header cells",
    "media.autoplay_sound": "Some media plays sound automatically",
    "media.no_captions": "Some videos have no captions",
    "aria_hidden.focusable": "Some hidden content can still receive keyboard focus",
    "click.not_keyboard_accessible": "Some controls only work with a mouse",
    "css.focus_outline_removed": "The keyboard focus indicator is not visible on some elements",
    "autocomplete.missing": "Personal-data fields cannot be filled automatically",
    "autocomplete.invalid": "Some autocomplete values are invalid",
    "group.no_fieldset": "Some radio button and checkbox groups have no group label",
    "meta.viewport_zoom_blocked": "Pinch zoom is disabled on mobile devices",
    "meta.refresh": "Some pages refresh or redirect automatically after a time limit",
    "input_image.alt_missing": "Some image buttons have no text alternative",
    "svg.name_missing": "Some graphics have no text alternative",
    "area.alt_missing": "Some image map areas have no text alternative",
    "heading.empty": "Some headings are empty",
    "label.for_missing_target": "Some labels are not connected to their fields",
    "element.moving_content": "Some moving content cannot be paused",
    "media.autoplay_no_controls": "Some auto-playing video cannot be paused",
    "role.invalid": "Some elements use invalid ARIA roles",
    "role.missing_required": "Some custom controls do not expose their state",
    "role.not_focusable": "Some custom controls cannot be reached with the keyboard",
    "aria.broken_reference": "Some ARIA references point at missing content",
    "link.fragment_target_missing": "Some in-page links (such as skip links) do not work",
    "bypass.no_skip_link": "There is no skip link to bypass repeated navigation",
    "error.not_associated": "Some error messages are not connected to their fields",
    "auth.paste_blocked": "Pasting into some login fields is blocked",
}


def sentence(text) -> str:
    """Capitalise the first letter and drop a trailing full stop (the template adds one)."""
    text = str(text or "").strip().rstrip(".")
    return text[:1].upper() + text[1:]


def esc(text) -> str:
    return html.escape(str(text or ""))


def render_markdown(cfg: dict, issues: list[dict]) -> str:
    std, lvl = cfg["standard"], cfg["level"]
    site = cfg.get("site_name") or cfg["site_url"]
    contact = cfg.get("contact") or {}
    lines = [
        f"# Accessibility statement for {site}",
        "",
        f"{cfg['organization']} is committed to making {site} ({cfg['site_url']}) accessible to as many people as "
        "possible, including people who use screen readers, magnifiers, voice control, keyboards or switches.",
        "",
        "## Conformance status",
        "",
        f"The [Web Content Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/standards-guidelines/wcag/) define "
        f"requirements to improve accessibility for people with disabilities. {site} "
        + CONFORMANCE[cfg["conformance"]].format(std=std, lvl=lvl),
        "",
    ]
    if issues:
        lines += ["## Known limitations", "", "We know about these problems and are working on them:", ""]
        for it in issues:
            ref = f" (WCAG {it['wcag']})" if it.get("wcag") else ""
            lines.append(f"- **{sentence(it['title'])}**{ref}.")
            for key, label in (("impact", "Impact"), ("workaround", "Workaround"), ("fix_by", "Planned fix")):
                if it.get(key):
                    lines.append(f"  {label}: {sentence(it[key])}.")
        lines.append("")
    if cfg.get("exemptions"):
        lines += ["## Content not within scope", ""]
        for ex in cfg["exemptions"]:
            lines.append(f"- **{ex.get('title', '')}**: {ex.get('reason', '')}")
        lines.append("")
    lines += ["## Feedback and contact", "", "If you find a barrier or need content in another format, tell us:", ""]
    if contact.get("email"):
        lines.append(f"- Email: [{contact['email']}](mailto:{contact['email']})")
    if contact.get("phone"):
        lines.append(f"- Phone: {contact['phone']}")
    if contact.get("form_url"):
        lines.append(f"- Feedback form: {contact['form_url']}")
    if contact.get("response_days"):
        lines.append(f"\nWe aim to respond within {contact['response_days']} working days.")
    lines.append("")
    if cfg.get("enforcement"):
        lines += ["## Enforcement procedure", "", cfg["enforcement"], ""]
    lines += ["## Technical information", ""]
    if cfg.get("technologies"):
        lines.append(f"Accessibility of {site} relies on: {', '.join(cfg['technologies'])}.")
    if cfg.get("compatible_with"):
        lines += ["", "It is designed to work with:", ""] + [f"- {c}" for c in cfg["compatible_with"]]
    assessment = cfg.get("assessment") or {}
    lines += ["", "## Assessment approach", ""]
    method = {
        "self-evaluation": "Self-evaluation by our own team",
        "external": "External evaluation by an independent auditor",
    }.get(assessment.get("method", ""), assessment.get("method", "Not stated"))
    lines.append(f"{method}." + (f" {assessment['details']}" if assessment.get("details") else ""))
    lines += ["", "## Date", ""]
    lines.append(f"This statement was prepared on {cfg['statement_date']}.")
    if cfg.get("last_reviewed"):
        lines.append(f"It was last reviewed on {cfg['last_reviewed']}.")
    return "\n".join(lines) + "\n"


def render_html(cfg: dict, issues: list[dict]) -> str:
    std, lvl = cfg["standard"], cfg["level"]
    site = cfg.get("site_name") or cfg["site_url"]
    contact = cfg.get("contact") or {}
    parts = [
        "<!DOCTYPE html>",
        '<html lang="' + esc(cfg.get("lang", "en")) + '">',
        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Accessibility statement - {esc(site)}</title></head>",
        '<body><main id="main">',
        f"<h1>Accessibility statement for {esc(site)}</h1>",
        f"<p>{esc(cfg['organization'])} is committed to making {esc(site)} "
        f'(<a href="{esc(cfg["site_url"])}">{esc(cfg["site_url"])}</a>) accessible to as many people as possible.</p>',
        "<h2>Conformance status</h2>",
        '<p>The <a href="https://www.w3.org/WAI/standards-guidelines/wcag/">Web Content Accessibility Guidelines '
        f"(WCAG)</a> define requirements to improve accessibility for people with disabilities. {esc(site)} "
        f"{esc(CONFORMANCE[cfg['conformance']].format(std=std, lvl=lvl))}</p>",
    ]
    if issues:
        parts += ["<h2>Known limitations</h2>", "<ul>"]
        for it in issues:
            ref = f" (WCAG {esc(it['wcag'])})" if it.get("wcag") else ""
            extra = "".join(
                f"<br>{label}: {esc(it[key])}"
                for key, label in (("impact", "Impact"), ("workaround", "Workaround"), ("fix_by", "Planned fix"))
                if it.get(key)
            )
            parts.append(f"<li><strong>{esc(sentence(it['title']))}</strong>{ref}.{extra}</li>")
        parts.append("</ul>")
    if cfg.get("exemptions"):
        parts += ["<h2>Content not within scope</h2>", "<ul>"]
        parts += [f"<li><strong>{esc(e.get('title'))}</strong>: {esc(e.get('reason'))}</li>" for e in cfg["exemptions"]]
        parts.append("</ul>")
    parts += [
        "<h2>Feedback and contact</h2>",
        "<p>If you find a barrier or need content in another format, tell us:</p>",
    ]
    parts.append("<ul>")
    if contact.get("email"):
        parts.append(f'<li>Email: <a href="mailto:{esc(contact["email"])}">{esc(contact["email"])}</a></li>')
    if contact.get("phone"):
        parts.append(f"<li>Phone: {esc(contact['phone'])}</li>")
    if contact.get("form_url"):
        parts.append(f'<li><a href="{esc(contact["form_url"])}">Accessibility feedback form</a></li>')
    parts.append("</ul>")
    if contact.get("response_days"):
        parts.append(f"<p>We aim to respond within {esc(contact['response_days'])} working days.</p>")
    if cfg.get("enforcement"):
        parts += ["<h2>Enforcement procedure</h2>", f"<p>{esc(cfg['enforcement'])}</p>"]
    parts.append("<h2>Technical information</h2>")
    if cfg.get("technologies"):
        parts.append(f"<p>Accessibility of {esc(site)} relies on: {esc(', '.join(cfg['technologies']))}.</p>")
    if cfg.get("compatible_with"):
        parts += ["<ul>"] + [f"<li>{esc(c)}</li>" for c in cfg["compatible_with"]] + ["</ul>"]
    assessment = cfg.get("assessment") or {}
    parts += [
        "<h2>Assessment approach</h2>",
        f"<p>{esc(assessment.get('method', 'Not stated'))}. {esc(assessment.get('details', ''))}</p>",
    ]
    parts += ["<h2>Date</h2>", f"<p>This statement was prepared on {esc(cfg['statement_date'])}."]
    if cfg.get("last_reviewed"):
        parts[-1] += f" It was last reviewed on {esc(cfg['last_reviewed'])}."
    parts[-1] += "</p>"
    parts += ["</main></body>", "</html>"]
    return "\n".join(parts) + "\n"


def issues_csv(issues: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["title", "wcag", "severity", "impact", "workaround", "fix_by", "rule", "pages", "suggested_fix", "status"]
    )
    for it in issues:
        w.writerow(
            [
                it.get("title", ""),
                it.get("wcag", ""),
                it.get("severity", ""),
                it.get("impact", ""),
                it.get("workaround", ""),
                it.get("fix_by", ""),
                it.get("rule", ""),
                " ".join(it.get("pages", [])),
                it.get("fix", ""),
                "open",
            ]
        )
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Generate an accessibility statement (Markdown/HTML) and an issue-tracker CSV from a JSON config.",
        epilog="Start with --init. Have the final statement reviewed by whoever owns legal compliance.",
    )
    p.add_argument("config", nargs="?", help="statement config JSON")
    p.add_argument("--init", action="store_true", help="print an example config and exit")
    p.add_argument("--format", choices=["markdown", "html"], default="markdown")
    p.add_argument("--out", help="write the statement to this file instead of stdout")
    p.add_argument("--findings", action="append", default=[], help="audit JSON report to import (repeatable)")
    p.add_argument("--min-severity", choices=["high", "medium", "low"], default="medium")
    p.add_argument("--issues-csv", help="also write known issues as CSV for an issue tracker")
    p.add_argument("--json", action="store_true", help="print the merged data as JSON instead of a statement")
    args = p.parse_args(argv)
    if args.init:
        print(json.dumps(EXAMPLE, indent=2))
        return 0
    if not args.config:
        p.error("give a config file (create one with --init)")
    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        reports = [json.loads(Path(f).read_text(encoding="utf-8")) for f in args.findings]
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    issues = list(cfg.get("known_issues") or [])
    imported = issues_from_findings(reports, args.min_severity)
    known_titles = {i.get("title") for i in issues}
    issues += [i for i in imported if i["title"] not in known_titles]
    if imported and cfg.get("conformance") == "full":
        cfg["conformance"] = "partial"
        print("note: imported findings exist, conformance changed from 'full' to 'partial'", file=sys.stderr)
    cfg["known_issues"] = issues
    problems = validate(cfg)
    if problems:
        for prob in problems:
            print(f"config problem: {prob}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(cfg, indent=2))
        return 0
    text = render_html(cfg, issues) if args.format == "html" else render_markdown(cfg, issues)
    try:
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            sys.stdout.write(text)
        if args.issues_csv:
            Path(args.issues_csv).write_text(issues_csv(issues), encoding="utf-8")
            print(f"wrote {args.issues_csv} ({len(issues)} issue(s))", file=sys.stderr)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
