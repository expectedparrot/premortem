from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Node(BaseModel):
    id: str
    label: str
    reason_id: str | None = None
    created_at: datetime
    notes: str | None = None


class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None
    created_at: datetime
