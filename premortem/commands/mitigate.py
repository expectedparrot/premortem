from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..models import Mitigation
from ..renderer import render_kv_panel, table
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Manage mitigations.")


@app.command("add")
def add_mitigation(
    text: str = typer.Option(..., "--text"),
    nodes: str = typer.Option(..., "--nodes", help="Comma-separated node IDs this mitigates."),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "mitigate add"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        node_ids = [n.strip() for n in nodes.split(",") if n.strip()]
        for nid in node_ids:
            store.get_node(nid)  # validate each node exists
        with store.locked():
            mit_id = store.next_id("m", [m.id for m in store.list_mitigations()])
            mitigation = Mitigation(
                id=mit_id,
                text=text,
                node_ids=node_ids,
                created_at=now_utc(),
                notes=notes,
            )
            store.save_mitigation(mitigation)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, mitigation.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Mitigation added",
            [("ID", mitigation.id), ("Nodes", ", ".join(mitigation.node_ids)), ("Text", mitigation.text)],
        )


@app.command("list")
def list_mitigations(
    node: str | None = typer.Option(None, "--node", help="Filter by node ID."),
    full: bool = typer.Option(False, "--full", help="Print each mitigation as a full block instead of a truncated table row."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "mitigate list"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        mitigations = store.list_mitigations()
    except PremortemError as err:
        fail(command, err, json_flag)
    if node:
        mitigations = [m for m in mitigations if node in m.node_ids]
    if json_flag:
        finish(command, [m.model_dump(mode="json") for m in mitigations], True, quiet)
        return
    if quiet:
        return
    from ..renderer import console

    if full:
        from rich.panel import Panel

        for m in mitigations:
            body_lines = [
                f"[bold]Nodes:[/bold] {', '.join(m.node_ids)}",
                "",
                m.text,
            ]
            if m.notes:
                body_lines.extend(["", f"[bold]Notes:[/bold] {m.notes}"])
            console.print(Panel("\n".join(body_lines), title=m.id))
        return

    tbl = table("ID", "Nodes", "Text")
    for m in mitigations:
        snippet = m.text if len(m.text) <= 80 else m.text[:80].rstrip() + "…"
        tbl.add_row(m.id, ", ".join(m.node_ids), snippet)
    console.print(tbl)
    console.print(
        "[dim](text truncated to 80 chars; use --full or `mitigate show <id>` for body)[/dim]"
    )


@app.command("show")
def show_mitigation(
    mitigation_id: str,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "mitigate show"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        mitigation = store.get_mitigation(mitigation_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, mitigation.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            mitigation.id,
            [
                ("Text", mitigation.text),
                ("Nodes", ", ".join(mitigation.node_ids)),
                ("Notes", mitigation.notes or ""),
            ],
        )


@app.command("edit")
def edit_mitigation(
    mitigation_id: str,
    text: str | None = typer.Option(None, "--text"),
    nodes: str | None = typer.Option(None, "--nodes", help="Comma-separated node IDs."),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "mitigate edit"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        mitigation = store.get_mitigation(mitigation_id)
        updates = mitigation.model_dump()
        if text is not None:
            updates["text"] = text
        if nodes is not None:
            node_ids = [n.strip() for n in nodes.split(",") if n.strip()]
            for nid in node_ids:
                store.get_node(nid)
            updates["node_ids"] = node_ids
        if notes is not None:
            updates["notes"] = notes
        mitigation = Mitigation.model_validate(updates)
        store.save_mitigation(mitigation)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, mitigation.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel("Mitigation updated", [("ID", mitigation.id)])


@app.command("delete")
def delete_mitigation(
    mitigation_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "mitigate delete"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if not confirm:
            raise PremortemError("VALIDATION_FAILED", "Deletion requires --confirm.", hint="Re-run with `--confirm`.")
        store.delete_mitigation(mitigation_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, {"deleted": mitigation_id}, True, quiet)
        return
    if not quiet:
        render_kv_panel("Mitigation deleted", [("ID", mitigation_id)])
