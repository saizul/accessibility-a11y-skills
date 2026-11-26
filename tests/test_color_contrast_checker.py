import json

import pytest

from conftest import CSS, load_script, run_script

SKILL, SCRIPT = "color-contrast-checker", "contrast.py"
m = load_script(SKILL, SCRIPT)


@pytest.mark.parametrize(
    "fg,bg,expected",
    [
        ("#000", "#fff", 21.0),
        ("#fff", "#fff", 1.0),
        ("#767676", "#ffffff", 4.54),
        ("#777777", "#ffffff", 4.47),  # 4.478: never rounded up, fails AA
        ("#595959", "#ffffff", 7.0),
        ("white", "#1a4fd6", 6.7),
        ("#ffffff", "#f59e0b", 2.14),
    ],
)
def test_known_ratios(fg, bg, expected):
    assert m.floor2(m.ratio(fg, bg)) == pytest.approx(expected, abs=0.011)


def test_ratio_is_symmetric():
    assert m.ratio("#123456", "#abcdef") == pytest.approx(m.ratio("#abcdef", "#123456"))


@pytest.mark.parametrize(
    "value,rgba",
    [
        ("#abc", (170, 187, 204, 1.0)),
        ("#aabbcc80", (170, 187, 204, 128 / 255)),
        ("rgb(10, 20, 30)", (10, 20, 30, 1.0)),
        ("rgb(10 20 30 / 50%)", (10, 20, 30, 0.5)),
        ("rgba(100%, 0%, 0%, .25)", (255, 0, 0, 0.25)),
        ("hsl(0 100% 50%)", (255, 0, 0, 1.0)),
        ("hsla(120deg, 100%, 25%, 1)", (0, 127.5, 0, 1.0)),
        ("RebeccaPurple", (102, 51, 153, 1.0)),
        ("transparent", (0, 0, 0, 0.0)),
    ],
)
def test_parse_color(value, rgba):
    assert m.parse_color(value) == pytest.approx(rgba, abs=0.6)


@pytest.mark.parametrize("bad", ["#12", "blurple", "rgb(1,2)", "color(display-p3 1 0 0)", "rgb(a b c)"])
def test_parse_errors(bad):
    with pytest.raises(m.ColorError):
        m.parse_color(bad)


def test_alpha_is_composited():
    # 50% black over white renders as #808080 (3.95:1 or so), not black (21:1)
    r = m.ratio("rgb(0 0 0 / 50%)", "#fff")
    assert 3.9 < r < 4.0


def test_evaluate_levels_and_large_text():
    r = m.evaluate("#8a8a8a", "#ffffff")
    assert not r["pass"] and r["AA_large"] and not r["AA_normal"]
    assert m.evaluate("#8a8a8a", "#ffffff", large=True)["pass"]
    aaa = m.evaluate("#595959", "#ffffff", level="AAA")
    assert aaa["pass"] and aaa["required"] == 7.0
    assert not m.evaluate("#767676", "#ffffff", level="AAA")["pass"]


def test_suggestions_pass():
    r = m.evaluate("#999999", "#ffffff")
    assert m.ratio(r["suggested_foreground"], "#ffffff") >= 4.5
    assert m.ratio("#999999", r["suggested_background"]) >= 4.5
    # the suggestion keeps the colour close: still a grey, only darker
    assert r["suggested_foreground"] in ("#767676", "#757575")


@pytest.mark.parametrize(
    "size,weight,large",
    [("24px", None, True), ("18pt", None, True), ("18.66px", "700", True), ("14pt", "bold", True),
     ("18px", "700", False), ("1.5rem", None, True), ("16px", "900", False), (None, None, False)],
)  # fmt: skip
def test_large_text_rule(size, weight, large):
    assert m.is_large(m.font_px(size), weight) is large


def test_css_extraction():
    items = m.pairs_from_css((CSS / "theme.css").read_text(), "#ffffff")
    by_sel = {i["selector"]: i for i in items}
    assert by_sel[".muted"]["fg"] == "#9a9a9a" and by_sel[".muted"]["bg_assumed"]
    assert by_sel[".btn-primary"]["bg"] == "#1a4fd6" and not by_sel[".btn-primary"]["large"]
    assert by_sel[".hero-title"]["large"]
    assert "skipped" in by_sel[".banner"]
    assert by_sel[".ghost"]["fg"].startswith("rgba")


def test_css_media_queries_comments_and_var_fallback():
    css = """
    /* comment { color: red } */
    @media (prefers-color-scheme: dark) {
      .card { color: var(--missing, #eeeeee); background-color: #111111; }
    }
    """
    items = m.pairs_from_css(css, "#ffffff")
    assert len(items) == 1 and items[0]["fg"] == "#eeeeee" and items[0]["bg"] == "#111111"


def test_read_pairs():
    pairs = m.read_pairs("# comment\n#000, #fff, label one\nrgb(0, 0, 0), white\n\n")
    assert pairs == [("#000", "#fff", "label one"), ("rgb(0, 0, 0)", "white", "")]
    with pytest.raises(m.ColorError):
        m.read_pairs("black\n")


def test_cli_single_pair():
    ok = run_script(SKILL, SCRIPT, "#767676", "#ffffff")
    assert ok.returncode == 0 and "PASS" in ok.stdout and "4.54:1" in ok.stdout
    bad = run_script(SKILL, SCRIPT, "#777", "#fff")
    assert bad.returncode == 1 and "FAIL" in bad.stdout and "suggestion" in bad.stdout
    large = run_script(SKILL, SCRIPT, "#777", "#fff", "--large")
    assert large.returncode == 0


def test_cli_ui_mode():
    r = run_script(SKILL, SCRIPT, "#949494", "#ffffff", "--ui", "--json")
    data = json.loads(r.stdout)["results"][0]
    assert r.returncode == 0 and data["required"] == 3.0 and "suggested_foreground" not in data
    r = run_script(SKILL, SCRIPT, "#999", "#fff", "--ui", "--json")
    data = json.loads(r.stdout)["results"][0]
    assert r.returncode == 1 and m.ratio(data["suggested_foreground"], "#fff") >= 3.0


def test_cli_pairs_and_css_json():
    r = run_script(SKILL, SCRIPT, "--pairs", str(CSS / "pairs.txt"), "--json")
    data = json.loads(r.stdout)
    assert r.returncode == 1 and len(data["results"]) == 4
    assert [x["pass"] for x in data["results"]] == [True, False, True, False]
    r = run_script(SKILL, SCRIPT, "--css", str(CSS / "theme.css"), "--json")
    data = json.loads(r.stdout)
    failing = {x["label"].split(" (")[0] for x in data["results"] if not x["pass"]}
    assert failing == {".muted", ".ghost", ".badge"} and len(data["skipped"]) == 1
    stdin = run_script(SKILL, SCRIPT, "--pairs", "-", stdin="#000, #fff\n")
    assert stdin.returncode == 0


def test_cli_errors(tmp_path):
    assert run_script(SKILL, SCRIPT, "notacolour", "#fff").returncode == 2
    assert run_script(SKILL, SCRIPT, "--css", str(tmp_path / "missing.css")).returncode == 2
    assert run_script(SKILL, SCRIPT).returncode == 2  # argparse usage error
    assert run_script(SKILL, SCRIPT, "#000").returncode == 2
