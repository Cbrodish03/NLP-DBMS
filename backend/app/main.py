from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
from .executor import execute_plan, compute_aggregates
from .nlp_parser import parse_query_to_plan
from .schemas import (
    QueryFilters,
    QueryMeta,
    QueryRequest,
    QueryResponse,
)


app = FastAPI(title="VT UDC NLP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def health():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    return {"status": "ok", "db_ok": db_ok}


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    plan = parse_query_to_plan(req.query)
    try:
        sections, subjects, aggregates, normalized_filters = execute_plan(plan)
        meta = QueryMeta(
            query=req.query,
            intent=plan.intent,
            confidence=plan.confidence,
            filters=normalized_filters,
            debug=plan.debug,
        )
        return QueryResponse(
            ok=True,
            meta=meta,
            sections=sections,
            aggregates=aggregates,
            subjects=subjects,
        )
    except Exception as exc:
        meta = QueryMeta(
            query=req.query,
            intent=plan.intent,
            confidence=plan.confidence,
            filters=QueryFilters(**plan.filters.dict()),
            debug=plan.debug,
        )
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
            aggregates=compute_aggregates([]),
            subjects=None,
            error=str(exc),
        )
