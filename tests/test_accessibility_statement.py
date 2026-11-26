import csv
import io
import json

import pytest

from conftest import FIXTURES, load_script, run_script

SKILL, SCRIPT = "accessibility-statement", "make_statement.py"
m = load_script(SKILL, SCRIPT)
CONFIG = FIXTURES / "statement" / "config.json"
AUDIT = FIXTURES / "statement" / "audit.json"


def cfg(**changes):
    data = json.loads(json.dumps(m.EXAMPLE))
    data.update(changes)
    return data


def test_example_config_is_valid_and_fixture_matches():
    assert m.validate(cfg()) == []
    assert json.loads(CONFIG.read_text()) == m.EXAMPLE


@pytest.mark.parametrize(
    "changes,problem",
    [
        ({"organization": ""}, "organization"),
        ({"conformance": "mostly"}, "full, partial, non"),
        ({"level": "AAAA"}, "A, AA or AAA"),
        ({"contact": {}}, "contact needs"),
        ({"conformance": "full"}, "use 'partial'"),
        ({"known_issues": []}, "no known_issues"),
        ({"known_issues": [{"wcag": "1.1.1"}]}, "needs a title"),
    ],
)
def test_validation(changes, problem):
    assert any(problem in p for p in m.validate(cfg(**changes)))


def test_markdown_statement():
    md = m.render_markdown(cfg(), cfg()["known_issues"])
    assert md.startswith("# Accessibility statement for Example shop")
    assert "partially conforms with WCAG 2.2 level AA" in md
    assert "**Product image carousel cannot be paused** (WCAG 2.2.2)." in md
    assert "Planned fix: 2027-01-31." in md and ".." not in md
    assert "mailto:accessibility@example.com" in md and "within 5 working days" in md
    assert "## Content not within scope" in md and "## Assessment approach" in md


def test_html_statement_escapes_and_is_accessible():
    data = cfg(organization="Tom & Jerry <Ltd>")
    out = m.render_html(data, data["known_issues"])
    assert "Tom &amp; Jerry &lt;Ltd&gt;" in out and "<Ltd>" not in out
    audit = load_script("wcag-html-audit", "html_audit.py")
    assert audit.audit(out) == []


def test_issues_from_findings_groups_by_rule():
    report = json.loads(AUDIT.read_text())
    issues = m.issues_from_findings([report])
    by_rule = {i["rule"]: i for i in issues}
    assert by_rule["form.label_missing"]["title"] == "Some form fields have no label"
    assert by_rule["form.label_missing"]["impact"].startswith("3 occurrence(s)")
    assert all(i["severity"] in ("high", "medium") for i in issues)
    assert issues[0]["severity"] == "high"
    assert len(m.issues_from_findings([report], "high")) < len(issues)


def test_issues_csv():
    rows = list(csv.DictReader(io.StringIO(m.issues_csv(m.issues_from_findings([json.loads(AUDIT.read_text())])))))
    assert rows and rows[0]["status"] == "open" and rows[0]["rule"]


def test_cli_init_and_markdown():
    init = run_script(SKILL, SCRIPT, "--init")
    assert init.returncode == 0 and json.loads(init.stdout)["level"] == "AA"
    md = run_script(SKILL, SCRIPT, str(CONFIG))
    assert md.returncode == 0 and md.stdout.startswith("# Accessibility statement")


def test_cli_findings_out_and_csv(tmp_path):
    full = tmp_path / "full.json"
    full.write_text(json.dumps(cfg(conformance="full", known_issues=[])))
    out, issues = tmp_path / "a11y.html", tmp_path / "issues.csv"
    r = run_script(
        SKILL,
        SCRIPT,
        str(full),
        "--findings",
        str(AUDIT),
        "--format",
        "html",
        "--out",
        str(out),
        "--issues-csv",
        str(issues),
    )
    assert r.returncode == 0, r.stderr
    assert "changed from 'full' to 'partial'" in r.stderr
    assert "partially conforms" in out.read_text() and out.read_text().startswith("<!DOCTYPE html>")
    assert issues.read_text().startswith("title,wcag,severity")


def test_cli_errors(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(cfg(contact={})))
    r = run_script(SKILL, SCRIPT, str(bad))
    assert r.returncode == 1 and "contact needs" in r.stderr
    broken = tmp_path / "broken.json"
    broken.write_text("{nope")
    assert run_script(SKILL, SCRIPT, str(broken)).returncode == 2
    assert run_script(SKILL, SCRIPT).returncode == 2
    js = run_script(SKILL, SCRIPT, str(CONFIG), "--json")
    assert js.returncode == 0 and json.loads(js.stdout)["organization"] == "Example Ltd"


def test_assets():
    assets = FIXTURES.parent.parent / "skills" / "accessibility-statement" / "assets"
    assert json.loads((assets / "statement-config.example.json").read_text()) == m.EXAMPLE
    issue_form = (assets / "accessibility-issue.yml").read_text()
    assert issue_form.startswith("# GitHub issue form") and "name: Accessibility barrier" in issue_form
    form = (assets / "feedback-form.html").read_text()
    for skill, script, fn in (
        ("wcag-html-audit", "html_audit.py", "audit"),
        ("accessible-forms", "forms_check.py", "check"),
        ("aria-review", "aria_lint.py", "lint"),
    ):
        assert getattr(load_script(skill, script), fn)(form) == []
