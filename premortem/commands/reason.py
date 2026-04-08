from __future__ import annotations

from pathlib import Path

import typer

from ..models import Reason, ReasonKind
from ..renderer import render_kv_panel, table
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Manage failure reasons.")


@app.command("add")
def add_reason(
    persona_id: str = typer.Option(..., "--persona"),
    kind: ReasonKind = typer.Option(..., "--kind", help="episodic (event chain) or structural (underlying factor)"),
    text: str = typer.Option(..., "--text"),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "reason add"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        store.get_persona(persona_id)  # validate persona exists
        with store.locked():
            reason_id = store.next_id("r", [r.id for r in store.list_reasons()])
            reason = Reason(
                id=reason_id,
                persona_id=persona_id,
                kind=kind,
                text=text,
                created_at=now_utc(),
                notes=notes,
            )
            store.save_reason(reason)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, reason.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Reason added",
            [("ID", reason.id), ("Persona", reason.persona_id), ("Kind", reason.kind), ("Text", reason.text)],
        )


@app.command("list")
def list_reasons(
    kind: ReasonKind | None = typer.Option(None, "--kind"),
    persona: str | None = typer.Option(None, "--persona"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "reason list"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        reasons = store.list_reasons()
    except PremortemError as err:
        fail(command, err, json_flag)
    if kind:
        reasons = [r for r in reasons if r.kind == kind]
    if persona:
        reasons = [r for r in reasons if r.persona_id == persona]
    if json_flag:
        finish(command, [r.model_dump(mode="json") for r in reasons], True, quiet)
        return
    if quiet:
        return
    tbl = table("ID", "Persona", "Kind", "Text")
    for r in reasons:
        tbl.add_row(r.id, r.persona_id, r.kind, r.text[:80])
    from ..renderer import console

    console.print(tbl)


@app.command("show")
def show_reason(
    reason_id: str,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "reason show"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        reason = store.get_reason(reason_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, reason.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            reason.id,
            [
                ("Persona", reason.persona_id),
                ("Kind", reason.kind),
                ("Text", reason.text),
                ("Notes", reason.notes or ""),
            ],
        )


@app.command("edit")
def edit_reason(
    reason_id: str,
    text: str | None = typer.Option(None, "--text"),
    kind: ReasonKind | None = typer.Option(None, "--kind"),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "reason edit"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        reason = store.get_reason(reason_id)
        updates = reason.model_dump()
        if text is not None:
            updates["text"] = text
        if kind is not None:
            updates["kind"] = kind
        if notes is not None:
            updates["notes"] = notes
        reason = Reason.model_validate(updates)
        store.save_reason(reason)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, reason.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel("Reason updated", [("ID", reason.id)])


@app.command("delete")
def delete_reason(
    reason_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "reason delete"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if not confirm:
            raise PremortemError("VALIDATION_FAILED", "Deletion requires --confirm.", hint="Re-run with `--confirm`.")
        store.delete_reason(reason_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, {"deleted": reason_id}, True, quiet)
        return
    if not quiet:
        render_kv_panel("Reason deleted", [("ID", reason_id)])
