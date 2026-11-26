import json

import pytest

from conftest import CSS, HTML, load_script, page, rules, run_script

SKILL, SCRIPT = "keyboard-and-focus", "focus_audit.py"
m = load_script(SKILL, SCRIPT)


def test_good_page_is_clean():
    assert m.audit((HTML / "good_page.html").read_text()) == []


def test_bad_fixture():
    found = rules(m.audit((HTML / "focus_bad.html").read_text()))
    expected = {
        "css.focus_outline_removed",
        "css.sticky_may_obscure_focus",
        "link.fragment_target_missing",
        "click.not_keyboard_accessible",
        "click.no_role",
        "click.no_key_handler",
        "tabindex.removed_from_order",
        "tabindex.positive",
        "mouse.dblclick",
        "mouse.hover_only",
        "focus.inline_outline_none",
        "focus.autofocus",
        "focus.accesskey",
        "target.too_small",
        "dialog.manual_check",
        "bypass.no_skip_link",
    }
    assert expected <= found, expected - found


@pytest.mark.parametrize(
    "snippet,rule",
    [
        ('<div onclick="x()">Open</div>', "click.not_keyboard_accessible"),
        ('<img src="a.png" alt="Zoom" @click="zoom">', "click.not_keyboard_accessible"),
        ('<li v-on:click="pick">A</li>', "click.not_keyboard_accessible"),
        ('<td (click)="sort()">Name</td>', "click.not_keyboard_accessible"),
        ('<span ng-click="go()">Go</span>', "click.not_keyboard_accessible"),
        ('<div role="button" onclick="x()">Open</div>', "click.role_not_focusable"),
        ('<button tabindex="1">A</button>', "tabindex.positive"),
        ('<button tabindex="-1">Hidden from tab</button>', "tabindex.removed_from_order"),
        ('<a href="#nowhere">Jump</a>', "link.fragment_target_missing"),
        ('<input aria-label="q" autofocus>', "focus.autofocus"),
        ('<a href="/" style="outline:0">Home</a>', "focus.inline_outline_none"),
        ('<button style="width: 20px; height: 20px" aria-label="Close">x</button>', "target.too_small"),
        ('<div onmouseenter="tip()">?</div>', "mouse.hover_only"),
    ],
)
def test_single_rules(snippet, rule):
    assert rule in rules(m.audit(page(snippet)))


@pytest.mark.parametrize(
    "snippet",
    [
        '<button type="button" onclick="x()">Open</button>',
        '<a href="/x" onclick="track()">Go</a>',
        '<div role="button" tabindex="0" onclick="x()" onkeydown="k(event)">Open</div>',
        '<div role="tablist"><button role="tab" tabindex="-1">B</button></div>',
        '<a href="#main">Skip</a>',
        '<a href="#top">Top</a>',
        '<a name="faq"></a><a href="#faq">FAQ</a>',
        '<dialog><input aria-label="Name" autofocus></dialog>',
        '<div onmouseover="tip()" onfocus="tip()" tabindex="0">?</div>',
        '<form onclick="x()"><button>Send</button></form>',
        '<button style="width: 44px; height: 44px" aria-label="Close">x</button>',
        '<div hidden><button tabindex="-1">x</button></div>',
    ],
)
def test_no_false_positives(snippet):
    found = [f for f in m.audit(page(snippet)) if f["severity"] in ("high", "medium")]
    assert found == [], found


@pytest.mark.parametrize(
    "css,count,severity",
    [
        ("a:focus { outline: none; }", 1, "high"),
        ("button:focus { outline: 0 !important; }", 1, "high"),
        ("input:focus { outline-style: none; }", 1, "high"),
        ("a:focus { outline: none; box-shadow: 0 0 0 3px blue; }", 0, None),
        ("a:focus { outline: none; border-color: blue; }", 0, None),
        (":focus:not(:focus-visible) { outline: none; }", 0, None),
        ("a:focus { outline: none; } a:focus-visible { outline: 2px solid; }", 1, "low"),
        ("a:hover { outline: none; }", 0, None),
        ("@media screen { .x:focus { outline: none } }", 1, "high"),
    ],
)
def test_css_outline_rules(css, count, severity):
    found = [f for f in m.audit_css(css, "t.css") if f["rule"] == "css.focus_outline_removed"]
    assert len(found) == count
    if severity:
        assert found[0]["severity"] == severity


def test_sticky_with_scroll_padding_is_fine():
    assert m.audit_css("header { position: sticky; top: 0 } html { scroll-padding-top: 4rem }", "t") == []
    assert rules(m.audit_css("header { position: fixed }", "t")) == {"css.sticky_may_obscure_focus"}


def test_tab_order():
    html = page('<a href="/a">A</a><button tabindex="2">B</button><input aria-label="C"><button tabindex="1">D</button>'
                '<div tabindex="-1">no</div><span tabindex="0">E</span><input type="hidden"><button disabled>F</button>')  # fmt: skip
    names = [it["name"] for it in m.focus_order_listing(html)]
    assert names == ["D", "B", "A", "C", "E"]


def test_skip_link_detection():
    nav = "".join(f'<a href="/p{i}">P{i}</a>' for i in range(8))
    no_skip = (
        f'<html lang="en"><head><title>T</title></head><body><nav>{nav}</nav><main><h1>x</h1></main></body></html>'
    )
    assert "bypass.no_skip_link" in rules(m.audit(no_skip))
    with_skip = no_skip.replace("<nav>", '<a href="#m">Skip to content</a><nav>').replace("<main>", '<main id="m">')
    assert "bypass.no_skip_link" not in rules(m.audit(with_skip))
    broken = with_skip.replace('<main id="m">', "<main>")
    found = [f for f in m.audit(broken) if f["rule"] == "link.fragment_target_missing"]
    assert found and found[0]["severity"] == "high"


def test_cli_css_files_and_order():
    r = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--css", str(CSS / "outline_removed.css"), "--json")
    data = json.loads(r.stdout)
    hits = [f for f in data["files"][0]["findings"] if f["rule"] == "css.focus_outline_removed"]
    assert r.returncode == 1 and len(hits) == 2  # .btn:focus has a box-shadow replacement
    r = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--css", str(CSS / "focus_visible_ok.css"))
    assert r.returncode == 0
    order = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--order")
    assert order.returncode == 0 and "1. line" in order.stdout and "Skip to main content" in order.stdout
    oj = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--order", "--json")
    first = next(iter(json.loads(oj.stdout).values()))[0]
    assert first["name"] == "Skip to main content"
    assert run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--css", "/no/such.css").returncode == 2
    bad = run_script(SKILL, SCRIPT, str(HTML / "focus_bad.html"), "--fail-on", "high")
    assert bad.returncode == 1
