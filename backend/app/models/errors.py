from __future__ import annotations

from typing import Any


class QuestionAnalysisError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        options: list[str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.options = options or []
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.code,
            "message": self.message,
        }
        if self.options:
            payload["options"] = self.options
        return payload
