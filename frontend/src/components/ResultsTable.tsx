import { TrendingUp } from 'lucide-react';
import type { QueryResult } from '../lib/queryProcessor';

interface ResultsTableProps {
  results: QueryResult[];
}

export default function ResultsTable({ results }: ResultsTableProps) {
  if (results.length === 0) {
    return (
      <div className="w-full max-w-6xl mt-8 p-8 bg-white rounded-xl shadow-sm text-center text-gray-500">
        No courses found matching your query. Try a different search.
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mt-8 bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Course</th>
              <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Instructor</th>
              <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Semester</th>
              <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Students</th>
              <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">B or Above</th>
              <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Grade Distribution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-semibold text-gray-900">
                    {result.department} {result.course_number}
                  </div>
                  <div className="text-sm text-gray-600">{result.course_name}</div>
                </td>
                <td className="px-6 py-4 text-gray-700">{result.instructor}</td>
                <td className="px-6 py-4 text-gray-700">{result.semester}</td>
                <td className="px-6 py-4 text-center text-gray-700">{result.total_students}</td>
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
                  <div className="grid grid-cols-7 gap-1 text-xs">
                    {[
                      { label: 'A+', value: result.grade_distribution.a_plus, color: 'bg-green-100 text-green-700' },
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
    </div>
  );
}
