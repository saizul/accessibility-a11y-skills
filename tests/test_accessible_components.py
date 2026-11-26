"""The component examples must pass every audit script in this repository."""

import re

import pytest

from conftest import SKILLS, load_script

ASSETS = sorted((SKILLS / "accessible-components" / "assets").glob("*.html"))
AUDITS = [
    ("wcag-html-audit", "html_audit.py", "audit"),
    ("aria-review", "aria_lint.py", "lint"),
    ("keyboard-and-focus", "focus_audit.py", "audit"),
    ("accessible-forms", "forms_check.py", "check"),
]


def test_assets_exist():
    names = {p.name for p in ASSETS}
    assert names == {"dialog.html", "tabs.html", "menu-button.html", "combobox.html"}


@pytest.mark.parametrize("asset", ASSETS, ids=lambda p: p.name)
@pytest.mark.parametrize("skill,script,fn", AUDITS, ids=lambda x: x if isinstance(x, str) else "")
def test_examples_pass_audits(asset, skill, script, fn):
    module = load_script(skill, script)
    findings = getattr(module, fn)(asset.read_text())
    assert findings == [], findings


@pytest.mark.parametrize("asset", ASSETS, ids=lambda p: p.name)
def test_examples_have_names_for_screen_readers(asset):
    sr = load_script("screen-reader-testing", "sr_outline.py")
    data = sr.outline(asset.read_text())
    assert data["problems"] == []
    assert all(c["name"] for c in data["controls"])


@pytest.mark.parametrize(
    "asset,needles",
    [
        ("dialog.html", ["showModal()", "aria-labelledby", 'addEventListener("close"', ".focus()"]),
        ("tabs.html", ["ArrowRight", "ArrowLeft", "Home", "End", "aria-selected", "tabIndex"]),
        ("menu-button.html", ["ArrowDown", "Escape", 'aria-expanded", "true"', "type-ahead"]),
        ("combobox.html", ["aria-activedescendant", "aria-expanded", "available", "Escape"]),
    ],
)
def test_examples_implement_keyboard_model(asset, needles):
    text = (SKILLS / "accessible-components" / "assets" / asset).read_text()
    for needle in needles:
        assert needle in text, needle


def test_references_cover_each_pattern():
    refs = SKILLS / "accessible-components" / "references"
    for name in ("dialog.md", "tabs.md", "menu.md", "combobox.md", "disclosure.md"):
        text = (refs / name).read_text()
        assert "## Test checklist" in text
        if name != "disclosure.md":
            assert re.search(r"^\| Key", text, re.M), name
