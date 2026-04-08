from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Literal

from .models import Mitigation, Persona, Reason, Score
from .store import PremortemError, ProjectStore, now_utc

RATING_NUMERIC = {"low": 1, "medium": 2, "high": 3}
NUMERIC_RATING = {1: "low", 2: "medium", 3: "high"}


def load_results_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise PremortemError("ID_NOT_FOUND", "Results file not found.", context=str(path)) from exc
    except json.JSONDecodeError as exc:
        raise PremortemError("VALIDATION_FAILED", "Invalid JSON in results file.", context=str(exc)) from exc
    if "rows" not in data:
        raise PremortemError("VALIDATION_FAILED", "Results file missing 'rows' key.", context=str(path))
    if "entity_type" not in data:
        raise PremortemError("VALIDATION_FAILED", "Results file missing 'entity_type' key.", context=str(path))
    return data


def ingest_personas(store: ProjectStore, rows: list[dict]) -> list[Persona]:
    created: list[Persona] = []
    with store.locked():
        for row in rows:
            name = row.get("persona_name", row.get("persona", "")).strip()
            role = row.get("role", "Stakeholder").strip()
            perspective = row.get("perspective", "").strip() or None
            if not name:
                continue
            persona_id = store.next_id("p", [p.id for p in store.list_personas()])
            persona = Persona(
                id=persona_id,
                name=name,
                role=role,
                perspective=perspective,
                created_at=now_utc(),
            )
            store.save_persona(persona)
            created.append(persona)
    return created


def ingest_reasons(store: ProjectStore, rows: list[dict]) -> tuple[list[Reason], list[str]]:
    personas = store.list_personas()
    name_to_id = {p.name.lower().strip(): p.id for p in personas}
    created: list[Reason] = []
    warnings: list[str] = []

    with store.locked():
        for row in rows:
            persona_name = row.get("persona", "").strip()
            persona_id = name_to_id.get(persona_name.lower())
            if not persona_id:
                warnings.append(f"No matching persona for '{persona_name}', skipping")
                continue

            for text in row.get("episodic_reasons", []):
                if not isinstance(text, str) or not text.strip():
                    continue
                reason_id = store.next_id("r", [r.id for r in store.list_reasons()])
                reason = Reason(
                    id=reason_id,
                    persona_id=persona_id,
                    kind="episodic",
                    text=text.strip(),
                    created_at=now_utc(),
                )
                store.save_reason(reason)
                created.append(reason)

            for text in row.get("structural_reasons", []):
                if not isinstance(text, str) or not text.strip():
                    continue
                reason_id = store.next_id("r", [r.id for r in store.list_reasons()])
                reason = Reason(
                    id=reason_id,
                    persona_id=persona_id,
                    kind="structural",
                    text=text.strip(),
                    created_at=now_utc(),
                )
                store.save_reason(reason)
                created.append(reason)

    return created, warnings


def _aggregate_rating(
    values: list[str],
    strategy: str,
) -> str:
    if not values:
        return "medium"
    if strategy == "first":
        return values[0]
    if strategy == "max":
        return max(values, key=lambda v: RATING_NUMERIC.get(v, 2))
    if strategy == "mode":
        counts = Counter(values)
        return counts.most_common(1)[0][0]
    # median (default)
    numeric = sorted(RATING_NUMERIC.get(v, 2) for v in values)
    mid = len(numeric) // 2
    if len(numeric) % 2 == 0:
        # tie-break pessimistically (take higher)
        median_val = max(numeric[mid - 1], numeric[mid])
    else:
        median_val = numeric[mid]
    return NUMERIC_RATING.get(median_val, "medium")


def ingest_scores(
    store: ProjectStore,
    rows: list[dict],
    strategy: str = "median",
) -> list[Score]:
    # Collect all ratings per node
    node_ids = {n.id for n in store.list_nodes()}
    likelihood_by_node: dict[str, list[str]] = {}
    impact_by_node: dict[str, list[str]] = {}

    for row in rows:
        for key, value in row.items():
            m = re.match(r"(likelihood|impact)_(n\d+)", key)
            if not m or not isinstance(value, str):
                continue
            kind, node_id = m.group(1), m.group(2)
            if node_id not in node_ids:
                continue
            if kind == "likelihood":
                likelihood_by_node.setdefault(node_id, []).append(value)
            else:
                impact_by_node.setdefault(node_id, []).append(value)

    created: list[Score] = []
    all_node_ids = set(likelihood_by_node.keys()) | set(impact_by_node.keys())
    for node_id in sorted(all_node_ids):
        likelihood = _aggregate_rating(likelihood_by_node.get(node_id, []), strategy)
        impact = _aggregate_rating(impact_by_node.get(node_id, []), strategy)
        score = Score(
            node_id=node_id,
            likelihood=likelihood,
            impact=impact,
            created_at=now_utc(),
            notes=f"Aggregated from {len(likelihood_by_node.get(node_id, []))} agents ({strategy})",
        )
        store.save_score(score)
        created.append(score)
    return created


def ingest_mitigations(store: ProjectStore, rows: list[dict]) -> list[Mitigation]:
    node_ids = {n.id for n in store.list_nodes()}

    # Collect all mitigation texts grouped by node
    by_node: dict[str, list[str]] = {}
    for row in rows:
        for key, value in row.items():
            m = re.match(r"mitigations_(n\d+)", key)
            if not m or not isinstance(value, list):
                continue
            node_id = m.group(1)
            if node_id not in node_ids:
                continue
            for text in value:
                if isinstance(text, str) and text.strip():
                    by_node.setdefault(node_id, []).append(text.strip())

    # Deduplicate within each node (normalized comparison)
    created: list[Mitigation] = []
    with store.locked():
        for node_id in sorted(by_node.keys()):
            seen: set[str] = set()
            for text in by_node[node_id]:
                normalized = " ".join(text.lower().split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                mit_id = store.next_id("m", [m.id for m in store.list_mitigations()])
                mitigation = Mitigation(
                    id=mit_id,
                    text=text,
                    node_ids=[node_id],
                    created_at=now_utc(),
                )
                store.save_mitigation(mitigation)
                created.append(mitigation)
    return created
