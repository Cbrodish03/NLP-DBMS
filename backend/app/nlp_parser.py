# nlp_parser.py
import re
from typing import Dict, Any

import spacy

from .query_plan import QueryPlan, PlanFilters


# Load spaCy model once
nlp = spacy.load("en_core_web_sm")


def parse_query_to_plan(text: str) -> QueryPlan:
    """
    Rule-based parser that turns the raw query string into a QueryPlan.

    Currently:
      - If we see SUBJECT + 4-digit number (e.g. CS 2104), intent=course_lookup
      - Otherwise, intent=browse_subjects
    """
    doc = nlp(text)
    tokens = [t.text for t in doc]
    upper_text = text.upper()

    debug: Dict[str, Any] = {"tokens": tokens}

    # Look for patterns like "CS 2104", "MATH 1224"
    m = re.search(r"\b([A-Z]{2,4})\s*([0-9]{4})\b", upper_text)

    filters = PlanFilters()

    if m:
        subject_code, course_number = m.group(1), m.group(2)
        filters.subjects = [subject_code]
        filters.course_numbers = [course_number]
        debug["regex_match"] = {
            "subject_code": subject_code,
            "course_number": course_number,
        }
        intent = "course_lookup"
        confidence = 1.0
    else:
        intent = "browse_subjects"
        confidence = 0.8  # arbitrary for now

    return QueryPlan(
        intent=intent,
        filters=filters,
        confidence=confidence,
        debug=debug,
    )
