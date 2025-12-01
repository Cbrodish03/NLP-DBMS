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
PLACEHOLDER_RANGE_RE = re.compile(r"\b([A-Z]{2,4})\s+(\d)[xX]{3}\b")
COURSE_BETWEEN_RE = re.compile(r"\bbetween\s+(\d{3,4})\s+(?:and|to)\s+(\d{3,4})\b", re.IGNORECASE)
GPA_HIGH_RE = re.compile(r"GPA\s*(?:ABOVE|OVER|>=?|GREATER(?: THAN)?|HIGHER(?: THAN)?|OR MORE|OR HIGHER)\s*(\d\.\d)", re.IGNORECASE)
GPA_LOW_RE = re.compile(r"GPA\s*(?:BELOW|UNDER|<=?|LESS(?: THAN)?|LOWER(?: THAN)?|OR LESS|OR LOWER)\s*(\d\.\d)", re.IGNORECASE)
TERM_RE = re.compile(r"\b(Fall|Spring|Summer)\s+'?(\d{2}|\d{4})\b", re.IGNORECASE)
RELATIVE_TERM_RE = re.compile(r"\b(last|this)\s+(spring|fall|summer)\b", re.IGNORECASE)
INSTRUCTOR_RE = re.compile(r"\b(?:WITH|BY|TAUGHT BY)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)", re.IGNORECASE)
CREDIT_RE = re.compile(r"(\d{1,2})\s*(?:CREDIT|CREDITS|CR)\b", re.IGNORECASE)
ENROLLMENT_RE = re.compile(r"(?:ENROLLMENT|STUDENTS|PEOPLE)\s*(?:ABOVE|OVER|>=?)\s*(\d+)", re.IGNORECASE)
ENROLLMENT_LOW_RE = re.compile(r"(?:ENROLLMENT|STUDENTS|PEOPLE)\s*(?:BELOW|UNDER|<=?)\s*(\d+)", re.IGNORECASE)
GRADE_COUNT_RE = re.compile(
    r"(\d+)\s+(?:students|people)\s+(?:got|received|with)\s+an?\s+(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)",
    re.IGNORECASE,
)
GRADE_PERCENT_RE = re.compile(
    r"(\d{1,3})\s*%[^\w]*(?:of\s+(?:students|the\s+class)\s+)?(?:got|received|are|have)?\s*(?:an?\s*)?"
    r"(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)(\s*(?:OR\s+ABOVE|OR\s+HIGHER))?",
    re.IGNORECASE,
)
NO_GRADES_RE = re.compile(
    r"\bno\s+((?:A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)(?:s)?(?:\s+or\s+(?:A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)(?:s)?)*)",
    re.IGNORECASE,
)
GRADE_COMPARE_RE = re.compile(
    r"\b(more|less|fewer)\s+(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)\s+than\s+(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|F)",
    re.IGNORECASE,
)
ENROLLMENT_BETWEEN_RE = re.compile(
    r"(?:between|from)\s+(\d+)\s+(?:and|to)\s+(\d+)\s+(?:students|people)",
    re.IGNORECASE,
)
ENROLLMENT_BETWEEN_ALT_RE = re.compile(
    r"(?:enrollment|students|people)\s+(?:between|from)\s+(\d+)\s+(?:and|to)\s+(\d+)",
    re.IGNORECASE,
)
LARGEST_K_RE = re.compile(r"(?:largest|biggest|most students|highest enrollment)\s+(\d+)", re.IGNORECASE)
SMALLEST_K_RE = re.compile(r"(?:smallest|fewest|least students)\s+(\d+)", re.IGNORECASE)

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
    "GPA",
    "GOT",
    "ENROLLMENT",
    "ENROLLMENTS",
    "STUDENT",
    "STUDENTS",
    "PEOPLE",
    "LARGEST",
    "SMALLEST",
    "LEAST",
    "AT",
    "LEAST",
    "MOST",
    "MORE",
    "LESS",
    "FEWER",
    "EXCLUDE",
    "EXCLUDING",
    "EXCLUDED",
    "SECTION",
    "SECTIONS",
    "F",
    "FS",
    "INSTRUCTOR",
    "PROFESSOR",
}
SUBJECT_STOPWORDS = {w.upper() for w in STOP_WORDS} | SUBJECT_STOPWORD_EXTRAS


def _is_descriptor(tok: spacy.tokens.Token) -> bool:
    """Heuristic: tokens that are structural/stopword-ish and should be ignored for fallback matching."""
    if tok.is_punct or tok.like_num:
        return True
    if tok.is_stop:
        return True
    if tok.pos_ in {"ADP", "AUX", "DET", "SCONJ", "CCONJ", "PART", "ADV", "PRON", "INTJ"}:
        return True
    return False


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
        if subject_code not in SUBJECT_STOPWORDS:
            filters.subjects = [subject_code]
            filters.course_numbers = [course_number]
            _add_signal(debug, "subject_course", {"subject_code": subject_code, "course_number": course_number})
    # Placeholder like "CS 2xxx"
    if not filters.subjects:
        ph = PLACEHOLDER_RANGE_RE.search(text)
        if ph:
            subject_code = ph.group(1).upper()
            base = int(ph.group(2)) * 1000
            filters.subjects = [subject_code]
            filters.course_number_min = base
            filters.course_number_max = base + 999
            filters.course_numbers = []
            _add_signal(debug, "course_placeholder", {"subject_code": subject_code, "course_number_min": base, "course_number_max": base + 999})

    # Subject-only fallback (when no course number matched)
    if not filters.subjects:
        subject_candidate = None
        for tok in doc:
            if _is_descriptor(tok):
                continue
            word = tok.text.upper()
            if word.isalpha() and 2 <= len(word) <= 4 and word not in SUBJECT_STOPWORDS:
                subject_candidate = word
                break
        if subject_candidate:
            filters.subjects = [subject_candidate]
            _add_signal(debug, "subject_only", {"subject_code": subject_candidate})

    # Course title keywords (quoted phrases or leftover meaningful tokens)
    title_terms: List[str] = []
    # Quoted phrases
    for match in re.finditer(r'"([^"]+)"|\'([^\']+)\'', text):
        phrase = match.group(1) or match.group(2)
        if phrase:
            title_terms.append(phrase.strip())
    # Meaningful leftover tokens
    for tok in doc:
        if _is_descriptor(tok) or tok.like_num:
            continue
        word = tok.text.strip()
        upper = word.upper()
        if re.match(r"^[A-Z]{2,4}\s*\d[xX]{3}$", word, re.IGNORECASE):
            continue
        if re.match(r"^\d[xX]{3}$", word):
            continue
        if upper in SUBJECT_STOPWORDS:
            continue
        if filters.subjects and upper in filters.subjects:
            continue
        if re.match(r"\d{3,4}", word):
            continue
        if len(word) < 3:
            continue
        title_terms.append(word)
    if title_terms:
        # Deduplicate preserve order
        seen_terms = set()
        deduped_terms: List[str] = []
        for term in title_terms:
            key = term.lower()
            if key not in seen_terms:
                seen_terms.add(key)
                deduped_terms.append(term)
        if deduped_terms:
            filters.course_title_contains = deduped_terms
            _add_signal(debug, "course_title", {"contains": deduped_terms})

    # Course level or numeric range (prefer explicit numeric range over inferred level)
    between_rng = COURSE_BETWEEN_RE.search(text)
    rng = RANGE_RE.search(text)
    lvl = LEVEL_RE.search(text) or LEVEL_AFTER_RE.search(text)
    if between_rng:
        start, end = int(between_rng.group(1)), int(between_rng.group(2))
        if start > end:
            start, end = end, start
        filters.course_number_min = start
        filters.course_number_max = end
        _add_signal(debug, "course_between", {"course_number_min": start, "course_number_max": end})
    elif rng:
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
    between = ENROLLMENT_BETWEEN_RE.search(text) or ENROLLMENT_BETWEEN_ALT_RE.search(text)
    if between:
        start, end = int(between.group(1)), int(between.group(2))
        if start > end:
            start, end = end, start
        filters.enrollment_min = start
        filters.enrollment_max = end
        _add_signal(debug, "enrollment_between", {"enrollment_min": start, "enrollment_max": end})
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
    # Drop instructor candidates that are made of stop/descriptor tokens.
    cleaned_instructors: List[str] = []
    for name in instructor_names:
        parts = name.replace(",", " ").split()
        if any(p.upper() in SUBJECT_STOPWORDS or p.lower() in STOP_WORDS for p in parts):
            continue
        cleaned_instructors.append(name)
    instructor_names = cleaned_instructors
    if not instructor_names:
        # Fallback: grab trailing tokens that look like names (e.g., "cao", "sully" in "cs cao sully").
        fallback: List[str] = []
        for tok in reversed(doc):
            word = tok.text.strip()
            upper = word.upper()
            if _is_descriptor(tok):
                continue
            if not tok.is_alpha:
                continue
            if len(word) < 3:
                continue
            if upper in SUBJECT_STOPWORDS:
                continue
            if filters.subjects and upper in filters.subjects:
                continue
            fallback.append(word)
            if len(fallback) >= 2:
                break
        instructor_names = list(reversed(fallback))

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

    # Grade counts like "5 students got an A"
    grade_match = GRADE_COUNT_RE.search(text)
    if grade_match:
        count = int(grade_match.group(1))
        grade = grade_match.group(2).upper().replace("PLUS", "+").replace("MINUS", "-")
        filters.grade_min[grade] = count
        _add_signal(debug, "grade_min", {"grade": grade, "count": count})

    percent_match = GRADE_PERCENT_RE.search(text)
    if percent_match:
        pct = float(percent_match.group(1))
        grade = percent_match.group(2).upper().replace("PLUS", "+").replace("MINUS", "-")
        or_above = bool(percent_match.group(3))
        if or_above and grade.startswith("B"):
            filters.b_or_above_percent_min = pct
            _add_signal(debug, "b_or_above_pct", {"pct": pct})
        else:
            filters.grade_min_percent[grade] = pct
            _add_signal(debug, "grade_min_percent", {"grade": grade, "pct": pct})

    no_grades = NO_GRADES_RE.search(text)
    if no_grades:
        grades_str = no_grades.group(1)
        parts = re.split(r"\s+or\s+", grades_str, flags=re.IGNORECASE)
        for p in parts:
            cleaned = p.strip().upper().rstrip("S")
            if cleaned:
                filters.grade_max[cleaned] = 0
        _add_signal(debug, "grade_max_zero", {"grades": list(filters.grade_max.keys())})

    compare_match = GRADE_COMPARE_RE.search(text)
    if compare_match:
        comp_word, left, right = compare_match.groups()
        op = ">"
        if comp_word.lower() in {"less", "fewer"}:
            op = "<"
        filters.grade_compare.append({"left": left.upper(), "right": right.upper(), "op": op})
        _add_signal(debug, "grade_compare", {"left": left.upper(), "right": right.upper(), "op": op})

    # Exclusion phrases for instructors/terms
    exclude_instr_matches = re.findall(r"\b(?:not|without|exclude)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)", text)
    if exclude_instr_matches:
        cleaned = []
        for name in exclude_instr_matches:
            # Skip single-word stopwords/seasons to avoid false instructors like "Fall".
            parts = name.strip().split()
            if len(parts) == 1 and (parts[0].upper() in SUBJECT_STOPWORDS or parts[0].lower() in STOP_WORDS):
                continue
            cleaned.append(name.strip())
        if cleaned:
            filters.exclude_instructors = cleaned
            _add_signal(debug, "exclude_instructors", {"exclude_instructors": cleaned})

    exclude_term_match = re.search(r"\bexclude\s+(Fall|Spring|Summer)\s+'?(\d{2}|\d{4})\b", text, re.IGNORECASE)
    if exclude_term_match:
        season = exclude_term_match.group(1).title()
        year_raw = exclude_term_match.group(2)
        year_full = f"20{year_raw[-2:]}" if len(year_raw) == 2 else year_raw
        term_label = f"{season} {year_full}"
        filters.exclude_terms = [term_label]
        _add_signal(debug, "exclude_term", {"term": term_label})
        if filters.terms:
            # Drop matching include terms if present to avoid conflicting filters.
            filters.terms = [t for t in filters.terms if t != term_label]
            removed = [term_label]
            filtered_out = debug.setdefault("filtered_out", {})
            filtered_out["terms"] = filtered_out.get("terms", []) + removed
        # If we just saw an exclude term and no include term matched, ensure we don't later add it.
        if not filters.terms:
            debug.setdefault("excluded_terms_only", []).append(term_label)

    # Ranking: largest/smallest K classes by enrollment
    top_k = LARGEST_K_RE.search(text)
    low_k = SMALLEST_K_RE.search(text)
    if top_k:
        try:
            k = int(top_k.group(1))
            plan_limit = max(k, 1)
            # Will be consumed later
            debug["rank_enrollment"] = {"limit": plan_limit, "order": "DESC"}
        except ValueError:
            pass
    if low_k and "rank_enrollment" not in debug:
        try:
            k = int(low_k.group(1))
            plan_limit = max(k, 1)
            debug["rank_enrollment"] = {"limit": plan_limit, "order": "ASC"}
        except ValueError:
            pass

    # If the query is a single token and we found an instructor guess, drop any subject-only guess to avoid noise.
    if len(doc) == 1 and filters.instructors and filters.subjects and not filters.course_numbers:
        filters.subjects = []
        signals = debug.get("signals", [])
        debug["signals"] = [s for s in signals if s != "subject_only"]
        if "details" in debug:
            debug["details"].pop("subject_only", None)

    # Term parsing like "Fall 2023" or "Spring '24"
    term = TERM_RE.search(text)
    if term:
        season = term.group(1).title()
        year_raw = term.group(2)
        year_full = f"20{year_raw[-2:]}" if len(year_raw) == 2 else year_raw
        term_label = f"{season} {year_full}"
        filters.terms = [term_label]
        _add_signal(debug, "term", {"term_label": term_label})
    else:
        rel_term = RELATIVE_TERM_RE.search(text)
        if rel_term:
            when, season = rel_term.group(1).lower(), rel_term.group(2).title()
            debug.setdefault("relative_term", {})["season"] = season
            debug["relative_term"]["when"] = when
            _add_signal(debug, "relative_term", {"season": season, "when": when})

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
                if _is_descriptor(tok):
                    continue
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
    # Apply enrollment ranking if detected ("largest/smallest k classes")
    rank_info = debug.get("rank_enrollment")
    if rank_info:
        plan.sort_by = "enrollment"
        plan.sort_order = rank_info.get("order")  # type: ignore
        plan.limit = rank_info.get("limit")

    return plan
