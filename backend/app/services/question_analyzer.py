from __future__ import annotations

import re
from typing import Optional

from app.models.errors import QuestionAnalysisError
from app.models.question_intent import QuestionIntent
from app.services.metadata_service import MetadataService

COUNTIES = frozenset(
    {"Alameda", "Santa Clara", "San Mateo", "Contra Costa", "San Francisco"}
)

# Bare tokens that map to multiple dimensions — do not guess (PRD).
_AMBIGUOUS_BY_TOKENS: dict[str, list[str]] = {
    "group": ["provider_group", "age_group", "county", "lob"],
}

_METRIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpmpm\b", re.I), "PMPM"),
    (re.compile(r"\boutstanding\b", re.I), "OUTSTANDING_CLAIMS"),
    (
        re.compile(r"\bpending(?:\s+payment|\s+claims?|\s+claim)?\b|\bclaims?\s+pending\b", re.I),
        "PENDING_CLAIMS",
    ),
    (
        re.compile(
            r"\bclaims?\s+by\s+status\b|\bclaim\s+status\b|\bclaim\s+count\s+by\s+status\b",
            re.I,
        ),
        "CLAIMS_BY_STATUS",
    ),
    (
        re.compile(
            r"\bclaims?\s+by\s+provider\b|\bclaims?\s+per\s+provider\b|\bclaim\s+(count|volume)\b.*\bprovider\b|\bprovider.*\bclaim\s+(count|volume)\b|\btotal\s+claims?\s+by\s+provider\b",
            re.I,
        ),
        "CLAIMS_BY_STATUS",
    ),
    (
        re.compile(r"\bmembers?\s+by\b|\bmember\s+count\b|\bcount\s+of\s+members?\b", re.I),
        "MEMBER_COUNT",
    ),
]

_BY_CLAUSE = re.compile(r"\bby\s+(.+?)(?:\?|$|\.)", re.I)
_BY_AND = re.compile(r"\s+and\s+", re.I)


class QuestionAnalyzer:
    def __init__(self, metadata: MetadataService | None = None) -> None:
        self._metadata = metadata or MetadataService()
        self._dimension_phrases: list[tuple[str, str]] = []
        self._metric_names: set[str] = set()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._metric_names = {m.metric_name for m in self._metadata.list_metrics()}
        phrases: list[tuple[str, str]] = []
        for dim in self._metadata.list_dimensions():
            candidates = [dim.dimension_name.replace("_", " "), dim.dimension_name]
            candidates.extend(dim.aliases)
            for phrase in candidates:
                normalized = phrase.strip().lower()
                if normalized:
                    phrases.append((normalized, dim.dimension_name))
        phrases.sort(key=lambda item: len(item[0]), reverse=True)
        self._dimension_phrases = phrases
        self._loaded = True

    def analyze(self, question: str) -> QuestionIntent:
        self._ensure_loaded()
        text = question.strip()
        lowered = text.lower()

        metric = self._extract_metric(lowered)
        if metric is None:
            raise QuestionAnalysisError(
                "UNKNOWN_METRIC",
                "Metric not found.",
            )
        if metric not in self._metric_names:
            raise QuestionAnalysisError(
                "UNKNOWN_METRIC",
                f"Metric not found: {metric}",
            )

        dimensions = self._extract_dimensions(text)
        filters = self._extract_filters(text, dimensions)

        return QuestionIntent(
            metric=metric,
            dimensions=dimensions,
            filters=filters,
            raw_question=text,
        )

    def _extract_metric(self, lowered: str) -> Optional[str]:
        for pattern, metric_name in _METRIC_RULES:
            if pattern.search(lowered):
                return metric_name
        return None

    def _extract_dimensions(self, question: str) -> list[str]:
        lowered = question.lower()
        found: list[str] = []

        for match in _BY_CLAUSE.finditer(lowered):
            clause = match.group(1).strip()
            for part in _BY_AND.split(clause):
                part = part.strip()
                if not part:
                    continue
                resolved = self._resolve_dimension_phrase(part)
                if resolved and resolved not in found:
                    found.append(resolved)

        return found

    def _resolve_dimension_phrase(self, phrase: str) -> Optional[str]:
        phrase = phrase.strip().lower()
        if not phrase:
            return None

        if phrase in _AMBIGUOUS_BY_TOKENS:
            raise QuestionAnalysisError(
                "AMBIGUOUS_DIMENSION",
                "Specify which dimension.",
                options=_AMBIGUOUS_BY_TOKENS[phrase],
            )

        matches = [
            dimension_name
            for pattern, dimension_name in self._dimension_phrases
            if phrase == pattern
        ]
        unique = sorted(set(matches))
        if not unique:
            raise QuestionAnalysisError(
                "UNKNOWN_DIMENSION",
                f"Dimension not recognized: {phrase}",
            )
        if len(unique) > 1:
            raise QuestionAnalysisError(
                "AMBIGUOUS_DIMENSION",
                "Specify which dimension.",
                options=unique,
            )
        return unique[0]

    def _extract_filters(self, question: str, dimensions: list[str]) -> dict[str, str]:
        filters: dict[str, str] = {}

        for county in COUNTIES:
            if re.search(rf"\b{re.escape(county)}\b", question, re.I):
                filters["county"] = county

        pending_match = re.search(r"\bpending\b", question, re.I)
        if pending_match and "claim_status" not in filters:
            if re.search(r"\bpending\s+claims?\b|\bclaims?\s+pending\b", question, re.I):
                filters["claim_status"] = "PENDING"

        return filters
