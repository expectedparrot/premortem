# Causal Graph

The causal graph is built by the orchestrating agent or analyst, not delegated to
EDSL.

Target about 8 nodes and 10 edges:

- 3-4 root causes with no incoming edges.
- 2-3 intermediate effects.
- 1-2 terminal outcomes.

Good graph labels are specific and domain-grounded. Avoid labels such as `poor
communication` or `lack of alignment`.

A useful graph is readable in under 30 seconds, shows convergence, and makes
intervention points obvious.

Typical commands:

`premortem graph add-node --label "..."`

`premortem graph add-edge --from n001 --to n004 --label "..."`
