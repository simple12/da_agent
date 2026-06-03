from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.services.query_executor import execute_query
from app.services.sql_generator import generate_sql
from app.services.sql_validator import SQLValidationError, validate_sql

app = FastAPI(title="Healthcare Data Analyst Agent", version="0.1.0")

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
    return {
        "status": "ok",
        "query_engine": settings.query_engine,
        "trino_catalog": settings.trino_catalog if settings.query_engine == "trino" else None,
    }


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    question = body.question.strip()
    try:
        sql = generate_sql(question)
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
