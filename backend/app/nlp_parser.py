# nlp_parser.py
import re
from typing import Dict, Any, List, Tuple

import spacy
from spacy.lang.en.stop_words import STOP_WORDS

from .query_plan import QueryPlan, PlanFilters


# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

# Pre-compiled regex helpers
SUBJECT_COURSE_RE = re.compile(r"\b([A-Z]{2,4})\s*[- ]?\s*(\d{4})\b")
LEVEL_RE = re.compile(r"\b(\d{3,4})\s*LEVEL\b", re.IGNORECASE)
LEVEL_AFTER_RE = re.compile(r"\bLEVEL\s*(\d{3,4})\b", re.IGNORECASE)
RANGE_RE = re.compile(r"\b(\d{3,4})\s*(?:-|to)\s*(\d{3,4})\b", re.IGNORECASE)
GPA_HIGH_RE = re.compile(r"GPA\s*(?:ABOVE|OVER|>=?|GREATER(?: THAN)?|HIGHER(?: THAN)?|OR MORE|OR HIGHER)\s*(\d\.\d)", re.IGNORECASE)
GPA_LOW_RE = re.compile(r"GPA\s*(?:BELOW|UNDER|<=?|LESS(?: THAN)?|LOWER(?: THAN)?|OR LESS|OR LOWER)\s*(\d\.\d)", re.IGNORECASE)
TERM_RE = re.compile(r"\b(Fall|Spring|Summer)\s+'?(\d{2}|\d{4})\b", re.IGNORECASE)
INSTRUCTOR_RE = re.compile(r"\b(?:WITH|BY|TAUGHT BY)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)", re.IGNORECASE)
CREDIT_RE = re.compile(r"(\d{1,2})\s*(?:CREDIT|CREDITS|CR)\b", re.IGNORECASE)
ENROLLMENT_RE = re.compile(r"(?:ENROLLMENT|STUDENTS|PEOPLE)\s*(?:ABOVE|OVER|>=?)\s*(\d+)", re.IGNORECASE)
ENROLLMENT_LOW_RE = re.compile(r"(?:ENROLLMENT|STUDENTS|PEOPLE)\s*(?:BELOW|UNDER|<=?)\s*(\d+)", re.IGNORECASE)

# Build a broad stopword set to avoid treating filler words as subject codes.
SUBJECT_STOPWORD_EXTRAS = {
    "JUST",
    "SOMETHING",
    "INTERESTING",
    "ALL",
    "SHOW",
    "SHOWING",
    "PLEASE",
    "GIVE",
    "FIND",
    "LIST",
    "LOOK",
    "LOOKING",
    "SEARCH",
    "ABOUT",
    "ANY",
    "EVERY",
    "EVERYTHING",
    "COURSE",
    "COURSES",
    "CLASS",
    "CLASSES",
    "WITH",
    "WITHOUT",
    "IN",
    "OF",
    "ON",
    "FOR",
    "BY",
    "TAUGHT",
    "ABOVE",
    "BELOW",
    "UNDER",
    "OVER",
    "TOP",
    "LEVEL",
    "FALL",
    "SPRING",
    "SUMMER",
    "POP",
    "QUIZ",
    "QUIZZES",
}
SUBJECT_STOPWORDS = {w.upper() for w in STOP_WORDS} | SUBJECT_STOPWORD_EXTRAS


def _add_signal(debug: Dict[str, Any], name: str, payload: Any = None) -> None:
    signals: List[str] = debug.setdefault("signals", [])
    signals.append(name)
    if payload is not None:
        debug.setdefault("details", {})[name] = payload


def _normalize_level_range(raw: str) -> Tuple[int, int]:
    """
    Turn "1000 level" or "200 level" into an inclusive numeric range.
    """
    level_num = int(raw)
    if level_num < 1000:
        base = (level_num // 100) * 100
        return base, base + 99
    base = (level_num // 1000) * 1000
    return base, base + 999


def parse_query_to_plan(text: str) -> QueryPlan:
    """
    Rule-based parser that turns the raw query string into a QueryPlan.

    Supports:
      - SUBJECT + 4-digit number (e.g. CS 2104, MATH-1224, CS2104 honors)
      - Subject-only queries
      - Course level ranges (e.g. "1000 level", "1000-2000")
      - GPA thresholds (above/below)
      - Instructor names (spaCy PERSON or after "with/by/taught by")
      - Term labels (Fall 2023, Spring '24)
    """
    doc = nlp(text)
    tokens = [t.text for t in doc]
    upper_text = text.upper()

    filters = PlanFilters()
    debug: Dict[str, Any] = {"tokens": tokens, "signals": []}

    # Subject + course number like "CS 2104" / "CS-2104" / "CS2104"
    m = SUBJECT_COURSE_RE.search(upper_text)
    if m:
        subject_code, course_number = m.group(1), m.group(2)
        filters.subjects = [subject_code]
        filters.course_numbers = [course_number]
        _add_signal(debug, "subject_course", {"subject_code": subject_code, "course_number": course_number})

    # Subject-only fallback (when no course number matched)
    if not filters.subjects:
        subject_candidate = None
        for tok in doc:
            word = tok.text.upper()
            if word.isalpha() and 2 <= len(word) <= 4 and word not in SUBJECT_STOPWORDS:
                subject_candidate = word
                break
        if subject_candidate:
            filters.subjects = [subject_candidate]
            _add_signal(debug, "subject_only", {"subject_code": subject_candidate})

    # Course level or numeric range (prefer explicit numeric range over inferred level)
    rng = RANGE_RE.search(text)
    lvl = LEVEL_RE.search(text) or LEVEL_AFTER_RE.search(text)
    if rng:
        start, end = int(rng.group(1)), int(rng.group(2))
        if start > end:
            start, end = end, start
        filters.course_number_min = start
        filters.course_number_max = end
        _add_signal(debug, "course_range", {"course_number_min": start, "course_number_max": end})
    elif lvl:
        course_min, course_max = _normalize_level_range(lvl.group(1))
        filters.course_number_min = course_min
        filters.course_number_max = course_max
        _add_signal(debug, "level_range", {"course_number_min": course_min, "course_number_max": course_max})
    # If we have a range, drop any exact course number captured from subject_course
    if filters.course_number_min is not None or filters.course_number_max is not None:
        filters.course_numbers = []

    # GPA thresholds
    above = GPA_HIGH_RE.search(text)
    below = GPA_LOW_RE.search(text)
    raw_gpa = None
    if not above and not below:
        raw_match = re.search(r"GPA[^0-9]{0,6}(\d\.\d)", text, re.IGNORECASE)
        if raw_match:
            raw_gpa = float(raw_match.group(1))
            surrounding = text[raw_match.start() : raw_match.end() + 15].lower()
            if any(word in surrounding for word in ["higher", "above", "over", "greater", "or more", "or higher"]):
                above = raw_match  # sentinel to reuse logic
            elif any(word in surrounding for word in ["lower", "below", "under", "less", "or less", "or lower"]):
                below = raw_match  # sentinel
            else:
                # Default to min if no comparator specified.
                filters.gpa_min = raw_gpa
                _add_signal(debug, "gpa_min", {"gpa_min": filters.gpa_min})

    if above:
        if hasattr(above, "group"):
            filters.gpa_min = float(above.group(1))
        else:
            filters.gpa_min = raw_gpa
        _add_signal(debug, "gpa_min", {"gpa_min": filters.gpa_min})
    if below:
        if hasattr(below, "group"):
            filters.gpa_max = float(below.group(1))
        else:
            filters.gpa_max = raw_gpa
        _add_signal(debug, "gpa_max", {"gpa_max": filters.gpa_max})

    # Credits (section or course). Treat bare "3 credits" as exact, or directional words for bounds.
    credit_match = CREDIT_RE.search(text)
    if credit_match:
        credits_val = int(credit_match.group(1))
        lowered = text.lower()
        if "at least" in lowered or "minimum" in lowered or ">=" in lowered or "over" in lowered or "above" in lowered:
            filters.credits_min = credits_val
            _add_signal(debug, "credits_min", {"credits_min": credits_val})
        elif "at most" in lowered or "maximum" in lowered or "<=" in lowered or "under" in lowered or "below" in lowered:
            filters.credits_max = credits_val
            _add_signal(debug, "credits_max", {"credits_max": credits_val})
        else:
            filters.credits_min = credits_val
            filters.credits_max = credits_val
            _add_signal(debug, "credits_exact", {"credits": credits_val})

    # Enrollment thresholds
    enroll_hi = ENROLLMENT_RE.search(text)
    enroll_lo = ENROLLMENT_LOW_RE.search(text)
    if enroll_hi:
        filters.enrollment_min = int(enroll_hi.group(1))
        _add_signal(debug, "enrollment_min", {"enrollment_min": filters.enrollment_min})
    if enroll_lo:
        filters.enrollment_max = int(enroll_lo.group(1))
        _add_signal(debug, "enrollment_max", {"enrollment_max": filters.enrollment_max})

    # Instructor names: try spaCy PERSON entities first, then heuristics after "with/by/taught by"
    instructor_names = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    instructor_names += INSTRUCTOR_RE.findall(text)
    instructor_names = [
        name
        for name in instructor_names
        if not any(
            bad in name.lower()
            for bad in ["gpa", "enrollment", "students", "people", "class", "classes"]
        )
    ]
    if instructor_names:
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for name in instructor_names:
            key = name.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(name)
        filters.instructors = deduped
        _add_signal(debug, "instructor", {"instructors": deduped})

    # Term parsing like "Fall 2023" or "Spring '24"
    term = TERM_RE.search(text)
    if term:
        season = term.group(1).title()
        year_raw = term.group(2)
        year_full = f"20{year_raw[-2:]}" if len(year_raw) == 2 else year_raw
        term_label = f"{season} {year_full}"
        filters.terms = [term_label]
        _add_signal(debug, "term", {"term_label": term_label})

    # If term recognition accidentally captured season/year as subject/course (e.g., "Fall 2024"),
    # drop that match so we can re-run subject fallback.
    if filters.terms and filters.subjects:
        season_subject = filters.subjects[0] in {"FALL", "SPRING", "SUMMER"}
        term_year = filters.terms[0].split()[1] if filters.terms and " " in filters.terms[0] else None
        season_year_misparse = season_subject and (
            (filters.course_numbers and len(filters.course_numbers) == 1 and filters.course_numbers[0] == term_year)
            or not filters.course_numbers
        )
        if season_year_misparse:
            filters.subjects = []
            filters.course_numbers = []
            _add_signal(debug, "term_overrode_subject_course")
            # Re-run subject-only fallback after clearing the incorrect match.
            subject_candidate = None
            for tok in doc:
                word = tok.text.upper()
                if word.isalpha() and 2 <= len(word) <= 4 and word not in SUBJECT_STOPWORDS:
                    subject_candidate = word
                    break
            if subject_candidate:
                filters.subjects = [subject_candidate]
                _add_signal(debug, "subject_only", {"subject_code": subject_candidate})
            # Clean misleading subject_course debug info
            signals = debug.get("signals", [])
            debug["signals"] = [s for s in signals if s != "subject_course"]
            if "details" in debug and "subject_course" in debug["details"]:
                debug["details"].pop("subject_course", None)

    # Course level (UG/GR) cues
    lowered = text.lower()
    if re.search(r"\bundergrad(uate)?\b", lowered) or re.search(r"\bug\b", lowered):
        filters.course_levels = ["UG"]
        _add_signal(debug, "course_level", {"course_levels": filters.course_levels})
    elif re.search(r"\bgrad(uate)?\b", lowered):
        filters.course_levels = ["GR"]
        _add_signal(debug, "course_level", {"course_levels": filters.course_levels})

    # Sorting / limit cues (basic ranking flavor)
    limit_val = None
    top_match = re.search(r"\bTOP\s+(\d+)\b", upper_text)
    if top_match:
        limit_val = int(top_match.group(1))
        _add_signal(debug, "limit", {"limit": limit_val})
    elif "TOP" in upper_text:
        limit_val = 5  # default small k when user says "top" without a number
        _add_signal(debug, "limit_default", {"limit": limit_val})

    sort_by = None
    sort_order = None
    if any(word in upper_text for word in ["EASIEST", "HIGHEST GPA", "BEST GPA"]):
        sort_by, sort_order = "gpa", "DESC"
        _add_signal(debug, "sort_gpa_desc")
    elif any(word in upper_text for word in ["HARDEST", "LOWEST GPA", "WORST GPA"]):
        sort_by, sort_order = "gpa", "ASC"
        _add_signal(debug, "sort_gpa_asc")
    elif "LARGEST" in upper_text or "BIGGEST" in upper_text:
        sort_by, sort_order = "enrollment", "DESC"
        _add_signal(debug, "sort_enrollment_desc")
    elif "SMALLEST" in upper_text or "FEWEST" in upper_text:
        sort_by, sort_order = "enrollment", "ASC"
        _add_signal(debug, "sort_enrollment_asc")
    elif "RECENT" in upper_text or "LATEST" in upper_text or "NEWEST" in upper_text:
        sort_by, sort_order = "term", "DESC"
        _add_signal(debug, "sort_term_desc")
    elif "OLDEST" in upper_text or "EARLIEST" in upper_text:
        sort_by, sort_order = "term", "ASC"
        _add_signal(debug, "sort_term_asc")

    # Decide on intent
    has_extra_filters = any(
        [
            filters.course_number_min is not None,
            filters.course_number_max is not None,
            filters.gpa_min is not None,
            filters.gpa_max is not None,
            bool(filters.instructors),
            bool(filters.terms),
            bool(filters.course_levels),
            filters.credits_min is not None,
            filters.credits_max is not None,
            filters.enrollment_min is not None,
            filters.enrollment_max is not None,
        ]
    )
    has_any_filters = any(
        [
            bool(filters.subjects),
            bool(filters.course_numbers),
            bool(filters.instructors),
            bool(filters.terms),
            filters.course_number_min is not None,
            filters.course_number_max is not None,
            filters.gpa_min is not None,
            filters.gpa_max is not None,
            filters.credits_min is not None,
            filters.credits_max is not None,
            filters.enrollment_min is not None,
            filters.enrollment_max is not None,
        ]
    )

    if m and not has_extra_filters and not (filters.course_number_min or filters.course_number_max):
        intent = "course_lookup"
    elif has_any_filters:
        intent = "section_filter"
    else:
        intent = "browse_subjects"

    if intent == "course_lookup":
        confidence = 1.0
    elif intent == "section_filter":
        confidence = 0.8
    else:
        confidence = 0.5

    plan = QueryPlan(
        intent=intent,
        filters=filters,
        confidence=confidence,
        debug=debug,
    )

    if sort_by:
        plan.sort_by = sort_by
    if sort_order:
        plan.sort_order = sort_order  # type: ignore
    if limit_val:
        plan.limit = limit_val

    return plan
