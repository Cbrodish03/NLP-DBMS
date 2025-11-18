# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
from .schemas import (
    QueryRequest,
    QueryResponse,
    QueryMeta,
    QueryFilters,
    Aggregates,
)
from .nlp_parser import parse_query_to_plan
from .executor import execute_plan


app = FastAPI(title="VT UDC NLP API")

# CORS: allow your frontend dev hosts
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
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
    """
    Unified query endpoint.

    Flow:
      1. Parse query string -> QueryPlan (nlp_parser)
      2. Execute plan against DB (executor)
      3. Wrap results into API contract (schemas)
    """
    plan = parse_query_to_plan(req.query)

    # Build meta (independent of DB success)
    filters = QueryFilters(**plan.filters.dict())
    meta = QueryMeta(
        query=req.query,
        intent=plan.intent,
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

    except Exception as e:
        # On error, still respect the contract
        empty_aggregates = Aggregates(
            section_count=0,
            avg_gpa=None,
            total_graded_enrollment=0,
        )
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
            aggregates=empty_aggregates,
            subjects=None,
            error=str(e),
        )
