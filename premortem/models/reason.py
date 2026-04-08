from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReasonKind = Literal["episodic", "structural"]


class Reason(BaseModel):
    id: str
    persona_id: str
    kind: ReasonKind
    text: str
    created_at: datetime
    notes: str | None = None
