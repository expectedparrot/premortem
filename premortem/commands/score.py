from __future__ import annotations

from pathlib import Path

import typer

from ..models import Rating, Score
from ..renderer import render_kv_panel, table
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Score causal graph nodes.")

RATING_NUMERIC = {"low": 1, "medium": 2, "high": 3}


@app.command("set")
def set_score(
    node_id: str = typer.Option(..., "--node"),
    likelihood: Rating = typer.Option(..., "--likelihood"),
    impact: Rating = typer.Option(..., "--impact"),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "score set"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        store.get_node(node_id)  # validate node exists
        score = Score(
            node_id=node_id,
            likelihood=likelihood,
            impact=impact,
            created_at=now_utc(),
            notes=notes,
        )
        store.save_score(score)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, score.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Score set",
            [("Node", node_id), ("Likelihood", likelihood), ("Impact", impact)],
        )


@app.command("list")
def list_scores(
    sort_by: str = typer.Option("risk", "--sort", help="Sort by: risk, likelihood, impact"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "score list"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        scores = store.list_scores()
        nodes = {n.id: n for n in store.list_nodes()}
    except PremortemError as err:
        fail(command, err, json_flag)

    def risk_value(s: Score) -> int:
        return RATING_NUMERIC[s.likelihood] * RATING_NUMERIC[s.impact]

    if sort_by == "risk":
        scores.sort(key=risk_value, reverse=True)
    elif sort_by == "likelihood":
        scores.sort(key=lambda s: RATING_NUMERIC[s.likelihood], reverse=True)
    elif sort_by == "impact":
        scores.sort(key=lambda s: RATING_NUMERIC[s.impact], reverse=True)

    if json_flag:
        finish(command, [s.model_dump(mode="json") for s in scores], True, quiet)
        return
    if quiet:
        return
    tbl = table("Node", "Label", "Likelihood", "Impact", "Risk")
    for s in scores:
        label = nodes[s.node_id].label if s.node_id in nodes else "?"
        risk = RATING_NUMERIC[s.likelihood] * RATING_NUMERIC[s.impact]
        tbl.add_row(s.node_id, label[:50], s.likelihood, s.impact, str(risk))
    from ..renderer import console

    console.print(tbl)


@app.command("show")
def show_score(
    node_id: str,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "score show"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        score = store.get_score(node_id)
        node = store.get_node(node_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, score.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        risk = RATING_NUMERIC[score.likelihood] * RATING_NUMERIC[score.impact]
        render_kv_panel(
            f"Score: {node_id}",
            [
                ("Label", node.label),
                ("Likelihood", score.likelihood),
                ("Impact", score.impact),
                ("Risk", str(risk)),
                ("Notes", score.notes or ""),
            ],
        )
