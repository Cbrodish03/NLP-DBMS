import { useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BarChart3, GraduationCap, Users, User, CalendarRange, BookOpen } from 'lucide-react';
import type { QueryResult } from '../lib/queryProcessor';

type GradeKey = keyof QueryResult['grade_distribution'];

const gradeDisplay: Array<{ key: GradeKey; label: string; color: string }> = [
  { key: 'a', label: 'A', color: 'bg-green-500' },
  { key: 'a_minus', label: 'A-', color: 'bg-green-400' },
  { key: 'b_plus', label: 'B+', color: 'bg-blue-500' },
  { key: 'b', label: 'B', color: 'bg-blue-400' },
  { key: 'b_minus', label: 'B-', color: 'bg-blue-300' },
  { key: 'c_plus', label: 'C+', color: 'bg-yellow-500' },
  { key: 'c', label: 'C', color: 'bg-yellow-400' },
  { key: 'c_minus', label: 'C-', color: 'bg-yellow-300' },
  { key: 'd_plus', label: 'D+', color: 'bg-orange-500' },
  { key: 'd', label: 'D', color: 'bg-orange-400' },
  { key: 'd_minus', label: 'D-', color: 'bg-orange-300' },
  { key: 'f', label: 'F', color: 'bg-red-400' },
];

export default function CourseDetail() {
  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams();

  const course = location.state as QueryResult | undefined;
  const courseId = id ?? course?.id ?? '';

  const totals = useMemo(() => {
    if (!course) {
      return { total: 0, gradeTotals: gradeDisplay.map((g) => ({ ...g, value: 0, percent: 0 })) };
    }
    const total = Object.values(course.grade_distribution).reduce((sum, val) => sum + val, 0);
    const gradeTotals = gradeDisplay.map((grade) => {
      const value = course.grade_distribution[grade.key];
      const percent = total > 0 ? (value / total) * 100 : 0;
      return { ...grade, value, percent };
    });
    return { total, gradeTotals };
  }, [course]);

  if (!course) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#fdf6ec] via-[#f7ece1] to-[#f9f5f1] flex items-center justify-center px-4">
        <div className="max-w-xl w-full bg-white shadow-md rounded-xl p-8 text-center space-y-4 border border-[#f2cbb3]">
          <BookOpen className="w-10 h-10 text-[#861f41] mx-auto" />
          <h2 className="text-2xl font-bold text-[#3b0d1f]">Course details unavailable</h2>
          <p className="text-[#7a5a46]">
            We couldn&apos;t load that course. Please return to the search page and select a class again.
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-[#861f41] text-white rounded-lg hover:bg-[#6f1936] transition-colors"
          >
            Back to search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#fdf6ec] via-white to-[#f7ece1]">
      <div className="container mx-auto px-4 py-10 space-y-8">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-[#861f41] hover:text-[#6f1936]"
        >
          <ArrowLeft size={18} />
          Back to results
        </button>

        <div className="bg-white shadow-lg rounded-2xl p-8 space-y-6 border border-[#f2cbb3]">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <BookOpen className="text-[#861f41]" size={32} />
              <div>
                <p className="text-sm uppercase tracking-wide text-[#7a5a46]">Course #{courseId}</p>
                <h1 className="text-3xl font-bold text-[#3b0d1f]">
                  {course.department} {course.course_number} — {course.course_name}
                </h1>
              </div>
            </div>
            <div className="flex flex-wrap gap-4 text-gray-700">
              <div className="flex items-center gap-2 bg-[#fce9dd] text-[#7a102d] px-3 py-1 rounded-full border border-[#f2cbb3]">
                <User size={16} />
                {course.instructor || 'Instructor TBA'}
              </div>
              <div className="flex items-center gap-2 bg-[#f6f0e9] text-[#3b0d1f] px-3 py-1 rounded-full border border-[#f2cbb3]">
                <CalendarRange size={16} />
                {course.semester || 'Semester TBD'}
              </div>
              <div className="flex items-center gap-2 bg-[#f1e0d7] text-[#3b0d1f] px-3 py-1 rounded-full border border-[#f2cbb3]">
                <GraduationCap size={16} />
                {course.department}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-xl bg-[#fce9dd] border border-[#f2cbb3]">
              <div className="flex items-center justify-between">
                <h3 className="text-sm text-[#7a102d] font-semibold">B or Above</h3>
                <BarChart3 className="text-[#e87722]" size={20} />
              </div>
              <div className="mt-3 text-3xl font-bold text-[#861f41]">
                {course.b_or_above_percentage.toFixed(1)}%
              </div>
              <p className="text-sm text-[#7a5a46] mt-1">
                {course.b_or_above_count} of {course.total_students} students
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#f6f0e9] border border-[#f2cbb3]">
              <div className="flex items-center justify-between">
                <h3 className="text-sm text-[#3b0d1f] font-semibold">Total Students</h3>
                <Users className="text-[#861f41]" size={20} />
              </div>
              <div className="mt-3 text-3xl font-bold text-[#3b0d1f]">{course.total_students}</div>
              <p className="text-sm text-[#7a5a46] mt-1">Grade distribution below</p>
            </div>

            <div className="p-5 rounded-xl bg-[#f1e0d7] border border-[#f2cbb3]">
              <div className="flex items-center justify-between">
                <h3 className="text-sm text-[#3b0d1f] font-semibold">Top Grade</h3>
                <GraduationCap className="text-[#e87722]" size={20} />
              </div>
              <div className="mt-3 text-3xl font-bold text-[#861f41]">
                {course.grade_distribution.a + course.grade_distribution.a_minus > 0 ? 'A Range' : 'Below A'}
              </div>
              <p className="text-sm text-[#7a5a46] mt-1">See full breakdown</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-md p-6 space-y-4 border border-[#f2cbb3]">
            <div className="flex items-center gap-2">
              <BarChart3 className="text-[#e87722]" size={20} />
              <h2 className="text-xl font-semibold text-[#3b0d1f]">Grade Distribution</h2>
            </div>

            <div className="space-y-3">
              {totals.gradeTotals.map((grade) => (
                <div key={grade.key} className="flex items-center gap-3">
                  <div className="w-12 font-semibold text-[#3b0d1f]">{grade.label}</div>
                  <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div className={`h-3 ${grade.color}`} style={{ width: `${grade.percent}%` }} />
                  </div>
                  <div className="w-28 text-right text-sm text-[#7a5a46]">
                    {grade.value} ({grade.percent.toFixed(1)}%)
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-md p-6 space-y-3 border border-[#f2cbb3]">
            <div className="flex items-center gap-2">
              <BookOpen className="text-[#861f41]" size={20} />
              <h2 className="text-xl font-semibold text-[#3b0d1f]">Class Snapshot</h2>
            </div>
            <ul className="space-y-3 text-[#3b0d1f]">
              <li className="flex items-center justify-between">
                <span>Department</span>
                <span className="font-semibold text-gray-900">{course.department}</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Course</span>
                <span className="font-semibold text-gray-900">
                  {course.department} {course.course_number}
                </span>
              </li>
              <li className="flex items-center justify-between">
                <span>Instructor</span>
                <span className="font-semibold text-gray-900">{course.instructor || 'TBA'}</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Term</span>
                <span className="font-semibold text-gray-900">{course.semester || 'TBD'}</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Total students</span>
                <span className="font-semibold text-gray-900">{course.total_students}</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-6 space-y-4 border border-[#f2cbb3]">
          <div className="flex items-center gap-2">
            <BarChart3 className="text-[#e87722]" size={20} />
            <h2 className="text-xl font-semibold text-[#3b0d1f]">Grade counts</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {totals.gradeTotals.map((grade) => (
              <div key={grade.key} className="p-3 rounded-xl bg-gray-50 border border-gray-100 text-center">
                <div className="text-sm font-semibold text-gray-700">{grade.label}</div>
                <div className="text-lg font-bold text-gray-900">{grade.value}</div>
                <div className="text-xs text-gray-500">{grade.percent.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
