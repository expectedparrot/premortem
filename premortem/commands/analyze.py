"""AI-powered analysis commands: personas, reasons, mitigations, research agenda, executive summary, HTML report."""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import typer

from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Run AI-powered analysis phases (personas, reasons, mitigations, research, summary, report).")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_dir(store) -> Path:
    d = store.root / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── personas ────────────────────────────────────────────────────


@app.command("personas")
def analyze_personas(
    domain_context: str = typer.Option(
        ..., "--context", "-c",
        help="Domain expertise for the facilitator agent (e.g., 'veteran org consultant who knows this institution intimately').",
    ),
    persona_requirements: str = typer.Option(
        ..., "--requirements", "-r",
        help="Comma-separated persona requirements (e.g., 'tenured faculty in rigid dept,current undergrad,employer partner,administrator,external expert').",
    ),
    model_name: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Generate deep stakeholder personas via EDSL."""
    from edsl import Agent, AgentList, QuestionList, Survey, Model

    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
    except PremortemError as err:
        fail("analyzepersonas", err, should_emit_json(human))

    reqs = [r.strip() for r in persona_requirements.split(",") if r.strip()]
    req_bullets = "\n".join(f"- {r}" for r in reqs)

    facilitator = Agent(traits={
        "persona": (
            f"You are a {domain_context}. "
            "You are designing a pre-mortem for a major initiative and need to select "
            "stakeholder personas who will have specific, conflicting perspectives."
        ),
    })

    q = QuestionList(
        question_name="personas",
        question_text=(
            f"Initiative: {meta.initiative}\n"
            f"Description: {meta.description}\n\n"
            "Propose exactly 5 stakeholder personas. These must be specific, realistic "
            "people with concrete institutional positions and incentives — not generic roles.\n\n"
            "For each persona, provide ALL fields separated by ' | ':\n"
            "Name | Title | 2-3 sentence bio with their specific context, "
            "what they care about, why they might be skeptical or supportive, "
            "and what they stand to lose or gain\n\n"
            f"Requirements:\n{req_bullets}\n\n"
            "Make them feel like real people, not interchangeable functionaries. "
            "Each should have a distinct reason to care."
        ),
    )

    model = Model(model_name)
    results = Survey(questions=[q]).by(AgentList([facilitator])).by(model).run()

    raw = results.select("answer.personas").to_dicts(remove_prefix=True)
    rows = []
    for item in raw[0].get("personas", []):
        parts = [p.strip() for p in item.split("|")]
        if len(parts) >= 3:
            rows.append({"persona_name": parts[0], "role": parts[1], "perspective": " | ".join(parts[2:])})
        elif len(parts) == 2:
            rows.append({"persona_name": parts[0], "role": parts[1], "perspective": ""})

    out_path = _output_dir(store) / "results_personas.json"
    envelope = {
        "premortem_version": "0.1.0",
        "entity_type": "personas",
        "initiative": meta.initiative,
        "generated_at": _now_iso(),
        "rows": rows,
    }
    out_path.write_text(json.dumps(envelope, indent=2))

    if not quiet:
        typer.echo(f"Generated {len(rows)} personas → {out_path}")
        for r in rows:
            typer.echo(f"  • {r['persona_name']} — {r['role']}")
    typer.echo(f"\nIngest with: premortem ingest personas --from {out_path}")


# ── reasons ─────────────────────────────────────────────────────


@app.command("reasons")
def analyze_reasons(
    domain_details: str = typer.Option(
        ..., "--domain", "-d",
        help="Domain-specific details agents should reference (e.g., 'product names, team structures, budget figures, timeline details').",
    ),
    bad_example: str = typer.Option(
        "Lack of alignment with institutional culture",
        "--bad-example",
        help="Example of a BAD (too generic) reason.",
    ),
    good_example: str = typer.Option(
        ..., "--good-example", "-g",
        help="Example of a GOOD (specific) reason.",
    ),
    model_name: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Elicit rich failure reason narratives via EDSL."""
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
    except PremortemError as err:
        fail("analyzereasons", err, should_emit_json(human))

    if not personas:
        typer.echo("No personas found. Run 'premortem analyze personas' first.", err=True)
        raise typer.Exit(1)

    agents = AgentList([
        Agent(
            name=p.name,
            traits={
                "persona": (
                    f"You are {p.name}, {p.role}. "
                    f"{p.perspective or ''} "
                    "You are participating in a pre-mortem exercise. Answer from "
                    f"your specific position, drawing on concrete details about {domain_details}. "
                    "Do NOT give generic management-consultant answers. Be specific."
                ),
            },
        )
        for p in personas
    ])

    q_episodic = QuestionFreeText(
        question_name="episodic_reasons",
        question_text=(
            f"FACT: {meta.failure_statement}\n\n"
            "This has already happened. It is over.\n\n"
            "From your specific position and experience, describe 3-4 concrete event "
            "chains that led to this failure. Each should be a sequence of specific "
            "things that went wrong, not abstract categories.\n\n"
            f"BAD example (too generic): '{bad_example}'\n"
            f"GOOD example: '{good_example}'\n\n"
            f"Be specific about: {domain_details}. Number each event chain."
        ),
    )

    q_structural = QuestionFreeText(
        question_name="structural_reasons",
        question_text=(
            "Now step back from the specific events. What deeper structural or "
            "institutional factors made this failure nearly inevitable?\n\n"
            f"BAD example: 'Insufficient stakeholder engagement'\n"
            f"GOOD example: '{good_example}'\n\n"
            "Give 3-4 structural factors, each 2-3 sentences. Be specific."
        ),
    )

    model = Model(model_name)
    results = Survey(questions=[q_episodic, q_structural]).by(agents).by(model).run()

    raw = results.select("agent.agent_name", "answer.episodic_reasons", "answer.structural_reasons").to_dicts(remove_prefix=True)

    # Build ingest-compatible format
    name_to_id = {p.name: p.id for p in personas}
    rows = []
    for item in raw:
        name = item["agent_name"]
        rows.append({
            "persona": name,
            "episodic_reasons": [item.get("episodic_reasons", "")],
            "structural_reasons": [item.get("structural_reasons", "")],
        })

    out_path = _output_dir(store) / "results_reasons.json"
    envelope = {
        "premortem_version": "0.1.0",
        "entity_type": "reasons",
        "initiative": meta.initiative,
        "generated_at": _now_iso(),
        "rows": rows,
    }
    out_path.write_text(json.dumps(envelope, indent=2))

    if not quiet:
        typer.echo(f"Generated reasons from {len(rows)} personas → {out_path}")
    typer.echo(f"\nIngest with: premortem ingest reasons --from {out_path}")


# ── mitigations ─────────────────────────────────────────────────


@app.command("mitigations")
def analyze_mitigations(
    bad_example: str = typer.Option(
        "Improve stakeholder engagement",
        "--bad-example",
        help="Example of a BAD (too generic) mitigation.",
    ),
    good_example: str = typer.Option(
        ..., "--good-example", "-g",
        help="Example of a GOOD (specific) mitigation.",
    ),
    model_name: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Elicit concrete mitigations from personas via EDSL."""
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        nodes = store.list_nodes()
    except PremortemError as err:
        fail("analyzemitigations", err, should_emit_json(human))

    if not personas or not nodes:
        typer.echo("Need personas and graph nodes. Run earlier phases first.", err=True)
        raise typer.Exit(1)

    node_list = "\n".join(f"  - {n.id}: {n.label}" for n in nodes)

    agents = AgentList([
        Agent(
            name=p.name,
            traits={
                "persona": (
                    f"You are {p.name}, {p.role}. "
                    f"{p.perspective or ''} "
                    "You participated in the pre-mortem and identified why this initiative failed. "
                    "Now you are proposing concrete preventive actions. Draw on your specific "
                    "institutional knowledge and position. Do NOT give generic advice."
                ),
            },
        )
        for p in personas
    ])

    q = QuestionFreeText(
        question_name="mitigations",
        question_text=(
            f"The pre-mortem identified these causal factors behind the failure of "
            f"{meta.initiative}:\n\n{node_list}\n\n"
            "Propose 3-5 concrete preventive actions. For each:\n"
            "1. State the specific action (who does what, by when)\n"
            "2. Say which causal factor(s) it targets\n"
            "3. Explain WHY it would work from your vantage point\n\n"
            f"BAD example: '{bad_example}'\n"
            f"GOOD example: '{good_example}'\n\n"
            "Be specific. Name offices, processes, timelines, and dollar amounts."
        ),
    )

    model = Model(model_name)
    results = Survey(questions=[q]).by(agents).by(model).run()

    raw = results.select("agent.agent_name", "answer.mitigations").to_dicts(remove_prefix=True)
    name_to_id = {p.name: p.id for p in personas}
    rows = []
    for item in raw:
        name = item["agent_name"]
        rows.append({
            "persona_id": name_to_id.get(name),
            "persona_name": name,
            "text": item.get("mitigations", ""),
        })

    out_path = _output_dir(store) / "results_mitigations.json"
    envelope = {
        "premortem_version": "0.1.0",
        "entity_type": "mitigations",
        "initiative": meta.initiative,
        "generated_at": _now_iso(),
        "rows": rows,
    }
    out_path.write_text(json.dumps(envelope, indent=2))

    if not quiet:
        typer.echo(f"Generated mitigations from {len(rows)} personas → {out_path}")


# ── research agenda ──────────────────────────────────────────────


@app.command("research-agenda")
def analyze_research_agenda(
    model_name: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Identify important uncertainties that could be resolved through empirical research."""
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        nodes = store.list_nodes()
        reasons = store.list_reasons()
    except PremortemError as err:
        fail("analyzeresearch-agenda", err, should_emit_json(human))

    if not personas or not nodes:
        typer.echo("Need personas and graph nodes. Run earlier phases first.", err=True)
        raise typer.Exit(1)

    node_list = "\n".join(f"  - {n.id}: {n.label}" for n in nodes)

    # Include reason excerpts so agents have the full context
    persona_map = {p.id: p.name for p in personas}
    reason_excerpts = ""
    for r in reasons:
        pname = persona_map.get(r.persona_id, "Unknown")
        reason_excerpts += f"\n[{pname}, {r.kind}]: {r.text[:400]}...\n"

    agents = AgentList([
        Agent(
            name=p.name,
            traits={
                "persona": (
                    f"You are {p.name}, {p.role}. "
                    f"{p.perspective or ''} "
                    "You participated in the pre-mortem and now you are identifying which "
                    "of the assumed failure factors are actually UNCERTAIN — things we believe "
                    "but haven't verified, that could be tested through empirical research "
                    "before committing to or abandoning the initiative."
                ),
            },
        )
        for p in personas
    ])

    q = QuestionFreeText(
        question_name="research_agenda",
        question_text=(
            f"The pre-mortem for '{meta.initiative}' identified these causal factors:\n\n"
            f"{node_list}\n\n"
            f"Context from the failure analysis:\n{reason_excerpts}\n\n"
            "Many of these factors were stated as certainties in the pre-mortem — but some "
            "are actually ASSUMPTIONS that haven't been tested. From your specific vantage "
            "point, identify 2-4 factors where the outcome is genuinely uncertain and could "
            "be resolved through empirical research BEFORE a launch decision.\n\n"
            "For each researchable uncertainty:\n"
            "1. **What we assume** — the specific belief embedded in the pre-mortem\n"
            "2. **Why it's uncertain** — what we don't actually know\n"
            "3. **How to resolve it** — the specific research method (survey, focus group, "
            "pilot study, data analysis, stakeholder interviews, etc.)\n"
            "4. **Who to study** — the specific population or data source\n"
            "5. **What finding would change the decision** — what result would make you "
            "more or less confident in proceeding\n\n"
            "Focus on uncertainties that are both IMPORTANT (they drive major causal paths) "
            "and RESOLVABLE (a feasible study could meaningfully reduce the uncertainty). "
            "Don't list things we already know for certain.\n\n"
            "BAD example: 'We should do more research on stakeholder needs'\n"
            "GOOD example: 'We assume participants won't enroll because the existing "
            "alternative is superior, but we've never actually asked. A survey of 200 "
            "prospective participants — stratified by whether they currently use the "
            "alternative — asking about interest in the new program would tell us "
            "whether demand exists. If >25% express strong interest, the enrollment "
            "assumptions in our failure scenario are wrong.'"
        ),
    )

    model = Model(model_name)
    results = Survey(questions=[q]).by(agents).by(model).run()

    raw = results.select("agent.agent_name", "answer.research_agenda").to_dicts(remove_prefix=True)
    name_to_id = {p.name: p.id for p in personas}
    rows = []
    for item in raw:
        name = item["agent_name"]
        rows.append({
            "persona_id": name_to_id.get(name),
            "persona_name": name,
            "text": item.get("research_agenda", ""),
        })

    out_path = _output_dir(store) / "results_research_agenda.json"
    envelope = {
        "premortem_version": "0.1.0",
        "entity_type": "research_agenda",
        "initiative": meta.initiative,
        "generated_at": _now_iso(),
        "rows": rows,
    }
    out_path.write_text(json.dumps(envelope, indent=2))

    if not quiet:
        typer.echo(f"Generated research agenda from {len(rows)} personas → {out_path}")


# ── executive summary ───────────────────────────────────────────


@app.command("summary")
def analyze_summary(
    model_name: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    """Generate an executive summary synthesizing all findings."""
    from edsl import Agent, QuestionFreeText, Survey, Model

    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        reasons = store.list_reasons()
        nodes = store.list_nodes()
        edges = store.list_edges()
    except PremortemError as err:
        fail("analyzesummary", err, should_emit_json(human))

    # Build context
    persona_summaries = "\n".join(f"- {p.name} ({p.role})" for p in personas)
    node_list = "\n".join(f"  - {n.id}: {n.label}" for n in nodes)
    edge_list = "\n".join(f"  - {e.source} → {e.target}: {e.label or ''}" for e in edges)

    reason_excerpts = ""
    persona_map = {p.id: p.name for p in personas}
    for r in reasons:
        pname = persona_map.get(r.persona_id, "Unknown")
        reason_excerpts += f"\n[{pname}, {r.kind}]: {r.text[:500]}...\n"

    # Load mitigations if available
    out_dir = _output_dir(store)
    mit_path = out_dir / "results_mitigations.json"
    mit_excerpts = ""
    if mit_path.exists():
        mit_data = json.loads(mit_path.read_text()).get("rows", [])
        for m in mit_data:
            mt = m.get("text") or ""
            if mt:
                mit_excerpts += f"\n[{m.get('persona_name', 'Unknown')}]: {mt[:500]}...\n"

    # Load research agenda if available
    research_path = out_dir / "results_research_agenda.json"
    research_excerpts = ""
    if research_path.exists():
        research_data = json.loads(research_path.read_text()).get("rows", [])
        for r in research_data:
            if r.get("text"):
                research_excerpts += f"\n[{r.get('persona_name', 'Unknown')}]: {r['text'][:500]}...\n"

    research_instruction = ""
    if research_excerpts:
        research_instruction = (
            f"\n\nResearchable uncertainties identified by stakeholders:\n{research_excerpts}\n\n"
            "IMPORTANT: The final paragraph of the executive summary MUST include a concrete "
            "research recommendation — specific studies, surveys, or analyses that should be "
            "conducted BEFORE a go/no-go decision. Synthesize the researchable uncertainties "
            "above into 3-5 specific, prioritized research actions. For each, state what "
            "question it answers and what the decision-relevant threshold is (e.g., 'if >25% "
            "of students express interest, the demand assumption is wrong'). Frame these as "
            "prerequisites to any launch decision, not optional nice-to-haves."
        )

    synthesizer = Agent(
        name="Synthesizer",
        traits={
            "persona": (
                "You are a senior strategy consultant writing an executive summary of a "
                "pre-mortem analysis. You synthesize findings across multiple stakeholder "
                "perspectives into clear, actionable conclusions. You write in crisp, direct "
                "prose — no jargon, no hedging. You are writing for a decision-maker."
            ),
        },
    )

    q = QuestionFreeText(
        question_name="executive_summary",
        question_text=(
            f"Write the executive summary for a pre-mortem analysis of: {meta.initiative}\n\n"
            f"Description: {meta.description}\n\n"
            f"Failure statement: {meta.failure_statement}\n\n"
            f"Personas consulted:\n{persona_summaries}\n\n"
            f"Causal graph:\n{node_list}\n\nEdges:\n{edge_list}\n\n"
            f"Key findings:\n{reason_excerpts}\n\n"
            f"Mitigations proposed:\n{mit_excerpts}\n\n"
            "Write 4-5 paragraphs:\n"
            "1. Core finding in one sentence\n"
            "2. 3-4 main causal mechanisms\n"
            "3. Highest-leverage intervention points\n"
            "4. Specific research that should be conducted before a decision, "
            "synthesized from stakeholder-identified uncertainties\n"
            "5. Clear bottom-line recommendation (go/no-go/conditional)\n\n"
            "Be specific — reference actual institutional dynamics. "
            "Write in flowing paragraphs, no bullet points."
            f"{research_instruction}"
        ),
    )

    model = Model(model_name)
    results = Survey(questions=[q]).by(synthesizer).by(model).run()

    raw = results.select("answer.executive_summary").to_dicts(remove_prefix=True)
    summary_text = raw[0].get("executive_summary", "")

    out_path = _output_dir(store) / "results_exec_summary.json"
    envelope = {
        "premortem_version": "0.1.0",
        "entity_type": "executive_summary",
        "initiative": meta.initiative,
        "generated_at": _now_iso(),
        "text": summary_text,
    }
    out_path.write_text(json.dumps(envelope, indent=2))

    if not quiet:
        typer.echo(f"Executive summary saved to {out_path}")
        typer.echo(f"\n{summary_text[:300]}...")


# ── HTML report ─────────────────────────────────────────────────

_BUILTIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pre-mortem: {{ initiative }}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }
  header { background: #1e293b; color: #f1f5f9; padding: 2.5rem 2rem; margin-bottom: 2rem; border-radius: 0.75rem; }
  header h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }
  header .meta { font-size: 0.875rem; color: #94a3b8; }
  header .failure { margin-top: 1rem; padding: 1rem; background: rgba(239,68,68,0.15); border-left: 4px solid #ef4444; border-radius: 0.375rem; font-style: italic; }
  section { background: #fff; border-radius: 0.75rem; padding: 1.75rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.07); }
  section > h2 { font-size: 1.125rem; font-weight: 700; color: #1e293b; margin-bottom: 1.25rem; padding-bottom: 0.625rem; border-bottom: 2px solid #e2e8f0; }
  .exec-summary { font-size: 0.9375rem; }
  .exec-summary p { margin-bottom: 0.875rem; }
  .steps { display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem; align-items: start; }
  .step-num { width: 1.75rem; height: 1.75rem; background: #3b82f6; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
  .step-text { padding: 0.25rem 0; font-size: 0.875rem; }
  .step-text .detail { color: #64748b; font-size: 0.8125rem; margin-top: 0.125rem; }
  .stats { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
  .stat-chip { background: #f1f5f9; border-radius: 999px; padding: 0.25rem 0.875rem; font-size: 0.8125rem; font-weight: 600; color: #475569; }
  .persona-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
  .persona-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1rem; }
  .persona-name { font-weight: 700; font-size: 0.9375rem; color: #1e293b; }
  .persona-role { font-size: 0.8125rem; color: #3b82f6; margin: 0.25rem 0 0.5rem; font-weight: 600; }
  .persona-perspective { font-size: 0.8125rem; color: #475569; }
  .narrative-group { border: 1px solid #e2e8f0; border-radius: 0.5rem; margin-bottom: 1rem; overflow: hidden; }
  .narrative-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
  .narrative-header h3 { font-size: 0.9375rem; font-weight: 700; }
  .role-tag { font-size: 0.75rem; color: #3b82f6; font-weight: 600; background: #eff6ff; border-radius: 999px; padding: 0.125rem 0.625rem; white-space: nowrap; }
  details summary { cursor: pointer; padding: 0.625rem 1rem; font-weight: 600; font-size: 0.875rem; list-style: none; border-bottom: 1px solid #f1f5f9; }
  details summary h4 { display: inline; font-size: 0.875rem; }
  details summary::-webkit-details-marker { display: none; }
  details summary::before { content: "▶ "; font-size: 0.625rem; color: #94a3b8; }
  details[open] summary::before { content: "▼ "; }
  .narrative { padding: 1rem; font-size: 0.875rem; }
  .narrative p { margin-bottom: 0.75rem; }
  .mermaid-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 0.5rem 0.75rem; background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-weight: 600; color: #475569; }
  td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #f1f5f9; }
  td.num { text-align: center; }
  .type-root { background: #fef3c7; color: #92400e; padding: 0.125rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
  .type-terminal { background: #fee2e2; color: #991b1b; padding: 0.125rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
  .type-mid { background: #e0e7ff; color: #3730a3; padding: 0.125rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
  .description { color: #64748b; font-style: italic; font-size: 0.875rem; }
  p em { color: #94a3b8; }
</style>
</head>
<body>
<div class="container">

<header>
  <h1>Pre-mortem: {{ initiative }}</h1>
  <div class="meta">Generated {{ date }}{{ description_line }}</div>
  <div class="failure"><strong>Failure statement:</strong> {{ failure_statement }}</div>
</header>

<section>
  <h2>Executive Summary</h2>
  <div class="exec-summary">{{ executive_summary }}</div>
</section>

<section>
  <h2>Methodology</h2>
  <div class="steps">{{ methodology_steps }}</div>
</section>

<section>
  <h2>Personas <span style="font-weight:400;font-size:0.875rem;color:#64748b;">({{ persona_count }})</span></h2>
  <div class="persona-grid">{{ persona_cards }}</div>
</section>

<section>
  <h2>Failure Narratives</h2>
  {{ reason_sections }}
</section>

<section>
  <h2>Causal Graph</h2>
  <div class="stats">
    <span class="stat-chip">{{ node_count }} nodes</span>
    <span class="stat-chip">{{ edge_count }} edges</span>
    <span class="stat-chip" style="background:#fef3c7;color:#92400e;">Yellow = root cause</span>
    <span class="stat-chip" style="background:#fee2e2;color:#991b1b;">Red = terminal</span>
  </div>
  <div class="mermaid-wrap">
    <div class="mermaid">
{{ mermaid_graph }}
    </div>
  </div>
  <table style="margin-top:1.25rem;">
    <thead><tr><th>ID</th><th>Label</th><th>Type</th><th style="text-align:center">In</th><th style="text-align:center">Out</th><th>Reasons cited</th></tr></thead>
    <tbody>{{ graph_table_rows }}</tbody>
  </table>
</section>

<section>
  <h2>Mitigations</h2>
  {{ mitigation_sections }}
</section>

<section>
  <h2>Research Agenda</h2>
  {{ research_agenda_sections }}
</section>

</div>
<script>mermaid.initialize({ startOnLoad: true, theme: 'neutral' });</script>
</body>
</html>"""


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _markdown_to_html(text: str) -> str:
    text = _html_escape(text)
    text = re.sub(r'^## (.+)$', r'<h4 style="display:block; margin-top:1.2rem; margin-bottom:0.4rem;">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h3 style="margin-top:1rem; margin-bottom:0.5rem;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\n---+\n', '\n<hr>\n', text)
    paras = re.split(r'\n\n+', text.strip())
    parts = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if p == '<hr>':
            parts.append('<hr>')
        elif p.startswith('<h3') or p.startswith('<h4'):
            parts.append(p)
        else:
            parts.append(f'<p>{p.replace(chr(10), "<br>" + chr(10))}</p>')
    return '\n'.join(parts)


def _short_label(label: str) -> str:
    """Keep the full label for Mermaid — let the renderer handle wrapping."""
    return label


@app.command("report")
def analyze_report(
    output: str = typer.Option("report.html", "--output", "-o", help="Output HTML file name (in .premortem/output/)."),
    project_dir: Path | None = ProjectDirOption,
    quiet: bool = QuietOption,
) -> None:
    """Generate a standalone HTML report from all pre-mortem data."""
    store = store_for(project_dir)
    h = _html_escape
    md = _markdown_to_html

    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        reasons = store.list_reasons()
        all_nodes = store.list_nodes()
        all_edges = store.list_edges()
    except PremortemError as err:
        fail("analyzereport", err, True)

    out_dir = _output_dir(store)

    # Load optional data
    mit_data = []
    mit_path = out_dir / "results_mitigations.json"
    # Also check v2 naming for backwards compat
    if not mit_path.exists():
        mit_path = out_dir / "results_mitigations_v2.json"
    if mit_path.exists():
        mit_data = json.loads(mit_path.read_text()).get("rows", [])

    exec_text = ""
    exec_path = out_dir / "results_exec_summary.json"
    if exec_path.exists():
        exec_text = json.loads(exec_path.read_text()).get("text", "")

    research_data = []
    research_path = out_dir / "results_research_agenda.json"
    if research_path.exists():
        research_data = json.loads(research_path.read_text()).get("rows", [])

    # Graph metrics
    in_edges = defaultdict(list)
    out_edges = defaultdict(list)
    for e in all_edges:
        in_edges[e.target].append(e)
        out_edges[e.source].append(e)
    root_nodes = {n.id for n in all_nodes if not in_edges[n.id]}
    terminal_nodes = {n.id for n in all_nodes if not out_edges[n.id]}

    # Group data
    ep_by_p = defaultdict(list)
    st_by_p = defaultdict(list)
    for r in reasons:
        (ep_by_p if r.kind == "episodic" else st_by_p)[r.persona_id].append(r.text)

    mit_by_p = {}
    for m in mit_data:
        pid = m.get("persona_id")
        if pid:
            mit_by_p[pid] = m.get("text", "")

    research_by_p = {}
    for r in research_data:
        pid = r.get("persona_id")
        if pid:
            research_by_p[pid] = r.get("text", "")

    # Template path. The built-in template is the expected default; we only
    # mention the override when the user asks for verbose output (debug flag).
    template_path = out_dir / "report_template.html"
    if template_path.exists():
        template = template_path.read_text()
    else:
        if os.getenv("PREMORTEM_DEBUG"):
            typer.echo(
                f"Using built-in HTML template (no override at {template_path}). "
                "To customize, copy report_template.html into .premortem/output/.",
                err=True,
            )
        template = _BUILTIN_TEMPLATE

    # Build replacements
    exec_html = md(exec_text) if exec_text else '<p><em>Run premortem analyze summary to generate.</em></p>'

    method_steps = f"""
  <div class="step-num">1</div>
  <div class="step-text"><strong>Failure statement crafted.</strong>
    <div class="detail">Vivid, specific description of the failure as established fact.</div></div>
  <div class="step-num">2</div>
  <div class="step-text"><strong>{len(personas)} stakeholder personas generated via EDSL + Claude Opus.</strong>
    <div class="detail">Each with specific institutional position, incentives, and domain context.</div></div>
  <div class="step-num">3</div>
  <div class="step-text"><strong>Two-round failure reason elicitation.</strong>
    <div class="detail">Event chains (concrete sequences) and structural factors (institutional forces).</div></div>
  <div class="step-num">4</div>
  <div class="step-text"><strong>Causal graph constructed.</strong>
    <div class="detail">{len(all_nodes)} nodes, {len(all_edges)} edges — root causes to terminal outcomes.</div></div>
  <div class="step-num">5</div>
  <div class="step-text"><strong>Mitigations elicited.</strong>
    <div class="detail">Concrete preventive actions from each persona.</div></div>"""

    persona_cards = ""
    for p in personas:
        persona_cards += f"""
    <div class="persona-card">
      <div class="persona-name">{h(p.name)}</div>
      <div class="persona-role">{h(p.role)}</div>
      <div class="persona-perspective">{h(p.perspective or '')}</div>
    </div>"""

    reason_sections = ""
    for p in personas:
        ep = ep_by_p.get(p.id, [])
        st = st_by_p.get(p.id, [])
        ep_html = "\n".join(md(t) for t in ep) if ep else "<p><em>None.</em></p>"
        st_html = "\n".join(md(t) for t in st) if st else "<p><em>None.</em></p>"
        reason_sections += f"""
    <div class="narrative-group">
      <div class="narrative-header"><h3>{h(p.name)}</h3><div class="role-tag">{h(p.role)}</div></div>
      <details open><summary><h4>Event Chains</h4></summary><div class="narrative">{ep_html}</div></details>
      <details><summary><h4>Structural Factors</h4></summary><div class="narrative">{st_html}</div></details>
    </div>"""

    # Mermaid with short labels
    mermaid = ["graph TD"]
    for n in all_nodes:
        mermaid.append(f'    {n.id}["{h(_short_label(n.label))}"]')
    for e in all_edges:
        if e.label:
            sl = e.label[:30] + ("..." if len(e.label) > 30 else "")
            mermaid.append(f'    {e.source} -->|"{h(sl)}"| {e.target}')
        else:
            mermaid.append(f'    {e.source} --> {e.target}')
    for nid in root_nodes:
        mermaid.append(f"    style {nid} fill:#fde68a,stroke:#b45309,color:#000")
    for nid in terminal_nodes:
        mermaid.append(f"    style {nid} fill:#fca5a5,stroke:#b91c1c,color:#000")

    graph_rows = ""
    for n in all_nodes:
        nt = "Root cause" if n.id in root_nodes else ("Terminal" if n.id in terminal_nodes else "Intermediate")
        tc = "type-root" if n.id in root_nodes else ("type-terminal" if n.id in terminal_nodes else "type-mid")
        # Surface multi-source convergence: number of cited reasons (0+) and the IDs.
        rids = list(getattr(n, "reason_ids", []) or [])
        if rids:
            reasons_cell = (
                f'<span class="reason-count">{len(rids)}×</span> '
                + " ".join(f'<code>{h(rid)}</code>' for rid in rids)
            )
        else:
            reasons_cell = "—"
        graph_rows += f"""
      <tr><td><code>{n.id}</code></td><td>{h(n.label)}</td>
      <td><span class="{tc}">{nt}</span></td>
      <td class="num">{len(in_edges[n.id])}</td><td class="num">{len(out_edges[n.id])}</td>
      <td>{reasons_cell}</td></tr>"""

    mit_sections = ""
    for p in personas:
        mt = mit_by_p.get(p.id, "")
        if mt:
            mit_sections += f"""
    <div class="narrative-group">
      <div class="narrative-header"><h3>{h(p.name)}</h3><div class="role-tag">{h(p.role)}</div></div>
      <details open><summary><h4>Proposed Preventive Actions</h4></summary>
      <div class="narrative">{md(mt)}</div></details>
    </div>"""
    if not mit_sections:
        mit_sections = '<p class="description"><em>Run premortem analyze mitigations to generate.</em></p>'

    research_sections = ""
    for p in personas:
        rt = research_by_p.get(p.id, "")
        if rt:
            research_sections += f"""
    <div class="narrative-group">
      <div class="narrative-header"><h3>{h(p.name)}</h3><div class="role-tag">{h(p.role)}</div></div>
      <details open><summary><h4>Researchable Uncertainties</h4></summary>
      <div class="narrative">{md(rt)}</div></details>
    </div>"""
    if not research_sections:
        research_sections = '<p class="description"><em>Run premortem analyze research-agenda to generate.</em></p>'

    description_line = f" &nbsp;·&nbsp; {h(meta.description)}" if meta.description else ""
    replacements = {
        "{{ initiative }}": h(meta.initiative),
        "{{ date }}": meta.created_at.strftime("%Y-%m-%d") if hasattr(meta.created_at, 'strftime') else str(meta.created_at)[:10],
        "{{ description_line }}": description_line,
        "{{ description }}": h(meta.description or ""),
        "{{ failure_statement }}": h(meta.failure_statement),
        "{{ executive_summary }}": exec_html,
        "{{ methodology_steps }}": method_steps,
        "{{ persona_count }}": str(len(personas)),
        "{{ persona_cards }}": persona_cards,
        "{{ reason_sections }}": reason_sections,
        "{{ node_count }}": str(len(all_nodes)),
        "{{ edge_count }}": str(len(all_edges)),
        "{{ mermaid_graph }}": "\n".join(mermaid),
        "{{ graph_table_rows }}": graph_rows,
        "{{ mitigation_sections }}": mit_sections,
        "{{ research_agenda_sections }}": research_sections,
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)

    out_path = out_dir / output
    out_path.write_text(result)
    if not quiet:
        typer.echo(f"HTML report written to {out_path}")
