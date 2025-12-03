# executor.py
from typing import List, Optional, Tuple, Any
from decimal import Decimal

from .db import get_db_conn
from .query_plan import QueryPlan
from .schemas import (
    SectionInfo,
    SectionGrades,
    CourseInfo,
    TermInfo,
    InstructorInfo,
    Aggregates,
    SubjectInfo,
    QueryFilters,
)

SECTION_SELECT = """
    SELECT
        s.section_id,
        s.course_id,
        s.term_id,
        s.instructor_id,
        s.section_credits,
        s.section_graded_enrollment,
        s.subject_code,
        s.subject_name,
        s.course_number,
        s.course_title,
        s.course_credits,
        s.course_level,
        s.term_label,
        s.academic_year,
        s.instructor,
        s.gpa,
        s.a,
        s.a_minus,
        s.b_plus,
        s.b,
        s.b_minus,
        s.c_plus,
        s.c,
        s.c_minus,
        s.d_plus,
        s.d,
        s.d_minus,
        s.f,
        s.withdraws,
        s.graded_enrollment
    FROM v_grade_distribution_full s
"""




def decimal_to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def compute_aggregates(sections: List[SectionInfo]) -> Aggregates:
    if not sections:
        return Aggregates(
            section_count=0,
            avg_gpa=None,
            total_graded_enrollment=0,
        )

    section_count = len(sections)
    total_enrollment = 0
    gpa_sum = 0.0
    gpa_count = 0

    for s in sections:
        if s.grades and s.grades.graded_enrollment is not None:
            total_enrollment += s.grades.graded_enrollment
        if s.grades and s.grades.gpa is not None:
            gpa_sum += s.grades.gpa
            gpa_count += 1

    avg_gpa = gpa_sum / gpa_count if gpa_count > 0 else None
    if avg_gpa is not None:
        avg_gpa = round(avg_gpa, 3)

    return Aggregates(
        section_count=section_count,
        avg_gpa=avg_gpa,
        total_graded_enrollment=total_enrollment,
    )


def row_to_section(row: Any) -> SectionInfo:
    (
        section_id,
        course_id,
        term_id,
        instructor_id,
        section_credits,
        section_graded_enrollment,
        subject_code,
        subject_name,
        course_number,
        course_title,
        course_credits,
        course_level,
        term_label,
        academic_year,
        instructor_name,
        gpa,
        a,
        a_minus,
        b_plus,
        b,
        b_minus,
        c_plus,
        c,
        c_minus,
        d_plus,
        d,
        d_minus,
        f,
        withdraws,
        grades_graded_enrollment,
    ) = row

    grades = SectionGrades(
        gpa=decimal_to_float(gpa),
        graded_enrollment=grades_graded_enrollment,
        withdraws=withdraws,
        breakdown={
            "A": a,
            "A-": a_minus,
            "B+": b_plus,
            "B": b,
            "B-": b_minus,
            "C+": c_plus,
            "C": c,
            "C-": c_minus,
            "D+": d_plus,
            "D": d,
            "D-": d_minus,
            "F": f,
        },
    )

    course = CourseInfo(
        course_id=course_id,
        subject_code=subject_code,
        subject_name=subject_name,
        course_number=course_number,
        title=course_title,
        credits=course_credits,
        level=course_level,
    )

    term = TermInfo(
        term_id=term_id,
        label=term_label,
        academic_year=academic_year,
    )

    instructor = InstructorInfo(
        instructor_id=instructor_id,
        name_display=instructor_name,
    )

    return SectionInfo(
        section_id=section_id,
        course_id=course_id,
        term_id=term_id,
        instructor_id=instructor_id,
        credits=section_credits,
        graded_enrollment=section_graded_enrollment,
        course=course,
        term=term,
        instructor=instructor,
        grades=grades,
    )


def filter_existing_instructors(cur, instructors: List[str]) -> Tuple[List[str], List[str]]:
    """Return only instructor names that exist in the DB (ILIKE match), plus dropped ones."""
    if not instructors:
        return [], []
    valid: List[str] = []
    dropped: List[str] = []
    for name in instructors:
        cur.execute(
            "SELECT 1 FROM instructor WHERE name_display ILIKE %s LIMIT 1;",
            (f"%{name}%",),
        )
        if cur.fetchone():
            valid.append(name)
        else:
            dropped.append(name)
    return valid, dropped


def filter_existing_subjects(cur, subjects: List[str]) -> Tuple[List[str], List[str]]:
    """Return only subject codes that exist in the DB (and capture drops)."""
    if not subjects:
        return [], []
    valid: List[str] = []
    dropped: List[str] = []
    for code in subjects:
        cur.execute("SELECT 1 FROM subject WHERE subject_code = %s LIMIT 1;", (code,))
        if cur.fetchone():
            valid.append(code)
        else:
            dropped.append(code)
    return valid, dropped


def filter_existing_titles(cur, titles: List[str]) -> Tuple[List[str], List[str]]:
    """Return only course titles that exist in the DB (ILIKE match), plus dropped ones."""
    if not titles:
        return [], []
    valid: List[str] = []
    dropped: List[str] = []
    for title in titles:
        cur.execute("SELECT 1 FROM course WHERE title ILIKE %s LIMIT 1;", (f"%{title}%",))
        if cur.fetchone():
            valid.append(title)
        else:
            dropped.append(title)
    return valid, dropped


def build_where_and_params(pf) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    enrollment_col = "COALESCE(s.section_graded_enrollment, s.graded_enrollment)"
    if pf.subjects:
        clauses.append("s.subject_code = ANY(%s)")
        params.append(pf.subjects)
    # Only apply exact course number match when no range constraints are present.
    if pf.course_numbers and pf.course_number_min is None and pf.course_number_max is None:
        clauses.append("CAST(s.course_number AS TEXT) = ANY(%s)")
        params.append(pf.course_numbers)
    if pf.course_number_min is not None:
        clauses.append("CAST(s.course_number AS INT) >= %s")
        params.append(pf.course_number_min)
    if pf.course_number_max is not None:
        clauses.append("CAST(s.course_number AS INT) <= %s")
        params.append(pf.course_number_max)
    if getattr(pf, "course_levels", None):
        clauses.append("s.course_level = ANY(%s)")
        params.append(pf.course_levels)
    if getattr(pf, "course_title_contains", None):
        clauses.append("s.course_title ILIKE ALL(%s)")
        params.append([f"%{t}%" for t in pf.course_title_contains])
    if pf.instructors:
        clauses.append("s.instructor ILIKE ANY(%s)")
        params.append([f"%{i}%" for i in pf.instructors])
    if getattr(pf, "exclude_instructors", None):
        clauses.append("NOT (s.instructor ILIKE ANY(%s))")
        params.append([f"%{i}%" for i in pf.exclude_instructors])
    if pf.terms:
        exact_terms = [t for t in pf.terms if " " in t]
        season_terms = [t for t in pf.terms if " " not in t]
        if exact_terms:
            clauses.append("s.term_label = ANY(%s)")
            params.append(exact_terms)
        if season_terms:
            clauses.append("s.term_label ILIKE ANY(%s)")
            params.append([f"{t} %" for t in season_terms])
    if getattr(pf, "exclude_terms", None):
        clauses.append("NOT (s.term_label = ANY(%s))")
        params.append(pf.exclude_terms)
    if pf.gpa_min is not None:
        clauses.append("s.gpa >= %s")
        params.append(pf.gpa_min)
    if pf.gpa_max is not None:
        clauses.append("s.gpa <= %s")
        params.append(pf.gpa_max)
    if getattr(pf, "credits_min", None) is not None:
        clauses.append("COALESCE(s.section_credits, s.course_credits) >= %s")
        params.append(pf.credits_min)
    if getattr(pf, "credits_max", None) is not None:
        clauses.append("COALESCE(s.section_credits, s.course_credits) <= %s")
        params.append(pf.credits_max)
    if getattr(pf, "enrollment_min", None) is not None:
        clauses.append(f"{enrollment_col} >= %s")
        params.append(pf.enrollment_min)
    if getattr(pf, "enrollment_max", None) is not None:
        clauses.append(f"{enrollment_col} <= %s")
        params.append(pf.enrollment_max)
    if getattr(pf, "grade_min", None):
        grade_map = {
            "A": "s.a",
            "A-": "s.a_minus",
            "B+": "s.b_plus",
            "B": "s.b",
            "B-": "s.b_minus",
            "C+": "s.c_plus",
            "C": "s.c",
            "C-": "s.c_minus",
            "D+": "s.d_plus",
            "D": "s.d",
            "D-": "s.d_minus",
            "F": "s.f",
        }
        for grade, threshold in pf.grade_min.items():
            col = grade_map.get(grade.upper())
            if col is None:
                continue
            clauses.append(f"{col} >= %s")
            params.append(threshold)
    if getattr(pf, "grade_max", None):
        grade_map = {
            "A": "s.a",
            "A-": "s.a_minus",
            "B+": "s.b_plus",
            "B": "s.b",
            "B-": "s.b_minus",
            "C+": "s.c_plus",
            "C": "s.c",
            "C-": "s.c_minus",
            "D+": "s.d_plus",
            "D": "s.d",
            "D-": "s.d_minus",
            "F": "s.f",
        }
        for grade, threshold in pf.grade_max.items():
            col = grade_map.get(grade.upper())
            if col is None:
                continue
            clauses.append(f"{col} <= %s")
            params.append(threshold)
    if getattr(pf, "grade_min_percent", None):
        grade_map = {
            "A": "s.a",
            "A-": "s.a_minus",
            "B+": "s.b_plus",
            "B": "s.b",
            "B-": "s.b_minus",
            "C+": "s.c_plus",
            "C": "s.c",
            "C-": "s.c_minus",
            "D+": "s.d_plus",
            "D": "s.d",
            "D-": "s.d_minus",
            "F": "s.f",
        }
        for grade, pct in pf.grade_min_percent.items():
            col = grade_map.get(grade.upper())
            if col is None:
                continue
            clauses.append(f"({col}::float) >= (%s / 100.0) * NULLIF({enrollment_col}, 0)")
            params.append(pct)
    if getattr(pf, "b_or_above_percent_min", None) is not None:
        b_cols = [
            "COALESCE(s.a,0)",
            "COALESCE(s.a_minus,0)",
            "COALESCE(s.b_plus,0)",
            "COALESCE(s.b,0)",
            "COALESCE(s.b_minus,0)",
        ]
        numerator = " + ".join(b_cols)
        clauses.append(f"(({numerator})::float) >= (%s / 100.0) * NULLIF({enrollment_col}, 0)")
        params.append(pf.b_or_above_percent_min)
    if getattr(pf, "grade_compare", None):
        grade_map = {
            "A": "s.a",
            "A-": "s.a_minus",
            "B+": "s.b_plus",
            "B": "s.b",
            "B-": "s.b_minus",
            "C+": "s.c_plus",
            "C": "s.c",
            "C-": "s.c_minus",
            "D+": "s.d_plus",
            "D": "s.d",
            "D-": "s.d_minus",
            "F": "s.f",
        }
        for comp in pf.grade_compare:
            left = grade_map.get(comp.get("left", "").upper())
            right = grade_map.get(comp.get("right", "").upper())
            op = comp.get("op")
            if left and right and op in {">", "<", ">=", "<="}:
                clauses.append(f"{left} {op} {right}")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def execute_plan(plan: QueryPlan) -> Tuple[List[SectionInfo], Optional[List[SubjectInfo]], Aggregates, QueryFilters]:
    """
    Execute a QueryPlan against the database.

    For now:
      - course_lookup: query v_grade_distribution_full for subject+course_number (+ optional filters)
      - browse_subjects: return subjects and no sections
      - section_filter: flexible WHERE-clause based on parsed filters
    """
    conn = get_db_conn()
    cur = conn.cursor()

    sections: List[SectionInfo] = []
    subjects: Optional[List[SubjectInfo]] = None
    normalized_filters = QueryFilters(**plan.filters.dict())

    try:
        if plan.intent == "course_lookup":
            pf = plan.filters.copy(deep=True)
            pf.subjects, dropped_subjects = filter_existing_subjects(cur, pf.subjects)
            pf.instructors, dropped_instructors = filter_existing_instructors(cur, pf.instructors)
            excl_instructors_valid, dropped_excl_instructors = filter_existing_instructors(
                cur, getattr(pf, "exclude_instructors", [])
            )
            pf.exclude_instructors = excl_instructors_valid
            pf.course_title_contains, dropped_titles = filter_existing_titles(cur, getattr(pf, "course_title_contains", []))
            # Resolve relative term hints (e.g., "last spring") to the latest matching term label.
            rel = plan.debug.get("relative_term") if isinstance(plan.debug, dict) else None
            if rel and rel.get("season") and not pf.terms:
                season = rel["season"]
                cur.execute(
                    "SELECT label FROM term WHERE label ILIKE %s ORDER BY term_id DESC LIMIT 1;",
                    (f"{season} %",),
                )
                row = cur.fetchone()
                if row:
                    pf.terms = [row[0]]
                    _ = plan.debug.setdefault("relative_term", {})
                    plan.debug["relative_term"]["resolved"] = row[0]
            # If exclude_terms overlaps with terms, prefer exclusion.
            if getattr(pf, "exclude_terms", None):
                if pf.terms:
                    filtered_out_terms = pf.terms.copy()
                    pf.terms = []
                    plan.debug.setdefault("filtered_out", {}).setdefault("terms", []).extend(filtered_out_terms)
                else:
                    plan.debug.setdefault("filtered_out", {}).setdefault("terms", []).extend(pf.exclude_terms)
            if not pf.subjects:
                pf.course_numbers = []
            if dropped_subjects or dropped_instructors or dropped_excl_instructors:
                filtered_out = plan.debug.setdefault("filtered_out", {})
                if dropped_subjects:
                    filtered_out["subjects"] = dropped_subjects
                if dropped_instructors:
                    filtered_out["instructors"] = dropped_instructors
                if dropped_excl_instructors:
                    filtered_out["exclude_instructors"] = dropped_excl_instructors
                if dropped_titles:
                    filtered_out["course_title_contains"] = dropped_titles
            normalized_filters = QueryFilters(**pf.dict())

            if not pf.subjects or not pf.course_numbers:
                aggregates = compute_aggregates(sections)
                return sections, subjects, aggregates, normalized_filters

            # Anchored match for a specific subject+course, using simple equality to avoid type/array sensitivity.
            clauses = [
                "s.subject_code = %s",
                "CAST(s.course_number AS TEXT) = %s",
            ]
            params: List[Any] = [pf.subjects[0], pf.course_numbers[0]]

            # Allow optional extra filters (e.g., term, instructor, GPA) on top of the exact match.
            pf_extra = pf.copy(deep=True)
            pf_extra.subjects = []
            pf_extra.course_numbers = []

            extra_where, extra_params = build_where_and_params(pf_extra)
            if extra_where:
                extra_parts = extra_where.replace("WHERE ", "").strip()
                if extra_parts:
                    clauses.append(extra_parts)
                    params.extend(extra_params)

            order_clause = "ORDER BY s.term_id DESC, s.section_id"
            if plan.sort_by:
                sort_field_map = {
                    "gpa": "s.gpa",
                    "enrollment": "COALESCE(s.section_graded_enrollment, s.graded_enrollment)",
                    "term": "s.term_id",
                }
                if plan.sort_by in sort_field_map:
                    direction = plan.sort_order or "DESC"
                    order_clause = f"ORDER BY {sort_field_map[plan.sort_by]} {direction}, s.section_id"

            limit_clause = f"LIMIT {plan.limit}" if plan.limit else ""

            sql = f"""
                {SECTION_SELECT}
                WHERE {' AND '.join(clauses)}
                {order_clause}
                {limit_clause};
            """
            cur.execute(sql, params)
            rows = cur.fetchall()
            sections = [row_to_section(row) for row in rows]

        elif plan.intent == "browse_subjects":
            cur.execute("SELECT subject_code, name FROM subject ORDER BY subject_code;")
            rows = cur.fetchall()
            subjects = [
                SubjectInfo(subject_code=r[0], name=r[1]) for r in rows
            ]

        elif plan.intent == "section_filter":
            pf = plan.filters.copy(deep=True)
            pf.subjects, dropped_subjects = filter_existing_subjects(cur, pf.subjects)
            pf.instructors, dropped_instructors = filter_existing_instructors(cur, pf.instructors)
            excl_instructors_valid, dropped_excl_instructors = filter_existing_instructors(
                cur, getattr(pf, "exclude_instructors", [])
            )
            pf.exclude_instructors = excl_instructors_valid
            pf.course_title_contains, dropped_titles = filter_existing_titles(cur, getattr(pf, "course_title_contains", []))
            rel = plan.debug.get("relative_term") if isinstance(plan.debug, dict) else None
            if rel and rel.get("season") and not pf.terms:
                season = rel["season"]
                cur.execute(
                    "SELECT label FROM term WHERE label ILIKE %s ORDER BY term_id DESC LIMIT 1;",
                    (f"{season} %",),
                )
                row = cur.fetchone()
                if row:
                    pf.terms = [row[0]]
                    _ = plan.debug.setdefault("relative_term", {})
                    plan.debug["relative_term"]["resolved"] = row[0]
            if getattr(pf, "exclude_terms", None):
                if pf.terms:
                    filtered_out_terms = pf.terms.copy()
                    pf.terms = []
                    plan.debug.setdefault("filtered_out", {}).setdefault("terms", []).extend(filtered_out_terms)
                else:
                    plan.debug.setdefault("filtered_out", {}).setdefault("terms", []).extend(pf.exclude_terms)
            if not pf.subjects:
                pf.course_numbers = []
            if dropped_subjects or dropped_instructors or dropped_excl_instructors or dropped_titles:
                filtered_out = plan.debug.setdefault("filtered_out", {})
                if dropped_subjects:
                    filtered_out["subjects"] = dropped_subjects
                if dropped_instructors:
                    filtered_out["instructors"] = dropped_instructors
                if dropped_excl_instructors:
                    filtered_out["exclude_instructors"] = dropped_excl_instructors
                if dropped_titles:
                    filtered_out["course_title_contains"] = dropped_titles
            normalized_filters = QueryFilters(**pf.dict())
            where_sql, params = build_where_and_params(pf)
            if not where_sql:
                aggregates = compute_aggregates(sections)
                return sections, subjects, aggregates, normalized_filters

            order_clause = "ORDER BY s.term_id DESC, s.section_id"
            if plan.sort_by:
                sort_field_map = {
                    "gpa": "s.gpa",
                    "enrollment": "COALESCE(s.section_graded_enrollment, s.graded_enrollment)",
                    "term": "s.term_id",
                }
                if plan.sort_by in sort_field_map:
                    direction = plan.sort_order or "DESC"
                    order_clause = f"ORDER BY {sort_field_map[plan.sort_by]} {direction}, s.section_id"

            limit_clause = f"LIMIT {plan.limit}" if plan.limit else ""

            sql = f"""
                {SECTION_SELECT}
                {where_sql}
                {order_clause}
                {limit_clause};
            """
            cur.execute(sql, params)
            rows = cur.fetchall()
            sections = [row_to_section(row) for row in rows]

        # Future: handle "ranking_query" here

        aggregates = compute_aggregates(sections)
        normalized_filters = QueryFilters(**pf.dict())
        return sections, subjects, aggregates, normalized_filters

    finally:
        cur.close()
        conn.close()
