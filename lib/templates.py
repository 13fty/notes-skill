"""Template loading and rendering for obsidian-skill.

Reads .md template files from the templates/ directory and renders them
with variable substitution ({{variable}} syntax).
"""

import re
from datetime import date
from pathlib import Path


# ── Template discovery ──────────────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _resolve(name: str) -> Path:
    """Resolve a template name to its file path.

    Names can be bare ('daily') or with extension ('daily.md').
    """
    if not name.endswith(".md"):
        name = f"{name}.md"
    return _TEMPLATE_DIR / name


def list_templates() -> list[str]:
    """Return names of all available templates (without .md extension)."""
    if not _TEMPLATE_DIR.exists():
        return []
    return sorted(
        p.stem for p in _TEMPLATE_DIR.glob("*.md")
    )


def load_template(name: str) -> str:
    """Load a template by name, returning raw markdown text.

    Raises FileNotFoundError if the template doesn't exist.
    """
    path = _resolve(name)
    if not path.exists():
        raise FileNotFoundError(f"Template '{name}' not found at {path}")
    return path.read_text(encoding="utf-8")


# ── Rendering ──────────────────────────────────────────────────────────────────

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


# Built-in variable providers
_BUILTINS = {
    "date": lambda: date.today().isoformat(),
    "year": lambda: str(date.today().year),
    "month": lambda: f"{date.today().month:02d}",
    "day": lambda: f"{date.today().day:02d}",
    "datetime": lambda: date.today().strftime("%Y-%m-%d %H:%M"),
}


def render_template(name: str, variables: dict[str, str] | None = None) -> str:
    """Load a template and substitute variables.

    Supports {{variable}} syntax. Built-in variables (date, year, month, day, datetime)
    are available automatically and can be overridden by passing them in `variables`.

    Example:
        render_template("daily", {"project": "MyProject"})
    """
    text = load_template(name)

    # Merge builtins with user-provided variables (user overrides builtins)
    vars_: dict[str, str] = {}
    for key, fn in _BUILTINS.items():
        vars_[key] = fn()
    if variables:
        vars_.update(variables)

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        return vars_.get(var, match.group(0))

    return _VAR_RE.sub(_replace, text)


def render_template_string(template_text: str, variables: dict[str, str] | None = None) -> str:
    """Render a template string (not from a file) with variable substitution.

    Useful when you have template content in memory rather than on disk.
    """
    vars_: dict[str, str] = {}
    for key, fn in _BUILTINS.items():
        vars_[key] = fn()
    if variables:
        vars_.update(variables)

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        return vars_.get(var, match.group(0))

    return _VAR_RE.sub(_replace, template_text)


def create_note(name: str, variables: dict[str, str] | None = None) -> str:
    """Convenience: render a template for creating a new note."""
    return render_template(name, variables)
