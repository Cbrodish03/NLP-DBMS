import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Filter, Info, RefreshCw, Bug, Clipboard, GitCompare } from 'lucide-react';
import QueryInput from '../components/QueryInput';
import ResultsTable from '../components/ResultsTable';
import {
  processQuery,
  type ProcessedQueryResponse,
  type QueryFilters,
  type QueryMeta,
  type QueryResult,
} from '../utils/queryProcessor';

type SortField = 'course' | 'instructor' | 'semester' | 'total_students' | 'threshold_percentage' | 'gpa';
type SortDirection = 'asc' | 'desc';

interface GradeDistribution {
  // NOTE: matches QueryResult.grade_distribution shape (no a_plus key)
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
}

export const CACHE_KEY = 'vt_last_query_state';

// --- Grade helpers shared across HomePage ---

type GradeLetter =
  | 'A+'
  | 'A'
  | 'A-'
  | 'B+'
  | 'B'
  | 'B-'
  | 'C+'
  | 'C'
  | 'C-'
  | 'D+'
  | 'D'
  | 'D-'
  | 'F';

const GRADE_ORDER: GradeLetter[] = [
  'A+',
  'A',
  'A-',
  'B+',
  'B',
  'B-',
  'C+',
  'C',
  'C-',
  'D+',
  'D',
  'D-',
  'F',
];

// Map A+ → 'a' so we don’t need an explicit a_plus field in the data
const GRADE_TO_KEY: Record<GradeLetter, keyof GradeDistribution> = {
  'A+': 'a',
  'A': 'a',
  'A-': 'a_minus',
  'B+': 'b_plus',
  'B': 'b',
  'B-': 'b_minus',
  'C+': 'c_plus',
  'C': 'c',
  'C-': 'c_minus',
  'D+': 'd_plus',
  'D': 'd',
  'D-': 'd_minus',
  'F': 'f',
};

// Standard 4.0-ish scale; tweak if you want to match VT’s internal scale more precisely
const GRADE_POINTS: Record<keyof GradeDistribution, number> = {
  a: 4.0,
  a_minus: 3.7,
  b_plus: 3.3,
  b: 3.0,
  b_minus: 2.7,
  c_plus: 2.3,
  c: 2.0,
  c_minus: 1.7,
  d_plus: 1.3,
  d: 1.0,
  d_minus: 0.7,
  f: 0.0,
};

function computeGpaFromDistribution(dist: GradeDistribution): number | null {
  let totalStudents = 0;
  let totalPoints = 0;

  (Object.keys(dist) as (keyof GradeDistribution)[]).forEach((key) => {
    const count = dist[key] ?? 0;
    const pts = GRADE_POINTS[key] ?? 0;
    totalStudents += count;
    totalPoints += count * pts;
  });

  if (!totalStudents) return null;
  return totalPoints / totalStudents;
}

function computeThresholdStats(
  result: QueryResult,
  threshold: GradeLetter,
): { count: number; pct: number } {
  const dist = result.grade_distribution as GradeDistribution;
  const thresholdIndex = GRADE_ORDER.indexOf(threshold);
  if (thresholdIndex === -1) return { count: 0, pct: 0 };

  let total = result.total_students ?? 0;
  if (!total || total <= 0) {
    // Fallback: recompute total from breakdown
    total = (Object.values(dist) as number[]).reduce((acc, v) => acc + (v ?? 0), 0);
  }
  if (!total) return { count: 0, pct: 0 };

  let count = 0;
  for (let i = 0; i <= thresholdIndex; i++) {
    const label = GRADE_ORDER[i];
    const key = GRADE_TO_KEY[label];
    count += dist[key] ?? 0;
  }
  const pct = (count / total) * 100;
  return { count, pct };
}

// --- Extra types for editable chips ---

type ChipKind = 'subject' | 'instructor' | 'term' | 'other';

interface Chip {
  label: string;
  kind: ChipKind;
}

interface ActiveFilters {
  subject?: string;
  instructor?: string;
  term?: string;
}

// --- Component ---

export default function HomePage() {
  const navigate = useNavigate();

  // Raw results from backend (always the full set for this query)
  const [baseResults, setBaseResults] = useState<QueryResult[]>([]);
  // Currently displayed results (after any client-side chip filtering)
  const [results, setResults] = useState<QueryResult[]>([]);

  const [filters, setFilters] = useState<QueryFilters | null>(null);
  const [meta, setMeta] = useState<QueryMeta | null>(null);
  const [lastQuery, setLastQuery] = useState<string>('');

  // DEFAULT: sort by GPA desc
  const [sortField, setSortField] = useState<SortField>('gpa');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Parser mode (regex vs ai)
  const [parserMode, setParserMode] = useState<'regex' | 'ai'>('regex');

  // Grade threshold for "grade and above" column
  const [gradeThreshold, setGradeThreshold] = useState<GradeLetter>('B');

  // Active client-side filters that come from editable chips
  const [activeFilters, setActiveFilters] = useState<ActiveFilters>({});

  // AI / GPT explanation of the query
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  // Helper: apply client-side filters to baseResults
  const applyActiveFilters = (data: QueryResult[], af: ActiveFilters): QueryResult[] => {
    return data.filter((r) => {
      if (af.subject && r.department !== af.subject) return false;
      if (af.instructor && r.instructor !== af.instructor) return false;
      if (af.term && r.semester !== af.term) return false;
      return true;
    });
  };

  const handleSearch = async (query: string, modeOverride?: 'regex' | 'ai') => {
    const mode = modeOverride ?? parserMode;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    setPage(1);
    setCopied(false);
    setLastQuery(query);
    setSelectedIds([]);
    setParserMode(mode); // remember which mode we just used
    setActiveFilters({}); // reset chip-based filters on new search
    setAiResponse(null); // reset previous AI explanation

    try {
      const data: ProcessedQueryResponse = await processQuery(query, mode);
      setBaseResults(data.results);
      setResults(data.results); // show full backend results initially
      setFilters(data.meta?.filters ?? null);
      setMeta(data.meta ?? null);

      // Try to pull an AI/GPT explanation out of meta.debug
      const debug = data.meta?.debug as any;
      const possibleAi =
        debug?.llm_response ??
        debug?.ai_response ??
        debug?.llm_explanation ??
        debug?.raw_llm_output;

      if (typeof possibleAi === 'string' && possibleAi.trim().length > 0) {
        setAiResponse(possibleAi);
      } else {
        setAiResponse(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setBaseResults([]);
      setResults([]);
      setFilters(null);
      setMeta(null);
      setAiResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedCourses = useMemo(
    () => results.filter((course) => selectedIds.includes(course.id)),
    [results, selectedIds],
  );

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((existing) => existing !== id) : [...prev, id]));
  };

  const handleClearSelection = () => setSelectedIds([]);

  const handleCompare = () => {
    if (selectedCourses.length < 2) return;
    navigate('/compare', { state: { courses: selectedCourses } });
  };

  const handleCompareAll = () => {
    if (sortedResults.length < 2) return;
    const allIds = sortedResults.map((course) => course.id);
    setSelectedIds(allIds);
    navigate('/compare', { state: { courses: sortedResults } });
  };

  // Distinct values from the current backend result set, used for dropdown options
  const allSubjects = useMemo(
    () => Array.from(new Set(baseResults.map((r) => r.department))).sort(),
    [baseResults],
  );

  const allInstructors = useMemo(
    () =>
      Array.from(
        new Set(
          baseResults
            .map((r) => r.instructor)
            .filter((name) => !!name && name.trim().length > 0),
        ),
      ).sort(),
    [baseResults],
  );

  const allTerms = useMemo(
    () =>
      Array.from(
        new Set(
          baseResults
            .map((r) => r.semester)
            .filter((t) => !!t && t.trim().length > 0),
        ),
      ).sort(),
    [baseResults],
  );

  // Build parsed-filter chips with metadata about what kind they are
  const chips = useMemo(() => {
    if (!filters) return [];
    const chipList: Chip[] = [];

    filters.subjects?.forEach((s) => chipList.push({ label: `Subject: ${s}`, kind: 'subject' }));
    filters.course_numbers?.forEach((c) => chipList.push({ label: `Course: ${c}`, kind: 'other' }));
    if (filters.course_number_min != null || filters.course_number_max != null) {
      chipList.push({
        label: `Course range: ${filters.course_number_min ?? 'Any'}–${filters.course_number_max ?? 'Any'}`,
        kind: 'other',
      });
    }
    if (filters.gpa_min != null) chipList.push({ label: `GPA ≥ ${filters.gpa_min}`, kind: 'other' });
    if (filters.gpa_max != null) chipList.push({ label: `GPA ≤ ${filters.gpa_max}`, kind: 'other' });
    filters.instructors?.forEach((name) => chipList.push({ label: `Instructor: ${name}`, kind: 'instructor' }));
    filters.terms?.forEach((t) => chipList.push({ label: `Term: ${t}`, kind: 'term' }));
    if (filters.grade_min) {
      Object.entries(filters.grade_min).forEach(([grade, count]) => {
        chipList.push({ label: `${count}+ ${grade}`, kind: 'other' });
      });
    }
    if (filters.grade_min_percent) {
      Object.entries(filters.grade_min_percent).forEach(([grade, pct]) => {
        chipList.push({ label: `${pct}% ${grade}`, kind: 'other' });
      });
    }
    if (filters.b_or_above_percent_min != null) {
      chipList.push({ label: `${filters.b_or_above_percent_min}% B or above`, kind: 'other' });
    }
    if (filters.grade_max) {
      Object.entries(filters.grade_max).forEach(([grade, max]) => {
        chipList.push({ label: `Max ${max} ${grade}`, kind: 'other' });
      });
    }
    if (filters.grade_compare) {
      filters.grade_compare.forEach((cmp) => {
        if (cmp.left && cmp.right && cmp.op) {
          chipList.push({ label: `${cmp.left} ${cmp.op} ${cmp.right}`, kind: 'other' });
        }
      });
    }
    if (filters.exclude_instructors) {
      filters.exclude_instructors.forEach((name) =>
        chipList.push({ label: `Exclude instructor: ${name}`, kind: 'other' }),
      );
    }
    if (filters.exclude_terms) {
      filters.exclude_terms.forEach((t) => chipList.push({ label: `Exclude term: ${t}`, kind: 'other' }));
    }
    if ((filters as any).relative_term?.resolved) {
      chipList.push({
        label: `Term: ${(filters as any).relative_term.resolved}`,
        kind: 'term',
      });
    }
    if (filters.course_title_contains) {
      filters.course_title_contains.forEach((t) => chipList.push({ label: `Title contains: ${t}`, kind: 'other' }));
    }
    const rank = (meta?.debug as any)?.rank_enrollment;
    if (rank?.limit) {
      chipList.push({
        label: `${rank.order === 'ASC' ? 'Smallest' : 'Largest'} ${rank.limit} by enrollment`,
        kind: 'other',
      });
    }
    if (filters.credits_min != null || filters.credits_max != null) {
      chipList.push({
        label: `Credits: ${filters.credits_min ?? 'Any'}–${filters.credits_max ?? 'Any'}`,
        kind: 'other',
      });
    }
    if (filters.enrollment_min != null || filters.enrollment_max != null) {
      chipList.push({
        label: `Enrollment: ${filters.enrollment_min ?? 'Any'}–${filters.enrollment_max ?? 'Any'}`,
        kind: 'other',
      });
    }
    return chipList;
  }, [filters, meta]);

  const sortedResults = useMemo(() => {
    const sorted = [...results];
    sorted.sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1;
      switch (sortField) {
        case 'course':
          return dir * `${a.department} ${a.course_number}`.localeCompare(`${b.department} ${b.course_number}`);
        case 'instructor':
          return dir * (a.instructor || '').localeCompare(b.instructor || '');
        case 'semester':
          return dir * (a.semester || '').localeCompare(b.semester || '');
        case 'gpa': {
          const gpaA = computeGpaFromDistribution(a.grade_distribution as GradeDistribution) ?? 0;
          const gpaB = computeGpaFromDistribution(b.grade_distribution as GradeDistribution) ?? 0;
          return dir * (gpaA - gpaB);
        }
        case 'total_students':
          return dir * ((a.total_students ?? 0) - (b.total_students ?? 0));
        case 'threshold_percentage':
        default: {
          const pctA = computeThresholdStats(a, gradeThreshold).pct;
          const pctB = computeThresholdStats(b, gradeThreshold).pct;
          return dir * (pctA - pctB);
        }
      }
    });
    return sorted;
  }, [results, sortDirection, sortField, gradeThreshold]);

  const totalPages = Math.max(1, Math.ceil(sortedResults.length / pageSize));
  const paginatedResults = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedResults.slice(start, start + pageSize);
  }, [sortedResults, page, pageSize]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'course' || field === 'instructor' || field === 'semester' ? 'asc' : 'desc');
    }
    setPage(1);
  };

  const handlePageChange = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages) return;
    setPage(nextPage);
  };

  // Handle changing a filter via chip dropdown
  const handleChipFilterChange = (kind: ChipKind, value: string) => {
    if (kind === 'other') return;

    setActiveFilters((prev) => {
      const next: ActiveFilters = { ...prev };
      if (kind === 'subject') {
        next.subject = value;
      } else if (kind === 'instructor') {
        next.instructor = value;
      } else if (kind === 'term') {
        next.term = value;
      }
      const newResults = applyActiveFilters(baseResults, next);
      setResults(newResults);
      setPage(1);
      setSelectedIds([]);
      return next;
    });
  };

  // Restore cached state on mount for smoother back-navigation from detail pages.
  useEffect(() => {
    const cached = sessionStorage.getItem(CACHE_KEY);
    if (!cached) return;
    try {
      const data = JSON.parse(cached);
      if (data.results) {
        setResults(data.results);
        setBaseResults(data.results); // treat cached results as base for this session
      }
      if (data.filters) setFilters(data.filters);
      if (data.meta) setMeta(data.meta);
      if (data.lastQuery) setLastQuery(data.lastQuery);
      if (data.sortField) setSortField(data.sortField);
      if (data.sortDirection) setSortDirection(data.sortDirection);
      if (data.page) setPage(data.page);
      if (data.pageSize) setPageSize(data.pageSize);
      if (data.hasSearched) setHasSearched(data.hasSearched);
      if (data.selectedIds || data.selectedCourseIds) {
        setSelectedIds(data.selectedIds ?? data.selectedCourseIds ?? []);
      }
      if (data.parserMode) setParserMode(data.parserMode);
      if (data.gradeThreshold) setGradeThreshold(data.gradeThreshold);
      if (typeof data.aiResponse === 'string') setAiResponse(data.aiResponse);
      // We don't persist activeFilters; new session starts with raw results.
    } catch {
      // ignore parse errors
    }
  }, []);

  // Persist state so returning from detail keeps results visible.
  useEffect(() => {
    if (!hasSearched) return;
    const payload = {
      results,
      filters,
      meta,
      lastQuery,
      sortField,
      sortDirection,
      page,
      pageSize,
      hasSearched,
      selectedIds,
      parserMode,
      gradeThreshold,
      aiResponse,
    };
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload));
  }, [
    results,
    filters,
    meta,
    lastQuery,
    sortField,
    sortDirection,
    page,
    pageSize,
    hasSearched,
    selectedIds,
    parserMode,
    gradeThreshold,
    aiResponse,
  ]);

  const handleCopyDebug = () => {
    if (!meta) return;
    const payload = JSON.stringify({ meta, result_count: results.length }, null, 2);
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(payload).then(() => setCopied(true));
    } else {
      setCopied(false);
    }
  };

  const unrecognizedTokens = useMemo(() => {
    const filtered = (meta?.debug as any)?.filtered_out;
    if (!filtered) return [];
    const tokens: string[] = [];
    if (Array.isArray(filtered.subjects)) tokens.push(...filtered.subjects);
    if (Array.isArray(filtered.instructors)) tokens.push(...filtered.instructors);
    if (Array.isArray(filtered.course_title_contains)) {
      // Ignore dropped title tokens to avoid noise.
    }

    // Drop tokens that are already represented in successful filters (e.g., "gpa" when gpa_min is set).
    const recognized = new Set<string>();
    if (filters?.subjects) filters.subjects.forEach((s) => recognized.add(s.toLowerCase()));
    if (filters?.course_numbers) filters.course_numbers.forEach((c) => recognized.add(String(c).toLowerCase()));
    if (filters?.instructors) filters.instructors.forEach((i) => recognized.add(i.toLowerCase()));
    if (filters?.terms) filters.terms.forEach((t) => recognized.add(t.toLowerCase()));
    if (filters?.gpa_min != null || filters?.gpa_max != null) recognized.add('gpa');
    if (filters?.credits_min != null || filters?.credits_max != null) recognized.add('credits');
    if (filters?.enrollment_min != null || filters?.enrollment_max != null) recognized.add('enrollment');
    if (filters?.grade_min) {
      Object.keys(filters.grade_min).forEach((g) => recognized.add(g.toLowerCase()));
    }
    if (filters?.grade_min_percent) {
      Object.keys(filters.grade_min_percent).forEach((g) => recognized.add(g.toLowerCase()));
    }
    if (filters?.b_or_above_percent_min != null) {
      recognized.add('b');
    }
    if (filters?.grade_max) {
      Object.keys(filters.grade_max).forEach((g) => recognized.add(g.toLowerCase()));
    }
    if (filters?.exclude_instructors) {
      filters.exclude_instructors.forEach((i) => {
        const lower = i.toLowerCase();
        recognized.add(lower);
        recognized.add(`not ${lower}`);
      });
    }
    if (filters?.exclude_terms) {
      filters.exclude_terms.forEach((t) => recognized.add(t.toLowerCase()));
    }
    if (filters?.enrollment_min != null || filters?.enrollment_max != null) {
      recognized.add('between');
      recognized.add('enrollment');
      recognized.add('students');
    }
    if (filters?.course_title_contains) {
      filters.course_title_contains.forEach((t) => recognized.add(t.toLowerCase()));
      recognized.add('title');
      recognized.add('course');
    }
    const rank = (meta?.debug as any)?.rank_enrollment;
    if (rank?.limit) {
      recognized.add('largest');
      recognized.add('smallest');
      recognized.add('biggest');
      recognized.add('most');
    }
    recognized.add('least');
    recognized.add('at');
    recognized.add('most');
    recognized.add('more');
    recognized.add('less');
    recognized.add('fewer');

    return tokens.filter((t) => !recognized.has(String(t).toLowerCase()));
  }, [meta, filters]);

  const handleSendToAssistant = () => {
    if (!meta?.query) return;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(meta.query);
      setCopied(true);
    }
  };

  // Helper for chip dropdown options
  const getOptionsForChipKind = (kind: ChipKind): string[] => {
    if (kind === 'subject') return allSubjects;
    if (kind === 'instructor') return allInstructors;
    if (kind === 'term') return allTerms;
    return [];
  };

  const isOptionActive = (kind: ChipKind, value: string): boolean => {
    if (kind === 'subject') return activeFilters.subject === value;
    if (kind === 'instructor') return activeFilters.instructor === value;
    if (kind === 'term') return activeFilters.term === value;
    return false;
  };

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-[#fdf6ec] via-[#f7ece1] to-[#f9f5f1]">
        <div className="container mx-auto px-4 py-12">
          <div className="flex flex-col items-center">
            <div className="flex items-center gap-3 mb-4">
              <BookOpen size={40} className="text-[#861f41]" />
              <h1 className="text-4xl font-bold text-[#3b0d1f]">Virginia Tech Grade Distribution Query</h1>
            </div>

            <p className="text-[#5b3a2c] mb-4 text-center max-w-2xl">
              Search courses with natural language. Choose fast regex parsing or AI-assisted parsing when needed.
            </p>

            {/* Parser mode toggle */}
            <div className="w-full max-w-4xl mb-4 flex flex-wrap items-center justify-center gap-2 text-sm">
              <span className="text-[#7a5a46]">Parser mode:</span>
              <button
                type="button"
                onClick={() => setParserMode('regex')}
                className={`px-3 py-1.5 rounded-full border ${
                  parserMode === 'regex'
                    ? 'bg-[#861f41] text-white border-[#861f41]'
                    : 'bg-white text-[#3b0d1f] border-[#f2cbb3]'
                }`}
              >
                Regex (fast, default)
              </button>
              <button
                type="button"
                onClick={() => setParserMode('ai')}
                className={`px-3 py-1.5 rounded-full border ${
                  parserMode === 'ai'
                    ? 'bg-[#861f41] text-white border-[#861f41]'
                    : 'bg-white text-[#3b0d1f] border-[#f2cbb3]'
                }`}
              >
                AI (ChatGPT)
              </button>
            </div>

            <QueryInput
              onSearch={(q) => {
                void handleSearch(q);
              }}
              isLoading={isLoading}
              initialValue={lastQuery}
            />

            {isLoading && (
              <div className="mt-8 text-[#5b3a2c]">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#e87722] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-[#e87722] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-[#e87722] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}

            {error && (
              <div className="mt-8 w-full max-w-4xl p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            {!isLoading && hasSearched && (
              <div className="w-full max-w-6xl mt-8 space-y-4">
                {/* AI / GPT response card */}
                {aiResponse && (
                  <div className="bg-white border border-[#f2cbb3] rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#3b0d1f] mb-2">
                      <Info size={16} className="text-[#e87722]" />
                      AI interpretation
                    </div>
                    <p className="text-sm text-[#5b3a2c] whitespace-pre-wrap">
                      {aiResponse}
                    </p>
                  </div>
                )}

                {chips.length > 0 && (
                  <div className="bg-white border border-[#f2cbb3] rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#3b0d1f] mb-3">
                      <Filter size={16} className="text-[#e87722]" />
                      Parsed filters
                    </div>
                    <div className="flex flex-wrap gap-2 relative">
                      {chips.map((chip, idx) => {
                        const options = getOptionsForChipKind(chip.kind);
                        const interactive = options.length > 0;

                        return (
                          <div key={`${chip.label}-${idx}`} className="relative group">
                            <button
                              type="button"
                              className={`px-3 py-1 rounded-full border text-sm ${
                                interactive
                                  ? 'bg-[#fce9dd] text-[#7a102d] border-[#f2cbb3] cursor-pointer'
                                  : 'bg-[#fce9dd] text-[#7a102d] border-[#f2cbb3] cursor-default'
                              }`}
                            >
                              {chip.label}
                            </button>
                            {interactive && (
                              <div className="absolute z-20 mt-1 hidden group-hover:block min-w-[200px] bg-white border border-[#f2cbb3] rounded-lg shadow-lg">
                                <div className="px-3 py-2 text-xs text-[#7a5a46] border-b border-[#f2cbb3]">
                                  Choose {chip.kind} to refine results
                                </div>
                                <ul className="max-h-56 overflow-y-auto text-sm">
                                  {options.map((opt) => {
                                    const active = isOptionActive(chip.kind, opt);
                                    return (
                                      <li key={opt}>
                                        <button
                                          type="button"
                                          onClick={() => handleChipFilterChange(chip.kind, opt)}
                                          className={`w-full text-left px-3 py-2 hover:bg-[#fce9dd] ${
                                            active ? 'bg-[#fce9dd] font-semibold text-[#7a102d]' : 'text-[#3b0d1f]'
                                          }`}
                                        >
                                          {opt}
                                        </button>
                                      </li>
                                    );
                                  })}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-xs text-[#7a5a46]">
                      <Info size={14} className="text-[#e87722]" />
                      Hover a filter chip to adjust subjects, instructors, or terms. Edit the query for deeper changes.
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center gap-2 text-sm text-[#7a5a46]">
                    <RefreshCw size={14} className="text-[#e87722]" />
                    <span>Sort and paginate locally for quick browsing.</span>
                  </div>
                  <div className="flex flex-wrap gap-2 items-center text-sm">
                    {sortedResults.length > 1 && (
                      <button
                        onClick={handleCompareAll}
                        className="px-3 py-1.5 rounded-lg bg-[#861f41] text-white hover:bg-[#6f1936] transition-colors"
                      >
                        Compare all
                      </button>
                    )}

                    {/* Threshold selector */}
                    <label className="text-[#7a5a46]">Threshold grade</label>
                    <select
                      value={gradeThreshold}
                      onChange={(e) => setGradeThreshold(e.target.value as GradeLetter)}
                      className="border border-[#f2cbb3] rounded-lg px-3 py-1.5 text-[#3b0d1f] bg-white"
                    >
                      {GRADE_ORDER.map((g) => (
                        <option key={g} value={g}>
                          {g}
                        </option>
                      ))}
                    </select>

                    <label className="text-[#7a5a46]">Sort by</label>
                    <select
                      value={sortField}
                      onChange={(e) => handleSort(e.target.value as SortField)}
                      className="border border-[#f2cbb3] rounded-lg px-3 py-1.5 text-[#3b0d1f] bg-white"
                    >
                      <option value="gpa">Avg GPA</option>
                      <option value="threshold_percentage">Grade ≥ {gradeThreshold} %</option>
                      <option value="total_students">Students</option>
                      <option value="course">Course</option>
                      <option value="instructor">Instructor</option>
                      <option value="semester">Term</option>
                    </select>
                    <button
                      onClick={() => handleSort(sortField)}
                      className="px-3 py-1.5 border border-[#f2cbb3] rounded-lg bg-white text-[#3b0d1f]"
                    >
                      {sortDirection === 'asc' ? 'Asc' : 'Desc'}
                    </button>
                    <label className="text-[#7a5a46] ml-2">Page size</label>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setPage(1);
                      }}
                      className="border border-[#f2cbb3] rounded-lg px-3 py-1.5 text-[#3b0d1f] bg-white"
                    >
                      {[5, 10, 20, 50].map((size) => (
                        <option key={size} value={size}>
                          {size}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {unrecognizedTokens.length > 0 && (
                  <div className="bg-white border border-[#f2cbb3] rounded-xl p-4 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm font-semibold text-[#3b0d1f]">Unrecognized parts of your query</div>
                      <button
                        onClick={handleSendToAssistant}
                        className="text-xs px-3 py-1 rounded-lg border border-[#f2cbb3] bg-white text-[#3b0d1f]"
                      >
                        Send to assistant
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2 text-sm text-[#7a5a46]">
                      {unrecognizedTokens.map((t) => (
                        <span
                          key={t}
                          className="px-3 py-1 bg-[#fce9dd] text-[#7a102d] rounded-full border border-[#f2cbb3]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <ResultsTable
                  results={paginatedResults}
                  totalCount={sortedResults.length}
                  page={page}
                  pageSize={pageSize}
                  onPageChange={handlePageChange}
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  selectedIds={selectedIds}
                  onToggleSelect={handleToggleSelect}
                  thresholdGrade={gradeThreshold}
                  onRetryWithAI={
                    lastQuery && parserMode === 'regex'
                      ? () => {
                          if (!lastQuery) return;
                          void handleSearch(lastQuery, 'ai');
                        }
                      : undefined
                  }
                />

                {meta && (
                  <div className="bg-white border border-[#f2cbb3] rounded-xl p-4 shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-semibold text-[#3b0d1f]">
                        <Bug size={16} className="text-[#e87722]" />
                        Debug (dev only)
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setShowDebug((prev) => !prev)}
                          className="text-xs px-3 py-1 rounded-lg border border-[#f2cbb3] bg-white text-[#3b0d1f]"
                        >
                          {showDebug ? 'Hide' : 'Show'}
                        </button>
                        <button
                          onClick={handleCopyDebug}
                          className="text-xs px-3 py-1 rounded-lg border border-[#f2cbb3] bg-white text-[#3b0d1f] flex items-center gap-1"
                        >
                          <Clipboard size={12} />
                          Copy
                        </button>
                        {copied && <span className="text-xs text-[#7a5a46]">Copied</span>}
                      </div>
                    </div>
                    {showDebug && (
                      <pre className="mt-2 text-xs bg-[#fdf6ec] border border-[#f2cbb3] rounded-lg p-3 overflow-auto max-h-72 text-[#3b0d1f]">
                        {JSON.stringify({ meta, result_count: results.length }, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {selectedCourses.length > 0 && (
        <div className="fixed right-4 bottom-4 md:top-24 md:bottom-auto w-[340px] max-w-[90vw] bg-white border border-[#f2cbb3] rounded-2xl shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-[#fdf6ec] border-b border-[#f2cbb3]">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#3b0d1f]">
              <GitCompare size={16} className="text-[#861f41]" />
              {selectedCourses.length} selected for comparison
            </div>
            <button onClick={handleClearSelection} className="text-xs text-[#861f41] underline">
              Clear
            </button>
          </div>

          <div className="max-h-[60vh] overflow-y-auto divide-y divide-[#f2cbb3]">
            {selectedCourses.map((course) => (
              <div key={course.id} className="px-4 py-3 flex items-start gap-3">
                <div className="flex-1">
                  <div className="font-semibold text-[#3b0d1f]">
                    {course.department} {course.course_number} · {course.course_name}
                  </div>
                  <div className="text-xs text-[#7a5a46]">
                    {course.instructor || 'Instructor TBA'} · {course.semester || 'Term TBD'} · Section {course.id}
                  </div>
                </div>
                <button onClick={() => handleToggleSelect(course.id)} className="text-xs text-[#861f41] underline">
                  Remove
                </button>
              </div>
            ))}
          </div>

          <div className="px-4 py-3 flex flex-col gap-2 bg-[#fdf6ec] border-t border-[#f2cbb3]">
            {selectedCourses.length < 2 && (
              <div className="text-xs text-[#7a5a46]">Select at least two classes to enable comparison.</div>
            )}
            <button
              onClick={handleCompare}
              disabled={selectedCourses.length < 2}
              className="w-full px-3 py-2 rounded-lg bg-[#861f41] text-white text-sm hover:bg-[#6f1936] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Compare classes
            </button>
          </div>
        </div>
      )}
    </>
  );
}
