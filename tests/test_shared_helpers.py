"""The DOM helpers are copied into each script so a skill folder works on its own.
These tests keep the copies identical and check the parser on messy HTML."""

import re

import pytest

from conftest import SKILLS, load_script

BLOCK = re.compile(r"# --- begin shared dom helpers.*?# --- end shared dom helpers ---", re.S)
SCRIPTS = [
    ("wcag-html-audit", "html_audit.py"),
    ("aria-review", "aria_lint.py"),
    ("keyboard-and-focus", "focus_audit.py"),
    ("accessible-forms", "forms_check.py"),
    ("screen-reader-testing", "sr_outline.py"),
]


def test_shared_blocks_are_identical():
    blocks = {}
    for skill, script in SCRIPTS:
        text = (SKILLS / skill / "scripts" / script).read_text()
        match = BLOCK.search(text)
        assert match, f"{skill}/{script} has no shared helper block"
        blocks[script] = match.group(0)
    assert len(set(blocks.values())) == 1, "shared dom helper blocks differ; copy the updated block to every script"


m = load_script("wcag-html-audit", "html_audit.py")


def test_parser_handles_unclosed_and_void_tags():
    root = m.parse_html("<ul><li>One<li>Two</ul><p>A<p>B<br><img src=x alt=y>")
    tags = [n.tag for n in root.iter()]
    assert tags == ["ul", "li", "li", "p", "p", "br", "img"]
    lis = [n for n in root.iter() if n.tag == "li"]
    assert all(li.parent.tag == "ul" for li in lis)


def test_stray_end_tags_are_ignored():
    root = m.parse_html("<div><span>x</div></span><p>y</p>")
    assert [n.tag for n in root.iter()] == ["div", "span", "p"]
    assert next(n for n in root.iter() if n.tag == "p").parent.tag == "#root"


@pytest.mark.parametrize(
    "html,name",
    [
        ('<button aria-label="Close dialog">X</button>', "Close dialog"),
        ('<button aria-labelledby="a b">X</button><span id="a">Save</span><span id="b">draft</span>', "Save draft"),
        ("<button><img src='x' alt='Print'> </button>", "Print"),
        ('<a href="/"><span aria-hidden="true">*</span>Home</a>', "Home"),
        ('<label for="i">Email</label><input id="i">', "Email"),
        ("<label>Phone <input></label>", "Phone"),
        ('<input type="submit">', "Submit"),
        ('<input type="button" value="Go">', "Go"),
        ('<input title="Tooltip only">', "Tooltip only"),
        ("<a href='/'><svg><title>Logo</title></svg></a>", "Logo"),
        ('<div role="button">Press <b>me</b></div>', "Press me"),
        ("<div>Not named from content</div>", ""),
    ],
)
def test_accessible_name(html, name):
    root = m.parse_html(html)
    ids = m.id_map(root)
    node = next(root.iter())
    assert m.accessible_name(node, root, ids) == name


def test_is_hidden_variants():
    root = m.parse_html(
        '<div hidden><a id="a"></a></div><div style="display: none"><a id="b"></a></div>'
        '<div aria-hidden="true"><a id="c"></a></div><a id="d"></a><input id="e" type="hidden">'
    )
    ids = m.id_map(root)
    assert [m.is_hidden(ids[k]) for k in "abcde"] == [True, True, True, False, True]


def test_heading_level():
    root = m.parse_html(
        '<h3>x</h3><div role="heading" aria-level="4">y</div><div role="heading" aria-level="x">z</div>'
    )
    assert [m.heading_level(n) for n in root.iter()] == [3, 4, 2]
