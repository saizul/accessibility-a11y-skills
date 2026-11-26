"""Shared helpers: import skill scripts by path, run them, and locate fixtures."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
HTML = FIXTURES / "html"
CSS = FIXTURES / "css"


def load_script(skill: str, filename: str):
    path = SKILLS / skill / "scripts" / filename
    name = f"skill_{skill.replace('-', '_')}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_script(skill: str, filename: str, *args: str, stdin: str | None = None):
    path = SKILLS / skill / "scripts" / filename
    return subprocess.run(
        [sys.executable, str(path), *args],
        capture_output=True,
        text=True,
        input=stdin,
        timeout=60,
        check=False,
    )


def rules(findings: list[dict]) -> set[str]:
    return {f["rule"] for f in findings}


def page(body: str, head: str = "<title>T</title>") -> str:
    """Wrap a fragment in a minimal valid document (lang, title, main)."""
    return f'<!DOCTYPE html><html lang="en"><head>{head}</head><body><main id="main">{body}</main></body></html>'
