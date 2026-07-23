from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import PremortemError
from .store import ProjectStore


CHECKLISTS: dict[str, list[str]] = {
    "init": [
        "Extract initiative name, description, stakeholders, timeline, and success criteria.",
        "Draft a definitive failure statement as completed fact.",
        "Remove causes and hedging from the failure statement.",
        "Run premortem init.",
    ],
    "personas": [
        "Generate an auditable personas EDSL job.",
        "Run the generated job and ingest results_personas.json.",
        "Review 4-6 personas for specificity and conflicting incentives.",
        "Ask the user to approve the persona panel before reasons.",
    ],
    "reasons": [
        "Generate an auditable reasons EDSL job with domain details and a strong good example.",
        "Run the generated job and ingest results_reasons.json.",
        "Confirm reasons are rich narratives, not generic bullets.",
    ],
    "causal-graph": [
        "Read failure reasons and synthesize about 8 causal nodes.",
        "Add 3-4 root causes, 2-3 intermediate effects, and 1-2 terminal outcomes.",
        "Add about 10 directed edges with concise mechanism labels.",
        "Review graph readability and ask the user before locking it.",
    ],
    "mitigations": [
        "Generate an auditable mitigations EDSL job.",
        "Require mitigations to mention target node IDs.",
        "Run the generated job and ingest results_mitigations.json.",
        "Review unassigned mitigations and map them to nodes where appropriate.",
    ],
    "research-agenda": [
        "Generate and run a research agenda job.",
        "Check that each item has an assumption, method, population, and decision threshold.",
    ],
    "summary-report": [
        "Generate and run an executive summary job.",
        "Generate the interactive HTML report.",
        "Write or compile the standard report if using a study scaffold.",
    ],
}


PHASE_DOCS = {
    "intake": "facilitation-guide",
    "init": "failure-statement",
    "personas": "personas",
    "reasons": "failure-reasons",
    "causal-graph": "causal-graph",
    "mitigations": "mitigations",
    "research-agenda": "research-agenda",
    "summary-report": "reporting",
}


INTAKE_CHECKLIST = [
    "Ask what initiative, launch, policy, program, or decision should be analyzed.",
    "Ask for context: stakeholders, timeline, scale, constraints, systems, budget, dependencies, or success criteria.",
    "Draft a concise initiative name, description, and completed-fact failure statement for user approval.",
    "After approval, run premortem init with the drafted values.",
]


def project_counts(store: ProjectStore) -> dict[str, int]:
    reasons = store.list_reasons()
    return {
        "personas": len(store.list_personas()),
        "reasons_episodic": len([r for r in reasons if r.kind == "episodic"]),
        "reasons_structural": len([r for r in reasons if r.kind == "structural"]),
        "graph_nodes": len(store.list_nodes()),
        "graph_edges": len(store.list_edges()),
        "scores": len(store.list_scores()),
        "mitigations": len(store.list_mitigations()),
    }


def infer_phase(store: ProjectStore) -> str:
    store.require_project()
    counts = project_counts(store)
    output_dir = store.root / "output"
    if counts["personas"] == 0:
        return "personas"
    if counts["reasons_episodic"] == 0 and counts["reasons_structural"] == 0:
        return "reasons"
    if counts["graph_nodes"] == 0:
        return "causal-graph"
    if counts["mitigations"] == 0:
        return "mitigations"
    if not (output_dir / "results_research_agenda.json").exists():
        return "research-agenda"
    if not (output_dir / "results_exec_summary.json").exists():
        return "summary-report"
    return "complete"


def artifacts(store: ProjectStore) -> list[dict[str, Any]]:
    study_root = store.root.parent if store.root.name == ".premortem" else store.root
    expected_paths: list[tuple[Path, str]] = [
        (store.root / "output" / "results_personas.json", "premortem_output"),
        (store.root / "output" / "results_reasons.json", "premortem_output"),
        (store.root / "output" / "results_mitigations.json", "premortem_output"),
        (store.root / "output" / "results_research_agenda.json", "premortem_output"),
        (store.root / "output" / "results_exec_summary.json", "premortem_output"),
        (store.root / "output" / "report.html", "premortem_output"),
        (study_root / "writeup" / "report.md", "macaw_writeup"),
        (study_root / "writeup" / "premortem_report.html", "macaw_writeup"),
        (study_root / "writeup" / "plots" / "causal_graph.png", "macaw_writeup"),
    ]
    records: list[dict[str, Any]] = [
        {
            "path": str(path),
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() and path.is_file() else None,
            "source": source,
        }
        for path, source in expected_paths
    ]
    # When running inside a macaw task, additionally surface every existing
    # file under the standard macaw subdirs (`writeup/`, `analysis/`, `data/`)
    # so `workflow artifacts` reports them even when the names don't match
    # premortem's expected file list.
    macaw_root = _macaw_task_root(store)
    if macaw_root is not None:
        seen = {record["path"] for record in records}
        for subdir, source in (
            ("writeup", "macaw_writeup"),
            ("analysis", "macaw_analysis"),
            ("data", "macaw_data"),
        ):
            base = macaw_root / subdir
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "path": key,
                        "exists": True,
                        "size": path.stat().st_size,
                        "source": source,
                    }
                )
    return records


def _macaw_task_root(store: ProjectStore) -> Path | None:
    if store.root.name == ".premortem":
        candidate = store.root.parent
        if (candidate / ".macaw_task").exists() or (candidate / "writeup").exists():
            return candidate
    return None


def next_steps(phase: str) -> list[dict[str, str]]:
    by_phase: dict[str, list[dict[str, str]]] = {
        "intake": [
            {"label": "Read the facilitation guide", "command": "premortem docs show facilitation-guide"},
            {"label": "Ask for initiative and context", "command": "Ask the user for the planned initiative and relevant context."},
            {"label": "Draft failure statement", "command": "Draft a completed-fact failure statement and ask the user to approve it."},
            {"label": "Initialize after approval", "command": "premortem init --initiative \"...\" --failure \"...\" --description \"...\""},
        ],
        "personas": [
            {"label": "Generate personas job", "command": "premortem job generate personas --context \"...\" --requirements \"...\""},
            {"label": "Run generated job", "command": "python jobs/run_personas.py"},
            {"label": "Ingest personas", "command": "premortem ingest personas --from .premortem/output/results_personas.json"},
        ],
        "reasons": [
            {"label": "Generate reasons job", "command": "premortem job generate reasons --domain \"...\" --good-example \"...\""},
            {"label": "Run generated job", "command": "python jobs/run_reasons.py"},
            {"label": "Ingest reasons", "command": "premortem ingest reasons --from .premortem/output/results_reasons.json"},
        ],
        "causal-graph": [
            {"label": "Review reasons", "command": "premortem reason list --human"},
            {"label": "Add nodes", "command": "premortem graph add-node --label \"...\" --reason r001"},
            {"label": "Add edges", "command": "premortem graph add-edge --from n001 --to n004 --label \"...\""},
        ],
        "mitigations": [
            {"label": "Generate mitigations job", "command": "premortem job generate mitigations --good-example \"...\""},
            {"label": "Run generated job", "command": "python jobs/run_mitigations.py"},
            {"label": "Ingest mitigations", "command": "premortem ingest mitigations --from .premortem/output/results_mitigations.json"},
        ],
        "research-agenda": [
            {"label": "Generate research agenda job", "command": "premortem job generate research-agenda"},
            {"label": "Run generated job", "command": "python jobs/run_research_agenda.py"},
        ],
        "summary-report": [
            {"label": "Generate summary job", "command": "premortem job generate summary"},
            {"label": "Run generated job", "command": "python jobs/run_summary.py"},
            {"label": "Generate HTML report", "command": "premortem analyze report"},
        ],
        "complete": [
            {"label": "Inspect status", "command": "premortem status --human"},
            {"label": "Regenerate HTML report", "command": "premortem analyze report"},
        ],
    }
    return by_phase.get(phase, [])


def missing_project_next(project_dir: Path) -> dict[str, Any]:
    return {
        "phase": "intake",
        "project_exists": False,
        "project_dir": str(project_dir),
        "doc_topic": "facilitation-guide",
        "checklist": INTAKE_CHECKLIST,
        "required_user_inputs": [
            "initiative to analyze",
            "context such as stakeholders, timeline, constraints, scale, systems, budget, dependencies, or success criteria",
        ],
        "facilitator_instruction": (
            "Do not ask the user to provide a polished failure statement. Ask for the initiative and context, "
            "draft the completed-fact failure statement yourself, then ask the user to approve or edit it."
        ),
        "recommended_next_steps": next_steps("intake"),
    }


def phase_state(store: ProjectStore) -> dict[str, Any]:
    try:
        phase = infer_phase(store)
        return {
            "phase": phase,
            "project_exists": True,
            "counts": project_counts(store),
            "checklist": CHECKLISTS.get(phase, []),
            "recommended_next_steps": next_steps(phase),
        }
    except PremortemError as err:
        if err.code == "ID_NOT_FOUND":
            return missing_project_next(store.root)
        raise
