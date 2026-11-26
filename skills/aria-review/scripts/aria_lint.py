#!/usr/bin/env python3
"""Lint HTML for WAI-ARIA misuse (static, offline, read-only).

Checks: invalid, abstract and deprecated roles; unknown or misspelled aria-* attributes;
invalid values (aria-expanded="yes"); aria-labelledby/describedby/controls pointing at
missing ids; aria-hidden="true" on focusable content or <body>; redundant roles
(<button role="button">); roles that override native semantics; missing required states
(role=checkbox without aria-checked) and context (role=tab outside tablist); interactive
roles that cannot be focused; unnamed dialogs/regions; aria-label on generic elements;
duplicate landmarks without labels.

Exit codes: 0 = ok, 1 = findings at or above --fail-on, 2 = error.
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


ROLES = set(
    """alert alertdialog application article banner blockquote button caption cell checkbox code
    columnheader combobox comment complementary contentinfo definition deletion dialog directory document
    emphasis feed figure form generic grid gridcell group heading image img insertion link list listbox
    listitem log main mark marquee math menu menubar menuitem menuitemcheckbox menuitemradio meter
    navigation none note option paragraph presentation progressbar radio radiogroup region row rowgroup
    rowheader scrollbar search searchbox sectionfooter sectionheader separator slider spinbutton status
    strong subscript suggestion superscript switch tab table tablist tabpanel term textbox time timer
    toolbar tooltip tree treegrid treeitem""".split()
)
ABSTRACT_ROLES = set(
    "command composite input landmark range roletype section sectionhead select structure widget window".split()
)
DEPRECATED_ROLES = {"directory"}
ARIA_ATTRS = set(
    """activedescendant atomic autocomplete braillelabel brailleroledescription busy checked colcount
    colindex colindextext colspan controls current describedby description details disabled dropeffect
    errormessage expanded flowto grabbed haspopup hidden invalid keyshortcuts label labelledby level live
    modal multiline multiselectable orientation owns placeholder posinset pressed readonly relevant
    required roledescription rowcount rowindex rowindextext rowspan selected setsize sort valuemax
    valuemin valuenow valuetext""".split()
)
DEPRECATED_ATTRS = {"dropeffect", "grabbed"}
TOKENS = {
    "atomic": {"true", "false"},
    "busy": {"true", "false"},
    "disabled": {"true", "false"},
    "modal": {"true", "false"},
    "multiline": {"true", "false"},
    "multiselectable": {"true", "false"},
    "readonly": {"true", "false"},
    "required": {"true", "false"},
    "expanded": {"true", "false", "undefined"},
    "hidden": {"true", "false", "undefined"},
    "selected": {"true", "false", "undefined"},
    "grabbed": {"true", "false", "undefined"},
    "checked": {"true", "false", "mixed", "undefined"},
    "pressed": {"true", "false", "mixed", "undefined"},
    "autocomplete": {"inline", "list", "both", "none"},
    "current": {"page", "step", "location", "date", "time", "true", "false"},
    "haspopup": {"false", "true", "menu", "listbox", "tree", "grid", "dialog"},
    "invalid": {"grammar", "false", "spelling", "true"},
    "live": {"assertive", "off", "polite"},
    "orientation": {"horizontal", "vertical", "undefined"},
    "sort": {"ascending", "descending", "none", "other"},
}
TOKEN_LISTS = {
    "relevant": {"additions", "removals", "text", "all"},
    "dropeffect": {"copy", "execute", "link", "move", "none", "popup"},
}
INTEGERS = {"level", "posinset", "setsize", "colcount", "colindex", "colspan", "rowcount", "rowindex", "rowspan"}
NUMBERS = {"valuemax", "valuemin", "valuenow"}
IDREFS = {"labelledby", "describedby", "controls", "owns", "flowto", "details", "errormessage", "activedescendant"}
REQUIRED_ATTRS = {
    "checkbox": ["aria-checked"],
    "menuitemcheckbox": ["aria-checked"],
    "menuitemradio": ["aria-checked"],
    "radio": ["aria-checked"],
    "switch": ["aria-checked"],
    "combobox": ["aria-expanded"],
    "slider": ["aria-valuenow"],
    "scrollbar": ["aria-controls", "aria-valuenow"],
    "spinbutton": [],
    "heading": ["aria-level"],
}
REQUIRED_CONTEXT = {
    "tab": {"tablist"},
    "option": {"listbox", "group", "combobox"},
    "menuitem": {"menu", "menubar", "group"},
    "menuitemcheckbox": {"menu", "menubar", "group"},
    "menuitemradio": {"menu", "menubar", "group"},
    "listitem": {"list", "directory", "group"},
    "treeitem": {"tree", "group"},
    "row": {"table", "grid", "treegrid", "rowgroup"},
    "cell": {"row"},
    "gridcell": {"row"},
    "columnheader": {"row"},
    "rowheader": {"row"},
}
INTERACTIVE_ROLES = {
    "button",
    "link",
    "checkbox",
    "radio",
    "switch",
    "tab",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "option",
    "slider",
    "spinbutton",
    "textbox",
    "searchbox",
    "combobox",
    "treeitem",
    "scrollbar",
}
NEEDS_NAME = {
    "dialog",
    "alertdialog",
    "img",
    "image",
    "progressbar",
    "meter",
    "tabpanel",
    "tree",
    "grid",
    "listbox",
    "menu",
    "radiogroup",
    "form",
    "region",
}
SECTIONING = {"article", "aside", "main", "nav", "section"}
LANDMARK_ROLES = {"banner", "complementary", "contentinfo", "form", "main", "navigation", "region", "search"}


def implicit_role(n: Node) -> str:
    """Implicit ARIA role of a native element (HTML-AAM, simplified)."""
    t = n.tag
    itype = (n.get("type") or "text").lower()
    if t in ("a", "area"):
        return "link" if n.has("href") else ""
    if t == "input":
        if n.get("list"):
            return "combobox"
        return {
            "checkbox": "checkbox",
            "radio": "radio",
            "range": "slider",
            "number": "spinbutton",
            "search": "searchbox",
            "button": "button",
            "submit": "button",
            "reset": "button",
            "image": "button",
            "text": "textbox",
            "email": "textbox",
            "tel": "textbox",
            "url": "textbox",
        }.get(itype, "")
    if t == "select":
        return "listbox" if n.has("multiple") or int((n.get("size") or "1").strip() or 1) > 1 else "combobox"
    if t in ("header", "footer"):
        if any(a.tag in SECTIONING for a in n.ancestors()):
            return ""
        return "banner" if t == "header" else "contentinfo"
    if t == "img":
        return "img" if (n.get("alt") or "").strip() else ""
    if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return "heading"
    return {
        "article": "article",
        "aside": "complementary",
        "button": "button",
        "datalist": "listbox",
        "details": "group",
        "dialog": "dialog",
        "fieldset": "group",
        "figure": "figure",
        "hr": "separator",
        "li": "listitem",
        "main": "main",
        "math": "math",
        "menu": "list",
        "meter": "meter",
        "nav": "navigation",
        "ol": "list",
        "ul": "list",
        "option": "option",
        "output": "status",
        "progress": "progressbar",
        "search": "search",
        "table": "table",
        "tbody": "rowgroup",
        "thead": "rowgroup",
        "tfoot": "rowgroup",
        "td": "cell",
        "th": "columnheader",
        "textarea": "textbox",
        "tr": "row",
        "form": "form" if (n.get("aria-label") or n.get("aria-labelledby") or n.get("name")) else "",
        "section": "region" if (n.get("aria-label") or n.get("aria-labelledby")) else "",
    }.get(t, "")


def role_of(n: Node) -> str:
    explicit = [r for r in (n.get("role") or "").lower().split() if r in ROLES]
    return explicit[0] if explicit else implicit_role(n)


def is_focusable(n: Node) -> bool:
    if n.has("disabled") or n.has("inert") or any(a.has("inert") for a in n.ancestors()):
        return False
    tab = (n.get("tabindex") or "").strip()
    if tab.lstrip("-").isdigit():
        return int(tab) >= 0
    if n.tag in ("a", "area"):
        return n.has("href")
    if n.tag == "input":
        return (n.get("type") or "").lower() != "hidden"
    if n.tag in ("button", "select", "textarea", "iframe", "summary"):
        return True
    if n.tag in ("audio", "video"):
        return n.has("controls")
    return (n.get("contenteditable") or "false").lower() in ("", "true", "plaintext-only")


def lint(text: str) -> list[dict]:
    root = parse_html(text)
    ids = id_map(root)
    nodes = list(root.iter())
    out: list[dict] = []
    landmarks: dict = {}
    # Popups driven by a combobox or an aria-activedescendant owner (options are not focused directly).
    popup_ids = set()
    for n in nodes:
        if n.get("aria-activedescendant") is not None or role_of(n) == "combobox":
            popup_ids.update((n.get("aria-controls") or "").split() + (n.get("aria-owns") or "").split())

    for n in nodes:
        raw_roles = (n.get("role") or "").lower().split()
        role = role_of(n)

        # Roles.
        if n.has("role") and not raw_roles:
            out.append(finding("medium", "role.empty", n, 'empty role=""', "remove the role attribute", "4.1.2"))
        if raw_roles:
            first = raw_roles[0]
            if first in ABSTRACT_ROLES:
                out.append(
                    finding(
                        "high",
                        "role.abstract",
                        n,
                        f'role="{first}" is an abstract role and must not be used in content',
                        "use a concrete role (e.g. group, button, region) or none",
                        "4.1.2",
                    )
                )
            elif first not in ROLES and not first.startswith(("doc-", "graphics-")):
                fallback = next((r for r in raw_roles[1:] if r in ROLES), None)
                sev = "low" if fallback else "high"
                out.append(
                    finding(
                        sev,
                        "role.invalid",
                        n,
                        f'role="{first}" is not a WAI-ARIA role' + (f" (falls back to {fallback})" if fallback else ""),
                        "use a valid role from WAI-ARIA 1.2, or a native HTML element",
                        "4.1.2",
                    )
                )
            elif first in DEPRECATED_ROLES:
                out.append(
                    finding("low", "role.deprecated", n, f'role="{first}" is deprecated', "use role=list", "4.1.2")
                )
            native = implicit_role(n)
            if first in ROLES and native and first == native:
                out.append(
                    finding(
                        "low",
                        "role.redundant",
                        n,
                        f'<{n.tag}> already has role "{native}"; role="{first}" is redundant',
                        "remove the role attribute",
                        "",
                    )
                )
            elif first in ROLES and native in INTERACTIVE_ROLES and first not in ("none", "presentation"):
                swapped = (native, first) in (("link", "button"), ("button", "link"))
                if swapped or first not in INTERACTIVE_ROLES:
                    out.append(
                        finding(
                            "low" if swapped else "medium",
                            "role.overrides_native",
                            n,
                            f'role="{first}" overrides the native {native} semantics of <{n.tag}>',
                            "use the element that matches what it does (<a href> navigates, <button> acts)",
                            "4.1.2",
                        )
                    )
            if first in ("none", "presentation") and (
                is_focusable(n) or any(n.has(a) for a in ("aria-label", "aria-labelledby", "aria-describedby"))
            ):
                out.append(
                    finding(
                        "medium",
                        "role.presentation_conflict",
                        n,
                        f'role="{first}" is ignored because the element is focusable or has global ARIA attributes',
                        "remove role=none, or make the element non-focusable and drop the ARIA attributes",
                        "4.1.2",
                    )
                )

        # ARIA attributes.
        for attr, value in n.attrs.items():
            if not attr.startswith("aria-"):
                continue
            key = attr[5:]
            value = (value or "").strip()
            if key not in ARIA_ATTRS:
                out.append(
                    finding(
                        "high",
                        "aria.unknown_attribute",
                        n,
                        f"{attr} is not a WAI-ARIA attribute (typo?)",
                        "check the spelling against WAI-ARIA 1.2 (e.g. aria-labelledby, aria-describedby)",
                        "4.1.2",
                    )
                )
                continue
            if key in DEPRECATED_ATTRS:
                out.append(finding("low", "aria.deprecated", n, f"{attr} is deprecated", "remove it", "4.1.2"))
            low = value.lower()
            if key in TOKENS and low not in TOKENS[key]:
                out.append(
                    finding(
                        "medium",
                        "aria.invalid_value",
                        n,
                        f'{attr}="{value}" is not valid (allowed: {", ".join(sorted(TOKENS[key]))})',
                        "use one of the allowed values",
                        "4.1.2",
                    )
                )
            elif key in TOKEN_LISTS and (not low or any(v not in TOKEN_LISTS[key] for v in low.split())):
                out.append(
                    finding(
                        "medium",
                        "aria.invalid_value",
                        n,
                        f'{attr}="{value}" is not valid',
                        f"use tokens from: {', '.join(sorted(TOKEN_LISTS[key]))}",
                        "4.1.2",
                    )
                )
            elif key in INTEGERS and not re.fullmatch(r"-?\d+", value):
                out.append(
                    finding(
                        "medium",
                        "aria.invalid_value",
                        n,
                        f'{attr}="{value}" must be an integer',
                        "fix the value",
                        "4.1.2",
                    )
                )
            elif key in NUMBERS and not re.fullmatch(r"-?\d+(\.\d+)?", value):
                out.append(
                    finding(
                        "medium",
                        "aria.invalid_value",
                        n,
                        f'{attr}="{value}" must be a number',
                        "fix the value",
                        "4.1.2",
                    )
                )
            elif key in IDREFS:
                refs = value.split()
                missing = [r for r in refs if r not in ids]
                if not refs or missing:
                    out.append(
                        finding(
                            "high" if key in ("labelledby", "describedby", "errormessage") else "medium",
                            "aria.broken_reference",
                            n,
                            f"{attr} points at missing id(s): {', '.join(missing) or '(empty)'}",
                            "make the ids exist on the page (unique) or remove the attribute",
                            "1.3.1, 4.1.2",
                        )
                    )
            elif key == "label" and not value:
                out.append(
                    finding("medium", "aria.empty_label", n, 'aria-label=""', "give it text or remove it", "4.1.2")
                )

        # aria-hidden on focusable content.
        if (n.get("aria-hidden") or "").lower() == "true":
            if n.tag in ("body", "html"):
                out.append(
                    finding(
                        "high",
                        "aria_hidden.body",
                        n,
                        f'aria-hidden="true" on <{n.tag}> hides the whole page',
                        "remove it; to hide background content behind a modal use inert on siblings",
                        "4.1.2",
                    )
                )
            focusables = [d for d in [n, *n.iter()] if is_focusable(d)]
            if focusables:
                first = focusables[0]
                out.append(
                    finding(
                        "high",
                        "aria_hidden.focusable",
                        n,
                        f'aria-hidden="true" element contains focusable {first.describe()} '
                        f"(line {first.line}); keyboard users reach it but screen readers announce nothing",
                        'remove aria-hidden, or also take it out of focus order (tabindex="-1", inert, disabled)',
                        "4.1.2",
                    )
                )

        # Required states, context and focusability.
        if raw_roles and role in REQUIRED_ATTRS and not re.fullmatch(r"h[1-6]", n.tag):
            native_state = n.tag == "input" and (n.get("type") or "").lower() in ("checkbox", "radio")
            for attr in REQUIRED_ATTRS[role]:
                if n.has(attr) or native_state:
                    continue
                if role == "heading" and attr == "aria-level":
                    out.append(
                        finding(
                            "low",
                            "role.missing_required",
                            n,
                            'role="heading" without aria-level defaults to level 2',
                            "add aria-level or use <h1>-<h6>",
                            "1.3.1",
                        )
                    )
                    continue
                out.append(
                    finding(
                        "high",
                        "role.missing_required",
                        n,
                        f'role="{role}" requires {attr}',
                        f"add {attr} and update it from script when the state changes",
                        "4.1.2",
                    )
                )
        if raw_roles and role in REQUIRED_CONTEXT:
            parent_roles = []
            for a in n.ancestors():
                r = role_of(a)
                if r in ("none", "presentation", "generic", "") and a.tag in ("div", "span", "template", "slot"):
                    continue
                if r in ("none", "presentation"):
                    continue
                parent_roles.append(r)
                break
            owned = any(n.get("id") and n.get("id") in (a.get("aria-owns") or "").split() for a in nodes)
            if not owned and (not parent_roles or parent_roles[0] not in REQUIRED_CONTEXT[role]):
                out.append(
                    finding(
                        "high",
                        "role.missing_context",
                        n,
                        f'role="{role}" must be inside {" or ".join(sorted(REQUIRED_CONTEXT[role]))}'
                        + (f" (parent is {parent_roles[0]})" if parent_roles else ""),
                        "wrap it in the required container role (e.g. role=tablist around tabs)",
                        "1.3.1",
                    )
                )
        if raw_roles and role in INTERACTIVE_ROLES and not is_focusable(n) and not is_hidden(n):
            in_composite = any(
                role_of(a) in ("listbox", "menu", "menubar", "tablist", "tree", "grid", "radiogroup", "combobox")
                and (a.get("aria-activedescendant") is not None or a.get("id") in popup_ids)
                for a in n.ancestors()
            )
            roving = role in ("tab", "option", "menuitem", "menuitemcheckbox", "menuitemradio", "treeitem", "radio")
            if not in_composite and not roving:
                out.append(
                    finding(
                        "high",
                        "role.not_focusable",
                        n,
                        f'<{n.tag} role="{role}"> cannot be reached with the keyboard',
                        f'use a native element, or add tabindex="0" and key handlers (Enter/Space for {role})',
                        "2.1.1, 4.1.2",
                    )
                )
            elif roving and not is_focusable(n) and not n.has("tabindex") and not in_composite:
                out.append(
                    finding(
                        "medium",
                        "role.roving_tabindex",
                        n,
                        f'role="{role}" has no tabindex; one item in the group needs tabindex="0" and the rest "-1"',
                        "implement roving tabindex or aria-activedescendant (see accessible-components)",
                        "2.1.1",
                    )
                )

        # Names.
        if role in NEEDS_NAME and (raw_roles or n.tag in ("dialog", "progress", "meter")) and not is_hidden(n):
            if not accessible_name(n, root, ids):
                out.append(
                    finding(
                        "medium",
                        "name.missing",
                        n,
                        f"{role} has no accessible name",
                        "add aria-labelledby pointing at its visible heading, or aria-label",
                        "4.1.2",
                    )
                )
        if n.tag in ("div", "span", "p", "b", "i", "em", "strong") and not raw_roles:
            if n.has("aria-label") or n.has("aria-labelledby"):
                out.append(
                    finding(
                        "medium",
                        "name.prohibited_on_generic",
                        n,
                        f"aria-label/labelledby on <{n.tag}> without a role is ignored by many screen readers",
                        "give the element a role that supports a name, or put the text in the content",
                        "4.1.2",
                    )
                )

        if role in LANDMARK_ROLES and not is_hidden(n):
            landmarks.setdefault(role, []).append(n)

    for role, group in landmarks.items():
        if len(group) > 1:
            unnamed = [g for g in group if not (g.get("aria-label") or g.get("aria-labelledby"))]
            if unnamed and role not in ("region", "form"):
                out.append(
                    finding(
                        "low" if role != "main" else "medium",
                        "landmark.duplicate_unlabelled",
                        unnamed[0],
                        f"{len(group)} {role} landmarks and {len(unnamed)} without a label",
                        'label each one (aria-label="Primary", "Footer") so users can tell them apart'
                        + ("; there should be only one main" if role == "main" else ""),
                        "1.3.1",
                    )
                )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Lint HTML for ARIA misuse: invalid/abstract roles, unknown aria-* attributes, invalid values, "
        "broken id references, aria-hidden on focusable content, redundant roles, missing required states and "
        "context, non-focusable interactive roles, unnamed dialogs, unlabelled duplicate landmarks.",
        epilog="Exit codes: 0 = no findings at/above --fail-on, 1 = findings, 2 = error.",
    )
    p.add_argument("paths", nargs="+", help="HTML files, folders or - for stdin")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--fail-on", default="medium", choices=[*SEVERITIES, "never"], help="default: medium")
    p.add_argument("--ignore", action="append", default=[], help="rule id to skip (repeatable)")
    args = p.parse_args(argv)
    try:
        inputs = read_inputs(args.paths)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = [(label, [f for f in lint(text) if f["rule"] not in args.ignore]) for label, text in inputs]
    return report(results, args.json, args.fail_on, "aria-review")


if __name__ == "__main__":
    sys.exit(main())
