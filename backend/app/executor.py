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


def execute_plan(plan: QueryPlan) -> Tuple[List[SectionInfo], Optional[List[SubjectInfo]], Aggregates]:
    """
    Execute a QueryPlan against the database.

    For now:
      - course_lookup: query v_grade_distribution_full for subject+course_number
      - browse_subjects: return subjects and no sections
    """
    conn = get_db_conn()
    cur = conn.cursor()

    sections: List[SectionInfo] = []
    subjects: Optional[List[SubjectInfo]] = None

    try:
        if plan.intent == "course_lookup":
            pf = plan.filters
            if not pf.subjects or not pf.course_numbers:
                # Parsed intent but missing concrete filters; just return empty.
                aggregates = compute_aggregates(sections)
                return sections, subjects, aggregates

            sql = """
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
                WHERE s.subject_code = %s AND s.course_number = %s
                ORDER BY s.term_id DESC, s.section_id;
            """
            cur.execute(sql, (pf.subjects[0], pf.course_numbers[0]))
            rows = cur.fetchall()

            for row in rows:
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

                section = SectionInfo(
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
                sections.append(section)

        elif plan.intent == "browse_subjects":
            cur.execute("SELECT subject_code, name FROM subject ORDER BY subject_code;")
            rows = cur.fetchall()
            subjects = [
                SubjectInfo(subject_code=r[0], name=r[1]) for r in rows
            ]

        # Future: handle "section_filter", "ranking_query" here

        aggregates = compute_aggregates(sections)
        return sections, subjects, aggregates

    finally:
        cur.close()
        conn.close()
