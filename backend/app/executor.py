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


def filter_existing_instructors(cur, instructors: List[str]) -> List[str]:
    """Return only instructor names that exist in the DB (ILIKE match)."""
    if not instructors:
        return []
    valid: List[str] = []
    for name in instructors:
        cur.execute(
            "SELECT 1 FROM instructor WHERE name_display ILIKE %s LIMIT 1;",
            (f"%{name}%",),
        )
        if cur.fetchone():
            valid.append(name)
    return valid


def filter_existing_subjects(cur, subjects: List[str]) -> List[str]:
    """Return only subject codes that exist in the DB."""
    if not subjects:
        return []
    valid: List[str] = []
    for code in subjects:
        cur.execute("SELECT 1 FROM subject WHERE subject_code = %s LIMIT 1;", (code,))
        if cur.fetchone():
            valid.append(code)
    return valid


def build_where_and_params(pf) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []
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
    if pf.instructors:
        clauses.append("s.instructor ILIKE ANY(%s)")
        params.append([f"%{i}%" for i in pf.instructors])
    if pf.terms:
        clauses.append("s.term_label = ANY(%s)")
        params.append(pf.terms)
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
        clauses.append("COALESCE(s.section_graded_enrollment, s.graded_enrollment) >= %s")
        params.append(pf.enrollment_min)
    if getattr(pf, "enrollment_max", None) is not None:
        clauses.append("COALESCE(s.section_graded_enrollment, s.graded_enrollment) <= %s")
        params.append(pf.enrollment_max)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def execute_plan(plan: QueryPlan) -> Tuple[List[SectionInfo], Optional[List[SubjectInfo]], Aggregates]:
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

    try:
        if plan.intent == "course_lookup":
            pf = plan.filters.copy(deep=True)
            pf.subjects = filter_existing_subjects(cur, pf.subjects)
            pf.instructors = filter_existing_instructors(cur, pf.instructors)

            if not pf.subjects or not pf.course_numbers:
                aggregates = compute_aggregates(sections)
                return sections, subjects, aggregates

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
            pf.subjects = filter_existing_subjects(cur, pf.subjects)
            pf.instructors = filter_existing_instructors(cur, pf.instructors)
            where_sql, params = build_where_and_params(pf)
            if not where_sql:
                aggregates = compute_aggregates(sections)
                return sections, subjects, aggregates

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
        return sections, subjects, aggregates

    finally:
        cur.close()
        conn.close()
