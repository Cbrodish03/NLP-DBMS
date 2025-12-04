// In production we route through ingress at /api; override with VITE_API_BASE_URL for local dev.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

type GradeBreakdown = Record<string, number | null | undefined>;

interface SectionData {
  section_id: number;
  graded_enrollment?: number | null;
  course: {
    subject_code?: string;
    course_number?: string;
    title?: string;
  };
  term: {
    label?: string;
  };
  instructor: {
    name_display?: string;
  };
  grades?: {
    gpa?: number | null;
    graded_enrollment?: number | null;
    breakdown?: GradeBreakdown;
  };
}

interface QueryApiResponse {
  ok: boolean;
  meta: QueryMeta;
  sections: SectionData[];
  error?: string;
}

export interface QueryFilters {
  subjects: string[];
  course_numbers: string[];
  instructors: string[];
  terms: string[];
  course_title_contains?: string[];
  course_levels: string[];
  grade_min?: Record<string, number>;
  grade_min_percent?: Record<string, number>;
  grade_max?: Record<string, number>;
  b_or_above_percent_min?: number | null;
  grade_compare?: Array<{ left: string; right: string; op: string }>;
  exclude_instructors?: string[];
  exclude_terms?: string[];
  // optional debug-resolved relative term info
  relative_term?: { season?: string; when?: string; resolved?: string };
  course_number_min?: number | null;
  course_number_max?: number | null;
  gpa_min?: number | null;
  gpa_max?: number | null;
  credits_min?: number | null;
  credits_max?: number | null;
  enrollment_min?: number | null;
  enrollment_max?: number | null;
}

export interface QueryMeta {
  query: string;
  intent: string;
  confidence: number;
  filters: QueryFilters;
  debug?: Record<string, unknown>;
}

export interface QueryResult {
  id: string;
  department: string;
  course_number: string;
  course_name: string;
  instructor: string;
  semester: string;
  total_students: number;
  gpa: number | null;
  b_or_above_percentage: number;
  b_or_above_count: number;
  grade_distribution: {
    a: number;
    a_minus: number;
    b_plus: number;
    b: number;
    b_minus: number;
    c_plus: number;
    c: number;
    c_minus: number;
    d_plus: number;
    d: number;
    d_minus: number;
    f: number;
  };
}

function normalizeGrades(breakdown?: GradeBreakdown) {
  const grades = breakdown || {};
  return {
    a: Number(grades["A"] ?? 0),
    a_minus: Number(grades["A-"] ?? 0),
    b_plus: Number(grades["B+"] ?? 0),
    b: Number(grades["B"] ?? 0),
    b_minus: Number(grades["B-"] ?? 0),
    c_plus: Number(grades["C+"] ?? 0),
    c: Number(grades["C"] ?? 0),
    c_minus: Number(grades["C-"] ?? 0),
    d_plus: Number(grades["D+"] ?? 0),
    d: Number(grades["D"] ?? 0),
    d_minus: Number(grades["D-"] ?? 0),
    f: Number(grades["F"] ?? 0),
  };
}

function mapSectionToResult(section: SectionData): QueryResult {
  const gradeDistribution = normalizeGrades(section.grades?.breakdown);
  const totalStudents =
    section.grades?.graded_enrollment ??
    section.graded_enrollment ??
    Object.values(gradeDistribution).reduce((acc, val) => acc + val, 0);
  const gpa = section.grades && typeof section.grades.gpa === "number" ? Number(section.grades.gpa) : null;

  const bOrAboveCount =
    gradeDistribution.a +
    gradeDistribution.a_minus +
    gradeDistribution.b_plus +
    gradeDistribution.b +
    gradeDistribution.b_minus;

  return {
    id: String(section.section_id),
    department: section.course?.subject_code || "",
    course_number: section.course?.course_number || "",
    course_name: section.course?.title || "",
    instructor: section.instructor?.name_display || "",
    semester: section.term?.label || "",
    total_students: totalStudents,
    gpa,
    b_or_above_percentage: totalStudents > 0 ? (bOrAboveCount / totalStudents) * 100 : 0,
    b_or_above_count: bOrAboveCount,
    grade_distribution: gradeDistribution,
  };
}

export interface ProcessedQueryResponse {
  results: QueryResult[];
  meta: QueryMeta;
}

export async function processQuery(query: string, parserMode: "regex" | "ai" = "regex"): Promise<ProcessedQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, parser_mode: parserMode }),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch results from the server");
  }

  const data: QueryApiResponse = await response.json();

  if (!data.ok) {
    throw new Error(data.error || "Query failed");
  }

  return {
    results: data.sections.map(mapSectionToResult),
    meta: data.meta,
  };
}
