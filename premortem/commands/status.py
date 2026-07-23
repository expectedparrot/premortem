from __future__ import annotations

from pathlib import Path

import typer

from ..renderer import render_kv_panel
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Show project status.")


@app.command("status")
def status_command(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "status"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        reasons = store.list_reasons()
        nodes = store.list_nodes()
        edges = store.list_edges()
        scores = store.list_scores()
        mitigations = store.list_mitigations()
    except PremortemError as err:
        fail(command, err, json_flag)
    episodic = [r for r in reasons if r.kind == "episodic"]
    structural = [r for r in reasons if r.kind == "structural"]
    data = {
        "initiative": meta.initiative,
        "failure_statement": meta.failure_statement,
        "phase": meta.phase,
        "personas": len(personas),
        "reasons_episodic": len(episodic),
        "reasons_structural": len(structural),
        "graph_nodes": len(nodes),
        "graph_edges": len(edges),
        "scores": len(scores),
        "mitigations": len(mitigations),
    }
    if json_flag:
        finish(command, data, True, quiet)
        return
    if not quiet:
        render_kv_panel(
            f"Pre-mortem: {meta.initiative}",
            [
                ("Failure", meta.failure_statement[:100]),
                ("Phase", meta.phase),
                ("Personas", str(len(personas))),
                ("Reasons (episodic)", str(len(episodic))),
                ("Reasons (structural)", str(len(structural))),
                ("Graph nodes", str(len(nodes))),
                ("Graph edges", str(len(edges))),
                ("Scores", str(len(scores))),
                ("Mitigations", str(len(mitigations))),
            ],
        )
