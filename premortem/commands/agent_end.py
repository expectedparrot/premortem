from __future__ import annotations

from pathlib import Path

import typer

from .. import workflow as workflow_lib
from ..renderer import render_markdown
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Wrap up an agent-facilitated premortem workflow.")


@app.command("agent-end")
def agent_end(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "agent-end"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        raw_state = workflow_lib.phase_state(store)
        data = {
            "project_exists": raw_state.get("project_exists", True),
            "wrapup_guide": _packaged_wrapup_guide(),
        }
        if "counts" in raw_state:
            data["counts"] = raw_state["counts"]
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, data, True, quiet)
        return
    if quiet:
        return
    lines = [
        "# Premortem Agent End",
        "",
        f"- Project exists: `{data['project_exists']}`",
        "",
        data["wrapup_guide"],
    ]
    render_markdown("\n".join(lines))


def _packaged_wrapup_guide() -> str:
    guide_path = Path(__file__).resolve().parents[2] / "WRAPUP.md"
    return guide_path.read_text(encoding="utf-8") if guide_path.exists() else ""
