# Mitigations

Mitigations should target graph nodes and specify who does what by when.

Good mitigations:

- Reference specific node IDs such as `n001`.
- Act before launch rather than merely monitoring after launch.
- Break root causes or high-convergence intermediate effects.
- Name owners, deadlines, processes, thresholds, and decision rules.

Bad mitigations:

- `Improve communication`.
- `Monitor the risk`.
- Actions that do not map to any graph node.

Typical command:

`premortem job generate mitigations --good-example "..."`
