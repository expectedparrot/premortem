from __future__ import annotations

from pathlib import Path

import typer

from .. import docs as docs_lib
from .. import workflow as workflow_lib
from ..renderer import render_markdown, table
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Show workflow checklists, current phase, and next steps.")


def _checklist_data(phase: str) -> dict:
    if phase not in workflow_lib.CHECKLISTS:
        raise PremortemError("ID_NOT_FOUND", "Workflow phase not found.", context=phase)
    return {
        "phase": phase,
        "doc_topic": workflow_lib.PHASE_DOCS.get(phase),
        "checklist": workflow_lib.CHECKLISTS[phase],
    }


@app.command("checklist")
def checklist(
    phase: str = typer.Option("overview", "--phase", help="Workflow phase, or overview."),
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "workflow checklist"
    json_flag = should_emit_json(human)
    try:
        if phase == "overview":
            data = {"phases": [{"phase": key, "checklist": value} for key, value in workflow_lib.CHECKLISTS.items()]}
        else:
            data = _checklist_data(phase)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, data, True, quiet)
        return
    if quiet:
        return
    if phase == "overview":
        lines = ["# Workflow Checklist", ""]
        for item in data["phases"]:
            lines.append(f"## {item['phase']}")
            lines.extend(f"- {entry}" for entry in item["checklist"])
            lines.append("")
        render_markdown("\n".join(lines))
    else:
        render_markdown("# " + data["phase"] + "\n\n" + "\n".join(f"- {entry}" for entry in data["checklist"]))


@app.command("guide")
def guide(
    phase: str,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "workflow guide"
    json_flag = should_emit_json(human)
    try:
        data = _checklist_data(phase)
        topic = data["doc_topic"]
        markdown = docs_lib.read_topic(topic) if topic else ""
    except (PremortemError, KeyError) as err:
        if isinstance(err, PremortemError):
            fail(command, err, json_flag)
        fail(command, PremortemError("ID_NOT_FOUND", "Workflow guide not found.", context=phase), json_flag)
    if json_flag:
        finish(command, {"phase": phase, "doc_topic": topic, "markdown": markdown, "checklist": data["checklist"]}, True, quiet)
        return
    if not quiet:
        render_markdown(markdown + "\n\n## Checklist\n\n" + "\n".join(f"- {entry}" for entry in data["checklist"]))


@app.command("phase")
def phase_command(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "workflow phase"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        phase = workflow_lib.infer_phase(store)
        counts = workflow_lib.project_counts(store)
    except PremortemError as err:
        fail(command, err, json_flag)
    data = {"phase": phase, "counts": counts}
    if json_flag:
        finish(command, data, True, quiet)
        return
    if not quiet:
        from ..renderer import render_kv_panel

        render_kv_panel("Workflow phase", [("Phase", phase), *[(key, str(value)) for key, value in counts.items()]])


@app.command("next")
def next_command(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "workflow next"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        data = workflow_lib.phase_state(store)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, data, True, quiet)
        return
    if quiet:
        return
    tbl = table("Step", "Command")
    for step in data["recommended_next_steps"]:
        tbl.add_row(step["label"], step["command"])
    from ..renderer import console, render_kv_panel

    panel_items = [("Phase", data["phase"])]
    if not data.get("project_exists", True):
        panel_items.append(("Project", "not initialized"))
        panel_items.append(("Project dir", data["project_dir"]))
    render_kv_panel("Workflow next", panel_items)
    console.print(tbl)


@app.command("artifacts")
def artifacts(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "workflow artifacts"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        data = {"artifacts": workflow_lib.artifacts(store)}
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, data, True, quiet)
        return
    if quiet:
        return
    tbl = table("Path", "Exists", "Size")
    for item in data["artifacts"]:
        tbl.add_row(item["path"], str(item["exists"]), "" if item["size"] is None else str(item["size"]))
    from ..renderer import console

    console.print(tbl)
