    -- 002_seed.sql
-- Tiny demo data so the full-stack test returns something.

INSERT INTO subject (subject_code, name)
VALUES
  ('CS',   'Computer Science'),
  ('MATH', 'Mathematics')
ON CONFLICT DO NOTHING;

INSERT INTO term (term_id, label, academic_year)
VALUES
  (202401, 'Spring 2024', '2023-2024')
ON CONFLICT DO NOTHING;

INSERT INTO course (course_id, subject_code, course_number, title, credits, level)
VALUES
  (1, 'CS', '2104', 'Intro to Problem Solving in CS', 3, 'UG')
ON CONFLICT DO NOTHING;

INSERT INTO instructor (instructor_id, name_display)
VALUES
  (1, 'Doe, John')
ON CONFLICT DO NOTHING;

INSERT INTO section (section_id, course_id, term_id, instructor_id, credits, graded_enrollment)
VALUES
  (1, 1, 202401, 1, 3, 100)
ON CONFLICT DO NOTHING;

INSERT INTO grade_distribution (
  section_id, gpa,
  a, a_minus, b_plus, b, b_minus, c_plus, c, c_minus, d_plus, d, d_minus, f,
  withdraws, graded_enrollment
)
VALUES
  (1, 32,   -- 3.2 GPA as 32
   30, 10, 15, 20, 5, 5, 5, 3, 2, 1, 1, 4,
   5, 100)
ON CONFLICT DO NOTHING;
