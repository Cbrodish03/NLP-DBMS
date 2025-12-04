import json
import os
from typing import Optional, Any, Dict

import logging
from openai import OpenAI  # pip install openai>=1.0.0

from .query_plan import QueryPlan, PlanFilters

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


def ai_fallback_parse_query_to_plan(text: str) -> Optional[QueryPlan]:
    """
    Call ChatGPT as a parser of last resort.

    Returns a QueryPlan if parsing works, otherwise None (so you can
    gracefully fall back to normal behavior).
    """
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

    try:
        # Use chat completion with JSON output; more widely supported in the OpenAI SDK.
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content
        if not content:
            log.warning("AI fallback: empty content for text=%r", text)
            return None
        data = json.loads(content)

    except Exception as exc:
        # Log and signal "no fallback" so we fall back to regex.
        log.exception("AI fallback: OpenAI response/parsing failed for text=%r", text)
        return None

    # Merge with defaults so we always have all keys
    filters_dict = _empty_filters()
    # Merge filters but ignore None so defaults stay valid types.
    for key, val in (data.get("filters") or {}).items():
        if val is None:
            continue
        filters_dict[key] = val

    try:
        pf = PlanFilters(**filters_dict)
    except Exception:
        log.exception("AI fallback: PlanFilters validation failed for text=%r", text)
        return None

    plan = QueryPlan(
        intent=data.get("intent", "section_filter"),
        filters=pf,
        confidence=0.7,  # slightly lower than a perfect rule-based parse
        debug={
            "source": "ai_fallback",
            "raw_ai": data,
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

    return plan
