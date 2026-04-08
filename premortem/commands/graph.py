from __future__ import annotations

from pathlib import Path

import typer

from ..models import Edge, Node
from ..renderer import render_kv_panel, table
from ..store import PremortemError, now_utc
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Manage the causal graph.")


@app.command("add-node")
def add_node(
    label: str = typer.Option(..., "--label"),
    reason: str | None = typer.Option(None, "--reason", help="Link to a reason ID."),
    notes: str | None = typer.Option(None, "--notes"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph add-node"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if reason:
            store.get_reason(reason)  # validate exists
        with store.locked():
            node_id = store.next_id("n", [n.id for n in store.list_nodes()])
            node = Node(
                id=node_id,
                label=label,
                reason_id=reason,
                created_at=now_utc(),
                notes=notes,
            )
            store.save_node(node)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, node.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Node added",
            [("ID", node.id), ("Label", node.label), ("Reason", node.reason_id or "—")],
        )


@app.command("add-edge")
def add_edge(
    source: str = typer.Option(..., "--from", help="Source node ID (cause)."),
    target: str = typer.Option(..., "--to", help="Target node ID (effect)."),
    label: str | None = typer.Option(None, "--label"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph add-edge"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        store.get_node(source)
        store.get_node(target)
        with store.locked():
            edge_id = store.next_id("e", [e.id for e in store.list_edges()])
            edge = Edge(
                id=edge_id,
                source=source,
                target=target,
                label=label,
                created_at=now_utc(),
            )
            store.save_edge(edge)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, edge.model_dump(mode="json"), True, quiet)
        return
    if not quiet:
        render_kv_panel(
            "Edge added",
            [("ID", edge.id), ("From", edge.source), ("To", edge.target), ("Label", edge.label or "—")],
        )


@app.command("list")
def list_graph(
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph list"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        nodes = store.list_nodes()
        edges = store.list_edges()
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(
            command,
            {"nodes": [n.model_dump(mode="json") for n in nodes], "edges": [e.model_dump(mode="json") for e in edges]},
            True,
            quiet,
        )
        return
    if quiet:
        return
    from ..renderer import console

    ntbl = table("ID", "Label", "Reason")
    for n in nodes:
        ntbl.add_row(n.id, n.label, n.reason_id or "—")
    console.print(ntbl)

    if edges:
        etbl = table("ID", "From", "To", "Label")
        for e in edges:
            etbl.add_row(e.id, e.source, e.target, e.label or "—")
        console.print(etbl)


@app.command("show")
def show_node(
    node_id: str,
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph show"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        node = store.get_node(node_id)
        edges = store.list_edges()
    except PremortemError as err:
        fail(command, err, json_flag)
    incoming = [e for e in edges if e.target == node_id]
    outgoing = [e for e in edges if e.source == node_id]
    if json_flag:
        finish(
            command,
            {
                "node": node.model_dump(mode="json"),
                "incoming": [e.model_dump(mode="json") for e in incoming],
                "outgoing": [e.model_dump(mode="json") for e in outgoing],
            },
            True,
            quiet,
        )
        return
    if not quiet:
        render_kv_panel(
            node.id,
            [
                ("Label", node.label),
                ("Reason", node.reason_id or "—"),
                ("Incoming", ", ".join(f"{e.source}->{e.target}" for e in incoming) or "none"),
                ("Outgoing", ", ".join(f"{e.source}->{e.target}" for e in outgoing) or "none"),
                ("Notes", node.notes or ""),
            ],
        )


@app.command("remove-node")
def remove_node(
    node_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph remove-node"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if not confirm:
            raise PremortemError("VALIDATION_FAILED", "Deletion requires --confirm.", hint="Re-run with `--confirm`.")
        store.delete_node(node_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, {"deleted": node_id}, True, quiet)
        return
    if not quiet:
        render_kv_panel("Node removed", [("ID", node_id)])


@app.command("remove-edge")
def remove_edge(
    edge_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph remove-edge"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        if not confirm:
            raise PremortemError("VALIDATION_FAILED", "Deletion requires --confirm.", hint="Re-run with `--confirm`.")
        store.delete_edge(edge_id)
    except PremortemError as err:
        fail(command, err, json_flag)
    if json_flag:
        finish(command, {"deleted": edge_id}, True, quiet)
        return
    if not quiet:
        render_kv_panel("Edge removed", [("ID", edge_id)])


@app.command("export")
def export_graph(
    format: str = typer.Option("dot", "--format", help="Export format: dot"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "graph export"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        nodes = store.list_nodes()
        edges = store.list_edges()
    except PremortemError as err:
        fail(command, err, json_flag)
    lines = ["digraph premortem {", '  rankdir=LR;', '  node [shape=box, style=rounded];']
    for n in nodes:
        escaped = n.label.replace('"', '\\"')
        lines.append(f'  {n.id} [label="{escaped}"];')
    for e in edges:
        attrs = f' [label="{e.label}"]' if e.label else ""
        lines.append(f"  {e.source} -> {e.target}{attrs};")
    lines.append("}")
    dot_text = "\n".join(lines) + "\n"
    if json_flag:
        finish(command, {"format": "dot", "content": dot_text}, True, quiet)
        return
    if not quiet:
        from ..renderer import console

        console.print(dot_text)
