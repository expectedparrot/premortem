from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer

from ..renderer import emit_json, render_error
from ..store import PremortemError, ProjectStore, default_project_dir, error_envelope, make_json_envelope

ProjectDirOption = typer.Option(None, "--project-dir", help="Override the project directory.")
HumanOption = typer.Option(False, "--human", help="Emit human-readable Rich output instead of JSON.")
QuietOption = typer.Option(False, "--quiet", help="Suppress non-error output.")


def resolve_project_dir(project_dir: Path | None) -> Path:
    """Resolve which directory to treat as the premortem project root.

    Resolution order (highest precedence first):
    1. Explicit ``--project-dir`` flag (``project_dir`` argument).
    2. ``PREMORTEM_PROJECT_DIR`` env var.
    3. ``./.premortem`` in cwd (legacy fallback).
    """
    if project_dir is not None:
        return project_dir
    return default_project_dir()


def should_emit_json(human_flag: bool) -> bool:
    if human_flag:
        return False
    return os.getenv("PREMORTEM_HUMAN_OUTPUT", "").lower() != "true"


def store_for(project_dir: Path | None) -> ProjectStore:
    return ProjectStore(resolve_project_dir(project_dir))


def finish(command: str, data: Any, json_output: bool, quiet: bool, warnings: list[str] | None = None, next_steps: list[str] | None = None) -> None:
    if json_output:
        emit_json(make_json_envelope(command, data, warnings=warnings, next_steps=next_steps))
    elif not quiet:
        return


def fail(command: str, err: PremortemError, json_output: bool) -> None:
    if json_output:
        emit_json(error_envelope(command, err))
    else:
        render_error(err)
    raise typer.Exit(code=1)
