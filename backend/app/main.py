from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
from .executor import execute_plan, compute_aggregates
from .nlp_parser import parse_query_to_plan
from .schemas import (
    QueryRequest,
    QueryResponse,
    QueryMeta,
    QueryFilters,
)


app = FastAPI(title="VT UDC NLP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    filters = QueryFilters(**plan.filters.dict())
    meta = QueryMeta(
        query=req.query,
        intent=plan.intent,
        confidence=plan.confidence,
        filters=filters,
        debug=plan.debug,
    )

    try:
        sections, subjects, aggregates = execute_plan(plan)
        return QueryResponse(
            ok=True,
            meta=meta,
            sections=sections,
            aggregates=aggregates,
            subjects=subjects,
        )
    except Exception as exc:
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
            aggregates=compute_aggregates([]),
            subjects=None,
            error=str(exc),
        )
