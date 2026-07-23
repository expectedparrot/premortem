from __future__ import annotations

from pathlib import Path

import typer

from ..ingest import (
    ingest_mitigations,
    ingest_personas,
    ingest_reasons,
    ingest_scores,
    load_results_file,
)
from ..renderer import render_kv_panel, table
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Ingest EDSL results into the project store.")

ReplaceOption = typer.Option(False, "--replace", help="Clear existing entities of this type before ingesting.")


@app.command("personas")
def ingest_personas_cmd(
    from_file: Path = typer.Option(..., "--from", help="Path to JSON results file."),
    replace: bool = ReplaceOption,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "ingest personas"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        data = load_results_file(from_file)
        if data["entity_type"] != "personas":
            raise PremortemError("VALIDATION_FAILED", f"Expected entity_type 'personas', got '{data['entity_type']}'.")
        if replace:
            for p in store.list_personas():
                store.delete_persona(p.id)
        created = ingest_personas(store, data["rows"])
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        if quiet:
            payload = {"ok": True, "created": len(created), "ids": [p.id for p in created]}
        else:
            payload = {"created": len(created), "personas": [p.model_dump(mode="json") for p in created]}
        finish(command, payload, True, quiet)
        return
    if not quiet:
        tbl = table("ID", "Name", "Role")
        for p in created:
            tbl.add_row(p.id, p.name, p.role)
        from ..renderer import console

        console.print(f"Ingested {len(created)} personas")
        console.print(tbl)


@app.command("reasons")
def ingest_reasons_cmd(
    from_file: Path = typer.Option(..., "--from", help="Path to JSON results file."),
    replace: bool = ReplaceOption,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "ingest reasons"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        data = load_results_file(from_file)
        if data["entity_type"] != "reasons":
            raise PremortemError("VALIDATION_FAILED", f"Expected entity_type 'reasons', got '{data['entity_type']}'.")
        if replace:
            for r in store.list_reasons():
                store.delete_reason(r.id)
        created, warnings = ingest_reasons(store, data["rows"])
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        if quiet:
            payload = {"ok": True, "created": len(created), "ids": [r.id for r in created]}
        else:
            payload = {"created": len(created), "reasons": [r.model_dump(mode="json") for r in created]}
        finish(
            command,
            payload,
            True,
            quiet,
            warnings=warnings,
        )
        return
    if not quiet:
        from ..renderer import console

        console.print(f"Ingested {len(created)} reasons")
        for w in warnings:
            console.print(f"[yellow]Warning:[/yellow] {w}")
        tbl = table("ID", "Persona", "Kind", "Text")
        for r in created:
            tbl.add_row(r.id, r.persona_id, r.kind, r.text[:60])
        console.print(tbl)


@app.command("scores")
def ingest_scores_cmd(
    from_file: Path = typer.Option(..., "--from", help="Path to JSON results file."),
    strategy: str = typer.Option("median", "--strategy", help="Aggregation: median, mode, max, first."),
    replace: bool = ReplaceOption,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "ingest scores"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        data = load_results_file(from_file)
        if data["entity_type"] != "scores":
            raise PremortemError("VALIDATION_FAILED", f"Expected entity_type 'scores', got '{data['entity_type']}'.")
        if replace:
            for s in store.list_scores():
                (store.root / "scores" / f"{s.node_id}.json").unlink(missing_ok=True)
        created = ingest_scores(store, data["rows"], strategy=strategy)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        if quiet:
            payload = {"ok": True, "created": len(created), "ids": [s.node_id for s in created]}
        else:
            payload = {"created": len(created), "scores": [s.model_dump(mode="json") for s in created]}
        finish(command, payload, True, quiet)
        return
    if not quiet:
        from ..renderer import console

        console.print(f"Ingested {len(created)} scores (strategy: {strategy})")
        tbl = table("Node", "Likelihood", "Impact")
        for s in created:
            tbl.add_row(s.node_id, s.likelihood, s.impact)
        console.print(tbl)


@app.command("mitigations")
def ingest_mitigations_cmd(
    from_file: Path = typer.Option(..., "--from", help="Path to JSON results file."),
    replace: bool = ReplaceOption,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "ingest mitigations"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        data = load_results_file(from_file)
        if data["entity_type"] != "mitigations":
            raise PremortemError("VALIDATION_FAILED", f"Expected entity_type 'mitigations', got '{data['entity_type']}'.")
        if replace:
            for m in store.list_mitigations():
                store.delete_mitigation(m.id)
        created = ingest_mitigations(store, data["rows"])
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        if quiet:
            payload = {"ok": True, "created": len(created), "ids": [m.id for m in created]}
        else:
            payload = {"created": len(created), "mitigations": [m.model_dump(mode="json") for m in created]}
        finish(command, payload, True, quiet)
        return
    if not quiet:
        from ..renderer import console

        console.print(f"Ingested {len(created)} mitigations")
        tbl = table("ID", "Nodes", "Text")
        for m in created:
            tbl.add_row(m.id, ", ".join(m.node_ids), m.text[:60])
        console.print(tbl)
