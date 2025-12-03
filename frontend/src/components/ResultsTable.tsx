import { TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { QueryResult } from '../utils/queryProcessor';

type SortField = 'course' | 'instructor' | 'semester' | 'total_students' | 'threshold_percentage' | 'gpa';

interface GradeDistribution {
  a_plus: number;
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

interface ResultsTableProps {
  results: QueryResult[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  sortField: SortField;
  sortDirection: 'asc' | 'desc';
  onSort: (field: SortField) => void;
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  thresholdGrade: GradeLetter;
  onRetryWithAI?: () => void;
}

const SortLabel = ({
  label,
  field,
  activeField,
  direction,
  onClick,
}: {
  label: string;
  field: SortField;
  activeField: SortField;
  direction: 'asc' | 'desc';
  onClick: (f: SortField) => void;
}) => {
  const isActive = field === activeField;
  return (
    <button
      type="button"
      onClick={() => onClick(field)}
      className={`flex items-center gap-1 ${isActive ? 'text-[#861f41]' : 'text-gray-700'}`}
    >
      <span className="text-sm font-semibold">{label}</span>
      {isActive && <span className="text-xs">{direction === 'asc' ? '▲' : '▼'}</span>}
    </button>
  );
};

// ---- Same helpers as in HomePage ----

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

const GRADE_TO_KEY: Record<GradeLetter, keyof GradeDistribution> = {
  'A+': 'a_plus',
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

const GRADE_POINTS: Record<keyof GradeDistribution, number> = {
  a_plus: 4.0,
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
  const dist = result.grade_distribution;
  const thresholdIndex = GRADE_ORDER.indexOf(threshold);
  if (thresholdIndex === -1) return { count: 0, pct: 0 };

  let total = result.total_students ?? 0;
  if (!total || total <= 0) {
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

// ---- Component ----

export default function ResultsTable({
  results,
  totalCount,
  page,
  pageSize,
  onPageChange,
  sortField,
  sortDirection,
  onSort,
  selectedIds,
  onToggleSelect,
  thresholdGrade,
  onRetryWithAI,
}: ResultsTableProps) {
  const navigate = useNavigate();

  const gpaColor = (gpa: number | null | undefined) => {
    if (gpa == null) return 'bg-gray-100 text-gray-600';
    if (gpa >= 3.5) return 'bg-green-100 text-green-700';
    if (gpa >= 3.0) return 'bg-emerald-50 text-emerald-700';
    if (gpa >= 2.5) return 'bg-yellow-50 text-yellow-700';
    return 'bg-red-50 text-red-700';
  };

  if (results.length === 0) {
    return (
      <div className="w-full max-w-6xl mt-8 p-8 bg-white rounded-xl shadow-sm text-center text-gray-500">
        <p>No courses found matching your query. Try a different search.</p>
        {onRetryWithAI && (
          <button
            type="button"
            onClick={onRetryWithAI}
            className="mt-4 inline-flex items-center justify-center px-4 py-2 rounded-lg bg-[#861f41] text-white text-sm hover:bg-[#6f1936] transition-colors"
          >
            Retry with AI parsing
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mt-8 bg-white rounded-xl shadow-lg overflow-hidden border border-[#f2cbb3]">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-4 text-center text-sm font-semibold text-gray-700">Compare</th>
              <th className="px-6 py-4 text-left">
                <SortLabel
                  label="Course"
                  field="course"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-left">
                <SortLabel
                  label="Instructor"
                  field="instructor"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-left">
                <SortLabel
                  label="Semester"
                  field="semester"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-center">
                <SortLabel
                  label="Students"
                  field="total_students"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-center">
                <SortLabel
                  label="Avg GPA"
                  field="gpa"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-center">
                <SortLabel
                  label={`Grade ≥ ${thresholdGrade}`}
                  field="threshold_percentage"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Grade Distribution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {results.map((result) => {
              const gpa = computeGpaFromDistribution(result.grade_distribution);
              const { count: thresholdCount, pct: thresholdPct } = computeThresholdStats(
                result,
                thresholdGrade,
              );

              return (
                <tr
                  key={result.id}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/course/${result.id}`, { state: result })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(`/course/${result.id}`, { state: result });
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <td className="px-4 py-4 text-center" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(result.id)}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                      onChange={() => onToggleSelect(result.id)}
                      className="h-4 w-4 accent-[#861f41] cursor-pointer"
                      aria-label={`Select ${result.department} ${result.course_number} for comparison`}
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-semibold text-gray-900">
                      {result.department} {result.course_number}
                    </div>
                    <div className="text-sm text-gray-600">{result.course_name}</div>
                    <div className="text-xs text-gray-500 mt-1">Section {result.id}</div>
                  </td>
                  <td className="px-6 py-4 text-gray-700">{result.instructor}</td>
                  <td className="px-6 py-4 text-gray-700">{result.semester}</td>
                  <td className="px-6 py-4 text-center text-gray-700">{result.total_students}</td>
                  <td className="px-6 py-4 text-center">
                    <span className={`inline-flex px-2 py-1 rounded-full text-sm font-semibold ${gpaColor(gpa)}`}>
                      {gpa != null ? gpa.toFixed(2) : '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <div className="flex items-center gap-1 text-green-600 font-semibold">
                        <TrendingUp size={16} />
                        {thresholdPct.toFixed(1)}%
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 text-center mt-1">
                      ({thresholdCount} students)
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="grid grid-cols-6 gap-1 text-xs">
                      {[
                        { label: 'A', value: result.grade_distribution.a, color: 'bg-green-100 text-green-700' },
                        { label: 'A-', value: result.grade_distribution.a_minus, color: 'bg-green-100 text-green-700' },
                        { label: 'B+', value: result.grade_distribution.b_plus, color: 'bg-blue-100 text-blue-700' },
                        { label: 'B', value: result.grade_distribution.b, color: 'bg-blue-100 text-blue-700' },
                        { label: 'B-', value: result.grade_distribution.b_minus, color: 'bg-blue-100 text-blue-700' },
                        { label: 'C+', value: result.grade_distribution.c_plus, color: 'bg-yellow-100 text-yellow-700' },
                      ].map((grade) => (
                        <div key={grade.label} className={`${grade.color} px-1 py-1 rounded text-center`}>
                          <div className="font-semibold">{grade.label}</div>
                          <div>{grade.value}</div>
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-6 gap-1 text-xs mt-1">
                      {[
                        { label: 'C', value: result.grade_distribution.c, color: 'bg-yellow-100 text-yellow-700' },
                        { label: 'C-', value: result.grade_distribution.c_minus, color: 'bg-yellow-100 text-yellow-700' },
                        { label: 'D+', value: result.grade_distribution.d_plus, color: 'bg-orange-100 text-orange-700' },
                        { label: 'D', value: result.grade_distribution.d, color: 'bg-orange-100 text-orange-700' },
                        { label: 'D-', value: result.grade_distribution.d_minus, color: 'bg-orange-100 text-orange-700' },
                        { label: 'F', value: result.grade_distribution.f, color: 'bg-red-100 text-red-700' },
                      ].map((grade) => (
                        <div key={grade.label} className={`${grade.color} px-1 py-1 rounded text-center`}>
                          <div className="font-semibold">{grade.label}</div>
                          <div>{grade.value}</div>
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between px-6 py-4 bg-gray-50 border-t border-gray-200 text-sm text-gray-700">
        <div>
          Showing {Math.min(totalCount, (page - 1) * pageSize + 1)}-
          {Math.min(totalCount, page * pageSize)} of {totalCount} results
        </div>
        <div className="flex items-center gap-2 mt-3 md:mt-0">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Prev
          </button>
          <span className="px-2">
            Page {page} / {Math.max(1, Math.ceil(totalCount / pageSize))}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page * pageSize >= totalCount}
            className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
