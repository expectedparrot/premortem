# Pre-mortem Workflow Overview

A pre-mortem states that an initiative has already failed, then works backward
to identify plausible causal paths, mitigations, and researchable uncertainties.

For the full facilitation procedure and command sequence, run:

`premortem docs show facilitation-guide`

Recommended phases:

1. Initialize the project with a vivid, definitive failure statement.
2. Generate and review 4-6 stakeholder personas.
3. Elicit episodic and structural failure reasons from those personas.
4. Build a simple causal graph with about 8 nodes and 10 edges.
5. Generate mitigations that target graph nodes.
6. Generate a research agenda for unresolved empirical questions.
7. Generate an executive summary and reports.

The CLI owns `.premortem/` state. Generated EDSL jobs should write result files
under `.premortem/output/`; use `premortem ingest ...` to mutate store state.
