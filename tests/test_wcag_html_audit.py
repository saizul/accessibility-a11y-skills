import json

import pytest

from conftest import HTML, load_script, page, rules, run_script

SKILL, SCRIPT = "wcag-html-audit", "html_audit.py"
m = load_script(SKILL, SCRIPT)


def test_good_page_is_clean():
    assert m.audit((HTML / "good_page.html").read_text()) == []


def test_bad_page_finds_everything():
    found = rules(m.audit((HTML / "bad_page.html").read_text()))
    expected = {
        "html.lang_missing",
        "document.title_missing",
        "meta.viewport_zoom_blocked",
        "meta.refresh",
        "img.alt_missing",
        "img.alt_placeholder",
        "link.empty",
        "link.generic_text",
        "link.new_window",
        "button.empty",
        "heading.empty",
        "heading.skipped_level",
        "form.label_missing",
        "label.for_missing_target",
        "input_image.alt_missing",
        "id.duplicate",
        "tabindex.positive",
        "iframe.title_missing",
        "table.no_headers",
        "media.autoplay_sound",
        "media.no_captions",
        "element.moving_content",
        "svg.name_missing",
        "landmark.main_missing",
    }
    assert expected <= found, expected - found


@pytest.mark.parametrize(
    "snippet,rule",
    [
        ('<img src="a.png">', "img.alt_missing"),
        ('<img src="a.png" alt="DSC_0042">', "img.alt_placeholder"),
        ('<img src="a.png" alt="" role="img">', "img.empty_alt_with_role"),
        ('<a href="/x"><img src="x.png" alt=""></a>', "link.empty"),
        ('<a href="/x">Read more</a>', "link.generic_text"),
        ('<a onclick="go()">Go</a>', "link.no_href"),
        ('<button><svg aria-hidden="true"></svg></button>', "button.empty"),
        ('<div role="button" tabindex="0"></div>', "button.empty"),
        ('<input type="button">', "button.empty"),
        ('<input type="text" placeholder="Search">', "form.label_missing"),
        ('<textarea title="Comments"></textarea>', "form.title_only_label"),
        ("<h1>A</h1><h3>B</h3>", "heading.skipped_level"),
        ("<h1>A</h1><h2> </h2>", "heading.empty"),
        ('<p id="a">1</p><p id="a">2</p>', "id.duplicate"),
        ('<button tabindex="2">x</button>', "tabindex.positive"),
        ('<iframe src="/x"></iframe>', "iframe.title_missing"),
        ("<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>", "table.no_headers"),
        ("<table><tr><th>a</th></tr><tr><td>1</td></tr></table>", "table.no_caption"),
        ('<audio src="a.mp3" autoplay></audio>', "media.autoplay_sound"),
        ('<video src="a.mp4" autoplay muted></video>', "media.autoplay_no_controls"),
        ('<p lang="english">Hi</p>', "lang.invalid"),
        ('<svg role="img"></svg>', "svg.name_missing"),
        ('<area href="/x" shape="rect" coords="0,0,1,1">', "area.alt_missing"),
        ("<object data='x.swf'></object>", "object.name_missing"),
    ],
)
def test_single_rules(snippet, rule):
    assert rule in rules(m.audit(page(snippet)))


@pytest.mark.parametrize(
    "snippet",
    [
        '<img src="a.png" alt="">',
        '<img src="a.png" alt="Bar chart of sales by month">',
        '<a href="/x"><img src="x.png" alt="Home"></a>',
        '<a href="/x" aria-label="Pricing details">More</a>',
        '<button aria-labelledby="l"><svg aria-hidden="true"></svg></button><span id="l">Close</span>',
        '<input type="submit">',
        '<label>Email <input type="email" name="email"></label>',
        '<span id="lab">Search</span><input aria-labelledby="lab">',
        '<input type="hidden" name="csrf">',
        "<h1>A</h1><h2>B</h2><h3>C</h3><h2>D</h2>",
        '<table role="presentation"><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>',
        '<video controls><track kind="captions" src="a.vtt"></video>',
        '<div hidden><img src="x.png"></div>',
        '<div aria-hidden="true"><a href="/x"></a></div>',
        '<iframe src="/x" title="Video: product tour"></iframe>',
        '<svg role="img" aria-label="Logo"></svg>',
        '<svg role="img"><title>Logo</title></svg>',
    ],
)
def test_no_false_positives(snippet):
    found = [f for f in m.audit(page("<h1>Title</h1>" + snippet)) if f["severity"] in ("high", "medium")]
    assert found == [], found


def test_fragment_skips_document_checks():
    found = rules(m.audit('<div><img src="x.png" alt="ok"></div>'))
    assert "html.lang_missing" not in found and "landmark.main_missing" not in found


def test_viewport_and_refresh_variants():
    assert "meta.viewport_zoom_blocked" in rules(
        m.audit(page("", '<title>T</title><meta name="viewport" content="maximum-scale=1.0">'))
    )
    assert "meta.viewport_zoom_blocked" not in rules(
        m.audit(page("", '<title>T</title><meta name="viewport" content="width=device-width, maximum-scale=5">'))
    )
    assert "meta.refresh" not in rules(
        m.audit(page("", '<title>T</title><meta http-equiv="refresh" content="0; url=/new">'))
    )


def test_duplicate_referenced_id_is_high():
    found = m.audit(page('<label for="e">Email</label><input id="e"><input id="e" aria-label="x">'))
    dup = [f for f in found if f["rule"] == "id.duplicate"]
    assert dup and dup[0]["severity"] == "high"


def test_findings_have_line_and_wcag():
    for f in m.audit((HTML / "bad_page.html").read_text()):
        assert set(f) == {"severity", "rule", "wcag", "line", "element", "message", "fix"}
        assert f["severity"] in m.SEVERITIES


def test_cli_exit_codes_and_json(tmp_path):
    good = run_script(SKILL, SCRIPT, str(HTML / "good_page.html"))
    assert good.returncode == 0 and "no findings" in good.stdout
    bad = run_script(SKILL, SCRIPT, str(HTML / "bad_page.html"), "--json")
    assert bad.returncode == 1
    data = json.loads(bad.stdout)
    assert data["tool"] == "wcag-html-audit" and data["files"][0]["summary"]["high"] > 10
    never = run_script(SKILL, SCRIPT, str(HTML / "bad_page.html"), "--fail-on", "never")
    assert never.returncode == 0
    missing = run_script(SKILL, SCRIPT, str(tmp_path / "nope.html"))
    assert missing.returncode == 2
    empty = run_script(SKILL, SCRIPT, str(tmp_path))
    assert empty.returncode == 2


def test_cli_folder_stdin_and_ignore():
    folder = run_script(SKILL, SCRIPT, str(HTML), "--json", "--fail-on", "never")
    assert len(json.loads(folder.stdout)["files"]) >= 5
    piped = run_script(SKILL, SCRIPT, "-", "--json", stdin='<img src="a.png">')
    assert piped.returncode == 1 and json.loads(piped.stdout)["files"][0]["file"] == "<stdin>"
    ignored = run_script(SKILL, SCRIPT, "-", "--ignore", "img.alt_missing", stdin='<img src="a.png">')
    assert ignored.returncode == 0


def test_fail_on_threshold():
    r = run_script(SKILL, SCRIPT, "-", "--fail-on", "high", stdin=page("<h1>A</h1><h3>B</h3>"))
    assert r.returncode == 0
    r = run_script(SKILL, SCRIPT, "-", "--fail-on", "medium", stdin=page("<h1>A</h1><h3>B</h3>"))
    assert r.returncode == 1
