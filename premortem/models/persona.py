from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Persona(BaseModel):
    id: str
    name: str
    role: str
    perspective: str | None = None
    created_at: datetime
    notes: str | None = None
