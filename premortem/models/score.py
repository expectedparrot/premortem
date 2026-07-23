from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Rating = Literal["low", "medium", "high"]


class Score(BaseModel):
    node_id: str
    likelihood: Rating
    impact: Rating
    created_at: datetime
    notes: str | None = None
