from __future__ import annotations

from pathlib import Path

import typer

from ..renderer import render_markdown
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Generate reports.")

RATING_NUMERIC = {"low": 1, "medium": 2, "high": 3}


@app.command("generate")
def generate_report(
    output: str | None = typer.Option(None, "--output", help="Write markdown to file instead of stdout."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "report generate"
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

    persona_map = {p.id: p for p in personas}
    node_map = {n.id: n for n in nodes}
    score_map = {s.node_id: s for s in scores}

    lines: list[str] = []
    lines.append(f"# Pre-mortem: {meta.initiative}")
    lines.append("")
    if meta.description:
        lines.append(f"{meta.description}")
        lines.append("")
    lines.append(f"**Failure statement:** {meta.failure_statement}")
    lines.append("")

    # personas
    lines.append("## Personas")
    lines.append("")
    for p in personas:
        lines.append(f"- **{p.name}** — {p.role}")
        if p.perspective:
            lines.append(f"  - Perspective: {p.perspective}")
    lines.append("")

    # episodic reasons
    episodic = [r for r in reasons if r.kind == "episodic"]
    if episodic:
        lines.append("## Round 1: Event Chains (Prospective Hindsight)")
        lines.append("")
        for r in episodic:
            pname = persona_map[r.persona_id].name if r.persona_id in persona_map else r.persona_id
            lines.append(f"- **{pname}** ({r.id}): {r.text}")
        lines.append("")

    # structural reasons
    structural = [r for r in reasons if r.kind == "structural"]
    if structural:
        lines.append("## Round 2: Structural Factors (Historical Foresight)")
        lines.append("")
        for r in structural:
            pname = persona_map[r.persona_id].name if r.persona_id in persona_map else r.persona_id
            lines.append(f"- **{pname}** ({r.id}): {r.text}")
        lines.append("")

    # causal graph summary
    if nodes:
        lines.append("## Causal Graph")
        lines.append("")
        for n in nodes:
            incoming = [e for e in edges if e.target == n.id]
            outgoing = [e for e in edges if e.source == n.id]
            parts = [f"**{n.id}**: {n.label}"]
            rids = list(getattr(n, "reason_ids", []) or [])
            if rids:
                # Mark multi-source convergence so the report makes the signal visible
                marker = f" [{len(rids)}× cited]" if len(rids) > 1 else ""
                parts.append(f"  reasons: {', '.join(rids)}{marker}")
            if incoming:
                parts.append(f"  caused by: {', '.join(e.source for e in incoming)}")
            if outgoing:
                parts.append(f"  leads to: {', '.join(e.target for e in outgoing)}")
            lines.append("- " + " | ".join(parts))
        lines.append("")

    # scores ranked by risk
    scored_nodes = [(n, score_map[n.id]) for n in nodes if n.id in score_map]
    scored_nodes.sort(key=lambda pair: RATING_NUMERIC[pair[1].likelihood] * RATING_NUMERIC[pair[1].impact], reverse=True)
    if scored_nodes:
        lines.append("## Risk Ranking")
        lines.append("")
        lines.append("| Node | Label | Likelihood | Impact | Risk |")
        lines.append("|------|-------|------------|--------|------|")
        for n, s in scored_nodes:
            risk = RATING_NUMERIC[s.likelihood] * RATING_NUMERIC[s.impact]
            lines.append(f"| {n.id} | {n.label} | {s.likelihood} | {s.impact} | {risk} |")
        lines.append("")

    # mitigations
    if mitigations:
        lines.append("## Mitigations")
        lines.append("")
        for m in mitigations:
            node_labels = [node_map[nid].label for nid in m.node_ids if nid in node_map]
            lines.append(f"- **{m.id}**: {m.text}")
            if node_labels:
                lines.append(f"  - Targets: {', '.join(node_labels)}")
        lines.append("")

    md_text = "\n".join(lines)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md_text)

    if json_flag:
        finish(command, {"markdown": md_text, "output_path": output}, True, quiet)
        return
    if not quiet:
        if output:
            from ..renderer import console

            console.print(f"Report written to {output}")
        else:
            render_markdown(md_text)
