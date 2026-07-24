# Pre-mortem Facilitation Guide

A pre-mortem is a structured prospective-hindsight exercise. Instead of asking
whether an initiative might fail, it states that the initiative has already
failed and asks how that failure happened.

That certainty matters. It lets participants stop defending the plan and start
describing concrete breakdowns, hidden dependencies, stakeholder incentives, and
failure paths that are hard to surface in ordinary risk reviews.

The output is not a prediction. It is a decision aid: a set of plausible failure
mechanisms, a simple causal graph, concrete mitigations, and research questions
that should be answered before launch.

## Core Rules

- State failure as a completed fact.
- Describe consequences in the failure statement, not causes.
- Use specific domain details, not generic management language.
- Use diverse stakeholder personas to generate different failure stories.
- Keep the causal graph simple enough to read quickly.
- Tie mitigations to graph nodes.
- Treat unresolved assumptions as research questions.

## Standard Command Sequence

The default project directory is `.premortem/`. Use `--project-dir` when working
outside the current directory.

## If You Are Facilitating For A User

Do not expect the user to provide a polished failure statement. The facilitator
should help create it.

Minimum intake:

1. What initiative, launch, policy, program, or decision should be analyzed?
2. What context matters: stakeholders, timeline, scale, constraints, systems,
   budget, dependencies, or success criteria?

If the user gives only a high-level initiative, ask at most two concise
clarifying questions. Then draft:

- A concise initiative name.
- A description using the user's context.
- A completed-fact failure statement that describes bad outcomes and leaves
  causes out.

Show that draft to the user for approval or edits before running
`premortem init`. The user should not need to know how to write a pre-mortem
failure statement in advance.

### 1. Initialize The Project

Draft a vivid failure statement before running this command. It should say what
went wrong in outcome terms and avoid explaining why. If you are an agent, draft
this yourself from the intake and ask the user to approve it.

```bash
premortem init \
  --initiative "<initiative name>" \
  --failure "<definitive failure statement>" \
  --description "<initiative context, stakeholders, timeline, constraints>"
```

Check your position:

```bash
premortem workflow next
premortem docs show failure-statement
```

### 2. Generate And Ingest Personas

Build a portable, model-free EDSL Jobs package:

```bash
premortem job generate personas \
  --context "<domain expert perspective>" \
  --requirements "<role 1>,<role 2>,<role 3>,<role 4>,<role 5>" \
  --output jobs/personas.jobs.ep
```

Run and ingest:

```bash
ep inspect jobs/personas.jobs.ep
ep jobs cost jobs/personas.jobs.ep
ep run jobs/personas.jobs.ep --model <model-name> --output jobs/personas-results.ep
premortem ingest personas --from jobs/personas-results.ep
premortem persona list --human
```

Pause here. Review whether the personas are specific, realistic, and distinct
before generating reasons.

### 3. Generate And Ingest Failure Reasons

Give the job concrete domain details and one strong example of the specificity
you expect.

```bash
premortem job generate reasons \
  --domain "<specific systems, dates, offices, budgets, stakeholders>" \
  --good-example "<specific failure chain grounded in the domain>" \
  --output jobs/reasons.jobs.ep
```

Run and ingest:

```bash
ep inspect jobs/reasons.jobs.ep
ep run jobs/reasons.jobs.ep --model <model-name> --output jobs/reasons-results.ep
premortem ingest reasons --from jobs/reasons-results.ep
premortem reason list --human
```

The result should include episodic event chains and structural factors. If the
output reads like generic risk bullets, regenerate with a stronger example.

### 4. Build The Causal Graph

The graph is analyst work. Do not delegate it blindly to EDSL. Read the reasons,
then synthesize about eight nodes and ten edges.

```bash
premortem reason list --human
premortem graph add-node --label "<specific root cause>" --reason r001
premortem graph add-node --label "<specific intermediate effect>" --reason r004
premortem graph add-node --label "<terminal failure outcome>"
premortem graph add-edge --from n001 --to n004 --label "<causal mechanism>"
premortem graph list --human
```

Target:

- 3-4 root causes.
- 2-3 intermediate effects.
- 1-2 terminal outcomes.

Pause here. The graph should be readable in under 30 seconds and should show
where multiple causes converge.

### 5. Generate And Ingest Mitigations

Mitigations should name node IDs and specify who does what by when.

```bash
premortem job generate mitigations \
  --good-example "<specific action that targets n001 by owner and date>" \
  --output jobs/mitigations.jobs.ep
```

Run and ingest:

```bash
ep inspect jobs/mitigations.jobs.ep
ep run jobs/mitigations.jobs.ep --model <model-name> --output jobs/mitigations-results.ep
premortem ingest mitigations --from jobs/mitigations-results.ep
premortem mitigate list --human
```

Review any mitigations with no node targets and either map them to graph nodes
or treat them as weak/unusable.

### 6. Generate The Research Agenda

The research agenda identifies assumptions that are important, uncertain, and
testable before launch.

```bash
premortem job generate research-agenda --output jobs/research-agenda.jobs.ep
ep run jobs/research-agenda.jobs.ep --model <model-name> --output jobs/research-agenda-results.ep
premortem ingest research-agenda --from jobs/research-agenda-results.ep
```

### 7. Generate The Executive Summary

```bash
premortem job generate summary --output jobs/summary.jobs.ep
ep run jobs/summary.jobs.ep --model <model-name> --output jobs/summary-results.ep
premortem ingest summary --from jobs/summary-results.ep
```

### 8. Generate Reports

Generate the interactive HTML report:

```bash
premortem analyze report
```

Generate a Markdown report from store-backed entities:

```bash
premortem report generate --output writeup/report.md
```

Check artifacts:

```bash
premortem workflow artifacts
```

## Useful Sense-Making Commands

```bash
premortem status --human
premortem workflow phase
premortem workflow next
premortem workflow checklist
premortem workflow guide causal-graph
premortem docs search "<question>"
```

## What Good Looks Like

The final analysis should answer:

1. What does definitive failure look like?
2. Which stakeholders see the failure differently?
3. What event chains and structural factors plausibly lead to failure?
4. Which root causes converge into the most dangerous pathways?
5. What concrete actions could break those pathways before launch?
6. What uncertainties should be tested before making a go/no-go decision?
