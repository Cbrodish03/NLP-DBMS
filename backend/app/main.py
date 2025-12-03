from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_conn
from .executor import execute_plan, compute_aggregates
from .nlp_parser import parse_query_to_plan
from .ai_fallback_parser import ai_fallback_parse_query_to_plan  # NEW
from .schemas import (
    QueryFilters,
    QueryMeta,
    QueryRequest,
    QueryResponse,
)
from .query_plan import QueryPlan  # NEW (for type hints)

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


# NEW: simple heuristic to decide when to call the AI fallback
def is_low_signal(plan: QueryPlan) -> bool:
    """
    Decide when the rule-based parser is too weak / ambiguous and we should
    try the AI fallback.

    You can tune these thresholds as you test.
    """
    f = plan.filters

    has_any_filters = any(
        [
            bool(getattr(f, "subjects", [])),
            bool(getattr(f, "course_numbers", [])),
            bool(getattr(f, "instructors", [])),
            bool(getattr(f, "terms", [])),
            bool(getattr(f, "course_title_contains", [])),
            getattr(f, "course_number_min", None) is not None,
            getattr(f, "course_number_max", None) is not None,
            getattr(f, "gpa_min", None) is not None,
            getattr(f, "gpa_max", None) is not None,
            getattr(f, "credits_min", None) is not None,
            getattr(f, "credits_max", None) is not None,
            getattr(f, "enrollment_min", None) is not None,
            getattr(f, "enrollment_max", None) is not None,
        ]
    )

    # Low overall confidence? call AI.
    if plan.confidence < 0.6:
        return True

    # Very vague browse query with no real filters → AI might help.
    if plan.intent == "browse_subjects" and not has_any_filters:
        return True

    return False


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    # 1) Primary rule-based parse
    primary_plan: QueryPlan = parse_query_to_plan(req.query)
    plan_to_use: QueryPlan = primary_plan
    ai_used = False

    # 2) Decide whether to invoke ChatGPT as parser-of-last-resort
    if is_low_signal(primary_plan):
        ai_plan = ai_fallback_parse_query_to_plan(req.query)
        if ai_plan is not None:
            # Keep original parser debug around for later analysis
            ai_plan.debug.setdefault("primary_parser_debug", primary_plan.debug)
            plan_to_use = ai_plan
            ai_used = True
        else:
            # If AI fails, just fall back to the original plan
            plan_to_use = primary_plan

    # 3) Execute whichever plan we decided to use
    try:
        sections, subjects, aggregates, normalized_filters = execute_plan(plan_to_use)

        debug = plan_to_use.debug or {}
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
        # Error path: still surface which plan we tried + whether AI was used
        debug = plan_to_use.debug or {}
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
