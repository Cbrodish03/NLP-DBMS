import { TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { QueryResult } from '../lib/queryProcessor';

type SortField = 'course' | 'instructor' | 'semester' | 'total_students' | 'b_or_above_percentage' | 'gpa';

interface ResultsTableProps {
  results: QueryResult[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  sortField: SortField;
  sortDirection: 'asc' | 'desc';
  onSort: (field: SortField) => void;
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

export default function ResultsTable({
  results,
  totalCount,
  page,
  pageSize,
  onPageChange,
  sortField,
  sortDirection,
  onSort,
}: ResultsTableProps) {
  const navigate = useNavigate();

  const gpaColor = (gpa: number | null | undefined) => {
    if (gpa == null) return "bg-gray-100 text-gray-600";
    if (gpa >= 3.5) return "bg-green-100 text-green-700";
    if (gpa >= 3.0) return "bg-emerald-50 text-emerald-700";
    if (gpa >= 2.5) return "bg-yellow-50 text-yellow-700";
    return "bg-red-50 text-red-700";
  };

  if (results.length === 0) {
    return (
      <div className="w-full max-w-6xl mt-8 p-8 bg-white rounded-xl shadow-sm text-center text-gray-500">
        No courses found matching your query. Try a different search.
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mt-8 bg-white rounded-xl shadow-lg overflow-hidden border border-[#f2cbb3]">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
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
                  label="B or Above"
                  field="b_or_above_percentage"
                  activeField={sortField}
                  direction={sortDirection}
                  onClick={onSort}
                />
              </th>
              <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Grade Distribution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {results.map((result) => (
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
                <td className="px-6 py-4">
                  <div className="font-semibold text-gray-900">
                    {result.department} {result.course_number}
                  </div>
                  <div className="text-sm text-gray-600">{result.course_name}</div>
                </td>
                <td className="px-6 py-4 text-gray-700">{result.instructor}</td>
                <td className="px-6 py-4 text-gray-700">{result.semester}</td>
                <td className="px-6 py-4 text-center text-gray-700">{result.total_students}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`inline-flex px-2 py-1 rounded-full text-sm font-semibold ${gpaColor(result.gpa)}`}>
                    {result.gpa != null ? result.gpa.toFixed(2) : '—'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center justify-center gap-2">
                    <div className="flex items-center gap-1 text-green-600 font-semibold">
                      <TrendingUp size={16} />
                      {result.b_or_above_percentage.toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 text-center mt-1">
                    ({result.b_or_above_count} students)
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
            ))}
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
