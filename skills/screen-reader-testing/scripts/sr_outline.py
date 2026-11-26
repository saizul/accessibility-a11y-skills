#!/usr/bin/env python3
"""Predict what a screen reader announces for an HTML page and write a test script (offline).

Lists the page title and language, landmarks, heading outline, links, form controls and
buttons with name, role and states (required, checked, expanded, invalid), images (alt or
decorative), and live regions. --format markdown writes a pre-filled NVDA + VoiceOver test
script with the expected announcements, ready to fill in during a manual test session.

Uses a simplified accessible-name computation from the HTML source: verify with a real
screen reader and the browser's accessibility tree.

Exit codes: 0 = no basic problems, 1 = unnamed controls/images or missing title/lang/main, 2 = error.
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


LANDMARK_TAGS = {"main": "main", "nav": "navigation", "aside": "complementary", "search": "search"}
LANDMARK_ROLES = {"banner", "complementary", "contentinfo", "form", "main", "navigation", "region", "search"}
CONTROL_ROLES = {
    "button",
    "link",
    "checkbox",
    "radio",
    "switch",
    "tab",
    "menuitem",
    "option",
    "slider",
    "spinbutton",
    "textbox",
    "searchbox",
    "combobox",
    "listbox",
}
LIVE_ROLES = {"alert": "assertive", "status": "polite", "log": "polite", "timer": "off", "marquee": "off"}


def landmark_role(n: Node) -> str:
    role = ((n.get("role") or "").split() or [""])[0].lower()
    if role:
        return role if role in LANDMARK_ROLES else ""
    if n.tag in LANDMARK_TAGS:
        return LANDMARK_TAGS[n.tag]
    sectioning = {"article", "aside", "main", "nav", "section"}
    if n.tag == "header" and not any(a.tag in sectioning for a in n.ancestors()):
        return "banner"
    if n.tag == "footer" and not any(a.tag in sectioning for a in n.ancestors()):
        return "contentinfo"
    if n.tag in ("section", "form") and (n.get("aria-label") or n.get("aria-labelledby")):
        return "region" if n.tag == "section" else "form"
    return ""


def control_role(n: Node) -> str:
    role = ((n.get("role") or "").split() or [""])[0].lower()
    if role:
        return role if role in CONTROL_ROLES else ""
    itype = (n.get("type") or "text").lower()
    if n.tag == "a" and n.has("href"):
        return "link"
    if n.tag == "button":
        return "button"
    if n.tag == "select":
        return "listbox" if n.has("multiple") else "combobox"
    if n.tag == "textarea":
        return "textbox"
    if n.tag == "input":
        return {
            "checkbox": "checkbox",
            "radio": "radio",
            "range": "slider",
            "number": "spinbutton",
            "search": "searchbox",
            "submit": "button",
            "reset": "button",
            "button": "button",
            "image": "button",
            "hidden": "",
        }.get(itype, "textbox")
    return ""


def outline(text: str) -> dict:
    root = parse_html(text)
    ids = id_map(root)
    nodes = [n for n in root.iter() if not is_hidden(n)]
    html = next((n for n in root.iter() if n.tag == "html"), None)
    title = next((n for n in root.iter() if n.tag == "title" and not any(a.tag == "svg" for a in n.ancestors())), None)
    data: dict = {
        "title": text_content(title) if title is not None else "",
        "lang": (html.get("lang") or "") if html is not None else "",
        "landmarks": [],
        "headings": [],
        "links": [],
        "controls": [],
        "images": [],
        "live_regions": [],
        "problems": [],
    }
    for n in nodes:
        lm = landmark_role(n)
        if lm:
            data["landmarks"].append({"role": lm, "name": accessible_name(n, root, ids), "line": n.line})
        if re.fullmatch(r"h[1-6]", n.tag) or (n.get("role") or "") == "heading":
            level = heading_level(n)
            data["headings"].append({"level": level, "text": accessible_name(n, root, ids), "line": n.line})
        role = control_role(n)
        if role:
            name = accessible_name(n, root, ids)
            entry = {"role": role, "name": name, "line": n.line, "element": n.describe()}
            states = []
            if n.has("required") or (n.get("aria-required") or "") == "true":
                states.append("required")
            if n.has("disabled") or (n.get("aria-disabled") or "") == "true":
                states.append("dimmed")
            if n.has("checked") or (n.get("aria-checked") or "") == "true":
                states.append("checked")
            if n.get("aria-expanded") in ("true", "false"):
                states.append("expanded" if n.get("aria-expanded") == "true" else "collapsed")
            if n.get("aria-pressed") in ("true", "false"):
                states.append("pressed" if n.get("aria-pressed") == "true" else "not pressed")
            if (n.get("aria-invalid") or "") == "true":
                states.append("invalid entry")
            entry["states"] = states
            desc = " ".join(text_content(ids[d], ids) for d in (n.get("aria-describedby") or "").split() if d in ids)
            if desc:
                entry["description"] = desc
            (data["links"] if role == "link" else data["controls"]).append(entry)
            if not name:
                data["problems"].append(
                    f"line {n.line}: {role} {n.describe()} has no name (announced as just '{role}')"
                )
        if n.tag == "img" or (n.get("role") or "") == "img":
            alt = n.get("alt")
            data["images"].append(
                {
                    "alt": alt,
                    "name": accessible_name(n, root, ids),
                    "decorative": alt == "" and not n.get("aria-label"),
                    "line": n.line,
                    "src": n.get("src") or "",
                }
            )
            if alt is None and not accessible_name(n, root, ids):
                data["problems"].append(
                    f"line {n.line}: image {n.get('src', '')!r} has no alt (screen readers may read the file name)"
                )
        live = (n.get("aria-live") or "").lower() or LIVE_ROLES.get((n.get("role") or "").lower(), "")
        if (live and live != "off") or n.tag == "output":
            data["live_regions"].append({"politeness": live or "polite", "element": n.describe(), "line": n.line})
    if not data["title"]:
        data["problems"].append("page has no <title>: the tab and window announce nothing useful")
    if html is not None and not data["lang"]:
        data["problems"].append("<html> has no lang: the speech synthesizer may use the wrong voice")
    if not any(lm["role"] == "main" for lm in data["landmarks"]):
        data["problems"].append("no main landmark: users cannot jump to the content (D / R / rotor)")
    return data


def as_text(label: str, d: dict) -> str:
    lines = [
        f"Screen reader outline: {label}",
        f"  title: {d['title']!r}  lang: {d['lang'] or '(none)'}",
        "",
        "Landmarks:",
    ]
    lines += [
        f"  - {lm['role']}" + (f" '{lm['name']}'" if lm["name"] else "") + f" (line {lm['line']})"
        for lm in d["landmarks"]
    ] or ["  (none)"]
    lines += ["", "Headings:"]
    lines += [f"  {'  ' * (h['level'] - 1)}h{h['level']} {h['text'] or '(empty)'}" for h in d["headings"]] or [
        "  (none)"
    ]
    lines += ["", f"Links ({len(d['links'])}):"]
    lines += [f"  - {lk['name'] or '(no name)'}" for lk in d["links"][:60]]
    if len(d["links"]) > 60:
        lines.append(f"  ... {len(d['links']) - 60} more")
    lines += ["", f"Form controls and buttons ({len(d['controls'])}):"]
    for c in d["controls"]:
        st = (", " + ", ".join(c["states"])) if c["states"] else ""
        desc = f" - {c['description']}" if c.get("description") else ""
        lines.append(f"  - {c['name'] or '(no name)'}, {c['role']}{st}{desc}")
    lines += ["", f"Images ({len(d['images'])}):"]
    for im in d["images"]:
        lines.append(f"  - {'(decorative, skipped)' if im['decorative'] else repr(im['name'] or im['src'])}")
    lines += ["", "Live regions:"]
    lines += [f"  - {lr['element']} aria-live={lr['politeness']}" for lr in d["live_regions"]] or ["  (none)"]
    if d["problems"]:
        lines += ["", "Problems a screen reader user will hit:"] + [f"  ! {p}" for p in d["problems"]]
    return "\n".join(lines) + "\n"


def as_markdown(label: str, d: dict) -> str:
    """A manual test script for NVDA and VoiceOver, pre-filled with this page's expectations."""
    out = [
        f"# Screen reader test script: {d['title'] or label}",
        "",
        f"Source: `{label}`. Tester: ______  Date: ______  Browser/SR: ______",
        "",
        "Mark each step Pass / Fail / Note. Expected values come from the page source; a mismatch is a finding.",
        "",
        "| # | Task | NVDA (Windows, Chrome/Firefox) | VoiceOver (macOS, Safari) | Expected | Result |",
        "| --- | --- | --- | --- | --- | --- |",
        f'| 1 | Page title announced on load | `NVDA+T` | `VO+F2` (twice) | "{d["title"] or "(missing!)"}" | |',
        f"| 2 | Language/voice is correct | listen | listen | lang `{d['lang'] or '(missing!)'}` | |",
    ]
    n = 3
    lm_list = ", ".join(lm["role"] + (f" '{lm['name']}'" if lm["name"] else "") for lm in d["landmarks"]) or "(none!)"
    out.append(f"| {n} | List landmarks | `NVDA+F7` > Landmarks, or `D` | `VO+U` > Landmarks | {lm_list} | |")
    n += 1
    hd = "; ".join(f"h{h['level']} {h['text'][:40]}" for h in d["headings"][:12]) or "(none!)"
    out.append(f"| {n} | Move through headings | `H` / `1`-`6` | `VO+Cmd+H` | {hd} | |")
    n += 1
    out.append(
        f"| {n} | List links; every name makes sense alone | `NVDA+F7` > Links | `VO+U` > Links | "
        f"{len(d['links'])} links, none unnamed or 'click here' | |"
    )
    n += 1
    if d["controls"]:
        out.append(
            f"| {n} | Tab through every control; name, role, state read | `Tab` | `Tab` (enable full "
            "keyboard access) | see table below | |"
        )
        n += 1
        out.append(
            f"| {n} | Fill the form in forms/focus mode; errors announced | `Enter` on field, `NVDA+Space` "
            "toggles mode | `VO+Shift+Down` into group | errors read when they appear | |"
        )
        n += 1
    if d["images"]:
        out.append(
            f"| {n} | Images: meaningful ones described, decorative skipped | `G` | `VO+Cmd+G` | see images below | |"
        )
        n += 1
    if d["live_regions"]:
        out.append(
            f"| {n} | Trigger each status message; it is announced without moving focus | act | act | "
            f"{len(d['live_regions'])} live region(s) | |"
        )
        n += 1
    out.append(
        f"| {n} | Read whole page; reading order matches visual order | `NVDA+Down` (say all) | `VO+A` | no "
        "hidden or duplicated text | |"
    )
    out += ["", "## Controls (expected announcement)", "", "| Line | Expected | Result |", "| --- | --- | --- |"]
    for c in d["controls"]:
        st = (", " + ", ".join(c["states"])) if c["states"] else ""
        out.append(f"| {c['line']} | {c['name'] or '**(no name)**'}, {c['role']}{st} | |")
    if d["images"]:
        out += ["", "## Images", "", "| Line | Expected | Result |", "| --- | --- | --- |"]
        for im in d["images"]:
            out.append(
                f"| {im['line']} | {'skipped (decorative)' if im['decorative'] else (im['name'] or '**no alt**')} | |"
            )
    if d["problems"]:
        out += ["", "## Known problems from the source", ""] + [f"- {p}" for p in d["problems"]]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Show what a screen reader exposes on a page (landmarks, headings, links, controls with "
        "name/role/state, images, live regions) and generate a pre-filled NVDA/VoiceOver test script.",
        epilog="Exit codes: 0 = no unnamed controls or missing basics, 1 = problems found, 2 = error. "
        "This predicts announcements from source; it does not replace testing with a real screen reader.",
    )
    p.add_argument("paths", nargs="+", help="HTML files, folders or - for stdin")
    p.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="default: text")
    p.add_argument("--json", action="store_true", help="same as --format json")
    args = p.parse_args(argv)
    try:
        inputs = read_inputs(args.paths)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    fmt = "json" if args.json else args.format
    results = [(label, outline(text)) for label, text in inputs]
    if fmt == "json":
        print(json.dumps([{"file": label, **d} for label, d in results], indent=2))
    else:
        render = as_markdown if fmt == "markdown" else as_text
        print("\n".join(render(label, d) for label, d in results), end="")
    return 1 if any(d["problems"] for _, d in results) else 0


if __name__ == "__main__":
    sys.exit(main())
