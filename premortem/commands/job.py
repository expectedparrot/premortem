from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from .. import edsl_jobs
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Build portable EDSL Jobs packages.")
generate_app = typer.Typer(help="Build .ep Jobs packages for analysis phases.")
app.add_typer(generate_app, name="generate")


def _default_output(phase: str) -> Path:
    return Path("jobs") / f"{phase}.jobs.ep"


def _finish(
    command: str,
    phase: str,
    jobs: object,
    output: Path,
    saved: object,
    json_flag: bool,
    quiet: bool,
    ingest_phase: str | None = None,
) -> None:
    expected = edsl_jobs.expected_results_path(output)
    run = f"ep run {output} --model <model-name> --output {expected}"
    data = {
        "object_type": "Jobs",
        "phase": phase,
        "output_path": str(output),
        "expected_results_path": str(expected),
        "question_names": list(jobs.survey.question_names),
        "agent_count": len(jobs.agents),
        "scenario_count": len(jobs.scenarios),
        "model_count": len(jobs.models),
        "saved": saved,
    }
    next_steps = [f"ep inspect {output}", f"ep jobs cost {output}", run]
    if ingest_phase:
        next_steps.append(f"premortem ingest {ingest_phase} --from {expected}")
    if json_flag:
        finish(command, data, True, quiet, next_steps=next_steps)
        return
    if not quiet:
        from ..renderer import render_kv_panel
        render_kv_panel("EDSL Jobs package", [
            ("Phase", phase),
            ("Jobs", str(output)),
            ("Inspect", f"ep inspect {output}"),
            ("Run", run),
        ])


def _build(
    command: str,
    phase: str,
    output: Path,
    project_dir: Path | None,
    human: bool,
    quiet: bool,
    builder: Callable,
    ingest_phase: str | None,
) -> None:
    json_flag = should_emit_json(human)
    try:
        jobs = builder(store_for(project_dir))
        saved = edsl_jobs.save_jobs(jobs, output)
    except PremortemError as err:
        fail(command, err, json_flag)
    except Exception as exc:
        fail(command, PremortemError("EDSL_ERROR", str(exc), context=str(output)), json_flag)
    _finish(command, phase, jobs, output, saved, json_flag, quiet, ingest_phase)


@generate_app.command("personas")
def generate_personas(
    context: str = typer.Option(..., "--context", "-c"),
    requirements: str = typer.Option(..., "--requirements", "-r"),
    output: Path = typer.Option(_default_output("personas"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    def builder(store):
        store.require_project()
        return edsl_jobs.personas_jobs(store.read_meta(), context, requirements)
    _build("job generate personas", "personas", output, project_dir, human, quiet, builder, "personas")


@generate_app.command("reasons")
def generate_reasons(
    domain: str = typer.Option(..., "--domain", "-d"),
    good_example: str = typer.Option(..., "--good-example", "-g"),
    bad_example: str = typer.Option("Lack of alignment with institutional culture", "--bad-example"),
    output: Path = typer.Option(_default_output("reasons"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    def builder(store):
        store.require_project()
        personas = store.list_personas()
        if not personas:
            raise PremortemError("WORKFLOW_BLOCKED", "Personas are required before building reason jobs.")
        return edsl_jobs.reasons_jobs(store.read_meta(), personas, domain, good_example, bad_example)
    _build("job generate reasons", "reasons", output, project_dir, human, quiet, builder, "reasons")


@generate_app.command("mitigations")
def generate_mitigations(
    good_example: str = typer.Option(..., "--good-example", "-g"),
    bad_example: str = typer.Option("Improve stakeholder engagement", "--bad-example"),
    output: Path = typer.Option(_default_output("mitigations"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    def builder(store):
        store.require_project()
        personas, nodes = store.list_personas(), store.list_nodes()
        if not personas or not nodes:
            raise PremortemError("WORKFLOW_BLOCKED", "Personas and graph nodes are required before building mitigation jobs.")
        return edsl_jobs.mitigations_jobs(store.read_meta(), personas, nodes, good_example, bad_example)
    _build("job generate mitigations", "mitigations", output, project_dir, human, quiet, builder, "mitigations")


@generate_app.command("research-agenda")
def generate_research(
    output: Path = typer.Option(_default_output("research-agenda"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    def builder(store):
        store.require_project()
        personas, nodes = store.list_personas(), store.list_nodes()
        if not personas or not nodes:
            raise PremortemError("WORKFLOW_BLOCKED", "Personas and graph nodes are required before building research jobs.")
        return edsl_jobs.research_jobs(store.read_meta(), personas, nodes, store.list_reasons())
    _build("job generate research-agenda", "research_agenda", output, project_dir, human, quiet, builder, "research-agenda")


@generate_app.command("summary")
def generate_summary(
    output: Path = typer.Option(_default_output("summary"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    def builder(store):
        store.require_project()
        return edsl_jobs.summary_jobs(
            store.read_meta(), store.list_personas(), store.list_nodes(), store.list_edges(), store.list_reasons()
        )
    _build("job generate summary", "executive_summary", output, project_dir, human, quiet, builder, "summary")
