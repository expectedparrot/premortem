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


def _load_ep_results(path: Path, entity_type: str) -> dict:
    try:
        from edsl import Results
        results = Results.git.load(path)
    except ImportError as exc:
        raise PremortemError("DEPENDENCY_ERROR", "EDSL is required to load .ep Results.") from exc
    except Exception as exc:
        raise PremortemError("VALIDATION_FAILED", "Unable to load EDSL Results.", context=f"{path}: {exc}") from exc

    question_names = set(results.survey.question_names)
    rows: list[dict] = []
    if entity_type == "personas":
        if "personas" not in question_names:
            raise PremortemError("VALIDATION_FAILED", "Results do not contain the personas question.")
        raw = results.select("answer.personas").to_dicts(remove_prefix=True)
        for item in raw[0].get("personas", []) if raw else []:
            parts = [part.strip() for part in str(item).split("|")]
            if len(parts) >= 2:
                rows.append({
                    "persona_name": parts[0],
                    "role": parts[1],
                    "perspective": " | ".join(parts[2:]) if len(parts) > 2 else "",
                })
    elif entity_type == "reasons":
        required = {"episodic_reasons", "structural_reasons"}
        if not required.issubset(question_names):
            raise PremortemError("VALIDATION_FAILED", "Results do not contain the reason questions.")
        raw = results.select(
            "agent.agent_name", "answer.episodic_reasons", "answer.structural_reasons"
        ).to_dicts(remove_prefix=True)
        rows = [{
            "persona": item.get("agent_name", ""),
            "episodic_reasons": [item.get("episodic_reasons", "")],
            "structural_reasons": [item.get("structural_reasons", "")],
        } for item in raw]
    elif entity_type == "mitigations":
        if "mitigations" not in question_names:
            raise PremortemError("VALIDATION_FAILED", "Results do not contain the mitigations question.")
        raw = results.select("agent.agent_name", "answer.mitigations").to_dicts(remove_prefix=True)
        rows = [{
            "persona_name": item.get("agent_name", ""),
            "text": item.get("mitigations", ""),
        } for item in raw]
    elif entity_type == "research_agenda":
        if "research_agenda" not in question_names:
            raise PremortemError("VALIDATION_FAILED", "Results do not contain the research agenda question.")
        raw = results.select("agent.agent_name", "answer.research_agenda").to_dicts(remove_prefix=True)
        rows = [{
            "persona_name": item.get("agent_name", ""),
            "text": item.get("research_agenda", ""),
        } for item in raw]
    elif entity_type == "executive_summary":
        if "executive_summary" not in question_names:
            raise PremortemError("VALIDATION_FAILED", "Results do not contain the executive summary question.")
        raw = results.select("answer.executive_summary").to_dicts(remove_prefix=True)
        return {
            "entity_type": entity_type,
            "text": raw[0].get("executive_summary", "") if raw else "",
            "rows": [],
        }
    else:
        raise PremortemError("VALIDATION_FAILED", "Unsupported EDSL Results entity type.", context=entity_type)
    return {"entity_type": entity_type, "rows": rows}


def load_results_file(path: Path, entity_type: str | None = None) -> dict:
    if path.suffix == ".ep":
        if entity_type is None:
            raise PremortemError("VALIDATION_FAILED", "An entity type is required for .ep Results.", context=str(path))
        return _load_ep_results(path, entity_type)
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


def _node_ids_from_value(value: object, valid_node_ids: set[str]) -> list[str]:
    if isinstance(value, str):
        candidates = re.findall(r"\bn\d+\b", value)
    elif isinstance(value, list):
        candidates = [item for item in value if isinstance(item, str)]
    else:
        return []
    return sorted({node_id for node_id in candidates if node_id in valid_node_ids})


def _split_mitigation_text(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    parts = re.split(r"(?:^|\n)\s*(?:[-*]\s+|\d+[.)]\s+)", stripped)
    items = [part.strip() for part in parts if part.strip()]
    return items if len(items) > 1 else [stripped]


def ingest_mitigations(store: ProjectStore, rows: list[dict]) -> list[Mitigation]:
    node_ids = {n.id for n in store.list_nodes()}

    # Normalize both the original per-node survey shape
    # (`mitigations_n001: [...]`) and the AI analysis shape
    # (`text: "..."`) into mitigation records.
    records: list[tuple[str, list[str], str | None]] = []
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
                    records.append((text.strip(), [node_id], None))

        text_value = row.get("text")
        if not isinstance(text_value, str):
            text_value = row.get("mitigations")
        if not isinstance(text_value, str):
            text_value = row.get("mitigation")
        if not isinstance(text_value, str) or not text_value.strip():
            continue

        explicit_node_ids = _node_ids_from_value(row.get("node_ids"), node_ids)
        if not explicit_node_ids:
            explicit_node_ids = _node_ids_from_value(row.get("nodes"), node_ids)

        persona = row.get("persona_name") or row.get("persona_id")
        notes = f"Generated from {persona}" if isinstance(persona, str) and persona.strip() else None
        for text in _split_mitigation_text(text_value):
            target_node_ids = explicit_node_ids or _node_ids_from_value(text, node_ids)
            records.append((text, target_node_ids, notes))

    # Deduplicate normalized text and target set while preserving unassigned items.
    created: list[Mitigation] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    with store.locked():
        for text, target_node_ids, notes in records:
            normalized = " ".join(text.lower().split())
            dedupe_key = (normalized, tuple(sorted(target_node_ids)))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            mit_id = store.next_id("m", [m.id for m in store.list_mitigations()])
            mitigation = Mitigation(
                id=mit_id,
                text=text,
                node_ids=target_node_ids,
                created_at=now_utc(),
                notes=notes,
            )
            store.save_mitigation(mitigation)
            created.append(mitigation)
    return created
