from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import PremortemError


def _imports() -> tuple[Any, ...]:
    try:
        from edsl import Agent, AgentList, Jobs, Scenario, ScenarioList
        from edsl.questions import QuestionFreeText, QuestionList
    except ImportError as exc:
        raise PremortemError(
            "DEPENDENCY_ERROR",
            "EDSL is required to create or ingest .ep objects.",
            hint="Install it with `python -m pip install edsl`.",
        ) from exc
    return Agent, AgentList, Jobs, Scenario, ScenarioList, QuestionFreeText, QuestionList


def expected_results_path(output: Path) -> Path:
    name = output.name
    if name.endswith(".jobs.ep"):
        return output.with_name(f"{name[:-8]}-results.ep")
    return output.with_name(f"{output.stem}-results.ep")


def save_jobs(jobs: Any, output: Path) -> Any:
    if output.suffix != ".ep":
        raise PremortemError("VALIDATION_FAILED", "--output must use the .ep extension.", context=str(output))
    if output.exists():
        raise PremortemError("VALIDATION_FAILED", "Output already exists.", context=str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    return jobs.git.save(output)


def personas_jobs(meta: Any, context: str, requirements: str) -> Any:
    Agent, AgentList, Jobs, Scenario, ScenarioList, _, QuestionList = _imports()
    question = QuestionList(
        question_name="personas",
        question_text=(
            "Initiative: {{ initiative }}\n"
            "Description: {{ description }}\n\n"
            "Propose exactly five stakeholder personas for this pre-mortem. "
            "For each return: Name | Title | a concrete 2-3 sentence perspective. "
            "Requirements: {{ requirements }}. Make positions and incentives specific."
        ),
        max_list_items=5,
    )
    scenario = Scenario({
        "premortem_phase": "personas",
        "project_id": meta.id,
        "initiative": meta.initiative,
        "description": meta.description or "",
        "requirements": requirements,
    })
    facilitator = Agent(name="premortem_facilitator", traits={"persona": context})
    return Jobs(survey=question.to_survey()).by(AgentList([facilitator])).by(ScenarioList([scenario]))


def reasons_jobs(meta: Any, personas: list[Any], domain: str, good_example: str, bad_example: str) -> Any:
    Agent, AgentList, Jobs, Scenario, ScenarioList, QuestionFreeText, _ = _imports()
    questions = [
        QuestionFreeText(
            question_name="episodic_reasons",
            question_text=(
                "FACT: {{ failure_statement }}\n"
                "From your position, describe 3-4 concrete event chains that led to this failure. "
                "Use {{ domain }}. Bad: {{ bad_example }}. Good: {{ good_example }}."
            ),
        ),
        QuestionFreeText(
            question_name="structural_reasons",
            question_text=(
                "For {{ initiative }}, identify 3-4 deeper structural factors that made the failure likely. "
                "Use concrete mechanisms from {{ domain }}, not generic management labels."
            ),
        ),
    ]
    agents = AgentList([
        Agent(
            name=p.name,
            traits={
                "premortem_persona_id": p.id,
                "persona": f"You are {p.name}, {p.role}. {p.perspective or ''}",
            },
        )
        for p in personas
    ])
    scenario = Scenario({
        "premortem_phase": "reasons",
        "project_id": meta.id,
        "initiative": meta.initiative,
        "failure_statement": meta.failure_statement,
        "domain": domain,
        "bad_example": bad_example,
        "good_example": good_example,
    })
    from edsl import Survey
    return Jobs(survey=Survey(questions)).by(agents).by(ScenarioList([scenario]))


def mitigations_jobs(meta: Any, personas: list[Any], nodes: list[Any], good_example: str, bad_example: str) -> Any:
    Agent, AgentList, Jobs, Scenario, ScenarioList, QuestionFreeText, _ = _imports()
    agents = AgentList([
        Agent(
            name=p.name,
            traits={"premortem_persona_id": p.id, "persona": f"You are {p.name}, {p.role}. {p.perspective or ''}"},
        )
        for p in personas
    ])
    question = QuestionFreeText(
        question_name="mitigations",
        question_text=(
            "Initiative: {{ initiative }}\nCausal graph:\n{{ node_list }}\n\n"
            "Propose 3-5 preventive actions. Name who does what by when, the node IDs targeted, "
            "and why the action works. Bad: {{ bad_example }}. Good: {{ good_example }}."
        ),
    )
    scenario = Scenario({
        "premortem_phase": "mitigations",
        "project_id": meta.id,
        "initiative": meta.initiative,
        "node_list": "\n".join(f"- {n.id}: {n.label}" for n in nodes),
        "bad_example": bad_example,
        "good_example": good_example,
    })
    return Jobs(survey=question.to_survey()).by(agents).by(ScenarioList([scenario]))


def research_jobs(meta: Any, personas: list[Any], nodes: list[Any], reasons: list[Any]) -> Any:
    Agent, AgentList, Jobs, Scenario, ScenarioList, QuestionFreeText, _ = _imports()
    agents = AgentList([
        Agent(
            name=p.name,
            traits={"premortem_persona_id": p.id, "persona": f"You are {p.name}, {p.role}. {p.perspective or ''}"},
        )
        for p in personas
    ])
    question = QuestionFreeText(
        question_name="research_agenda",
        question_text=(
            "Initiative: {{ initiative }}\nCausal graph:\n{{ node_list }}\n"
            "Failure evidence:\n{{ reason_list }}\n\n"
            "Identify 2-4 important, uncertain, resolvable assumptions. For each state what is assumed, "
            "why it is uncertain, how and whom to study, and what finding would change the decision."
        ),
    )
    scenario = Scenario({
        "premortem_phase": "research_agenda",
        "project_id": meta.id,
        "initiative": meta.initiative,
        "node_list": "\n".join(f"- {n.id}: {n.label}" for n in nodes),
        "reason_list": "\n".join(f"- {r.id}: {r.text}" for r in reasons),
    })
    return Jobs(survey=question.to_survey()).by(agents).by(ScenarioList([scenario]))


def summary_jobs(meta: Any, personas: list[Any], nodes: list[Any], edges: list[Any], reasons: list[Any]) -> Any:
    Agent, AgentList, Jobs, Scenario, ScenarioList, QuestionFreeText, _ = _imports()
    question = QuestionFreeText(
        question_name="executive_summary",
        question_text=(
            "Write a decision-ready executive summary for {{ initiative }}.\n"
            "Failure: {{ failure_statement }}\nPersonas: {{ persona_list }}\n"
            "Nodes: {{ node_list }}\nEdges: {{ edge_list }}\nReasons: {{ reason_list }}\n\n"
            "Cover the core finding, causal mechanisms, intervention points, research priorities, "
            "and a clear go/no-go/conditional recommendation."
        ),
    )
    scenario = Scenario({
        "premortem_phase": "executive_summary",
        "project_id": meta.id,
        "initiative": meta.initiative,
        "failure_statement": meta.failure_statement,
        "persona_list": "\n".join(f"- {p.name}: {p.role}" for p in personas),
        "node_list": "\n".join(f"- {n.id}: {n.label}" for n in nodes),
        "edge_list": "\n".join(f"- {e.source} -> {e.target}: {e.label or ''}" for e in edges),
        "reason_list": "\n".join(f"- {r.id}: {r.text}" for r in reasons),
    })
    synthesizer = Agent(name="premortem_synthesizer", traits={"persona": "Senior strategy analyst"})
    return Jobs(survey=question.to_survey()).by(AgentList([synthesizer])).by(ScenarioList([scenario]))
