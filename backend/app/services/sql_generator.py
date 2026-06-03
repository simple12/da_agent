from __future__ import annotations

import re

from openai import OpenAI

from app.config import settings
from app.models.question_intent import QuestionIntent
from app.services.metadata_service import MetadataService
from app.services.prompt_builder import PromptBuilder


def _strip_sql_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text.rstrip(";")


def _mock_sql_from_metadata(question: str, metadata: MetadataService) -> str | None:
    samples = metadata.list_sample_queries()
    ranked: list[tuple[int, re.Pattern[str], str]] = []
    for sample in samples:
        pattern = re.compile(sample.question_pattern, re.I)
        ranked.append((len(sample.question_pattern), pattern, sample.sql_template))

    ranked.sort(key=lambda item: item[0], reverse=True)
    for _, pattern, sql_template in ranked:
        if pattern.search(question):
            return sql_template.strip()
    return None


def generate_sql(
    question: str,
    intent: QuestionIntent,
    metadata: MetadataService | None = None,
    prompt_builder: PromptBuilder | None = None,
) -> str:
    metadata = metadata or MetadataService()
    prompt_builder = prompt_builder or PromptBuilder(metadata)

    if settings.llm_provider == "mock":
        mock = _mock_sql_from_metadata(question, metadata)
        if mock:
            return mock
        raise ValueError(
            "No mock SQL template for this question. Set LLM_PROVIDER=openai and OPENAI_API_KEY."
        )

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    system_prompt = prompt_builder.build(intent)
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    return _strip_sql_fences(content)
