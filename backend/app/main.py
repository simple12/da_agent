from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.models.errors import QuestionAnalysisError
from app.routes.metadata import router as metadata_router
from app.services.metadata_service import MetadataService
from app.services.question_analyzer import QuestionAnalyzer
from app.services.prompt_builder import PromptBuilder
from app.services.query_executor import execute_query
from app.services.sql_generator import generate_sql
from app.services.sql_validator import SQLValidationError, validate_sql

app = FastAPI(title="Healthcare Data Analyst Agent", version="0.1.0")
app.include_router(metadata_router)
metadata_service = MetadataService()
question_analyzer = QuestionAnalyzer(metadata_service)
prompt_builder = PromptBuilder(metadata_service)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    sql: str
    results: list[dict]


@app.get("/health")
def health():
    semantic_ready = False
    metric_count = 0
    try:
        metric_count = metadata_service.metric_count()
        semantic_ready = metric_count > 0
    except Exception:
        semantic_ready = False

    return {
        "status": "ok",
        "query_engine": settings.query_engine,
        "trino_catalog": settings.trino_catalog if settings.query_engine == "trino" else None,
        "semantic_metadata_ready": semantic_ready,
        "semantic_metric_count": metric_count,
    }


@app.get("/analyze")
def analyze_question(question: str):
    try:
        return question_analyzer.analyze(question.strip())
    except QuestionAnalysisError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e


@app.get("/prompt")
def preview_prompt(question: str):
    try:
        intent = question_analyzer.analyze(question.strip())
    except QuestionAnalysisError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    return {"intent": intent, "prompt": prompt_builder.build(intent)}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    question = body.question.strip()
    try:
        intent = question_analyzer.analyze(question)
    except QuestionAnalysisError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e

    try:
        sql = generate_sql(question, intent, metadata_service, prompt_builder)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SQL generation failed: {e}") from e

    try:
        validated_sql = validate_sql(sql)
    except SQLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        results = execute_query(validated_sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e}") from e

    return AskResponse(question=question, sql=validated_sql, results=results)
