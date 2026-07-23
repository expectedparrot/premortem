from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator


class Node(BaseModel):
    """A causal-graph node.

    Each node may cite zero or more failure reasons that justify it. Nodes
    that converge on multiple personas' reasons (very common for root causes)
    should list all of them in `reason_ids` — that convergence is meaningful
    signal in the analysis and is rendered visibly in reports.

    Backward compatibility: legacy stores have `reason_id: str | None`. We
    accept either field on read and always serialize as `reason_ids: list[str]`.
    """

    id: str
    label: str
    reason_ids: list[str] = []
    created_at: datetime
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_reason_id(cls, data):
        if isinstance(data, dict):
            if "reason_ids" not in data and "reason_id" in data:
                legacy = data.pop("reason_id")
                data["reason_ids"] = [legacy] if legacy else []
            elif "reason_id" in data:
                # both present — drop legacy
                data.pop("reason_id")
        return data

    @property
    def reason_id(self) -> str | None:
        """Compatibility shim for code that still reads the singular form.
        Returns the first reason if any, else None."""
        return self.reason_ids[0] if self.reason_ids else None


class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None
    created_at: datetime
