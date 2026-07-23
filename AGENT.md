# Premortem Agent Guide

Use this guide when you are facilitating a pre-mortem for a user. Start here.
Use `README.md` for command syntax, storage layout, and package mechanics.

## Instructions To The Agent

- Facilitate the analysis; do not expect the user to know the premortem method.
- Use the premortem CLI as the source of truth for workflow state and stored
  artifacts.
- Do not edit `.premortem/*.json` directly.
- Draft the failure statement yourself from the user's intake, then get
  approval before initializing the project.
- Pause for review after the failure statement, after personas, after the
  causal graph, and before any destructive or overwrite action.
- Keep outputs concrete and domain-specific. If results are generic, regenerate
  with stronger context and examples.
- Build the causal graph as analyst work. Do not blindly delegate it.
- Tie mitigations to graph nodes, and treat unresolved assumptions as research
  questions.
- Use explicit approval checkpoints. Do not push past a review point just
  because a command is available.

## What A Premortem Produces

A premortem is a structured prospective-hindsight exercise. It assumes the
initiative has already failed and works backward to identify plausible failure
paths, mitigations, and research questions.

The output is a decision aid:

- plausible failure mechanisms
- a simple causal graph
- concrete mitigations
- research questions that should be answered before launch

## Core Rules

- State failure as a completed fact.
- Describe consequences in the failure statement, not causes.
- Avoid hedging words such as `might`, `could`, `possible`, or `risk`.
- Avoid causal phrases in the failure statement such as `because`, `due to`, or
  `caused by`.
- Use specific domain details, not generic management language.
- Use diverse stakeholder personas to generate different failure stories.
- Keep the causal graph simple enough to read quickly.
- Tie mitigations to graph nodes.
- Treat unresolved assumptions as research questions.

## Approval Checkpoints

Stop and get explicit user confirmation at these points:

- after drafting the failure statement and before initialization
- after generating personas and before reasons
- after synthesizing the causal graph and before mitigations
- before any overwrite, regeneration that replaces accepted work, or other
  destructive action

At each checkpoint, surface the artifact itself, not just a summary of it.

## Facilitation Flow

### 1. Intake

Minimum intake:

1. What initiative, launch, policy, program, or decision should be analyzed?
2. What context matters: stakeholders, timeline, scale, constraints, systems,
   budget, dependencies, or success criteria?

If the user gives only a high-level initiative, ask at most two concise
clarifying questions. Then draft:

- a concise initiative name
- a description using the user's context
- a completed-fact failure statement that describes bad outcomes and leaves
  causes out

Show that draft to the user for approval or edits before initialization.

Good failure statements include vivid consequences such as lost users, partner
exits, budget overruns, reputational damage, missed deadlines, or shutdown
decisions.

### 2. Initialize The Project

Draft a vivid failure statement before initialization. It should say what went
wrong in outcome terms and avoid explaining why.

After initialization, check workflow state and confirm the next phase before
moving on.

### 3. Generate Personas

Generate 4 to 6 stakeholder personas that are specific, realistic, and
distinct. Review them before generating reasons.

Pause here for user review.

### 4. Generate Failure Reasons

Prompt for concrete domain details and include one strong example of the
specificity you expect. The result should include both episodic event chains
and structural factors.

If the output reads like generic risk bullets, regenerate with a stronger
example.

### 5. Build The Causal Graph

Read the reasons and synthesize a simple graph of about 8 nodes and 10 edges.

Target:

- 3 to 4 root causes
- 2 to 3 intermediate effects
- 1 to 2 terminal outcomes

Graph labels should be specific and domain-grounded. Avoid labels such as
`poor communication` or `lack of alignment` unless they are made concrete.

Good graph construction heuristics:

- root causes should have no incoming edges
- terminal outcomes should have no outgoing edges
- multiple reasons can map to the same node when they describe the same
  mechanism
- edges should name a causal mechanism, not just imply sequence
- prefer one readable graph over an exhaustive graph

The graph should be readable in under 30 seconds and should show where
multiple causes converge.

Pause here for user review.

### 6. Generate Mitigations

Mitigations should name graph nodes and specify who does what by when. Review
anything with no node target and either map it to the graph or treat it as
weak.

### 7. Generate The Research Agenda

The research agenda should identify assumptions that are important, uncertain,
and testable before launch.

### 8. Generate Summary And Reports

Finish with a concise executive summary and final report artifacts.

### 9. Wrap Up

Run `premortem agent-end` for the wrap-up guide before handing the analysis
back to the user. The hand-off is its own phase: lead with the recommendation,
name the highest-leverage research questions as homework, and point at the
canonical report file. Do not just say "done".

## What Good Looks Like

The final analysis should answer:

1. What does definitive failure look like?
2. Which stakeholders see the failure differently?
3. What event chains and structural factors plausibly lead to failure?
4. Which root causes converge into the most dangerous pathways?
5. What concrete actions could break those pathways before launch?
6. What uncertainties should be tested before making a go/no-go decision?

## Command Reference

Use `README.md` for the command sequence, examples, and storage layout.
