import json
import os
import difflib
from typing import Optional, Any, Dict, List

import logging
from openai import OpenAI  # pip install openai>=1.0.0

from .query_plan import QueryPlan, PlanFilters
from .db import get_db_conn

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
log = logging.getLogger(__name__)


def _empty_filters() -> Dict[str, Any]:
    """
    Default empty filters matching QueryFilters / PlanFilters structure.
    """
    return {
        "subjects": [],
        "course_numbers": [],
        "instructors": [],
        "terms": [],
        "course_title_contains": [],
        "exclude_instructors": [],
        "exclude_terms": [],
        "course_levels": [],
        "grade_min": {},
        "grade_min_percent": {},
        "grade_max": {},
        "b_or_above_percent_min": None,
        "grade_compare": [],
        "course_number_min": None,
        "course_number_max": None,
        "gpa_min": None,
        "gpa_max": None,
        "credits_min": None,
        "credits_max": None,
        "enrollment_min": None,
        "enrollment_max": None,
    }


def _normalize_instructors(raw_names: List[str]) -> List[str]:
    """
    Take instructor strings from the AI (possibly misspelled or with
    extra words like 'Professor') and map them to the best matching
    instructor.name_display value from the database.

    This avoids needing Postgres extensions like pg_trgm/similarity().
    We:
      - load all instructor names from the DB once,
      - clean the AI string (strip titles),
      - use difflib.get_close_matches for fuzzy matching,
      - fall back to substring search or the cleaned name if needed.
    """
    if not raw_names:
        return []

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("SELECT name_display FROM instructor;")
        rows = cur.fetchall()
    except Exception as e:
        print("AI fallback: error loading instructors from DB:", repr(e))
        cur.close()
        conn.close()
        # If we can't even read instructor names, just return cleaned raw names.
        normalized_fallback: List[str] = []
        for raw in raw_names:
            cleaned = (
                raw.replace("Professor", "")
                .replace("Prof.", "")
                .replace("Prof", "")
                .replace("Dr.", "")
                .replace("Dr", "")
                .strip()
            )
            normalized_fallback.append(cleaned)
        return normalized_fallback

    names = [row[0] for row in rows if row and row[0]]
    lower_to_original: Dict[str, str] = {}
    for n in names:
        ln = n.lower()
        # if multiple rows have same lowercase name, keep the first
        if ln not in lower_to_original:
            lower_to_original[ln] = n

    normalized: List[str] = []

    for raw in raw_names:
        cleaned = (
            raw.replace("Professor", "")
            .replace("Prof.", "")
            .replace("Prof", "")
            .replace("Dr.", "")
            .replace("Dr", "")
            .strip()
        )

        # Use the last reasonably long token as the main search key
        tokens = [t for t in cleaned.split() if len(t) >= 3]
        search_token = tokens[-1] if tokens else cleaned

        best_match: Optional[str] = None

        # 1) Fuzzy match on full names using difflib
        candidate_lowers = list(lower_to_original.keys())
        close = difflib.get_close_matches(
            search_token.lower(), candidate_lowers, n=1, cutoff=0.6
        )
        if close:
            best_match = lower_to_original[close[0]]

        # 2) If no fuzzy match, try simple substring search
        if best_match is None:
            st_lower = search_token.lower()
            candidate = next(
                (n for n in names if st_lower in n.lower()),
                None,
            )
            best_match = candidate

        normalized.append(best_match or cleaned)

    cur.close()
    conn.close()
    return normalized


def ai_fallback_parse_query_to_plan(text: str) -> Optional[QueryPlan]:
    """
    Call ChatGPT as a parser of last resort.

    Returns a QueryPlan if parsing works, otherwise None (so you can
    gracefully fall back to normal behavior).
    """
    if not os.getenv("OPENAI_API_KEY"):
        log.warning("AI fallback disabled: OPENAI_API_KEY not set")
        return None

    system_prompt = """
You are a strict JSON API that converts natural language about college
courses and grade distributions into structured filters.

Only output JSON using this schema:

{
  "intent": "course_lookup" | "section_filter" | "browse_subjects",
  "sort_by": "gpa" | "enrollment" | "term" | null,
  "sort_order": "ASC" | "DESC" | null,
  "limit": int or null,
  "filters": {
    "subjects": [ "MATH", "CS", ... ],
    "course_numbers": [ "4626", "2104", ... ],

    "course_number_min": int or null,
    "course_number_max": int or null,

    "course_levels": [ "UG", "GR" ],

    "instructors": [ "Smith", "Johnson" ],
    "exclude_instructors": [ "Doe" ],

    "terms": [ "Spring 2023", "Fall 2022" ],
    "exclude_terms": [ "Fall 2020" ],

    "course_title_contains": [ "algebra", "probability" ],

    "gpa_min": float or null,
    "gpa_max": float or null,

    "credits_min": int or null,
    "credits_max": int or null,

    "enrollment_min": int or null,
    "enrollment_max": int or null,

    "grade_min": { "A": int, "B+": int, ... },
    "grade_max": { "F": int, ... },
    "grade_min_percent": { "A": float, "B": float, ... },

    "b_or_above_percent_min": float or null,

    "grade_compare": [
      { "left": "A", "right": "B", "op": ">" },
      { "left": "C", "right": "F", "op": "<" }
    ]
  }
}

Rules:
- Be conservative; if you are unsure, leave fields empty or null.
- "subjects" must be upper-case subject codes like "MATH", "CS".
- For instructors, remove titles like "Professor", "Prof.", "Dr.", "Mr.", "Ms." etc.
- For instructors, prefer just the last name if that is all the user provides.
- If the query talks about "easy", "easiest", "highest GPA", treat that as
  sort_by="gpa", sort_order="DESC".
- If the query talks about "since YEAR" or "after YEAR", use a term range
  only if you can infer specific terms; otherwise leave terms empty.
- If the query just asks for browsing a subject (e.g. "show all MATH classes"),
  use intent="section_filter".
- Use "browse_subjects" only for very vague queries like "show subjects".
- Always output valid JSON and nothing else.
    """

    user_prompt = f'User query:\n"{text}"'
    json_schema_spec = {
        "name": "QueryPlanFallback",
        "schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["course_lookup", "section_filter", "browse_subjects"],
                },
                "sort_by": {
                    "type": ["string", "null"],
                    "enum": ["gpa", "enrollment", "term", None],
                },
                "sort_order": {
                    "type": ["string", "null"],
                    "enum": ["ASC", "DESC", None],
                },
                "limit": {
                    "type": ["integer", "null"],
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        # mirror QueryFilters / PlanFilters
                        "subjects": {"type": "array", "items": {"type": "string"}},
                        "course_numbers": {"type": "array", "items": {"type": "string"}},
                        "instructors": {"type": "array", "items": {"type": "string"}},
                        "terms": {"type": "array", "items": {"type": "string"}},
                        "course_title_contains": {"type": "array", "items": {"type": "string"}},
                        "exclude_instructors": {"type": "array", "items": {"type": "string"}},
                        "exclude_terms": {"type": "array", "items": {"type": "string"}},
                        "course_levels": {"type": "array", "items": {"type": "string"}},
                        "grade_min": {
                            "type": "object",
                            "additionalProperties": {"type": "integer"},
                        },
                        "grade_min_percent": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                        "grade_max": {
                            "type": "object",
                            "additionalProperties": {"type": "integer"},
                        },
                        "b_or_above_percent_min": {
                            "type": ["number", "null"],
                        },
                        "grade_compare": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "left": {"type": "string"},
                                    "right": {"type": "string"},
                                    "op": {"type": "string"},
                                },
                                "required": ["left", "right", "op"],
                            },
                        },
                        "course_number_min": {"type": ["integer", "null"]},
                        "course_number_max": {"type": ["integer", "null"]},
                        "gpa_min": {"type": ["number", "null"]},
                        "gpa_max": {"type": ["number", "null"]},
                        "credits_min": {"type": ["integer", "null"]},
                        "credits_max": {"type": ["integer", "null"]},
                        "enrollment_min": {"type": ["integer", "null"]},
                        "enrollment_max": {"type": ["integer", "null"]},
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
            "required": ["intent", "filters"],
            "additionalProperties": False,
        },
    }

    content: Optional[str] = None
    transport_used = None

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": json_schema_spec,
            },
        )
        content = resp.output[0].content[0].text
        transport_used = "responses"
    except (TypeError, AttributeError) as exc:
        log.warning(
            "AI fallback: responses API missing response_format support, falling back to chat.completions: %s",
            exc,
        )
    except Exception as exc:
        log.warning("AI fallback: OpenAI request failed via responses API: %s", exc)

    if content is None:
        try:
            chat_resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": json_schema_spec,
                },
            )
            content = chat_resp.choices[0].message.content
            transport_used = "chat.completions"
        except Exception as exc:
            log.warning("AI fallback: OpenAI request failed via chat.completions: %s", exc)
            return None

    if not content:
        return None

    try:
        data = json.loads(content)
    except Exception as exc:
        log.warning("AI fallback: model returned non-JSON content: %s", exc)
        return None

    #  SANITIZE FILTERS FROM AI 
    ai_filters = data.get("filters", {}) or {}

    # These should be dicts for PlanFilters; if the model returned null, drop them
    for key in ("grade_min", "grade_max", "grade_min_percent"):
        if ai_filters.get(key) is None:
            ai_filters.pop(key, None)

    filters_dict = _empty_filters()
    filters_dict.update(ai_filters)

    try:
        pf = PlanFilters(**filters_dict)
    except Exception as exc:
        log.warning("AI fallback: model returned invalid filters: %s", exc)
        return None

    normalized_instructors = _normalize_instructors(pf.instructors)
    pf.instructors = normalized_instructors

    plan = QueryPlan(
        intent=data.get("intent", "section_filter"),
        filters=pf,
        confidence=0.7,  # slightly lower than a perfect rule-based parse
        debug={
            "source": "ai_fallback",
            "raw_ai": data,
            "normalized_instructors": normalized_instructors,
            "transport_used": transport_used,
        },
    )

    sort_by = data.get("sort_by")
    sort_order = data.get("sort_order")
    limit = data.get("limit")

    if sort_by:
        plan.sort_by = sort_by
    if sort_order:
        plan.sort_order = sort_order  # type: ignore
    if isinstance(limit, int):
        plan.limit = limit

    print("AI plan:", plan)
    return plan
