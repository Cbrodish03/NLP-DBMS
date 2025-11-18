# query_plan.py
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel


class PlanFilters(BaseModel):
    subjects: List[str] = []
    course_numbers: List[str] = []
    instructors: List[str] = []
    terms: List[str] = []

    course_number_min: Optional[int] = None
    course_number_max: Optional[int] = None
    gpa_min: Optional[float] = None
    gpa_max: Optional[float] = None


IntentType = Literal[
    "course_lookup",
    "browse_subjects",
    "section_filter",   # future
    "ranking_query",    # future
]


class QueryPlan(BaseModel):
    intent: IntentType
    filters: PlanFilters = PlanFilters()

    # Future-ready fields
    group_by: Optional[Literal["course", "instructor", "term"]] = None
    metric: Optional[str] = None
    sort_order: Optional[Literal["asc", "desc"]] = None
    limit: Optional[int] = None

    # For LLM / parser confidence later
    confidence: float = 1.0

    # For debug info we want to surface in meta.debug
    debug: Dict[str, Any] = {}
