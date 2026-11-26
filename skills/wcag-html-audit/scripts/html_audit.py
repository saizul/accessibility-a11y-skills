#!/usr/bin/env python3
"""Audit HTML files for common WCAG 2.2 Level A/AA failures (static, offline, read-only).

Checks: html lang, page title, img/area/input[type=image]/svg alt text, placeholder alt,
empty and generic links, empty buttons, form labels, broken label targets, heading order,
duplicate ids, positive tabindex, iframe titles, data table headers, autoplay media,
missing captions, marquee/blink, zoom-blocking viewport, meta refresh, main landmark.

Static analysis of the HTML source only: it cannot see CSS, JavaScript-rendered DOM or
contrast. Save the rendered DOM (browser devtools > Copy outerHTML) for SPA pages.

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


LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$")
FILENAME_ALT_RE = re.compile(
    r"(^|\s)[\w-]+\.(png|jpe?g|gif|webp|svg|avif|bmp)$|^(img|image|dsc|photo|pic)[_-]?\d+$", re.I
)
PLACEHOLDER_ALT = {"image", "picture", "photo", "graphic", "img", "icon", "logo", "spacer", "banner"}
GENERIC_LINK_TEXT = {
    "click here",
    "here",
    "read more",
    "more",
    "learn more",
    "link",
    "this link",
    "details",
    "more info",
    "continue",
    "go",
}
LABELLABLE_SKIP = {"hidden", "submit", "reset", "button", "image"}


def audit(text: str) -> list[dict]:
    root = parse_html(text)
    ids = id_map(root)
    nodes = list(root.iter())
    out: list[dict] = []

    # Document language and title.
    html = next((n for n in nodes if n.tag == "html"), None)
    is_fragment = html is None
    if not is_fragment:
        lang = (html.get("lang") or "").strip()
        if not lang:
            out.append(
                finding(
                    "high",
                    "html.lang_missing",
                    html,
                    "<html> has no lang attribute; screen readers guess the pronunciation",
                    'add lang="en" (or the page language) to <html>',
                    "3.1.1",
                )
            )
        elif not LANG_RE.match(lang):
            out.append(
                finding(
                    "high",
                    "html.lang_invalid",
                    html,
                    f"lang={lang!r} is not a valid BCP 47 tag",
                    'use a tag such as "en", "en-GB", "bn", "pt-BR"',
                    "3.1.1",
                )
            )
        title = next((n for n in nodes if n.tag == "title" and "svg" not in [a.tag for a in n.ancestors()]), None)
        if title is None or not text_content(title):
            out.append(
                finding(
                    "high",
                    "document.title_missing",
                    title or html,
                    "the page has no (or an empty) <title>",
                    "add a unique, descriptive <title>: 'Page topic - Site name'",
                    "2.4.2",
                )
            )
    for n in nodes:
        if n.has("lang") and n.tag != "html":
            value = (n.get("lang") or "").strip()
            if value and not LANG_RE.match(value):
                out.append(
                    finding(
                        "medium",
                        "lang.invalid",
                        n,
                        f"lang={value!r} is not a valid BCP 47 tag",
                        "fix the language tag of this passage",
                        "3.1.2",
                    )
                )

    # Meta viewport and refresh.
    for n in nodes:
        if n.tag != "meta":
            continue
        if (n.get("name") or "").lower() == "viewport":
            content = (n.get("content") or "").lower().replace(" ", "")
            m = re.search(r"maximum-scale=([\d.]+)", content)
            if "user-scalable=no" in content or "user-scalable=0" in content or (m and float(m.group(1) or 0) < 2):
                out.append(
                    finding(
                        "high",
                        "meta.viewport_zoom_blocked",
                        n,
                        f"viewport blocks zoom ({n.get('content')})",
                        "remove user-scalable=no and maximum-scale (or set maximum-scale>=5)",
                        "1.4.4",
                    )
                )
        if (n.get("http-equiv") or "").lower() == "refresh":
            m = re.match(r"\s*(\d+)", n.get("content") or "")
            if m and int(m.group(1)) > 0:
                out.append(
                    finding(
                        "high",
                        "meta.refresh",
                        n,
                        f"page refreshes or redirects after {m.group(1)}s",
                        "use a server-side redirect, or let the user extend/stop the timer",
                        "2.2.1",
                    )
                )

    # Images and other non-text content.
    for n in nodes:
        if is_hidden(n):
            continue
        if n.tag == "img":
            role = (n.get("role") or "").lower()
            if not n.has("alt"):
                if n.get("aria-label") or n.get("aria-labelledby"):
                    continue
                out.append(
                    finding(
                        "high",
                        "img.alt_missing",
                        n,
                        f"<img src={n.get('src', '')!r}> has no alt attribute",
                        'describe the image in alt="...", or alt="" if it is purely decorative',
                        "1.1.1",
                    )
                )
                continue
            alt = (n.get("alt") or "").strip()
            if not alt and role not in ("", "presentation", "none"):
                out.append(
                    finding(
                        "medium",
                        "img.empty_alt_with_role",
                        n,
                        f'alt="" but role="{role}" says it is meaningful',
                        "give it a real alt text or drop the role",
                        "1.1.1",
                    )
                )
            if alt and (FILENAME_ALT_RE.search(alt) or alt.lower() in PLACEHOLDER_ALT):
                out.append(
                    finding(
                        "medium",
                        "img.alt_placeholder",
                        n,
                        f"alt={alt!r} looks like a file name or placeholder",
                        "write what the image shows or does; use alt='' if decorative",
                        "1.1.1",
                    )
                )
            elif len(alt) > 150:
                out.append(
                    finding(
                        "info",
                        "img.alt_long",
                        n,
                        f"alt text is {len(alt)} characters",
                        "keep alt short; put long descriptions (charts, diagrams) in nearby text or a <figcaption>",
                        "1.1.1",
                    )
                )
        elif n.tag == "input" and (n.get("type") or "").lower() == "image" and not accessible_name(n, root, ids):
            out.append(
                finding(
                    "high",
                    "input_image.alt_missing",
                    n,
                    '<input type="image"> has no alt',
                    "add alt describing the action, e.g. alt='Search'",
                    "1.1.1",
                )
            )
        elif n.tag == "area" and n.has("href") and not accessible_name(n, root, ids):
            out.append(
                finding(
                    "high", "area.alt_missing", n, "image map <area> has no alt", "add alt to every <area>", "1.1.1"
                )
            )
        elif n.tag == "svg" and (n.get("role") or "").lower() == "img" and not accessible_name(n, root, ids):
            out.append(
                finding(
                    "high",
                    "svg.name_missing",
                    n,
                    '<svg role="img"> has no accessible name',
                    'add <title> as first child or aria-label; use aria-hidden="true" if decorative',
                    "1.1.1",
                )
            )
        elif n.tag in ("object", "embed") and not accessible_name(n, root, ids) and not text_content(n):
            out.append(
                finding(
                    "medium",
                    "object.name_missing",
                    n,
                    f"<{n.tag}> has no text alternative",
                    "add a title/aria-label and fallback content",
                    "1.1.1",
                )
            )

    # Links and buttons.
    for n in nodes:
        if is_hidden(n):
            continue
        role = (n.get("role") or "").split()
        role = role[0].lower() if role else ""
        if (n.tag == "a" and n.has("href")) or role == "link":
            name = accessible_name(n, root, ids)
            if not name:
                out.append(
                    finding(
                        "high",
                        "link.empty",
                        n,
                        f"link to {n.get('href', '')!r} has no accessible name",
                        "add link text, alt text on the image inside it, or aria-label",
                        "2.4.4, 4.1.2",
                    )
                )
            elif name.lower().strip(" .!>»→") in GENERIC_LINK_TEXT:
                out.append(
                    finding(
                        "low",
                        "link.generic_text",
                        n,
                        f"link text {name!r} does not say where it goes",
                        "make the text describe the target ('Read more about pricing') or add visually hidden text",
                        "2.4.4",
                    )
                )
            if (n.get("target") or "").lower() == "_blank" and "new" not in name.lower():
                out.append(
                    finding(
                        "info",
                        "link.new_window",
                        n,
                        "link opens a new window without saying so",
                        "add '(opens in a new tab)' to the text or a visually hidden span",
                        "3.2.5",
                    )
                )
        elif n.tag == "a" and not n.has("href") and n.has("onclick") and not role:
            out.append(
                finding(
                    "high",
                    "link.no_href",
                    n,
                    "<a> with onclick but no href is not focusable",
                    "use <button type='button'> for actions or add a real href for navigation",
                    "2.1.1",
                )
            )
        if (
            n.tag == "button"
            or role == "button"
            or (n.tag == "input" and (n.get("type") or "").lower() in ("button", "submit", "reset"))
        ):
            if not accessible_name(n, root, ids):
                out.append(
                    finding(
                        "high",
                        "button.empty",
                        n,
                        "button has no accessible name (icon-only?)",
                        "add visible text, aria-label, or visually hidden text inside the button",
                        "4.1.2",
                    )
                )

    # Form controls need labels.
    for n in nodes:
        if is_hidden(n) or n.tag not in ("input", "select", "textarea"):
            continue
        itype = (n.get("type") or "text").lower()
        if n.tag == "input" and itype in LABELLABLE_SKIP:
            continue
        if accessible_name(n, root, ids):
            if not labels_for(n, root) and not n.get("aria-labelledby") and n.get("title") and not n.get("aria-label"):
                out.append(
                    finding(
                        "low",
                        "form.title_only_label",
                        n,
                        "control is labelled only by title (tooltip)",
                        "use a visible <label for=...>",
                        "3.3.2",
                    )
                )
            continue
        hint = " (placeholder is not a label)" if n.get("placeholder") else ""
        out.append(
            finding(
                "high",
                "form.label_missing",
                n,
                f"<{n.tag}{' type=' + itype if n.tag == 'input' else ''}> has no label{hint}",
                "add <label for='id'>, wrap it in <label>, or use aria-labelledby pointing at visible text",
                "1.3.1, 4.1.2",
            )
        )
    for n in nodes:
        if n.tag == "label" and n.get("for") and n.get("for") not in ids:
            out.append(
                finding(
                    "medium",
                    "label.for_missing_target",
                    n,
                    f"<label for={n.get('for')!r}> points at no element",
                    "make for= match the control's id",
                    "1.3.1",
                )
            )

    # Headings.
    headings = [n for n in nodes if re.fullmatch(r"h[1-6]", n.tag) and not is_hidden(n)]
    headings += [n for n in nodes if (n.get("role") or "") == "heading" and not is_hidden(n)]
    order = {id(n): i for i, n in enumerate(nodes)}
    headings.sort(key=lambda n: order[id(n)])
    prev = 0
    h1s = 0
    for h in headings:
        level = heading_level(h)
        if level == 1:
            h1s += 1
        if not text_content(h, ids) and not accessible_name(h, root, ids):
            out.append(
                finding(
                    "high",
                    "heading.empty",
                    h,
                    f"empty <{h.tag}>",
                    "remove it or give it text; do not use headings for spacing",
                    "1.3.1, 2.4.6",
                )
            )
        if prev and level > prev + 1:
            out.append(
                finding(
                    "medium",
                    "heading.skipped_level",
                    h,
                    f"heading level jumps from h{prev} to h{level}",
                    f"use h{prev + 1} here (style it with CSS if it must look smaller)",
                    "1.3.1",
                )
            )
        prev = level
    if not is_fragment and headings and h1s == 0:
        out.append(
            finding(
                "low",
                "heading.no_h1",
                headings[0],
                "page has headings but no h1",
                "make the main page title an <h1>",
                "1.3.1, 2.4.6",
            )
        )
    if not is_fragment and not headings and any(n.tag == "body" for n in nodes):
        out.append(
            finding(
                "low",
                "heading.none",
                None,
                "page has no headings",
                "add an <h1> and section headings so screen reader users can navigate",
                "1.3.1, 2.4.6",
            )
        )

    # Duplicate ids and broken references.
    seen: dict = {}
    for n in nodes:
        nid = n.get("id")
        if nid:
            seen.setdefault(nid, []).append(n)
    referenced = set()
    for n in nodes:
        for attr in ("for", "aria-labelledby", "aria-describedby", "aria-controls", "headers"):
            referenced.update((n.get(attr) or "").split())
    for nid, group in seen.items():
        if len(group) > 1:
            sev = "high" if nid in referenced else "medium"
            out.append(
                finding(
                    sev,
                    "id.duplicate",
                    group[1],
                    f"id {nid!r} is used {len(group)} times (lines {', '.join(str(g.line) for g in group)})",
                    "make ids unique; labels and ARIA references pick the first one only",
                    "1.3.1, 4.1.2",
                )
            )

    # Focus order.
    for n in nodes:
        tab = (n.get("tabindex") or "").strip()
        if tab.lstrip("-").isdigit() and int(tab) > 0:
            out.append(
                finding(
                    "medium",
                    "tabindex.positive",
                    n,
                    f"tabindex={tab} changes the natural focus order",
                    'use tabindex="0" (or none) and fix the DOM order instead',
                    "2.4.3",
                )
            )

    # Frames.
    for n in nodes:
        if n.tag in ("iframe", "frame") and not is_hidden(n) and not (n.get("title") or "").strip():
            if n.get("aria-label") or n.get("aria-labelledby"):
                continue
            out.append(
                finding(
                    "high",
                    "iframe.title_missing",
                    n,
                    f"<{n.tag} src={n.get('src', '')!r}> has no title",
                    "add title describing the content, e.g. title='Map of our office'",
                    "4.1.2",
                )
            )

    # Data tables.
    for t in (n for n in nodes if n.tag == "table"):
        if (t.get("role") or "").lower() in ("presentation", "none"):
            continue
        cells = [c for c in t.iter() if c.tag in ("td", "th")]
        rows = [r for r in t.iter() if r.tag == "tr"]
        has_th = any(c.tag == "th" for c in cells) or any(
            (c.get("role") or "") in ("columnheader", "rowheader") for c in cells
        )
        if len(rows) >= 2 and len(cells) >= 4 and not has_th:
            out.append(
                finding(
                    "high",
                    "table.no_headers",
                    t,
                    f"data table ({len(rows)} rows) has no <th> header cells",
                    'mark header cells as <th scope="col"> / <th scope="row">, or role="presentation" for '
                    "layout tables",
                    "1.3.1",
                )
            )
        if any(c.tag == "th" for c in cells) and not any(c.tag == "caption" for c in t.iter()):
            if not t.get("aria-label") and not t.get("aria-labelledby"):
                out.append(
                    finding(
                        "info",
                        "table.no_caption",
                        t,
                        "data table has no <caption>",
                        "add a <caption> that names the table",
                        "1.3.1",
                    )
                )

    # Media.
    for n in nodes:
        if n.tag not in ("video", "audio"):
            continue
        if n.has("autoplay") and not n.has("muted"):
            out.append(
                finding(
                    "high",
                    "media.autoplay_sound",
                    n,
                    f"<{n.tag} autoplay> plays sound automatically",
                    "remove autoplay, or add muted; provide a pause/stop and volume control",
                    "1.4.2",
                )
            )
        elif n.has("autoplay") and n.tag == "video" and not n.has("controls"):
            out.append(
                finding(
                    "medium",
                    "media.autoplay_no_controls",
                    n,
                    "auto-playing video has no controls",
                    "add controls or a visible pause button (moving content longer than 5s needs pause)",
                    "2.2.2",
                )
            )
        if n.tag == "video" and not any(
            c.tag == "track" and (c.get("kind") or "subtitles") in ("captions", "subtitles") for c in n.iter()
        ):
            out.append(
                finding(
                    "medium",
                    "media.no_captions",
                    n,
                    "<video> has no captions <track>",
                    'add <track kind="captions" src="..." srclang="en" label="English"> (skip if the video '
                    "has no speech)",
                    "1.2.2",
                )
            )
    for n in nodes:
        if n.tag in ("marquee", "blink"):
            out.append(
                finding(
                    "high",
                    "element.moving_content",
                    n,
                    f"<{n.tag}> moves or blinks with no way to stop it",
                    "remove it; use static text",
                    "2.2.2",
                )
            )

    # Landmarks.
    if not is_fragment and not any(n.tag == "main" or (n.get("role") or "") == "main" for n in nodes):
        out.append(
            finding(
                "low",
                "landmark.main_missing",
                None,
                "page has no <main> landmark",
                "wrap the primary content in <main> (one per page)",
                "1.3.1, 2.4.1",
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Audit HTML files for common WCAG 2.2 A/AA failures: alt text, empty links and buttons, "
        "form labels, heading order, lang, title, duplicate ids, positive tabindex, iframe titles, "
        "table headers, autoplay media, zoom blocking.",
        epilog="Exit codes: 0 = no findings at/above --fail-on, 1 = findings, 2 = error. "
        "Static checks only: confirm with a browser, keyboard and screen reader.",
    )
    p.add_argument("paths", nargs="+", help="HTML files, folders (scanned for *.html/*.htm) or - for stdin")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--fail-on", default="medium", choices=[*SEVERITIES, "never"], help="default: medium")
    p.add_argument("--ignore", action="append", default=[], help="rule id to skip (repeatable), e.g. link.new_window")
    args = p.parse_args(argv)
    try:
        inputs = read_inputs(args.paths)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = [(label, [f for f in audit(text) if f["rule"] not in args.ignore]) for label, text in inputs]
    return report(results, args.json, args.fail_on, "wcag-html-audit")


if __name__ == "__main__":
    sys.exit(main())
