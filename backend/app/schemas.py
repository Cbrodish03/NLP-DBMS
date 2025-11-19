# schemas.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str


class QueryFilters(BaseModel):
    subjects: List[str] = Field(default_factory=list)
    course_numbers: List[str] = Field(default_factory=list)
    instructors: List[str] = Field(default_factory=list)
    terms: List[str] = Field(default_factory=list)
    course_levels: List[str] = Field(default_factory=list)

    course_number_min: Optional[int] = None
    course_number_max: Optional[int] = None
    gpa_min: Optional[float] = None
    gpa_max: Optional[float] = None
    credits_min: Optional[int] = None
    credits_max: Optional[int] = None
    enrollment_min: Optional[int] = None
    enrollment_max: Optional[int] = None


class QueryMeta(BaseModel):
    query: str
    intent: str
    confidence: float
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

    # Section-level info
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
    sections: List[SectionInfo] = Field(default_factory=list)
    aggregates: Aggregates
    subjects: Optional[List[SubjectInfo]] = None
    error: Optional[str] = None
