from __future__ import annotations

from pathlib import Path

import typer

from ..models import ProjectMeta
from ..renderer import render_kv_panel
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Initialize a new pre-mortem project.")


@app.command("init")
def init_command(
    initiative: str = typer.Option(..., "--initiative", help="Name of the initiative."),
    failure: str = typer.Option(..., "--failure", help="Definitive failure statement. State as certain fact, no hedging."),
    description: str | None = typer.Option(None, "--description", help="Longer description of the initiative."),
    id: str | None = typer.Option(None, "--id"),
    notes: str | None = typer.Option(None, "--notes"),
    force: bool = typer.Option(False, "--force"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "init"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        timestamp = now_utc()
        project_id = id or f"pm_{timestamp.year}_{timestamp.strftime('%m%d%H%M%S')}"
        meta = ProjectMeta(
            id=project_id,
            initiative=initiative,
            description=description,
            failure_statement=failure,
            created_at=timestamp,
            updated_at=timestamp,
            phase="personas",
            notes=notes,
        )
        store.init_project(meta, force=force)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, meta.model_dump(mode="json"), True, quiet, next_steps=["premortem persona add"])
        return
    if not quiet:
        render_kv_panel(
            "Pre-mortem initialized",
            [
                ("Project", meta.id),
                ("Initiative", meta.initiative),
                ("Failure", meta.failure_statement),
                ("Next step", "premortem persona add"),
            ],
        )
