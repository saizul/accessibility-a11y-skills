import json

import pytest

from conftest import HTML, load_script, page, rules, run_script

SKILL, SCRIPT = "aria-review", "aria_lint.py"
m = load_script(SKILL, SCRIPT)


def test_good_page_is_clean():
    assert m.lint((HTML / "good_page.html").read_text()) == []


def test_bad_fixture():
    found = rules(m.lint((HTML / "aria_bad.html").read_text()))
    expected = {
        "role.invalid",
        "role.abstract",
        "role.missing_required",
        "role.not_focusable",
        "role.missing_context",
        "role.redundant",
        "role.presentation_conflict",
        "aria.unknown_attribute",
        "aria.invalid_value",
        "aria.broken_reference",
        "aria_hidden.focusable",
        "name.missing",
        "name.prohibited_on_generic",
        "landmark.duplicate_unlabelled",
    }
    assert expected <= found, expected - found


@pytest.mark.parametrize(
    "snippet,rule",
    [
        ('<div role="tabpanell">x</div>', "role.invalid"),
        ('<div role="landmark">x</div>', "role.abstract"),
        ('<ul role="directory"><li>x</li></ul>', "role.deprecated"),
        ('<div role="">x</div>', "role.empty"),
        ('<nav role="navigation"><a href="/">x</a></nav>', "role.redundant"),
        ('<button role="heading">x</button>', "role.overrides_native"),
        ('<div aria-hiden="true">x</div>', "aria.unknown_attribute"),
        ('<div role="button" tabindex="0" aria-pressed="yes">x</div>', "aria.invalid_value"),
        ('<div aria-live="loud">x</div>', "aria.invalid_value"),
        ('<div aria-relevant="additions everything">x</div>', "aria.invalid_value"),
        ('<div role="slider" tabindex="0" aria-valuenow="high">x</div>', "aria.invalid_value"),
        ('<input aria-label="">', "aria.empty_label"),
        ('<button aria-controls="nope">x</button>', "aria.broken_reference"),
        ('<button aria-hidden="true">x</button>', "aria_hidden.focusable"),
        ('<div aria-hidden="true"><input></div>', "aria_hidden.focusable"),
        ('<span role="switch" tabindex="0">x</span>', "role.missing_required"),
        ('<div role="combobox" tabindex="0">x</div>', "role.missing_required"),
        ('<div role="option">x</div>', "role.missing_context"),
        ('<div role="menu"><div role="menuitem">x</div></div>', "role.roving_tabindex"),
        ('<span role="link">x</span>', "role.not_focusable"),
        ('<div role="dialog" aria-modal="true">x</div>', "name.missing"),
        ('<span aria-label="x">y</span>', "name.prohibited_on_generic"),
        ('<a href="/" role="none">x</a>', "role.presentation_conflict"),
    ],
)
def test_single_rules(snippet, rule):
    assert rule in rules(m.lint(page(snippet))), m.lint(page(snippet))


@pytest.mark.parametrize(
    "snippet",
    [
        '<div role="tablist" aria-label="Tabs"><button role="tab" aria-selected="true" aria-controls="p1">A</button>'
        '<button role="tab" aria-selected="false" tabindex="-1" aria-controls="p2">B</button></div>'
        '<div role="tabpanel" id="p1" aria-label="A">1</div><div role="tabpanel" id="p2" aria-label="B" hidden>2</div>',
        '<ul role="listbox" aria-label="Fruit" tabindex="0" aria-activedescendant="o1"><li role="option" id="o1">Apple</li></ul>',
        '<input type="checkbox" role="switch" id="s"><label for="s">Wi-Fi</label>',
        '<button aria-expanded="false" aria-controls="menu1">Menu</button><ul id="menu1" hidden></ul>',
        '<div role="dialog" aria-modal="true" aria-labelledby="dt"><h2 id="dt">Title</h2></div>',
        '<dialog aria-label="Settings"><p>x</p></dialog>',
        '<div aria-hidden="true"><svg></svg></div>',
        '<div aria-hidden="true"><a href="/x" tabindex="-1">x</a></div>',
        '<div aria-hidden="true"><button disabled>x</button></div>',
        '<div role="slider" tabindex="0" aria-valuenow="5" aria-valuemin="0" aria-valuemax="10" aria-label="V"></div>',
        '<div role="doc-chapter">x</div>',
        '<img src="x.png" alt="" role="presentation">',
        '<nav aria-label="Primary"><a href="/">x</a></nav><nav aria-label="Footer"><a href="/">y</a></nav>',
        '<div role="region" aria-label="Notes">x</div>',
        '<a href="/a" role="button">Act</a>',
        '<div role="checkbox" tabindex="0" aria-checked="mixed">All</div>',
        '<span role="heading" aria-level="3">Sub</span>',
    ],
)
def test_no_false_positives(snippet):
    found = [f for f in m.lint(page(snippet)) if f["severity"] in ("high", "medium")]
    assert found == [], found


def test_implicit_roles():
    root = m.parse_html(
        '<header>h</header><article><header>a</header></article><input type="email"><select multiple></select>'
        '<input list="dl"><section aria-label="S"></section><section></section><a>no href</a>'
    )
    roles = [m.implicit_role(n) for n in root.iter()]
    assert roles == ["banner", "article", "", "textbox", "listbox", "combobox", "region", "", ""]


def test_owned_context_counts():
    html = page('<div role="list" aria-owns="i1"></div><div><div role="listitem" id="i1">x</div></div>')
    assert "role.missing_context" not in rules(m.lint(html))


def test_cli():
    bad = run_script(SKILL, SCRIPT, str(HTML / "aria_bad.html"), "--json")
    assert bad.returncode == 1 and json.loads(bad.stdout)["tool"] == "aria-review"
    ok = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"))
    assert ok.returncode == 0
    low_only = run_script(SKILL, SCRIPT, "-", stdin=page('<ul role="list"><li>x</li></ul>'))
    assert low_only.returncode == 0
    strict = run_script(SKILL, SCRIPT, "-", "--fail-on", "low", stdin=page('<ul role="list"><li>x</li></ul>'))
    assert strict.returncode == 1
    assert run_script(SKILL, SCRIPT, "/no/such/file.html").returncode == 2
