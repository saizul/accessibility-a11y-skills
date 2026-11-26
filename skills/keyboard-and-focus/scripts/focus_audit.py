#!/usr/bin/env python3
"""Static keyboard and focus audit for HTML (and CSS) files (offline, read-only).

Checks: positive tabindex; tabindex=-1 on visible links/buttons; click handlers on
non-interactive elements (onclick, @click, v-on:click, (click), ng-click) without role,
tabindex or key handlers; hover-only and double-click handlers; autofocus; accesskey;
outline:none in inline styles, <style> blocks and CSS files without a visible
replacement; sticky headers without scroll-padding (focus obscured, 2.4.11); targets
under 24x24px in inline styles (2.5.8); skip link presence and broken in-page targets;
custom dialogs to test for traps. --order prints the predicted Tab sequence.

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


CLICK_ATTRS = ("onclick", "@click", "v-on:click", "(click)", "ng-click", "x-on:click", "on:click")
INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea", "summary", "details", "label", "option", "iframe"}
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
}


def natively_focusable(n: Node) -> bool:
    if n.has("disabled"):
        return False
    if n.tag in ("a", "area"):
        return n.has("href")
    if n.tag == "input":
        return (n.get("type") or "").lower() != "hidden"
    if n.tag in ("button", "select", "textarea", "iframe", "summary"):
        return True
    if n.tag in ("audio", "video"):
        return n.has("controls")
    return (n.get("contenteditable") or "false").lower() in ("", "true", "plaintext-only")


def tabindex(n: Node) -> int | None:
    raw = (n.get("tabindex") or "").strip()
    return int(raw) if raw.lstrip("-").isdigit() else None


def tab_order(root: Node) -> list[Node]:
    """Sequential focus order: positive tabindex first (ascending), then DOM order."""
    items = []
    for i, n in enumerate(root.iter()):
        if is_hidden(n) or n.has("inert") or any(a.has("inert") for a in n.ancestors()):
            continue
        t = tabindex(n)
        if t is not None and t < 0:
            continue
        if natively_focusable(n) or t is not None:
            items.append((0 if (t or 0) > 0 else 1, t or 0, i, n))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in items]


def css_rules(css: str):
    """Yield (selector, declarations dict, line) from CSS, flattening @media/@supports."""
    css = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
    stack: list[tuple[str, int]] = []
    start = 0
    for i, ch in enumerate(css):
        if ch == "{":
            stack.append((css[start:i].strip(), i))
            start = i + 1
        elif ch == "}":
            if stack:
                selector, open_at = stack.pop()
                body = css[open_at + 1 : i]
                if "{" not in body and not selector.startswith("@"):
                    decls = {}
                    for d in body.split(";"):
                        if ":" in d:
                            k, v = d.split(":", 1)
                            decls[k.strip().lower()] = v.strip().lower()
                    yield selector.split(";")[-1].strip(), decls, css.count("\n", 0, open_at) + 1
            start = i + 1
        elif ch == ";" and not stack:
            start = i + 1


def removes_outline(decls: dict) -> bool:
    for key in ("outline", "outline-style", "outline-width"):
        v = decls.get(key, "").replace("!important", "").strip()
        if v in ("none", "0", "0px", "none 0", "0 none") or (key == "outline" and re.match(r"^(none|0(px)?)\b", v)):
            return True
    return False


def has_replacement(decls: dict) -> bool:
    if any(k.startswith("outline") and not removes_outline({k: v}) for k, v in decls.items()):
        return True
    shadow = decls.get("box-shadow", "")
    if shadow and shadow != "none":
        return True
    return any(k.startswith("border") or k in ("background", "background-color", "text-decoration") for k in decls)


def audit_css(css: str, label: str) -> list[dict]:
    out = []
    rules = list(css_rules(css))
    visible_rules = [d for sel, d, _ in rules if ":focus-visible" in sel and not removes_outline(d)]
    for sel, decls, line in rules:
        if ":focus" not in sel or not removes_outline(decls):
            continue
        if has_replacement(decls):
            continue
        if ":focus-visible" not in sel and ":not(:focus-visible)" not in sel and visible_rules:
            sev, extra = "low", " (a :focus-visible rule exists; check it covers these elements)"
        elif ":not(:focus-visible)" in sel:
            continue
        else:
            sev, extra = "high", ""
        out.append(
            {
                "severity": sev,
                "rule": "css.focus_outline_removed",
                "wcag": "2.4.7",
                "line": line,
                "element": f"{label}: {' '.join(sel.split())[:80]}",
                "message": f"focus outline removed with no visible replacement{extra}",
                "fix": "keep the outline, or replace it in :focus-visible with outline: 3px solid <colour "
                "with 3:1 contrast>",
            }
        )
    fixed = [(sel, line) for sel, d, line in rules if d.get("position", "").startswith(("fixed", "sticky"))]
    pads = any("scroll-padding" in k for _, d, _ in rules for k in d)
    if fixed and not pads:
        sel, line = fixed[0]
        out.append(
            {
                "severity": "info",
                "rule": "css.sticky_may_obscure_focus",
                "wcag": "2.4.11",
                "line": line,
                "element": f"{label}: {sel[:80]}",
                "message": "fixed/sticky element and no scroll-padding: focused items may hide underneath it",
                "fix": "add html { scroll-padding-top: <header height> } (and bottom for sticky footers); "
                "tab through to verify",
            }
        )
    return out


def audit(text: str, extra_css: list[tuple[str, str]] | None = None) -> list[dict]:
    root = parse_html(text)
    ids = id_map(root)
    nodes = list(root.iter())
    out: list[dict] = []

    for n in nodes:
        t = tabindex(n)
        role = ((n.get("role") or "").split() or [""])[0].lower()
        if t is not None and t > 0:
            out.append(
                finding(
                    "medium",
                    "tabindex.positive",
                    n,
                    f"tabindex={t} jumps ahead of the page order",
                    'use tabindex="0" and put the element where it belongs in the DOM',
                    "2.4.3",
                )
            )
        if t is not None and t < 0 and natively_focusable(n) and not is_hidden(n) and role not in INTERACTIVE_ROLES:
            if not any(
                (a.get("role") or "")
                in ("tablist", "menu", "menubar", "listbox", "toolbar", "tree", "grid", "radiogroup")
                for a in n.ancestors()
            ):
                out.append(
                    finding(
                        "medium",
                        "tabindex.removed_from_order",
                        n,
                        f"tabindex={t} removes a visible {n.tag} from the keyboard order",
                        "remove tabindex unless it is part of a roving-tabindex widget or is also hidden",
                        "2.1.1",
                    )
                )
        clicky = [a for a in CLICK_ATTRS if n.has(a)]
        if (
            clicky
            and n.tag not in INTERACTIVE_TAGS
            and role not in INTERACTIVE_ROLES
            and n.tag not in ("body", "html", "form")
        ):
            if t is None:
                out.append(
                    finding(
                        "high",
                        "click.not_keyboard_accessible",
                        n,
                        f"<{n.tag}> has a click handler ({clicky[0]}) but no role or tabindex: mouse-only",
                        "use <button type='button'> (or <a href> for navigation); a div needs role, "
                        "tabindex=0 and Enter/Space handlers",
                        "2.1.1, 4.1.2",
                    )
                )
            else:
                out.append(
                    finding(
                        "medium",
                        "click.no_role",
                        n,
                        f"focusable <{n.tag}> with a click handler has no role",
                        "add role='button' and Enter/Space key handling, or better, use <button>",
                        "4.1.2",
                    )
                )
        if clicky and role in INTERACTIVE_ROLES and not natively_focusable(n) and t is None:
            out.append(
                finding(
                    "high",
                    "click.role_not_focusable",
                    n,
                    f'role="{role}" with a click handler but no tabindex',
                    'add tabindex="0" and key handlers, or use the native element',
                    "2.1.1",
                )
            )
        if clicky and role in ("button", "link") and n.tag not in INTERACTIVE_TAGS:
            keys = any(
                n.has(k)
                for k in ("onkeydown", "onkeyup", "onkeypress", "@keydown", "v-on:keydown", "(keydown)", "@keyup")
            )
            if not keys:
                out.append(
                    finding(
                        "low",
                        "click.no_key_handler",
                        n,
                        f'custom role="{role}" has a click handler but no key handler in markup',
                        "make sure Enter (and Space for buttons) triggers it; a native <button> does this for free",
                        "2.1.1",
                    )
                )
        if (n.has("onmouseover") or n.has("onmouseenter")) and not (n.has("onfocus") or n.has("onfocusin")):
            out.append(
                finding(
                    "low",
                    "mouse.hover_only",
                    n,
                    "hover handler without a matching focus handler",
                    "show the same content on focus (onfocus/onfocusin) and let Escape dismiss it",
                    "2.1.1, 1.4.13",
                )
            )
        if n.has("ondblclick"):
            out.append(
                finding(
                    "medium",
                    "mouse.dblclick",
                    n,
                    "double-click action has no keyboard equivalent in markup",
                    "provide a button or key shortcut for the same action",
                    "2.1.1",
                )
            )
        if n.has("autofocus") and n.tag != "dialog" and not any(a.tag == "dialog" for a in n.ancestors()):
            out.append(
                finding(
                    "low",
                    "focus.autofocus",
                    n,
                    "autofocus moves focus on page load; screen reader users miss the content before it",
                    "remove autofocus except on single-purpose pages (search, login) or inside dialogs",
                    "2.4.3, 3.2.1",
                )
            )
        if n.has("accesskey"):
            out.append(
                finding(
                    "info",
                    "focus.accesskey",
                    n,
                    f"accesskey={n.get('accesskey')!r} may clash with browser and screen reader shortcuts",
                    "document it, or offer remappable shortcuts (2.1.4)",
                    "2.1.4",
                )
            )
        style = (n.get("style") or "").replace(" ", "").lower()
        if "outline:none" in style or "outline:0" in style:
            out.append(
                finding(
                    "medium",
                    "focus.inline_outline_none",
                    n,
                    "inline style removes the focus outline",
                    "remove outline:none or provide a visible :focus-visible style",
                    "2.4.7",
                )
            )
        if (natively_focusable(n) or role in INTERACTIVE_ROLES) and n.tag != "input":
            w = re.search(r"(?<![-\w])width:(\d+(?:\.\d+)?)px", style)
            h = re.search(r"(?<![-\w])height:(\d+(?:\.\d+)?)px", style)
            if (w and float(w.group(1)) < 24) or (h and float(h.group(1)) < 24):
                out.append(
                    finding(
                        "low",
                        "target.too_small",
                        n,
                        "target is smaller than 24x24 CSS px (inline style)",
                        "make it at least 24x24px, or leave 24px spacing around it",
                        "2.5.8",
                    )
                )

    # Skip link and bypass blocks.
    order = tab_order(root)
    body = next((n for n in nodes if n.tag == "body"), None)
    links_before_main = 0
    main = next((n for n in nodes if n.tag == "main" or (n.get("role") or "") == "main"), None)
    if main is not None:
        in_order = {id(n) for n in order}
        for n in nodes:
            if n is main:
                break
            if id(n) in in_order:
                links_before_main += 1
    first = order[0] if order else None
    skip = None
    for n in order[:3]:
        href = n.get("href") or ""
        if n.tag == "a" and href.startswith("#") and len(href) > 1:
            name = accessible_name(n, root, ids).lower()
            if "skip" in name or "main" in name or "content" in name:
                skip = n
                break
    for n in nodes:
        href = n.get("href") or ""
        if n.tag == "a" and href.startswith("#") and len(href) > 1 and href[1:] not in ids:
            if href == "#top" or any(x.get("name") == href[1:] for x in nodes):
                continue
            sev = "high" if n is skip or "skip" in accessible_name(n, root, ids).lower() else "medium"
            out.append(
                finding(
                    sev,
                    "link.fragment_target_missing",
                    n,
                    f"in-page link {href} points at no element",
                    f'add id="{href[1:]}" to the target (e.g. <main id="{href[1:]}">)',
                    "2.4.1",
                )
            )
    if body is not None and skip is None and links_before_main >= 5:
        out.append(
            finding(
                "medium",
                "bypass.no_skip_link",
                first,
                f"{links_before_main} focusable elements before <main> and no skip link",
                'add <a class="skip-link" href="#main">Skip to main content</a> as the first focusable element',
                "2.4.1",
            )
        )
    if body is not None and main is None:
        out.append(
            finding(
                "low",
                "bypass.no_main",
                None,
                "no <main> landmark for screen reader users to jump to",
                "wrap the page content in <main id='main'>",
                "2.4.1",
            )
        )

    # Dialogs to test for traps and focus return.
    for n in nodes:
        if n.tag == "dialog" or (n.get("role") or "") in ("dialog", "alertdialog"):
            if n.tag != "dialog" and (n.get("aria-modal") or "") != "true":
                out.append(
                    finding(
                        "info",
                        "dialog.manual_check",
                        n,
                        "custom dialog without aria-modal: verify focus moves in, stays in, Escape closes, "
                        "focus returns",
                        "prefer <dialog> with showModal(); see accessible-components",
                        "2.1.2, 2.4.3",
                    )
                )

    # CSS from <style> blocks and extra files.
    styles = [
        ("inline <style>", "".join(c for c in n.children if isinstance(c, str))) for n in nodes if n.tag == "style"
    ]
    for label, css in [*styles, *(extra_css or [])]:
        out += audit_css(css, label)
    return out


def focus_order_listing(text: str) -> list[dict]:
    root = parse_html(text)
    ids = id_map(root)
    return [
        {
            "index": i + 1,
            "line": n.line,
            "element": n.describe(),
            "tabindex": tabindex(n),
            "name": (accessible_name(n, root, ids) or text_content(n, ids))[:80],
        }
        for i, n in enumerate(tab_order(root))
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Static keyboard and focus audit: positive tabindex, mouse-only click handlers, removed focus "
        "outlines (HTML and CSS), skip links and broken in-page targets, autofocus, small targets, dialogs to test.",
        epilog="Exit codes: 0 = no findings at/above --fail-on, 1 = findings, 2 = error. Always finish with a real "
        "Tab-key walkthrough: the script cannot run JavaScript.",
    )
    p.add_argument("paths", nargs="+", help="HTML files, folders or - for stdin")
    p.add_argument(
        "--css", action="append", default=[], help="extra CSS file to check for outline removal (repeatable)"
    )
    p.add_argument("--order", action="store_true", help="print the predicted Tab order instead of findings")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--fail-on", default="medium", choices=[*SEVERITIES, "never"], help="default: medium")
    p.add_argument("--ignore", action="append", default=[], help="rule id to skip (repeatable)")
    args = p.parse_args(argv)
    try:
        inputs = read_inputs(args.paths)
        css = [(c, Path(c).read_text(encoding="utf-8")) for c in args.css]
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    if args.order:
        listing = {label: focus_order_listing(text) for label, text in inputs}
        if args.json:
            print(json.dumps(listing, indent=2))
        else:
            for label, items in listing.items():
                print(f"Tab order: {label}")
                for it in items:
                    tab = f" tabindex={it['tabindex']}" if it["tabindex"] is not None else ""
                    print(f"  {it['index']:3}. line {it['line']:<5} {it['element']}{tab}  {it['name']!r}")
        return 0
    results = []
    for i, (label, text) in enumerate(inputs):
        fs = audit(text, css if i == 0 else None)
        results.append((label, [f for f in fs if f["rule"] not in args.ignore]))
    return report(results, args.json, args.fail_on, "keyboard-and-focus")


if __name__ == "__main__":
    sys.exit(main())
