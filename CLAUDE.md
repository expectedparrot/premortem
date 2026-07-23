# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project overview

Premortem is a Typer-based CLI for Gary Klein style pre-mortem analysis. It manages a `.premortem/` project directory, walks a user through the phases of a pre-mortem, generates auditable LLM jobs, ingests their outputs into structured JSON records, and produces summary/report artifacts.

The package is also exposed to the broader research workspace as a Macaw plugin via the `premortem` entry in `pyproject.toml`.

## Commands

```bash
pip install -e .              # install editable
premortem --help              # CLI entry point
python -m premortem.cli       # run without installing
premortem docs list           # list bundled facilitation docs
premortem status         # bootstrap payload for agents
premortem workflow next       # infer current phase and next steps
```

There is no local test suite in this package today.

## Architecture

- `premortem/cli.py` wires the Typer subcommands together. Each command group lives in `premortem/commands/`.
- `premortem/store.py` is the persistence layer. `ProjectStore` owns `.premortem/`, reads/writes all Pydantic models, creates the on-disk layout, resolves the default project directory, and provides a lock file for single-writer mutations.
- `premortem/workflow.py` infers the current phase from on-disk state, defines per-phase checklists, expected artifacts, and recommended next commands.
- `premortem/docs.py` and `premortem/docs_content/*.md` provide the built-in facilitation and workflow guidance surfaced through `premortem docs ...`.
- `premortem/jobgen.py` and `jobs/run_*.py` support the LLM-backed phases: personas, reasons, mitigations, research agenda, and summary generation.
- `premortem/ingest.py` converts generated result files into store records.
- `premortem/renderer.py` handles JSON and human-readable output.

## Agent-facing contract

- JSON is the default output mode. `--human` switches commands to rich text; `PREMORTEM_HUMAN_OUTPUT=true` flips the default globally.
- All command groups use the shared envelope helpers in `premortem/commands/common.py`: successful JSON responses include `command`, `status`, `data`, `warnings`, `errors`, and `next_steps`.
- `premortem workflow next` and `premortem workflow phase` are the main source of truth for execution order. Avoid hard-coding phase transitions elsewhere.
- Do not edit `.premortem/*.json` by hand when command coverage exists. Use the CLI and ingestion paths so state stays consistent.

## Storage model

The project root is usually `<task_dir>/.premortem`, but resolution is layered:

1. `--project-dir`
2. `PREMORTEM_PROJECT_DIR`
3. `./.premortem`

Within `.premortem/`, state is flat JSON by collection:

- `meta.json`
- `personas/*.json`
- `reasons/*.json`
- `graph/nodes/*.json`
- `graph/edges/*.json`
- `scores/*.json`
- `mitigations/*.json`
- `output/` for generated result files and reports

## Important conventions

- `ProjectStore.init_project()` creates the canonical directory layout. New features should fit that layout instead of inventing parallel storage.
- Workflow phase is inferred from counts and expected output files, not stored as durable workflow metadata.
- Deleting a graph node also removes connected edges; code that mutates the graph should preserve that invariant.
- Human-readable output is implemented inside each command, but JSON output should stay machine-stable because agents depend on it.
- Bundled docs are package data. If you add or rename a doc in `premortem/docs_content/`, keep `docs.py` behavior and any workflow doc references aligned.
