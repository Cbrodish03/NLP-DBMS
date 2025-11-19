<<<<<<< HEAD
# main.py
=======
>>>>>>> query
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
<<<<<<< HEAD
=======
from .executor import execute_plan, compute_aggregates
from .nlp_parser import parse_query_to_plan
>>>>>>> query
from .schemas import (
    QueryRequest,
    QueryResponse,
    QueryMeta,
    QueryFilters,
<<<<<<< HEAD
    Aggregates,
)
from .nlp_parser import parse_query_to_plan
from .executor import execute_plan
=======
)
>>>>>>> query


app = FastAPI(title="VT UDC NLP API")

<<<<<<< HEAD
# CORS: allow your frontend dev hosts
=======
>>>>>>> query
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
<<<<<<< HEAD
    """
    Unified query endpoint.

    Flow:
      1. Parse query string -> QueryPlan (nlp_parser)
      2. Execute plan against DB (executor)
      3. Wrap results into API contract (schemas)
    """
    plan = parse_query_to_plan(req.query)

    # Build meta (independent of DB success)
=======
    plan = parse_query_to_plan(req.query)
>>>>>>> query
    filters = QueryFilters(**plan.filters.dict())
    meta = QueryMeta(
        query=req.query,
        intent=plan.intent,
<<<<<<< HEAD
=======
        confidence=plan.confidence,
>>>>>>> query
        filters=filters,
        debug=plan.debug,
    )

    try:
        sections, subjects, aggregates = execute_plan(plan)
<<<<<<< HEAD

=======
>>>>>>> query
        return QueryResponse(
            ok=True,
            meta=meta,
            sections=sections,
            aggregates=aggregates,
            subjects=subjects,
        )
<<<<<<< HEAD

    except Exception as e:
        # On error, still respect the contract
        empty_aggregates = Aggregates(
            section_count=0,
            avg_gpa=None,
            total_graded_enrollment=0,
        )
=======
    except Exception as exc:
>>>>>>> query
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
<<<<<<< HEAD
            aggregates=empty_aggregates,
=======
            aggregates=compute_aggregates([]),
>>>>>>> query
            subjects=None,
            error=str(exc),
        )
