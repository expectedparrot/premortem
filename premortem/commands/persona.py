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


@app.command("rename")
def rename_persona(
    persona_id: str,
    new_name: str = typer.Option(..., "--new-name", help="The new name for this persona."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would change without saving."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Rename a persona and propagate the rename through `role` and `perspective` fields."""
    command = "persona rename"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        persona = store.get_persona(persona_id)
        old_name = persona.name
        if not old_name:
            raise PremortemError("VALIDATION_FAILED", "Persona has no existing name to rename.", context=persona_id)
        old_role = persona.role or ""
        old_perspective = persona.perspective or ""
        new_role = old_role.replace(old_name, new_name) if old_name else old_role
        new_perspective = old_perspective.replace(old_name, new_name) if old_name else old_perspective
        changes: list[tuple[str, str, str]] = [("name", old_name, new_name)]
        if new_role != old_role:
            changes.append(("role", old_role, new_role))
        if new_perspective != old_perspective:
            changes.append(("perspective", old_perspective, new_perspective))
        if not dry_run:
            updates = persona.model_dump()
            updates["name"] = new_name
            updates["role"] = new_role
            updates["perspective"] = new_perspective if new_perspective else None
            persona = Persona.model_validate(updates)
            store.save_persona(persona)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(
            command,
            {
                "id": persona.id,
                "dry_run": dry_run,
                "changes": [
                    {"field": field, "old": old, "new": new} for field, old, new in changes
                ],
                "persona": persona.model_dump(mode="json"),
            },
            True,
            quiet,
        )
        return
    if not quiet:
        items: list[tuple[str, str]] = [("ID", persona.id)]
        for field, old, new in changes:
            items.append((field, f"{old!r} -> {new!r}"))
        title = "Persona rename (dry-run)" if dry_run else "Persona renamed"
        render_kv_panel(title, items)


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
