from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Mitigation(BaseModel):
    id: str
    text: str
    node_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    notes: str | None = None
