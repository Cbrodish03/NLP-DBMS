import os
import re
from decimal import Decimal
from typing import List, Dict, Any, Optional

import spacy
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

app = FastAPI(title="VT UDC NLP API")

# CORS: frontend runs at http://localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB helper ----------

def get_db_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "nlp"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )

# ---------- Models (API contract) ----------

class QueryRequest(BaseModel):
    query: str

class QueryFilters(BaseModel):
    subjects: List[str] = []
    course_numbers: List[str] = []
    instructors: List[str] = []
    terms: List[str] = []
    # room to grow for more complex filters
    course_number_min: Optional[int] = None
    course_number_max: Optional[int] = None
    gpa_min: Optional[float] = None
    gpa_max: Optional[float] = None

class QueryMeta(BaseModel):
    query: str
    intent: str
    filters: QueryFilters
    debug: Dict[str, Any]

class CourseInfo(BaseModel):
    course_id: Optional[int] = None
    subject_code: str
    subject_name: Optional[str] = None
    course_number: str
    title: Optional[str] = None
    credits: Optional[int] = None
    level: Optional[str] = None

class TermInfo(BaseModel):
    term_id: int
    label: str
    academic_year: Optional[str] = None

class InstructorInfo(BaseModel):
    instructor_id: int
    name_display: str

class SectionGrades(BaseModel):
    gpa: Optional[float]
    graded_enrollment: int
    withdraws: int
    breakdown: Dict[str, int]

class SectionInfo(BaseModel):
    section_id: int
    course_id: int
    term_id: int
    instructor_id: int
    # section-level numbers (credits / enrollment from section table)
    credits: Optional[int]
    graded_enrollment: Optional[int]
    course: CourseInfo
    term: TermInfo
    instructor: InstructorInfo
    grades: SectionGrades

class Aggregates(BaseModel):
    section_count: int
    avg_gpa: Optional[float]
    total_graded_enrollment: int

class SubjectInfo(BaseModel):
    subject_code: str
    name: Optional[str] = None

class QueryResponse(BaseModel):
    ok: bool
    meta: QueryMeta
    sections: List[SectionInfo] = []
    aggregates: Aggregates
    subjects: Optional[List[SubjectInfo]] = None
    error: Optional[str] = None

# ---------- Utility helpers ----------

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

# ---------- Routes ----------

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

@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Unified query endpoint.

    For now:
    - If we find SUBJECT + 4-digit number, treat as course lookup.
    - Otherwise, fallback to browse_subjects.
    """
    doc = nlp(req.query)
    tokens = [t.text for t in doc]
    text_up = req.query.upper()

    # Regex: CS 2104, MATH 1224, etc.
    m = re.search(r"\b([A-Z]{2,4})\s*([0-9]{4})\b", text_up)

    filters = QueryFilters()
    debug: Dict[str, Any] = {"tokens": tokens}

    if m:
        subject_code, course_number = m.group(1), m.group(2)
        filters.subjects = [subject_code]
        filters.course_numbers = [course_number]
        debug["regex_match"] = {
            "subject_code": subject_code,
            "course_number": course_number,
        }
        intent = "course_lookup"
    else:
        intent = "browse_subjects"

    meta = QueryMeta(
        query=req.query,
<<<<<<< Updated upstream
        intent=intent,
=======
        confidence=plan.confidence,
        intent=plan.intent,
>>>>>>> Stashed changes
        filters=filters,
        debug=debug,
    )

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        sections: List[SectionInfo] = []
        subjects: Optional[List[SubjectInfo]] = None

        if intent == "course_lookup":
            # Pull everything from the v_grade_distribution_full view
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
            cur.execute(sql, (filters.subjects[0], filters.course_numbers[0]))
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

        else:
            # browse_subjects fallback
            cur.execute(
                "SELECT subject_code, name FROM subject ORDER BY subject_code;"
            )
            rows = cur.fetchall()
            subjects = [
                SubjectInfo(subject_code=r[0], name=r[1])
                for r in rows
            ]

        cur.close()
        conn.close()

        aggregates = compute_aggregates(sections)

        return QueryResponse(
            ok=True,
            meta=meta,
            sections=sections,
            aggregates=aggregates,
            subjects=subjects,
        )

    except Exception as e:
        return QueryResponse(
            ok=False,
            meta=meta,
            sections=[],
            aggregates=Aggregates(
                section_count=0,
                avg_gpa=None,
                total_graded_enrollment=0,
            ),
            subjects=None,
            error=str(e),
        )
