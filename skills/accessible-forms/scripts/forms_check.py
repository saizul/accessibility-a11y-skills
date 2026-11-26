#!/usr/bin/env python3
"""Check HTML forms for accessibility problems (static, offline, read-only).

Checks: autocomplete values against the HTML autofill grammar (section-*, shipping/billing,
home/work/mobile, field name, webauthn); personal-data fields without autocomplete
(WCAG 1.3.5) with the token to use; autocomplete=off on personal data; input type that
does not match the token; missing labels and placeholder-as-label; aria-label that does
not contain the visible label (2.5.3); radio/checkbox groups without fieldset/legend;
aria-invalid without an associated error message; required shown only visually; paste
blocking on inputs (3.3.8); CAPTCHAs; forms without a submit button.

Exit codes: 0 = ok, 1 = findings at or above --fail-on (or an invalid --token), 2 = error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# --- begin shared dom helpers (keep identical in every script; tests check this) ---
VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
AUTO_CLOSE = {
    "li": {"li"},
    "option": {"option"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
    "tr": {"tr", "td", "th"},
    "td": {"td", "th"},
    "th": {"td", "th"},
    "p": {"p"},
}
SKIP_TEXT = {"script", "style", "template", "noscript"}


class Node:
    """A tiny element tree node; text children are plain strings."""

    def __init__(self, tag: str, attrs: dict, parent: Node | None, line: int):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.line = line
        self.children: list = []

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def has(self, name: str) -> bool:
        return name in self.attrs

    def iter(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.iter()

    def ancestors(self):
        node = self.parent
        while node is not None and node.tag != "#root":
            yield node
            node = node.parent

    def describe(self) -> str:
        bits = [self.tag]
        if self.get("id"):
            bits.append(f"#{self.get('id')}")
        cls = (self.get("class") or "").split()
        if cls:
            bits.append("." + ".".join(cls[:2]))
        return "".join(bits)


class TreeBuilder(HTMLParser):
    """Build a forgiving element tree from HTML with line numbers."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None, 0)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in AUTO_CLOSE and self.cur.tag in AUTO_CLOSE[tag]:
            self.cur = self.cur.parent or self.root
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur, self.getpos()[0])
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur, self.getpos()[0])
        self.cur.children.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        node = self.cur
        while node is not None and node.tag != "#root":
            if node.tag == tag:
                self.cur = node.parent or self.root
                return
            node = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(text: str) -> Node:
    builder = TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


def is_hidden(node: Node) -> bool:
    """True when the node or an ancestor is hidden from assistive technology."""
    for n in [node, *node.ancestors()]:
        if n.get("aria-hidden", "").strip().lower() == "true" or n.has("hidden"):
            return True
        style = (n.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            return True
        if n.tag == "input" and (n.get("type") or "").lower() == "hidden":
            return True
    return False


def id_map(root: Node) -> dict:
    ids: dict = {}
    for n in root.iter():
        if n.get("id"):
            ids.setdefault(n.get("id"), n)
    return ids


def text_content(node: Node, ids: dict | None = None, _depth: int = 0) -> str:
    """Visible text of a subtree as a screen reader would read it (simplified accname)."""
    if _depth > 50:
        return ""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
            continue
        if child.tag in SKIP_TEXT or child.get("aria-hidden", "").lower() == "true" or child.has("hidden"):
            continue
        if child.get("aria-label", "").strip():
            parts.append(child.get("aria-label"))
        elif child.tag in ("img", "area") or (child.tag == "input" and (child.get("type") or "").lower() == "image"):
            parts.append(child.get("alt") or "")
        elif child.tag == "svg":
            title = next((t for t in child.iter() if t.tag == "title"), None)
            parts.append(text_content(title, ids, _depth + 1) if title else "")
        else:
            parts.append(text_content(child, ids, _depth + 1))
    return " ".join(" ".join(parts).split())


def labels_for(node: Node, root: Node) -> list:
    out = []
    nid = node.get("id")
    for n in root.iter():
        if n.tag == "label" and nid and n.get("for") == nid:
            out.append(n)
    for anc in node.ancestors():
        if anc.tag == "label" and anc not in out:
            out.append(anc)
    return out


NAME_FROM_CONTENT = {
    "a",
    "button",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "summary",
    "option",
    "legend",
    "caption",
    "th",
    "td",
    "label",
    "li",
}


def accessible_name(node: Node, root: Node, ids: dict) -> str:
    """Simplified accessible name computation (aria-labelledby, aria-label, native, content, title)."""
    refs = (node.get("aria-labelledby") or "").split()
    if refs:
        name = " ".join(text_content(ids[r], ids) for r in refs if r in ids).strip()
        if name:
            return name
    if (node.get("aria-label") or "").strip():
        return node.get("aria-label").strip()
    tag = node.tag
    itype = (node.get("type") or "text").lower()
    if tag in ("img", "area") or (tag == "input" and itype == "image"):
        if (node.get("alt") or "").strip():
            return node.get("alt").strip()
    elif tag in ("input", "select", "textarea", "meter", "progress", "output"):
        if tag == "input" and itype in ("submit", "reset", "button"):
            value = (node.get("value") or "").strip()
            if value:
                return value
            if itype in ("submit", "reset"):
                return itype.capitalize()
        else:
            name = " ".join(text_content(lab, ids) for lab in labels_for(node, root)).strip()
            if name:
                return name
    elif tag == "fieldset":
        legend = next((c for c in node.children if isinstance(c, Node) and c.tag == "legend"), None)
        if legend is not None and text_content(legend, ids):
            return text_content(legend, ids)
    elif tag == "table":
        cap = next((c for c in node.iter() if c.tag == "caption"), None)
        if cap is not None and text_content(cap, ids):
            return text_content(cap, ids)
    elif tag == "svg":
        title = next((c for c in node.iter() if c.tag == "title"), None)
        if title is not None and text_content(title, ids):
            return text_content(title, ids)
    role = (node.get("role") or "").split()
    from_content = tag in NAME_FROM_CONTENT or (
        role
        and role[0]
        in {
            "button",
            "link",
            "heading",
            "tab",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "option",
            "checkbox",
            "radio",
            "switch",
            "treeitem",
            "cell",
            "columnheader",
            "rowheader",
            "tooltip",
        }
    )
    if from_content:
        name = text_content(node, ids)
        if name:
            return name
    return (node.get("title") or "").strip()


def heading_level(n: Node) -> int:
    """Level of <h1>-<h6> or role=heading (aria-level, default 2)."""
    if re.fullmatch(r"h[1-6]", n.tag):
        return int(n.tag[1])
    raw = (n.get("aria-level") or "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else 2


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    """Return (label, text) for files, folders (*.html, *.htm) and '-' (stdin)."""
    out = []
    for p in paths:
        if p == "-":
            out.append(("<stdin>", sys.stdin.read()))
            continue
        path = Path(p)
        if path.is_dir():
            for f in sorted([*path.rglob("*.html"), *path.rglob("*.htm")]):
                out.append((str(f), f.read_text(encoding="utf-8", errors="replace")))
        else:
            out.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
    return out


SEVERITIES = ["info", "low", "medium", "high"]


def finding(severity: str, rule: str, node: Node | None, message: str, fix: str, wcag: str = "") -> dict:
    return {
        "severity": severity,
        "rule": rule,
        "wcag": wcag,
        "line": node.line if node is not None else 0,
        "element": node.describe() if node is not None else "",
        "message": message,
        "fix": fix,
    }


def report(results: list[tuple[str, list[dict]]], as_json: bool, fail_on: str, title: str) -> int:
    """Print findings per file; return exit code 1 when any finding reaches fail_on."""
    threshold = SEVERITIES.index(fail_on) if fail_on in SEVERITIES else len(SEVERITIES)
    failing = any(SEVERITIES.index(f["severity"]) >= threshold for _, fs in results for f in fs)
    if as_json:
        payload = {
            "tool": title,
            "files": [
                {
                    "file": label,
                    "summary": {s: sum(1 for f in fs if f["severity"] == s) for s in reversed(SEVERITIES)},
                    "findings": fs,
                }
                for label, fs in results
            ],
        }
        print(json.dumps(payload, indent=2))
        return 1 if failing else 0
    for label, fs in results:
        counts = ", ".join(f"{sum(1 for f in fs if f['severity'] == s)} {s}" for s in reversed(SEVERITIES))
        print(f"{title}: {label} - {counts}")
        order = sorted(fs, key=lambda f: (-SEVERITIES.index(f["severity"]), f["line"]))
        for f in order:
            wcag = f" [WCAG {f['wcag']}]" if f["wcag"] else ""
            where = f"line {f['line']} {f['element']}".strip() if f["line"] else "page"
            print(f"  {f['severity'].upper():6} {f['rule']}{wcag} ({where}): {f['message']}")
            print(f"         fix: {f['fix']}")
        if not fs:
            print("  no findings")
        print()
    return 1 if failing else 0


# --- end shared dom helpers ---


FIELD_NAMES = set(
    """name honorific-prefix given-name additional-name family-name honorific-suffix nickname username
    new-password current-password one-time-code organization-title organization street-address
    address-line1 address-line2 address-line3 address-level4 address-level3 address-level2 address-level1
    country country-name postal-code cc-name cc-given-name cc-additional-name cc-family-name cc-number
    cc-exp cc-exp-month cc-exp-year cc-csc cc-type transaction-currency transaction-amount language bday
    bday-day bday-month bday-year sex url photo""".split()
)
CONTACT_FIELD_NAMES = set(
    """tel tel-country-code tel-national tel-area-code tel-local tel-local-prefix tel-local-suffix
    tel-extension email impp""".split()
)
CONTACT_TYPES = {"home", "work", "mobile", "fax", "pager"}
# Guess the purpose of a field from its name/id/label: (regex, token).
PURPOSE_HINTS = [
    (r"e.?mail", "email"),
    (r"phone|mobile|\btel\b|telephone|\bcell\b", "tel"),
    (r"first.?name|given.?name|fname|forename", "given-name"),
    (r"last.?name|family.?name|surname|lname", "family-name"),
    (r"middle.?name", "additional-name"),
    (r"full.?name|^name$|your.?name|^customer.?name|^contact.?name", "name"),
    (r"user.?name|login|user.?id", "username"),
    (r"new.?password|confirm.?password|password.?confirm|repeat.?password", "new-password"),
    (r"password|passwd|pwd", "current-password"),
    (r"one.?time|otp|verification.?code|2fa|mfa", "one-time-code"),
    (r"address.?(line)?.?2|\bapt\b|\bsuite\b", "address-line2"),
    (r"street|address.?(line)?.?1|^address$", "address-line1"),
    (r"\bcity\b|\btown\b|locality", "address-level2"),
    (r"\bstate\b|province|\bregion\b|\bcounty\b", "address-level1"),
    (r"zip|postal|post.?code|postcode", "postal-code"),
    (r"country", "country-name"),
    (r"company|organi[sz]ation|employer", "organization"),
    (r"job.?title|position", "organization-title"),
    (r"card.?number|cc.?num|ccnumber|credit.?card", "cc-number"),
    (r"name.?on.?card|card.?holder|cc.?name", "cc-name"),
    (r"cvc|cvv|csc|security.?code", "cc-csc"),
    (r"expir|exp.?date|cc.?exp", "cc-exp"),
    (r"birth|dob|bday", "bday"),
    (r"website|homepage|^url$", "url"),
]
TYPE_FOR_TOKEN = {
    "email": {"email"},
    "tel": {"tel"},
    "url": {"url"},
    "new-password": {"password"},
    "current-password": {"password"},
}
NON_TEXT_TYPES = {"checkbox", "radio", "submit", "reset", "button", "image", "hidden", "file", "range", "color"}


def validate_autocomplete(value: str) -> tuple[bool, str]:
    """Validate an autocomplete attribute value against the HTML autofill grammar."""
    tokens = value.lower().split()
    if not tokens:
        return False, "empty autocomplete value"
    if tokens in (["on"], ["off"]):
        return True, ""
    if tokens[-1] == "webauthn":
        tokens = tokens[:-1]
        if not tokens:
            return False, "'webauthn' must follow a field name such as username or current-password"
    i = 0
    if i < len(tokens) and tokens[i].startswith("section-"):
        i += 1
    if i < len(tokens) and tokens[i] in ("shipping", "billing"):
        i += 1
    if i < len(tokens) and tokens[i] in CONTACT_TYPES:
        if i + 1 >= len(tokens) or tokens[i + 1] not in CONTACT_FIELD_NAMES:
            return False, f"'{tokens[i]}' may only precede tel*, email or impp"
        i += 1
    if i >= len(tokens):
        return False, "missing field name (e.g. email, given-name, postal-code)"
    field = tokens[i]
    if field not in FIELD_NAMES and field not in CONTACT_FIELD_NAMES:
        close = [f for f in sorted(FIELD_NAMES | CONTACT_FIELD_NAMES) if field.replace("_", "-") == f or field in f]
        hint = f" (did you mean {close[0]}?)" if close else ""
        return False, f"'{field}' is not an autofill field name{hint}"
    if i != len(tokens) - 1:
        return False, f"unexpected token(s) after '{field}': {' '.join(tokens[i + 1 :])}"
    return True, ""


NEW_PASSWORD_RE = r"new.?password|confirm.?password|password.?confirm|repeat.?password"


def _words(value: str) -> str:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return " ".join(re.sub(r"[_\-\[\].]+", " ", value).lower().split())


def guess_purpose(n: Node, label: str) -> str | None:
    """Guess the autofill purpose from type, name, id and label text."""
    pieces = [_words(n.get("name") or ""), _words(n.get("id") or ""), _words(label)]
    itype = (n.get("type") or "text").lower()
    if itype == "email":
        return "email"
    if itype == "tel":
        return "tel"
    if itype == "password":
        return "new-password" if any(re.search(NEW_PASSWORD_RE, p) for p in pieces) else "current-password"
    if itype in ("search", "number", "date", "time", "month", "week", "datetime-local"):
        return None
    for pattern, token in PURPOSE_HINTS:
        if token in ("new-password", "current-password"):
            continue
        if any(p and re.search(pattern, p) for p in pieces):
            return token
    return None


def check(text: str) -> list[dict]:
    root = parse_html(text)
    ids = id_map(root)
    nodes = list(root.iter())
    out: list[dict] = []
    controls = [n for n in nodes if n.tag in ("input", "select", "textarea") and not is_hidden(n)]

    for n in controls:
        itype = (n.get("type") or "text").lower()
        label = " ".join(text_content(lab, ids) for lab in labels_for(n, root))
        name = accessible_name(n, root, ids)
        if itype not in ("submit", "reset", "button", "image") and not name:
            hint = " - placeholder disappears on input and is not a label" if n.get("placeholder") else ""
            out.append(
                finding(
                    "high",
                    "label.missing",
                    n,
                    f"<{n.tag} name={n.get('name', '')!r}> has no label{hint}",
                    "add a visible <label for=...>; aria-label only when a visible label is impossible",
                    "1.3.1, 3.3.2, 4.1.2",
                )
            )
        elif label and n.get("aria-label") and label.lower() not in n.get("aria-label").lower():
            out.append(
                finding(
                    "medium",
                    "label.name_mismatch",
                    n,
                    f"aria-label {n.get('aria-label')!r} does not contain the visible label {label!r}",
                    "remove aria-label or start it with the visible text (voice control users say what they see)",
                    "2.5.3",
                )
            )

        # Autocomplete.
        if n.has("autocomplete"):
            ok, why = validate_autocomplete(n.get("autocomplete") or "")
            if not ok:
                out.append(
                    finding(
                        "high",
                        "autocomplete.invalid",
                        n,
                        f'autocomplete="{n.get("autocomplete")}": {why}',
                        "use a token from the HTML autofill list (see references/autocomplete-tokens.md)",
                        "1.3.5",
                    )
                )
                continue
        if n.tag == "select" or (n.tag == "input" and itype not in NON_TEXT_TYPES) or n.tag == "textarea":
            purpose = guess_purpose(n, label)
            value = (n.get("autocomplete") or "").lower().split()
            field = value[-1] if value and value[-1] != "webauthn" else (value[-2] if len(value) > 1 else "")
            if purpose and not value:
                out.append(
                    finding(
                        "medium",
                        "autocomplete.missing",
                        n,
                        f"field looks like {purpose} but has no autocomplete",
                        f'add autocomplete="{purpose}" so browsers and assistive tech can fill it',
                        "1.3.5",
                    )
                )
            elif purpose and value == ["off"]:
                out.append(
                    finding(
                        "low",
                        "autocomplete.off_on_personal",
                        n,
                        f"autocomplete=off on a {purpose} field",
                        f'use autocomplete="{purpose}"; off forces users with memory or motor impairments to retype',
                        "1.3.5, 3.3.7",
                    )
                )
            if field in TYPE_FOR_TOKEN and n.tag == "input" and itype not in TYPE_FOR_TOKEN[field]:
                out.append(
                    finding(
                        "low",
                        "input.type_mismatch",
                        n,
                        f'autocomplete="{field}" on type="{itype}"',
                        f'use type="{sorted(TYPE_FOR_TOKEN[field])[0]}" for the right mobile keyboard and validation',
                        "1.3.5",
                    )
                )

        # Errors and required state.
        if (n.get("aria-invalid") or "").lower() in ("true", "grammar", "spelling"):
            described = (n.get("aria-describedby") or "").split() + (n.get("aria-errormessage") or "").split()
            if not any(d in ids for d in described):
                out.append(
                    finding(
                        "medium",
                        "error.not_associated",
                        n,
                        'aria-invalid="true" but no aria-describedby/aria-errormessage pointing at an error message',
                        "render the error text next to the field and reference it with aria-describedby",
                        "3.3.1",
                    )
                )
        if (
            label
            and re.search(r"\*|\brequired\b", label, re.I)
            and not (n.has("required") or (n.get("aria-required") or "") == "true")
        ):
            out.append(
                finding(
                    "low",
                    "required.not_programmatic",
                    n,
                    "label marks the field as required but the control has no required/aria-required",
                    "add the required attribute (or aria-required=true with custom validation)",
                    "3.3.2, 4.1.2",
                )
            )
        if n.has("onpaste") and re.search(r"return\s+false|preventdefault", n.get("onpaste") or "", re.I):
            out.append(
                finding(
                    "high",
                    "auth.paste_blocked",
                    n,
                    "pasting is blocked; password managers and copy-paste stop working",
                    "remove the onpaste handler",
                    "3.3.8",
                )
            )

    # Radio/checkbox groups.
    groups: dict = {}
    for n in controls:
        itype = (n.get("type") or "").lower()
        if n.tag == "input" and itype in ("radio", "checkbox") and n.get("name"):
            groups.setdefault((itype, n.get("name")), []).append(n)
    for (itype, gname), members in groups.items():
        if len(members) < 2:
            continue
        first = members[0]
        grouped = False
        for a in first.ancestors():
            role = (a.get("role") or "").lower()
            if (
                a.tag == "fieldset"
                and any(isinstance(c, Node) and c.tag == "legend" for c in a.children)
                or role in ("radiogroup", "group")
                and accessible_name(a, root, ids)
            ):
                grouped = True
            if grouped:
                break
        if not grouped:
            out.append(
                finding(
                    "medium",
                    "group.no_fieldset",
                    first,
                    f"{len(members)} {itype} inputs named {gname!r} are not in a <fieldset> with <legend>",
                    "wrap them in <fieldset><legend>Question</legend>...</fieldset> so the question is announced",
                    "1.3.1, 3.3.2",
                )
            )

    # Forms.
    for f in (n for n in nodes if n.tag == "form"):
        inner = list(f.iter())
        submits = [
            x
            for x in inner
            if (x.tag == "button" and (x.get("type") or "submit").lower() == "submit")
            or (x.tag == "input" and (x.get("type") or "").lower() in ("submit", "image"))
        ]
        fields = [
            x for x in inner if x.tag in ("input", "select", "textarea") and (x.get("type") or "").lower() != "hidden"
        ]
        if fields and not submits:
            out.append(
                finding(
                    "low",
                    "form.no_submit",
                    f,
                    "form has no submit button",
                    "add <button type='submit'>; submitting on change or blur surprises users",
                    "3.2.2",
                )
            )
        if any("captcha" in (x.get("class") or "").lower() or "captcha" in (x.get("src") or "").lower() for x in inner):
            out.append(
                finding(
                    "info",
                    "auth.captcha",
                    f,
                    "CAPTCHA detected",
                    "offer a non-cognitive alternative (passkey, email link) and an audio option; see 3.3.8",
                    "3.3.8, 1.1.1",
                )
            )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Check HTML forms: autocomplete token validity and missing autocomplete on personal-data fields "
        "(1.3.5), labels, label-in-name, radio/checkbox fieldsets, error association, required state, paste "
        "blocking (3.3.8), forms without submit.",
        epilog="Exit codes: 0 = no findings at/above --fail-on, 1 = findings, 2 = error. "
        "--token VALUE validates one autocomplete value and exits.",
    )
    p.add_argument("paths", nargs="*", help="HTML files, folders or - for stdin")
    p.add_argument(
        "--token", action="append", default=[], help="validate an autocomplete value, e.g. 'shipping postal-code'"
    )
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--fail-on", default="medium", choices=[*SEVERITIES, "never"], help="default: medium")
    p.add_argument("--ignore", action="append", default=[], help="rule id to skip (repeatable)")
    args = p.parse_args(argv)
    if args.token:
        res = [
            {"value": t, "valid": validate_autocomplete(t)[0], "reason": validate_autocomplete(t)[1]}
            for t in args.token
        ]
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            for r in res:
                print(
                    f"{'VALID  ' if r['valid'] else 'INVALID'} {r['value']!r}"
                    + (f": {r['reason']}" if r["reason"] else "")
                )
        return 0 if all(r["valid"] for r in res) else 1
    if not args.paths:
        p.error("give HTML paths or --token")
    try:
        inputs = read_inputs(args.paths)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = [(label, [f for f in check(text) if f["rule"] not in args.ignore]) for label, text in inputs]
    return report(results, args.json, args.fail_on, "accessible-forms")


if __name__ == "__main__":
    sys.exit(main())
