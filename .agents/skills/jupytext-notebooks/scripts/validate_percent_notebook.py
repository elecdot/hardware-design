#!/usr/bin/env python3
"""Validate a Jupytext percent-format notebook pair."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


CELL_MARKER_RE = re.compile(r"^# %%($| .*)")
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
MARKDOWN_CELL_MARKER = "# %% [markdown]"


@dataclass
class ValidationResult:
    path: str
    errors: list[str]


def paired_percent_path(path: Path) -> Path:
    if path.suffix == ".ipynb":
        return path.with_suffix(".py")
    return path


def read_source(raw_path: str) -> tuple[str, str]:
    if raw_path == "-":
        return "<stdin>", sys.stdin.read()

    input_path = Path(raw_path)
    percent_path = paired_percent_path(input_path)

    if input_path.suffix not in {".ipynb", ".py"}:
        raise ValueError(f"expected a .ipynb or .py path, got: {input_path}")
    if not percent_path.exists():
        raise FileNotFoundError(f"percent-format file not found: {percent_path}")
    if not percent_path.is_file():
        raise ValueError(f"not a file: {percent_path}")

    return str(percent_path), percent_path.read_text(encoding="utf-8")


def looks_like_notebook_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") and '"cells"' in text and '"nbformat"' in text


def validate_source(path: str, text: str) -> ValidationResult:
    errors: list[str] = []

    if not text.strip():
        errors.append("file is empty")

    if looks_like_notebook_json(text):
        errors.append("file looks like raw .ipynb JSON, not py:percent text")

    lines = text.splitlines()
    marker_lines: list[int] = []
    malformed_markers: list[int] = []
    in_markdown_cell = False

    for lineno, line in enumerate(lines, start=1):
        if line.startswith(CONFLICT_MARKERS):
            errors.append(f"unresolved merge conflict marker at line {lineno}")

        if line.startswith("# %%"):
            if CELL_MARKER_RE.match(line):
                marker_lines.append(lineno)
                in_markdown_cell = line.startswith(MARKDOWN_CELL_MARKER)
            else:
                malformed_markers.append(lineno)
        elif line.startswith("#%%"):
            malformed_markers.append(lineno)
        elif in_markdown_cell and line and not line.startswith("#"):
            errors.append(
                f"uncommented text in markdown cell at line {lineno}; "
                "markdown cell content should start with '#'",
            )

    if not marker_lines:
        errors.append("no percent-format cell markers found; expected lines like '# %%'")

    for lineno in malformed_markers:
        errors.append(f"malformed cell marker at line {lineno}; use '# %%' or '# %% [markdown]'")

    return ValidationResult(path=path, errors=errors)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the structure of a Jupytext py:percent notebook file.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more .ipynb paths, .py percent-format paths, or '-' for stdin.",
    )
    args = parser.parse_args()

    failed = False
    for raw_path in args.paths:
        try:
            path, text = read_source(raw_path)
            result = validate_source(path, text)
        except (OSError, ValueError) as exc:
            failed = True
            print(f"[FAIL] {raw_path}: {exc}", file=sys.stderr)
            continue

        if result.errors:
            failed = True
            for error in result.errors:
                print(f"[FAIL] {result.path}: {error}", file=sys.stderr)
        else:
            print(f"[OK] {result.path}: percent-format structure looks valid")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
