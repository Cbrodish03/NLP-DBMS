-- =========================
-- Views
-- =========================

CREATE OR REPLACE VIEW v_course_sections AS
SELECT
    s.section_id,
    c.course_id,
    c.subject_code,
    c.course_number,
    c.title AS course_title,
    t.term_id,
    t.label AS term_label,
    i.instructor_id,
    i.name_display AS instructor,
    s.credits,
    s.graded_enrollment
FROM section s
JOIN course c ON s.course_id = c.course_id
JOIN term t   ON s.term_id   = t.term_id
JOIN instructor i ON s.instructor_id = i.instructor_id;

CREATE OR REPLACE VIEW v_grade_distribution_full AS
SELECT
    gd.section_id,
    c.subject_code,
    c.course_number,
    c.title AS course_title,
    t.term_id,
    t.label AS term_label,
    i.instructor_id,
    i.name_display AS instructor,
    s.credits,
    gd.gpa,
    gd.a, gd.a_minus, gd.b_plus, gd.b, gd.b_minus,
    gd.c_plus, gd.c, gd.c_minus,
    gd.d_plus, gd.d, gd.d_minus,
    gd.f,
    gd.withdraws,
    gd.graded_enrollment
FROM grade_distribution gd
JOIN section s ON gd.section_id = s.section_id
JOIN course  c ON s.course_id = c.course_id
JOIN instructor i ON s.instructor_id = i.instructor_id
JOIN term t ON s.term_id = t.term_id;

CREATE OR REPLACE VIEW v_course_summary AS
SELECT
    c.course_id,
    c.subject_code,
    c.course_number,
    c.title AS course_title,
    COUNT(s.section_id) AS section_count,
    AVG(gd.gpa) AS avg_gpa,
    SUM(gd.graded_enrollment) AS total_enrollment
FROM course c
LEFT JOIN section s ON c.course_id = s.course_id
LEFT JOIN grade_distribution gd ON s.section_id = gd.section_id
GROUP BY c.course_id;

CREATE OR REPLACE VIEW v_instructor_stats AS
SELECT
    i.instructor_id,
    i.name_display,
    COUNT(s.section_id) AS sections_taught,
    AVG(gd.gpa) AS avg_gpa,
    SUM(gd.graded_enrollment) AS total_students
FROM instructor i
LEFT JOIN section s ON i.instructor_id = s.instructor_id
LEFT JOIN grade_distribution gd ON s.section_id = gd.section_id
GROUP BY i.instructor_id;

CREATE OR REPLACE VIEW v_term_overview AS
SELECT
    t.term_id,
    t.label AS term_label,
    COUNT(s.section_id) AS section_count,
    COUNT(DISTINCT c.course_id) AS distinct_courses,
    AVG(gd.gpa) AS avg_gpa,
    SUM(gd.graded_enrollment) AS total_enrollment
FROM term t
LEFT JOIN section s ON t.term_id = s.term_id
LEFT JOIN course  c ON s.course_id = c.course_id
LEFT JOIN grade_distribution gd ON s.section_id = gd.section_id
GROUP BY t.term_id;

