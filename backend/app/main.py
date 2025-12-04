from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
from .executor import execute_plan, compute_aggregates
from .nlp_parser import parse_query_to_plan
from .ai_fallback_parser import ai_fallback_parse_query_to_plan
from .schemas import (
    QueryFilters,
    QueryMeta,
    QueryRequest,
    QueryResponse,
)
from .query_plan import QueryPlan

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
@app.get("/api/healthz")
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
@app.post("/api/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Explicit parser selection:
      - parser_mode="regex": always use rule-based parser.
      - parser_mode="ai": try AI parser first, fall back to regex on failure.

    The frontend can also hit this with parser_mode="ai" when the user clicks
    "Retry with AI" or selects AI parsing in the UI.
    """
    ai_used = False

    # Decide which parser to run
    if req.parser_mode == "ai":
        ai_plan = ai_fallback_parse_query_to_plan(req.query)
        if ai_plan is not None:
            plan_to_use: QueryPlan = ai_plan
            ai_used = True
        else:
            # AI failed or API key not configured → fall back to regex
            plan_to_use = parse_query_to_plan(req.query)
    else:
        # Default: pure regex / rule-based parser
        plan_to_use = parse_query_to_plan(req.query)

    try:
        sections, subjects, aggregates, normalized_filters = execute_plan(plan_to_use)

        debug = plan_to_use.debug or {}
        debug["parser_mode"] = req.parser_mode
        debug["ai_fallback_used"] = ai_used

        meta = QueryMeta(
            query=req.query,
            intent=plan_to_use.intent,
            confidence=plan_to_use.confidence,
            filters=normalized_filters,
            debug=debug,
        )
        return QueryResponse(
            ok=True,
            meta=meta,
            sections=sections,
            aggregates=aggregates,
            subjects=subjects,
        )
    except Exception as exc:
        debug = plan_to_use.debug or {}
        debug["parser_mode"] = req.parser_mode
        debug["ai_fallback_used"] = ai_used

        meta = QueryMeta(
            query=req.query,
            intent=plan_to_use.intent,
            confidence=plan_to_use.confidence,
            filters=QueryFilters(**plan_to_use.filters.dict()),
            debug=debug,
        )
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
            aggregates=compute_aggregates([]),
            subjects=None,
            error=str(exc),
        )
