import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, BookOpen, CalendarRange, GitCompare, Gauge, TrendingUp, User, Users, X } from 'lucide-react';
import type { QueryResult } from '../utils/queryProcessor';
import { CACHE_KEY } from './HomePage';

type LocationState = {
  courses?: QueryResult[];
};

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

function restoreFromCache(): QueryResult[] {
  const cached = sessionStorage.getItem(CACHE_KEY);
  if (!cached) return [];
  try {
    const data = JSON.parse(cached);
    if (!Array.isArray(data?.results) || !Array.isArray(data?.selectedIds)) return [];
    return (data.results as QueryResult[]).filter((course) => data.selectedIds.includes(course.id));
  } catch {
    return [];
  }
}

export default function ComparisonPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const stateCourses = (location.state as LocationState | undefined)?.courses ?? [];
  const [courses, setCourses] = useState<QueryResult[]>(stateCourses.length > 0 ? stateCourses : restoreFromCache());

  const gradeRows = useMemo(() => {
    return courses.map((course) => {
      const total = Object.values(course.grade_distribution).reduce((sum, val) => sum + val, 0);
      const rows = gradeDisplay.map((grade) => {
        const value = course.grade_distribution[grade.key] ?? 0;
        const percent = total > 0 ? (value / total) * 100 : 0;
        return { ...grade, value, percent };
      });
      return { id: course.id, rows, total };
    });
  }, [courses]);

  const leaderboard = useMemo(() => {
    if (courses.length === 0) return null;
    const byGpa = [...courses].sort((a, b) => (b.gpa ?? 0) - (a.gpa ?? 0))[0];
    const byB = [...courses].sort((a, b) => b.b_or_above_percentage - a.b_or_above_percentage)[0];
    const byEnrollment = [...courses].sort((a, b) => b.total_students - a.total_students)[0];
    return { byGpa, byB, byEnrollment };
  }, [courses]);

  const instructorStats = useMemo(() => {
    const map = new Map<
      string,
      {
        name: string;
        courses: QueryResult[];
        totalStudents: number;
        bCount: number;
        gpaWeighted: number;
        gpaStudents: number;
      }
    >();

    courses.forEach((course) => {
      const name = course.instructor?.trim() || 'Instructor TBA';
      const entry =
        map.get(name) ??
        {
          name,
          courses: [],
          totalStudents: 0,
          bCount: 0,
          gpaWeighted: 0,
          gpaStudents: 0,
        };
      entry.courses.push(course);
      entry.totalStudents += course.total_students ?? 0;
      entry.bCount += course.b_or_above_count ?? 0;
      if (course.gpa != null) {
        entry.gpaWeighted += course.gpa * (course.total_students ?? 0);
        entry.gpaStudents += course.total_students ?? 0;
      }
      map.set(name, entry);
    });

    return Array.from(map.values())
      .map((entry) => ({
        ...entry,
        avgGpa: entry.gpaStudents > 0 ? entry.gpaWeighted / entry.gpaStudents : null,
        bPercent: entry.totalStudents > 0 ? (entry.bCount / entry.totalStudents) * 100 : 0,
      }))
      .sort((a, b) => b.bPercent - a.bPercent || b.totalStudents - a.totalStudents);
  }, [courses]);

  const handleRemove = (id: string) => {
    setCourses((prev) => prev.filter((course) => course.id !== id));
  };

  if (courses.length < 2) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#fdf6ec] via-[#f7ece1] to-[#f9f5f1] flex items-center justify-center px-4">
        <div className="max-w-xl w-full bg-white shadow-md rounded-xl p-8 text-center space-y-4 border border-[#f2cbb3]">
          <GitCompare className="w-10 h-10 text-[#861f41] mx-auto" />
          <h2 className="text-2xl font-bold text-[#3b0d1f]">Select classes to compare</h2>
          <p className="text-[#7a5a46]">
            Choose at least two classes from your search results to view a side-by-side comparison.
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 bg-[#861f41] text-white rounded-lg hover:bg-[#6f1936] transition-colors"
            >
              Back to search
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#fdf6ec] via-white to-[#f7ece1]">
      <div className="container mx-auto px-4 py-10 space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2 text-[#861f41] hover:text-[#6f1936]"
          >
            <ArrowLeft size={18} />
            Back to results
          </button>
          <div className="flex items-center gap-2 text-sm font-semibold text-[#3b0d1f]">
            <GitCompare size={18} className="text-[#861f41]" />
            {courses.length} classes in comparison
          </div>
        </div>

        <div className="bg-white shadow-lg rounded-2xl p-6 border border-[#f2cbb3] space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <BookOpen className="text-[#861f41]" size={28} />
              <div>
                <p className="text-sm uppercase tracking-wide text-[#7a5a46]">Comparison overview</p>
                <h1 className="text-2xl font-bold text-[#3b0d1f]">Grade outcomes across selected classes</h1>
              </div>
            </div>
            <div className="text-sm text-[#7a5a46]">
              Tap on any class to remove it from this view.
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            {courses.map((course) => (
              <button
                key={course.id}
                onClick={() => handleRemove(course.id)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#f2cbb3] bg-[#fdf6ec] text-sm text-left text-[#3b0d1f] hover:border-[#e87722] transition-colors"
              >
                <div>
                  <div className="font-semibold">
                    {course.department} {course.course_number} · Section {course.id}
                  </div>
                  <div className="text-xs text-[#7a5a46]">{course.course_name}</div>
                  <div className="text-[11px] text-[#7a5a46]">
                    {course.instructor || 'Instructor TBA'} · {course.semester || 'Term TBD'}
                  </div>
                </div>
                <X size={14} className="text-[#861f41]" />
              </button>
            ))}
          </div>
        </div>

        {leaderboard && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-xl bg-[#fce9dd] border border-[#f2cbb3]">
              <div className="flex items-center justify-between text-[#7a102d]">
                <span className="text-sm font-semibold">Best Avg GPA</span>
                <Gauge size={18} />
              </div>
              <div className="mt-3 text-xl font-bold text-[#861f41]">
                {leaderboard.byGpa.gpa?.toFixed(2) ?? '—'}
              </div>
              <div className="text-sm text-[#7a5a46]">
                {leaderboard.byGpa.department} {leaderboard.byGpa.course_number} · Section {leaderboard.byGpa.id}
              </div>
              <div className="text-[11px] text-[#927a67]">
                {leaderboard.byGpa.semester || 'Term TBD'} · {leaderboard.byGpa.instructor || 'Instructor TBA'}
              </div>
            </div>
            <div className="p-5 rounded-xl bg-[#f6f0e9] border border-[#f2cbb3]">
              <div className="flex items-center justify-between text-[#3b0d1f]">
                <span className="text-sm font-semibold">Highest B or Above</span>
                <TrendingUp size={18} className="text-[#e87722]" />
              </div>
              <div className="mt-3 text-xl font-bold text-[#861f41]">
                {leaderboard.byB.b_or_above_percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-[#7a5a46]">
                {leaderboard.byB.department} {leaderboard.byB.course_number} · Section {leaderboard.byB.id}
              </div>
              <div className="text-[11px] text-[#927a67]">
                {leaderboard.byB.semester || 'Term TBD'} · {leaderboard.byB.instructor || 'Instructor TBA'}
              </div>
            </div>
            <div className="p-5 rounded-xl bg-[#f1e0d7] border border-[#f2cbb3]">
              <div className="flex items-center justify-between text-[#3b0d1f]">
                <span className="text-sm font-semibold">Largest Class</span>
                <Users size={18} className="text-[#861f41]" />
              </div>
              <div className="mt-3 text-xl font-bold text-[#861f41]">{leaderboard.byEnrollment.total_students}</div>
              <div className="text-sm text-[#7a5a46]">
                {leaderboard.byEnrollment.department} {leaderboard.byEnrollment.course_number} · Section {leaderboard.byEnrollment.id}
              </div>
              <div className="text-[11px] text-[#927a67]">
                {leaderboard.byEnrollment.semester || 'Term TBD'} · {leaderboard.byEnrollment.instructor || 'Instructor TBA'}
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-md p-6 space-y-4 border border-[#f2cbb3]">
          <div className="flex items-center gap-2">
            <GitCompare className="text-[#861f41]" size={20} />
            <h2 className="text-xl font-semibold text-[#3b0d1f]">Side-by-side metrics</h2>
          </div>
          <div className="overflow-x-auto">
            <div className="min-w-[980px]">
              <div className="grid grid-cols-7 bg-gray-50 border-b border-gray-200 text-[#3b0d1f] text-sm font-semibold">
                <div className="px-4 py-3">Class</div>
                <div className="px-4 py-3 text-center">Section</div>
                <div className="px-4 py-3">Instructor</div>
                <div className="px-4 py-3">Term</div>
                <div className="px-4 py-3 text-center">Students</div>
                <div className="px-4 py-3 text-center">Avg GPA</div>
                <div className="px-4 py-3 text-center">B or Above</div>
              </div>
              <div className="divide-y divide-gray-200 text-[#3b0d1f]">
                {courses.map((course) => (
                  <div key={course.id} className="grid grid-cols-7 items-center hover:bg-gray-50 transition-colors text-sm">
                    <div className="px-4 py-3">
                      <div className="font-semibold">
                        {course.department} {course.course_number}
                      </div>
                      <div className="text-xs text-[#7a5a46]">{course.course_name}</div>
                    </div>
                    <div className="px-4 py-3 text-center">
                      <span className="inline-flex items-center justify-center px-2 py-1 rounded-lg bg-[#fdf6ec] border border-[#f2cbb3] text-xs font-semibold text-[#3b0d1f]">
                        #{course.id}
                      </span>
                    </div>
                    <div className="px-4 py-3 flex items-center gap-2 whitespace-nowrap">
                      <User size={14} className="text-[#861f41]" />
                      <span>{course.instructor || 'Instructor TBA'}</span>
                    </div>
                    <div className="px-4 py-3 flex items-center gap-2 whitespace-nowrap">
                      <CalendarRange size={14} className="text-[#e87722]" />
                      <span>{course.semester || 'Term TBD'}</span>
                    </div>
                    <div className="px-4 py-3 text-center font-semibold">{course.total_students}</div>
                    <div className="px-4 py-3 text-center font-semibold">
                      {course.gpa != null ? course.gpa.toFixed(2) : '—'}
                    </div>
                    <div className="px-4 py-3 text-center">
                      <div className="inline-flex items-center gap-2 rounded-full bg-[#fce9dd] px-3 py-1 text-[#7a102d] font-semibold">
                        <TrendingUp size={14} />
                        {course.b_or_above_percentage.toFixed(1)}%
                      </div>
                      <div className="text-xs text-[#7a5a46] mt-1">
                        {course.b_or_above_count} of {course.total_students} students
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {instructorStats.length > 1 && (
          <div className="bg-white rounded-2xl shadow-md p-6 space-y-4 border border-[#f2cbb3]">
            <div className="flex items-center gap-2">
              <User className="text-[#861f41]" size={20} />
              <h2 className="text-xl font-semibold text-[#3b0d1f]">Instructor comparison</h2>
            </div>
            <div className="overflow-x-auto">
              <div className="min-w-[720px]">
                <div className="grid grid-cols-5 bg-gray-50 border-b border-gray-200 text-[#3b0d1f] text-sm font-semibold">
                  <div className="px-4 py-3">Instructor</div>
                  <div className="px-4 py-3 text-center">Classes</div>
                  <div className="px-4 py-3 text-center">Students</div>
                  <div className="px-4 py-3 text-center">Avg GPA</div>
                  <div className="px-4 py-3 text-center">B or Above</div>
                </div>
                <div className="divide-y divide-gray-200 text-[#3b0d1f]">
                  {instructorStats.map((instructor) => (
                    <div key={instructor.name} className="grid grid-cols-5 items-center text-sm">
                      <div className="px-4 py-3">
                        <div className="font-semibold">{instructor.name}</div>
                        <div className="text-[11px] text-[#7a5a46]">
                          {instructor.courses
                            .map((course) => `${course.department} ${course.course_number} (Sec ${course.id})`)
                            .join(' · ')}
                        </div>
                      </div>
                      <div className="px-4 py-3 text-center">{instructor.courses.length}</div>
                      <div className="px-4 py-3 text-center font-semibold">{instructor.totalStudents}</div>
                      <div className="px-4 py-3 text-center font-semibold">
                        {instructor.avgGpa != null ? instructor.avgGpa.toFixed(2) : '—'}
                      </div>
                      <div className="px-4 py-3 text-center">
                        <div className="inline-flex items-center gap-2 rounded-full bg-[#fce9dd] px-3 py-1 text-[#7a102d] font-semibold">
                          <TrendingUp size={14} />
                          {instructor.bPercent.toFixed(1)}%
                        </div>
                        <div className="text-xs text-[#7a5a46] mt-1">
                          {instructor.bCount} of {instructor.totalStudents} students
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-md p-6 space-y-6 border border-[#f2cbb3]">
          <div className="flex items-center gap-2">
            <BookOpen className="text-[#861f41]" size={20} />
            <h2 className="text-xl font-semibold text-[#3b0d1f]">Grade distribution per class</h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {courses.map((course) => {
              const grades = gradeRows.find((row) => row.id === course.id);
              if (!grades) return null;
              return (
                <div key={course.id} className="p-4 rounded-xl border border-[#f2cbb3] bg-[#fdf6ec]">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="font-semibold text-[#3b0d1f]">
                        {course.department} {course.course_number} · Section {course.id}
                      </div>
                      <div className="text-xs text-[#7a5a46]">{course.course_name}</div>
                      <div className="text-[11px] text-[#7a5a46]">
                        {course.instructor || 'Instructor TBA'} · {course.semester || 'Term TBD'}
                      </div>
                    </div>
                    <div className="text-xs text-[#7a5a46]">{grades.total} grades</div>
                  </div>
                  <div className="space-y-2">
                    {grades.rows.map((grade) => (
                      <div key={grade.key} className="flex items-center gap-3">
                        <div className="w-10 text-sm font-semibold text-[#3b0d1f]">{grade.label}</div>
                        <div className="flex-1 h-2.5 bg-white rounded-full overflow-hidden border border-[#f2cbb3]">
                          <div className={`${grade.color} h-2.5`} style={{ width: `${grade.percent}%` }} />
                        </div>
                        <div className="w-24 text-right text-sm text-[#7a5a46]">
                          {grade.value} ({grade.percent.toFixed(1)}%)
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
