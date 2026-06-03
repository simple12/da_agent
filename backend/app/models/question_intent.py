from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionIntent(BaseModel):
    metric: str
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    raw_question: str
