from __future__ import annotations

from pathlib import Path

import typer

from ..models import Persona
from ..renderer import render_kv_panel, table
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Manage personas.")


@app.command("add")
def add_persona(
    name: str = typer.Option(..., "--name"),
    role: str = typer.Option(..., "--role"),
    perspective: str | None = typer.Option(None, "--perspective"),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "persona add"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        with store.locked():
            persona_id = store.next_id("p", [p.id for p in store.list_personas()])
            persona = Persona(
                id=persona_id,
                name=name,
                role=role,
                perspective=perspective,
                created_at=now_utc(),
                notes=notes,
            )
            store.save_persona(persona)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, persona.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Persona added",
            [("ID", persona.id), ("Name", persona.name), ("Role", persona.role)],
        )


@app.command("list")
def list_personas(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "persona list"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        personas = store.list_personas()
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, [p.model_dump(mode="json") for p in personas], True, quiet)
        return
    if quiet:
        return
    tbl = table("ID", "Name", "Role", "Perspective")
    for p in personas:
        tbl.add_row(p.id, p.name, p.role, p.perspective or "")
    from ..renderer import console

    console.print(tbl)


@app.command("show")
def show_persona(
    persona_id: str,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "persona show"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        persona = store.get_persona(persona_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, persona.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            persona.id,
            [
                ("Name", persona.name),
                ("Role", persona.role),
                ("Perspective", persona.perspective or ""),
                ("Notes", persona.notes or ""),
            ],
        )


@app.command("edit")
def edit_persona(
    persona_id: str,
    name: str | None = typer.Option(None, "--name"),
    role: str | None = typer.Option(None, "--role"),
    perspective: str | None = typer.Option(None, "--perspective"),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "persona edit"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        persona = store.get_persona(persona_id)
        updates = persona.model_dump()
        if name is not None:
            updates["name"] = name
        if role is not None:
            updates["role"] = role
        if perspective is not None:
            updates["perspective"] = perspective
        if notes is not None:
            updates["notes"] = notes
        persona = Persona.model_validate(updates)
        store.save_persona(persona)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, persona.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel("Persona updated", [("ID", persona.id), ("Name", persona.name)])


@app.command("delete")
def delete_persona(
    persona_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "persona delete"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if not confirm:
            raise PremortemError("VALIDATION_FAILED", "Deletion requires --confirm.", hint="Re-run with `--confirm`.")
        store.delete_persona(persona_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, {"deleted": persona_id}, True, quiet)
        return
    if not quiet:
        render_kv_panel("Persona deleted", [("ID", persona_id)])
