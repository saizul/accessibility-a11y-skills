import json

import pytest

from conftest import HTML, load_script, page, rules, run_script

SKILL, SCRIPT = "accessible-forms", "forms_check.py"
m = load_script(SKILL, SCRIPT)


@pytest.mark.parametrize(
    "value",
    [
        "on",
        "off",
        "email",
        "name",
        "given-name",
        "street-address",
        "shipping postal-code",
        "billing cc-number",
        "section-blue shipping address-line1",
        "work email",
        "mobile tel",
        "home tel-national",
        "username webauthn",
        "current-password webauthn",
        "one-time-code",
        "bday-year",
        "  EMAIL  ",
    ],
)
def test_valid_tokens(value):
    assert m.validate_autocomplete(value) == (True, "")


@pytest.mark.parametrize(
    "value,why",
    [
        ("", "empty"),
        ("surname", "not an autofill field name"),
        ("e-mail", "not an autofill field name"),
        ("mobile street-address", "may only precede"),
        ("shipping", "missing field name"),
        ("email name", "unexpected token"),
        ("webauthn", "must follow"),
        ("billing shipping email", "not an autofill field name"),
        ("off email", "not an autofill field name"),
        ("postal_code", "did you mean postal-code"),
    ],
)
def test_invalid_tokens(value, why):
    ok, reason = m.validate_autocomplete(value)
    assert not ok and why in reason, reason


@pytest.mark.parametrize(
    "attrs,label,purpose",
    [
        ('type="email"', "", "email"),
        ('type="tel"', "", "tel"),
        ('name="first_name"', "", "given-name"),
        ('name="lastName"', "", "family-name"),
        ('name="billing[zip]"', "", "postal-code"),
        ('name="x"', "Your name", "name"),
        ('name="x"', "City", "address-level2"),
        ('type="password" name="pw"', "", "current-password"),
        ('type="password" name="confirm_password"', "", "new-password"),
        ('name="cc_num"', "Card number", "cc-number"),
        ('name="capacity"', "Capacity", None),
        ('name="q" type="search"', "Search", None),
        ('name="ethnicity"', "", None),
    ],
)
def test_guess_purpose(attrs, label, purpose):
    root = m.parse_html(f"<input {attrs}>")
    node = next(root.iter())
    assert m.guess_purpose(node, label) == purpose


def test_good_page_is_clean():
    assert m.check((HTML / "good_page.html").read_text()) == []


def test_bad_fixture():
    found = rules(m.check((HTML / "forms_bad.html").read_text()))
    expected = {
        "autocomplete.invalid",
        "autocomplete.missing",
        "autocomplete.off_on_personal",
        "input.type_mismatch",
        "label.missing",
        "label.name_mismatch",
        "error.not_associated",
        "required.not_programmatic",
        "auth.paste_blocked",
        "group.no_fieldset",
        "form.no_submit",
        "auth.captcha",
    }
    assert expected <= found, expected - found


@pytest.mark.parametrize(
    "snippet",
    [
        '<form><label for="e">Email</label><input id="e" type="email" autocomplete="email"><button>Go</button></form>',
        '<form><fieldset><legend>Size</legend><input type="radio" name="s" id="a"><label for="a">S</label>'
        '<input type="radio" name="s" id="b"><label for="b">M</label></fieldset><button>Go</button></form>',
        '<div role="radiogroup" aria-label="Size"><input type="radio" name="s" aria-label="S">'
        '<input type="radio" name="s" aria-label="M"></div>',
        '<label for="q">Search</label><input id="q" type="search" name="q">',
        '<label for="x">Name</label><input id="x" name="name" autocomplete="name" aria-label="Name (required)">',
        '<label for="c">Coupon</label><input id="c" name="coupon" aria-invalid="true" aria-errormessage="ce">'
        '<p id="ce">Coupon expired</p>',
        '<label for="r">Email *</label><input id="r" type="email" autocomplete="email" required>',
    ],
)
def test_no_false_positives(snippet):
    found = [f for f in m.check(page(snippet)) if f["severity"] in ("high", "medium")]
    assert found == [], found


def test_cli_token_mode():
    ok = run_script(SKILL, SCRIPT, "--token", "shipping postal-code", "--token", "email")
    assert ok.returncode == 0 and ok.stdout.count("VALID") == 2
    bad = run_script(SKILL, SCRIPT, "--token", "zip", "--json")
    data = json.loads(bad.stdout)
    assert bad.returncode == 1 and data[0]["valid"] is False


def test_cli_files():
    bad = run_script(SKILL, SCRIPT, str(HTML / "forms_bad.html"), "--json")
    assert bad.returncode == 1 and json.loads(bad.stdout)["tool"] == "accessible-forms"
    assert run_script(SKILL, SCRIPT, str(HTML / "good_page.html")).returncode == 0
    assert run_script(SKILL, SCRIPT).returncode == 2
    assert run_script(SKILL, SCRIPT, "/no/such.html").returncode == 2


FIELD = '<label for="n">Name</label><input id="n" name="n" autocomplete="name">'


@pytest.mark.parametrize(
    "control",
    [
        '<button type="reset">Clear</button>',
        '<button type="RESET">Clear</button>',
        '<input type="reset" value="Clear">',
    ],
)
def test_reset_button_is_flagged(control):
    found = [
        f
        for f in m.check(page(f"<form>{FIELD}{control}<button>Send</button></form>"))
        if f["rule"] == "form.reset_button"
    ]
    assert len(found) == 1
    assert found[0]["severity"] == "low"
    assert found[0]["wcag"] == "3.3.4"
    assert found[0]["element"].startswith(("button", "input"))


@pytest.mark.parametrize(
    "control",
    [
        '<button type="reset" hidden>Clear</button>',
        '<button type="reset" disabled>Clear</button>',
        '<input type="reset" style="display:none">',
        '<button type="button">Clear</button>',
    ],
)
def test_hidden_disabled_or_plain_buttons_are_not_reset_findings(control):
    found = rules(m.check(page(f"<form>{FIELD}{control}<button>Send</button></form>")))
    assert "form.reset_button" not in found


def test_reset_button_in_form_without_fields_is_ignored():
    found = rules(m.check(page('<form><button type="reset">Clear</button><button>Go</button></form>')))
    assert "form.reset_button" not in found


def test_reset_button_counted_once_per_form_and_ignorable(tmp_path):
    html = tmp_path / "f.html"
    html.write_text(
        page(f'<form>{FIELD}<button type="reset">A</button><input type="reset"><button>Go</button></form>'),
        encoding="utf-8",
    )
    res = run_script(SKILL, SCRIPT, str(html), "--json", "--fail-on", "low")
    data = json.loads(res.stdout)
    resets = [f for f in data["files"][0]["findings"] if f["rule"] == "form.reset_button"]
    assert len(resets) == 1 and "2 reset" in resets[0]["message"]
    assert res.returncode == 1
    res = run_script(SKILL, SCRIPT, str(html), "--fail-on", "low", "--ignore", "form.reset_button")
    assert res.returncode == 0, res.stdout
