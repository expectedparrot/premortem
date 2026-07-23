from __future__ import annotations

from pathlib import Path

import typer

from ..renderer import render_kv_panel
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Manage project metadata.")


@app.command("update")
def update_command(
    initiative: str | None = typer.Option(None, "--initiative", help="New initiative name."),
    description: str | None = typer.Option(None, "--description", help="New description."),
    failure: str | None = typer.Option(None, "--failure", help="New failure statement."),
    notes: str | None = typer.Option(None, "--notes", help="New notes."),
    id: str | None = typer.Option(None, "--id", help="New project ID."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Update project metadata in place without touching child entities (personas, reasons, graph, mitigations)."""
    command = "project update"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    changed: list[tuple[str, str, str]] = []
    try:
        meta = store.read_meta()
        if initiative is not None and initiative != meta.initiative:
            changed.append(("initiative", meta.initiative, initiative))
            meta.initiative = initiative
        if description is not None and description != (meta.description or ""):
            changed.append(("description", meta.description or "", description))
            meta.description = description
        if failure is not None and failure != meta.failure_statement:
            changed.append(("failure_statement", meta.failure_statement, failure))
            meta.failure_statement = failure
        if notes is not None and notes != (meta.notes or ""):
            changed.append(("notes", meta.notes or "", notes))
            meta.notes = notes
        if id is not None and id != meta.id:
            changed.append(("id", meta.id, id))
            meta.id = id
        if changed:
            with store.locked():
                store.write_meta(meta)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(
            command,
            {
                "updated": [field for field, _, _ in changed],
                "meta": meta.model_dump(mode="json"),
            },
            True,
            quiet,
        )
        return
    if not quiet:
        if not changed:
            render_kv_panel("Project unchanged", [("Project", meta.id)])
        else:
            items = [("Project", meta.id)]
            for field, old, new in changed:
                items.append((field, f"{old!r} -> {new!r}"))
            render_kv_panel("Project updated", items)
