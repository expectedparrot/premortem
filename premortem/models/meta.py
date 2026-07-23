from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Phase = Literal[
    "personas",
    "reasons",
    "graphing",
    "scoring",
    "mitigation",
    "complete",
]


class ProjectMeta(BaseModel):
    id: str
    initiative: str
    description: str | None = None
    failure_statement: str
    created_at: datetime
    updated_at: datetime
    phase: Phase = "personas"
    notes: str | None = None
