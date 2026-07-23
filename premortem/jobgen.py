from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from .models import Edge, Node, Persona, ProjectMeta, Reason

# Max output tokens per LLM call. Persona-voice prompts in this module ask for
# multiple paragraphs of vivid prose per persona; values below ~3000 cause
# truncation mid-sentence on the longer reasons / summary outputs. 4096 is the
# safe floor; raise if you add prompts that ask for more.
DEFAULT_MAX_TOKENS = 4096


def _py(value: Any) -> str:
    return repr(value)


def _header(phase: str, meta: ProjectMeta, model_name: str, output_path: Path, max_tokens: int) -> str:
    return f'''"""Generated EDSL job for premortem {phase}.

This script writes EDSL results to:
{output_path}

Next step after a successful run:
premortem ingest {phase} --from {output_path}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


MODEL_NAME = {_py(model_name)}
MAX_TOKENS = {_py(max_tokens)}
OUTPUT_PATH = Path({_py(str(output_path))})
PROJECT = {_py(meta.model_dump(mode="json"))}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _looks_truncated(text: str) -> bool:
    """Heuristic: an LLM output that ends without sentence-final punctuation
    very likely hit max_tokens. We warn rather than fail so the job still
    persists what it got."""
    if not text:
        return False
    tail = text.rstrip()
    if not tail:
        return False
    return tail[-1] not in ".!?\\"'\\u201d\\u2019)]}}"


def _warn_if_truncated(label: str, text: str) -> None:
    if _looks_truncated(text):
        print(
            f"[warn] {{label}} output appears truncated (no sentence-final punctuation). "
            f"Last 80 chars: ...{{text[-80:]!r}}. Consider raising MAX_TOKENS."
        )


'''


def _write_envelope(entity_type: str, body: str) -> str:
    return f'''
def write_results(rows):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    envelope = {{
        "premortem_version": "0.1.0",
        "entity_type": "{entity_type}",
        "initiative": PROJECT["initiative"],
        "generated_at": now_iso(),
        "rows": rows,
    }}
    OUTPUT_PATH.write_text(json.dumps(envelope, indent=2) + "\\n")
    print(f"Wrote {{len(rows)}} rows to {{OUTPUT_PATH}}")
    print("Next: premortem ingest {entity_type} --from " + str(OUTPUT_PATH))


{body}


if __name__ == "__main__":
    main()
'''


def personas_job(
    meta: ProjectMeta,
    output_path: Path,
    context: str,
    requirements: str,
    model_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    reqs = [r.strip() for r in requirements.split(",") if r.strip()]
    req_bullets = "\n".join(f"- {item}" for item in reqs)
    body = f'''
CONTEXT = {_py(context)}
REQUIREMENT_BULLETS = {_py(req_bullets)}


def main():
    from edsl import Agent, AgentList, QuestionList, Survey, Model

    facilitator = Agent(traits={{
        "persona": (
            f"You are a {{CONTEXT}}. "
            "You are designing a pre-mortem for a major initiative and need to select "
            "stakeholder personas who will have specific, conflicting perspectives."
        ),
    }})

    q = QuestionList(
        question_name="personas",
        question_text=(
            f"Initiative: {{PROJECT['initiative']}}\\n"
            f"Description: {{PROJECT.get('description')}}\\n\\n"
            "Propose exactly 5 stakeholder personas. These must be specific, realistic "
            "people with concrete institutional positions and incentives, not generic roles.\\n\\n"
            "For each persona, provide ALL fields separated by ' | ':\\n"
            "Name | Title | 2-3 sentence bio with their specific context, "
            "what they care about, why they might be skeptical or supportive, "
            "and what they stand to lose or gain\\n\\n"
            f"Requirements:\\n{{REQUIREMENT_BULLETS}}\\n\\n"
            "Make them feel like real people, not interchangeable functionaries. "
            "Each should have a distinct reason to care."
        ),
    )

    results = Survey(questions=[q]).by(AgentList([facilitator])).by(Model(MODEL_NAME, max_tokens=MAX_TOKENS)).run()
    raw = results.select("answer.personas").to_dicts(remove_prefix=True)

    rows = []
    for item in raw[0].get("personas", []):
        parts = [part.strip() for part in item.split("|")]
        if len(parts) >= 3:
            rows.append({{"persona_name": parts[0], "role": parts[1], "perspective": " | ".join(parts[2:])}})
        elif len(parts) == 2:
            rows.append({{"persona_name": parts[0], "role": parts[1], "perspective": ""}})

    write_results(rows)
'''
    return _header("personas", meta, model_name, output_path, max_tokens) + _write_envelope("personas", textwrap.dedent(body))


def reasons_job(
    meta: ProjectMeta,
    personas: list[Persona],
    output_path: Path,
    domain_details: str,
    good_example: str,
    bad_example: str,
    model_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    personas_data = [p.model_dump(mode="json") for p in personas]
    body = f'''
PERSONAS = {_py(personas_data)}
DOMAIN_DETAILS = {_py(domain_details)}
GOOD_EXAMPLE = {_py(good_example)}
BAD_EXAMPLE = {_py(bad_example)}


def main():
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    if not PERSONAS:
        raise SystemExit("No personas found in snapshot. Generate and ingest personas first.")

    agents = AgentList([
        Agent(
            name=p["name"],
            traits={{
                "persona": (
                    f"You are {{p['name']}}, {{p['role']}}. "
                    f"{{p.get('perspective') or ''}} "
                    "You are participating in a pre-mortem exercise. Answer from "
                    f"your specific position, drawing on concrete details about {{DOMAIN_DETAILS}}. "
                    "Do NOT give generic management-consultant answers. Be specific."
                ),
            }},
        )
        for p in PERSONAS
    ])

    q_episodic = QuestionFreeText(
        question_name="episodic_reasons",
        question_text=(
            f"FACT: {{PROJECT['failure_statement']}}\\n\\n"
            "This has already happened. It is over.\\n\\n"
            "From your specific position and experience, describe 3-4 concrete event "
            "chains that led to this failure. Each should be a sequence of specific "
            "things that went wrong, not abstract categories.\\n\\n"
            f"BAD example (too generic): '{{BAD_EXAMPLE}}'\\n"
            f"GOOD example: '{{GOOD_EXAMPLE}}'\\n\\n"
            f"Be specific about: {{DOMAIN_DETAILS}}. Number each event chain."
        ),
    )

    q_structural = QuestionFreeText(
        question_name="structural_reasons",
        question_text=(
            "Now step back from the specific events. What deeper structural or "
            "institutional factors made this failure nearly inevitable?\\n\\n"
            "BAD example: 'Insufficient stakeholder engagement'\\n"
            f"GOOD example: '{{GOOD_EXAMPLE}}'\\n\\n"
            "Give 3-4 structural factors, each 2-3 sentences. Be specific."
        ),
    )

    results = Survey(questions=[q_episodic, q_structural]).by(agents).by(Model(MODEL_NAME, max_tokens=MAX_TOKENS)).run()
    raw = results.select("agent.agent_name", "answer.episodic_reasons", "answer.structural_reasons").to_dicts(remove_prefix=True)

    rows = []
    for item in raw:
        episodic = item.get("episodic_reasons", "")
        structural = item.get("structural_reasons", "")
        _warn_if_truncated(f"{{item['agent_name']}} episodic_reasons", episodic)
        _warn_if_truncated(f"{{item['agent_name']}} structural_reasons", structural)
        rows.append({{
            "persona": item["agent_name"],
            "episodic_reasons": [episodic],
            "structural_reasons": [structural],
        }})

    write_results(rows)
'''
    return _header("reasons", meta, model_name, output_path, max_tokens) + _write_envelope("reasons", textwrap.dedent(body))


def mitigations_job(
    meta: ProjectMeta,
    personas: list[Persona],
    nodes: list[Node],
    output_path: Path,
    good_example: str,
    bad_example: str,
    model_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    personas_data = [p.model_dump(mode="json") for p in personas]
    nodes_data = [n.model_dump(mode="json") for n in nodes]
    body = f'''
PERSONAS = {_py(personas_data)}
NODES = {_py(nodes_data)}
GOOD_EXAMPLE = {_py(good_example)}
BAD_EXAMPLE = {_py(bad_example)}


def main():
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    if not PERSONAS or not NODES:
        raise SystemExit("Need personas and graph nodes in snapshot. Run earlier phases first.")

    node_list = "\\n".join(f"  - {{n['id']}}: {{n['label']}}" for n in NODES)
    name_to_id = {{p["name"]: p["id"] for p in PERSONAS}}
    agents = AgentList([
        Agent(
            name=p["name"],
            traits={{
                "persona": (
                    f"You are {{p['name']}}, {{p['role']}}. "
                    f"{{p.get('perspective') or ''}} "
                    "You participated in the pre-mortem and identified why this initiative failed. "
                    "Now you are proposing concrete preventive actions. Draw on your specific "
                    "institutional knowledge and position. Do NOT give generic advice."
                ),
            }},
        )
        for p in PERSONAS
    ])

    q = QuestionFreeText(
        question_name="mitigations",
        question_text=(
            f"The pre-mortem identified these causal factors behind the failure of "
            f"{{PROJECT['initiative']}}:\\n\\n{{node_list}}\\n\\n"
            "Propose 3-5 concrete preventive actions. For each:\\n"
            "1. State the specific action (who does what, by when)\\n"
            "2. Say which causal factor node ID(s) it targets, such as n001 or n003\\n"
            "3. Explain WHY it would work from your vantage point\\n\\n"
            f"BAD example: '{{BAD_EXAMPLE}}'\\n"
            f"GOOD example: '{{GOOD_EXAMPLE}}'\\n\\n"
            "Be specific. Name offices, processes, timelines, and dollar amounts."
        ),
    )

    results = Survey(questions=[q]).by(agents).by(Model(MODEL_NAME, max_tokens=MAX_TOKENS)).run()
    raw = results.select("agent.agent_name", "answer.mitigations").to_dicts(remove_prefix=True)

    rows = []
    for item in raw:
        name = item["agent_name"]
        text = item.get("mitigations", "")
        _warn_if_truncated(f"{{name}} mitigations", text)
        rows.append({{
            "persona_id": name_to_id.get(name),
            "persona_name": name,
            "text": text,
        }})

    write_results(rows)
'''
    return _header("mitigations", meta, model_name, output_path, max_tokens) + _write_envelope("mitigations", textwrap.dedent(body))


def research_agenda_job(
    meta: ProjectMeta,
    personas: list[Persona],
    nodes: list[Node],
    reasons: list[Reason],
    output_path: Path,
    model_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    personas_data = [p.model_dump(mode="json") for p in personas]
    nodes_data = [n.model_dump(mode="json") for n in nodes]
    reasons_data = [r.model_dump(mode="json") for r in reasons]
    body = f'''
PERSONAS = {_py(personas_data)}
NODES = {_py(nodes_data)}
REASONS = {_py(reasons_data)}


def main():
    from edsl import Agent, AgentList, QuestionFreeText, Survey, Model

    if not PERSONAS or not NODES:
        raise SystemExit("Need personas and graph nodes in snapshot. Run earlier phases first.")

    node_list = "\\n".join(f"  - {{n['id']}}: {{n['label']}}" for n in NODES)
    persona_map = {{p["id"]: p["name"] for p in PERSONAS}}
    reason_excerpts = ""
    for r in REASONS:
        pname = persona_map.get(r["persona_id"], "Unknown")
        reason_excerpts += f"\\n[{{pname}}, {{r['kind']}}]: {{r['text'][:400]}}...\\n"

    name_to_id = {{p["name"]: p["id"] for p in PERSONAS}}
    agents = AgentList([
        Agent(
            name=p["name"],
            traits={{
                "persona": (
                    f"You are {{p['name']}}, {{p['role']}}. "
                    f"{{p.get('perspective') or ''}} "
                    "You participated in the pre-mortem and now you are identifying which "
                    "assumed failure factors are actually uncertain and testable before launch."
                ),
            }},
        )
        for p in PERSONAS
    ])

    q = QuestionFreeText(
        question_name="research_agenda",
        question_text=(
            f"The pre-mortem for '{{PROJECT['initiative']}}' identified these causal factors:\\n\\n"
            f"{{node_list}}\\n\\n"
            f"Context from the failure analysis:\\n{{reason_excerpts}}\\n\\n"
            "Identify 2-4 important and resolvable uncertainties. For each, state what "
            "we assume, why it is uncertain, how to resolve it, who to study, and what "
            "finding would change the decision. Be concrete about surveys, pilots, "
            "interviews, analyses, thresholds, and decision rules."
        ),
    )

    results = Survey(questions=[q]).by(agents).by(Model(MODEL_NAME, max_tokens=MAX_TOKENS)).run()
    raw = results.select("agent.agent_name", "answer.research_agenda").to_dicts(remove_prefix=True)

    rows = []
    for item in raw:
        name = item["agent_name"]
        text = item.get("research_agenda", "")
        _warn_if_truncated(f"{{name}} research_agenda", text)
        rows.append({{
            "persona_id": name_to_id.get(name),
            "persona_name": name,
            "text": text,
        }})

    write_results(rows)
'''
    return _header("research-agenda", meta, model_name, output_path, max_tokens) + _write_envelope("research_agenda", textwrap.dedent(body))


def summary_job(
    meta: ProjectMeta,
    personas: list[Persona],
    nodes: list[Node],
    edges: list[Edge],
    reasons: list[Reason],
    output_path: Path,
    model_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    personas_data = [p.model_dump(mode="json") for p in personas]
    nodes_data = [n.model_dump(mode="json") for n in nodes]
    edges_data = [e.model_dump(mode="json") for e in edges]
    reasons_data = [r.model_dump(mode="json") for r in reasons]
    body = f'''
PERSONAS = {_py(personas_data)}
NODES = {_py(nodes_data)}
EDGES = {_py(edges_data)}
REASONS = {_py(reasons_data)}


def main():
    from edsl import Agent, QuestionFreeText, Survey, Model

    persona_summaries = "\\n".join(f"- {{p['name']}} ({{p['role']}})" for p in PERSONAS)
    node_list = "\\n".join(f"  - {{n['id']}}: {{n['label']}}" for n in NODES)
    edge_list = "\\n".join(f"  - {{e['source']}} -> {{e['target']}}: {{e.get('label') or ''}}" for e in EDGES)
    persona_map = {{p["id"]: p["name"] for p in PERSONAS}}

    reason_excerpts = ""
    for r in REASONS:
        pname = persona_map.get(r["persona_id"], "Unknown")
        reason_excerpts += f"\\n[{{pname}}, {{r['kind']}}]: {{r['text'][:500]}}...\\n"

    synthesizer = Agent(
        name="Synthesizer",
        traits={{
            "persona": (
                "You are a senior strategy consultant writing an executive summary of a "
                "pre-mortem analysis. You synthesize findings across multiple stakeholder "
                "perspectives into clear, actionable conclusions. You write in crisp, direct "
                "prose, no jargon and no hedging."
            ),
        }},
    )

    q = QuestionFreeText(
        question_name="executive_summary",
        question_text=(
            f"Write the executive summary for a pre-mortem analysis of: {{PROJECT['initiative']}}\\n\\n"
            f"Description: {{PROJECT.get('description')}}\\n\\n"
            f"Failure statement: {{PROJECT['failure_statement']}}\\n\\n"
            f"Personas consulted:\\n{{persona_summaries}}\\n\\n"
            f"Causal graph:\\n{{node_list}}\\n\\nEdges:\\n{{edge_list}}\\n\\n"
            f"Key findings:\\n{{reason_excerpts}}\\n\\n"
            "Write 4-5 paragraphs covering: core finding, main causal mechanisms, "
            "highest-leverage intervention points, research needed before a decision, "
            "and bottom-line recommendation. Be specific."
        ),
    )

    results = Survey(questions=[q]).by(synthesizer).by(Model(MODEL_NAME, max_tokens=MAX_TOKENS)).run()
    raw = results.select("answer.executive_summary").to_dicts(remove_prefix=True)
    summary_text = raw[0].get("executive_summary", "")
    _warn_if_truncated("executive_summary", summary_text)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    envelope = {{
        "premortem_version": "0.1.0",
        "entity_type": "executive_summary",
        "initiative": PROJECT["initiative"],
        "generated_at": now_iso(),
        "text": summary_text,
    }}
    OUTPUT_PATH.write_text(json.dumps(envelope, indent=2) + "\\n")
    print(f"Wrote executive summary to {{OUTPUT_PATH}}")
    print("Next: premortem analyze report")
'''
    return _header("summary", meta, model_name, output_path, max_tokens) + textwrap.dedent(body) + '\n\nif __name__ == "__main__":\n    main()\n'
