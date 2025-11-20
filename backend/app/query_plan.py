# query_plan.py
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class PlanFilters(BaseModel):
    subjects: List[str] = Field(default_factory=list)
    course_numbers: List[str] = Field(default_factory=list)
    instructors: List[str] = Field(default_factory=list)
    terms: List[str] = Field(default_factory=list)
    course_levels: List[str] = Field(default_factory=list)  # e.g., UG, GR

    course_number_min: Optional[int] = None
    course_number_max: Optional[int] = None
    gpa_min: Optional[float] = None
    gpa_max: Optional[float] = None
    credits_min: Optional[int] = None
    credits_max: Optional[int] = None
    enrollment_min: Optional[int] = None
    enrollment_max: Optional[int] = None


IntentType = Literal[
    "course_lookup",
    "browse_subjects",
    "section_filter",   # future
    "ranking_query",    # future
]


class QueryPlan(BaseModel):
    intent: IntentType
    filters: PlanFilters = Field(default_factory=PlanFilters)

    # Future-ready fields
    group_by: Optional[Literal["course", "instructor", "term"]] = None
    metric: Optional[str] = None
    sort_order: Optional[Literal["asc", "desc"]] = None
    limit: Optional[int] = None
    sort_by: Optional[Literal["gpa", "enrollment", "term"]] = None

    # For LLM / parser confidence later
    confidence: float = 1.0

    # For debug info we want to surface in meta.debug
    debug: Dict[str, Any] = Field(default_factory=dict)
