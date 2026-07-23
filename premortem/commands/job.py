from __future__ import annotations

from pathlib import Path

import typer

from .. import jobgen
from ..store import PremortemError
from .common import HumanOption, ProjectDirOption, QuietOption, fail, finish, should_emit_json, store_for

app = typer.Typer(help="Generate auditable EDSL job scripts.")
generate_app = typer.Typer(help="Generate EDSL scripts for analysis phases.")
app.add_typer(generate_app, name="generate")

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 4096


def _write_script(output: Path, content: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output


def _default_output(name: str) -> Path:
    return Path("jobs") / f"run_{name}.py"


def _result_path(store, name: str) -> Path:
    return store.root / "output" / f"results_{name}.json"


def _finish_job(
    command: str,
    script_path: Path,
    result_path: Path,
    ingest_command: str | None,
    json_flag: bool,
    quiet: bool,
) -> None:
    data = {
        "script_path": str(script_path),
        "result_path": str(result_path),
        "run_command": f"python {script_path}",
        "ingest_command": ingest_command,
    }
    next_steps = [f"python {script_path}"]
    if ingest_command:
        next_steps.append(ingest_command)
    if json_flag:
        finish(command, data, True, quiet, next_steps=next_steps)
        return
    if not quiet:
        from ..renderer import render_kv_panel

        items = [
            ("Script", str(script_path)),
            ("Run", f"python {script_path}"),
            ("Results", str(result_path)),
        ]
        if ingest_command:
            items.append(("Then", ingest_command))
        render_kv_panel("EDSL job generated", items)


@generate_app.command("personas")
def generate_personas(
    context: str = typer.Option(..., "--context", "-c"),
    requirements: str = typer.Option(..., "--requirements", "-r"),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    max_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens", help="Per-call output token cap. Raise if outputs are getting truncated."),
    output: Path = typer.Option(_default_output("personas"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "job generate personas"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        result_path = _result_path(store, "personas")
        script_path = _write_script(output, jobgen.personas_job(meta, result_path, context, requirements, model_name, max_tokens))
    except PremortemError as err:
        fail(command, err, json_flag)
    _finish_job(command, script_path, result_path, f"premortem ingest personas --from {result_path}", json_flag, quiet)


@generate_app.command("reasons")
def generate_reasons(
    domain_details: str = typer.Option(..., "--domain", "-d"),
    good_example: str = typer.Option(..., "--good-example", "-g"),
    bad_example: str = typer.Option("Lack of alignment with institutional culture", "--bad-example"),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    max_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens", help="Per-call output token cap. Raise if outputs are getting truncated."),
    output: Path = typer.Option(_default_output("reasons"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "job generate reasons"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        result_path = _result_path(store, "reasons")
        script_path = _write_script(
            output,
            jobgen.reasons_job(meta, personas, result_path, domain_details, good_example, bad_example, model_name, max_tokens),
        )
    except PremortemError as err:
        fail(command, err, json_flag)
    _finish_job(command, script_path, result_path, f"premortem ingest reasons --from {result_path}", json_flag, quiet)


@generate_app.command("mitigations")
def generate_mitigations(
    good_example: str = typer.Option(..., "--good-example", "-g"),
    bad_example: str = typer.Option("Improve stakeholder engagement", "--bad-example"),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    max_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens", help="Per-call output token cap. Raise if outputs are getting truncated."),
    output: Path = typer.Option(_default_output("mitigations"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "job generate mitigations"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        nodes = store.list_nodes()
        result_path = _result_path(store, "mitigations")
        script_path = _write_script(
            output,
            jobgen.mitigations_job(meta, personas, nodes, result_path, good_example, bad_example, model_name, max_tokens),
        )
    except PremortemError as err:
        fail(command, err, json_flag)
    _finish_job(command, script_path, result_path, f"premortem ingest mitigations --from {result_path}", json_flag, quiet)


@generate_app.command("research-agenda")
def generate_research_agenda(
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    max_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens", help="Per-call output token cap. Raise if outputs are getting truncated."),
    output: Path = typer.Option(_default_output("research_agenda"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "job generate research-agenda"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        nodes = store.list_nodes()
        reasons = store.list_reasons()
        result_path = _result_path(store, "research_agenda")
        script_path = _write_script(
            output,
            jobgen.research_agenda_job(meta, personas, nodes, reasons, result_path, model_name, max_tokens),
        )
    except PremortemError as err:
        fail(command, err, json_flag)
    _finish_job(command, script_path, result_path, None, json_flag, quiet)


@generate_app.command("summary")
def generate_summary(
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", "-m"),
    max_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens", help="Per-call output token cap. Raise if outputs are getting truncated."),
    output: Path = typer.Option(_default_output("summary"), "--output", "-o"),
    project_dir: Path | None = ProjectDirOption,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "job generate summary"
    json_flag = should_emit_json(human)
    store = store_for(project_dir)
    try:
        store.require_project()
        meta = store.read_meta()
        personas = store.list_personas()
        nodes = store.list_nodes()
        edges = store.list_edges()
        reasons = store.list_reasons()
        result_path = store.root / "output" / "results_exec_summary.json"
        script_path = _write_script(
            output,
            jobgen.summary_job(meta, personas, nodes, edges, reasons, result_path, model_name, max_tokens),
        )
    except PremortemError as err:
        fail(command, err, json_flag)
    _finish_job(command, script_path, result_path, None, json_flag, quiet)
