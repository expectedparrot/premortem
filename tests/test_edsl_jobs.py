from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from edsl import Agent, Jobs, Model, Results, Scenario
from edsl.results import Result

from premortem import edsl_jobs
from premortem.ingest import load_results_file
from premortem.models import ProjectMeta


def meta() -> ProjectMeta:
    timestamp = datetime(2026, 7, 23, tzinfo=timezone.utc)
    return ProjectMeta(
        id="pm_test",
        initiative="Analytics launch",
        description="Launch analytics to enterprise customers.",
        failure_statement="It is six months later. Adoption is below 10%.",
        created_at=timestamp,
        updated_at=timestamp,
        phase="personas",
    )


def test_personas_builder_creates_model_free_jobs() -> None:
    jobs = edsl_jobs.personas_jobs(
        meta(),
        "B2B SaaS product-launch facilitator",
        "customer admin, support lead, engineering lead",
    )

    assert jobs.survey.question_names == ["personas"]
    assert len(jobs.agents) == 1
    assert len(jobs.scenarios) == 1
    assert len(jobs.models) == 0
    scenario = dict(jobs.scenarios[0])
    assert scenario["premortem_phase"] == "personas"
    assert scenario["project_id"] == "pm_test"


def test_jobs_round_trip_through_ep_package(tmp_path) -> None:
    output = tmp_path / "personas.jobs.ep"
    jobs = edsl_jobs.personas_jobs(meta(), "Facilitator", "admin, operator, skeptic")

    edsl_jobs.save_jobs(jobs, output)
    loaded = Jobs.git.load(output)

    assert loaded.survey.question_names == ["personas"]
    assert len(loaded.models) == 0
    assert dict(loaded.scenarios[0])["initiative"] == "Analytics launch"
    assert edsl_jobs.expected_results_path(output).name == "personas-results.ep"


def test_personas_results_ep_normalizes_for_ingestion(tmp_path) -> None:
    jobs = edsl_jobs.personas_jobs(meta(), "Facilitator", "admin, operator, skeptic")
    result = Result(
        agent=Agent(name="premortem_facilitator"),
        scenario=Scenario(dict(jobs.scenarios[0])),
        model=Model("test"),
        iteration=0,
        answer={"personas": ["Avery | Support lead | Owns the escalation queue."]},
    )
    output = tmp_path / "personas-results.ep"
    Results(survey=jobs.survey, data=[result]).git.save(output)

    normalized = load_results_file(output, "personas")

    assert normalized["entity_type"] == "personas"
    assert normalized["rows"] == [{
        "persona_name": "Avery",
        "role": "Support lead",
        "perspective": "Owns the escalation queue.",
    }]


def test_all_phase_builders_are_portable_and_model_free() -> None:
    personas = [SimpleNamespace(id="p001", name="Avery", role="Support lead", perspective="Owns escalations.")]
    nodes = [SimpleNamespace(id="n001", label="Migration blocks setup")]
    reasons = [SimpleNamespace(id="r001", text="Admins cannot map legacy roles.")]
    edges = [SimpleNamespace(source="n001", target="n002", label="causes abandonment")]

    jobs_objects = [
        edsl_jobs.reasons_jobs(meta(), personas, "permissions", "Specific example", "Generic example"),
        edsl_jobs.mitigations_jobs(meta(), personas, nodes, "Specific action", "Generic action"),
        edsl_jobs.research_jobs(meta(), personas, nodes, reasons),
        edsl_jobs.summary_jobs(meta(), personas, nodes, edges, reasons),
    ]

    assert [jobs.survey.question_names for jobs in jobs_objects] == [
        ["episodic_reasons", "structural_reasons"],
        ["mitigations"],
        ["research_agenda"],
        ["executive_summary"],
    ]
    assert all(len(jobs.models) == 0 for jobs in jobs_objects)
