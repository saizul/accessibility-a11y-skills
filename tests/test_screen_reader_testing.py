import json

from conftest import HTML, load_script, page, run_script

SKILL, SCRIPT = "screen-reader-testing", "sr_outline.py"
m = load_script(SKILL, SCRIPT)


def test_outline_of_good_page():
    d = m.outline((HTML / "good_page.html").read_text())
    assert d["title"] == "Contact us - Example Shop" and d["lang"] == "en"
    assert [lm["role"] for lm in d["landmarks"]] == ["banner", "navigation", "main", "contentinfo"]
    assert d["landmarks"][1]["name"] == "Primary"
    assert [(h["level"], h["text"]) for h in d["headings"]][:2] == [(1, "Contact us"), (2, "Send a message")]
    email = next(c for c in d["controls"] if c["name"] == "Email address")
    assert email["role"] == "textbox" and "required" in email["states"] and "invalid entry" in email["states"]
    assert email["description"].startswith("Enter an email address")
    assert any(c["role"] == "radio" and "checked" in c["states"] for c in d["controls"])
    assert next(c for c in d["controls"] if c["name"] == "Search")["states"] == ["collapsed"]
    assert any(im["decorative"] for im in d["images"])
    assert d["live_regions"] and d["problems"] == []


def test_problems_detected():
    html = '<html><body><a href="/x"></a><button></button><img src="cat.jpg"></body></html>'
    d = m.outline(html)
    text = " ".join(d["problems"])
    assert "link" in text and "button" in text and "cat.jpg" in text
    assert "no <title>" in text and "no lang" in text and "no main" in text


def test_hidden_content_excluded():
    d = m.outline(page('<div hidden><a href="/x">Hidden</a></div><a href="/y">Shown</a>'))
    assert [lk["name"] for lk in d["links"]] == ["Shown"]


def test_role_heading_and_live_roles():
    d = m.outline(page('<div role="heading" aria-level="3">Sub</div><div role="alert">Saved</div>'))
    assert d["headings"] == [{"level": 3, "text": "Sub", "line": 1}]
    assert d["live_regions"][0]["politeness"] == "assertive"


def test_markdown_test_script():
    md = m.as_markdown("x.html", m.outline((HTML / "good_page.html").read_text()))
    assert md.startswith("# Screen reader test script: Contact us - Example Shop")
    assert "NVDA+F7" in md and "VO+U" in md and "| --- |" in md
    assert "Email address, textbox, required, invalid entry" in md


def test_cli_formats():
    t = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"))
    assert t.returncode == 0 and "Landmarks:" in t.stdout and "h1 Contact us" in t.stdout
    md = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"), "--format", "markdown")
    assert md.returncode == 0 and "| # | Task |" in md.stdout
    js = run_script(SKILL, SCRIPT, str(HTML / "bad_page.html"), "--json")
    data = json.loads(js.stdout)
    assert js.returncode == 1 and data[0]["problems"]
    assert run_script(SKILL, SCRIPT, "/no/such.html").returncode == 2
