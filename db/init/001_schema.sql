-- 001_schema.sql
-- Core VT UDC schema: subject / term / course / instructor / section / grade_distribution

-- Drop in dependency order for easy rebuilds in dev
DROP TABLE IF EXISTS grade_distribution CASCADE;
DROP TABLE IF EXISTS section CASCADE;
DROP TABLE IF EXISTS instructor CASCADE;
DROP TABLE IF EXISTS course CASCADE;
DROP TABLE IF EXISTS term CASCADE;
DROP TABLE IF EXISTS subject CASCADE;


-- =========================
-- Subject
-- =========================
CREATE TABLE subject (
    subject_code   TEXT PRIMARY KEY,         -- PK, NOT NULL, UNIQUE
    name           TEXT                     -- nullable
);


-- =========================
-- Term
-- =========================
CREATE TABLE term (
    term_id        INT PRIMARY KEY,          -- PK, NOT NULL, UNIQUE
    label          TEXT NOT NULL UNIQUE,     -- e.g. 'Fall 2024'
    academic_year  TEXT                      -- e.g. '2024-2025'
);


-- =========================
-- Course
-- =========================
CREATE TABLE course (
    course_id      INT PRIMARY KEY,          -- PK, NOT NULL
    subject_code   TEXT NOT NULL,            -- FK -> subject.subject_code
    course_number  TEXT NOT NULL,            -- e.g. '2104'
    title          TEXT,                     -- nullable
    credits        INT,                      -- nullable
    level          TEXT,                     -- e.g. 'UG', 'GR'

    CONSTRAINT fk_course_subject
        FOREIGN KEY (subject_code)
        REFERENCES subject(subject_code),

    -- Unique constraint: (subject_code, course_number)
    CONSTRAINT uq_course_subject_number
        UNIQUE (subject_code, course_number)
);


-- =========================
-- Instructor
-- =========================
CREATE TABLE instructor (
    instructor_id  INT PRIMARY KEY,          -- PK, NOT NULL
    name_display   TEXT NOT NULL             -- e.g. 'Boyer, John'
);


-- =========================
-- Section
-- =========================
CREATE TABLE section (
    section_id        INT PRIMARY KEY,       -- PK, NOT NULL
    course_id         INT NOT NULL,          -- FK -> course.course_id
    term_id           INT NOT NULL,          -- FK -> term.term_id
    instructor_id     INT NOT NULL,          -- FK -> instructor.instructor_id
    credits           INT,                   -- nullable
    graded_enrollment INT,                   -- nullable

    CONSTRAINT fk_section_course
        FOREIGN KEY (course_id)
        REFERENCES course(course_id),

    CONSTRAINT fk_section_term
        FOREIGN KEY (term_id)
        REFERENCES term(term_id),

    CONSTRAINT fk_section_instructor
        FOREIGN KEY (instructor_id)
        REFERENCES instructor(instructor_id)
);

CREATE INDEX idx_section_term_id       ON section(term_id);
CREATE INDEX idx_section_course_id     ON section(course_id);
CREATE INDEX idx_section_instructor_id ON section(instructor_id);


-- =========================
-- Grade_Distribution
-- =========================
CREATE TABLE grade_distribution (
    section_id        INT PRIMARY KEY,       -- PK & FK, NOT NULL
    gpa               DECIMAL(10,2) NOT NULL,          -- overall GPA for this section

    a                 INT NOT NULL DEFAULT 0,
    a_minus           INT NOT NULL DEFAULT 0,
    b_plus            INT NOT NULL DEFAULT 0,
    b                 INT NOT NULL DEFAULT 0,
    b_minus           INT NOT NULL DEFAULT 0,
    c_plus            INT NOT NULL DEFAULT 0,
    c                 INT NOT NULL DEFAULT 0,
    c_minus           INT NOT NULL DEFAULT 0,
    d_plus            INT NOT NULL DEFAULT 0,
    d                 INT NOT NULL DEFAULT 0,
    d_minus           INT NOT NULL DEFAULT 0,
    f                 INT NOT NULL DEFAULT 0,

    withdraws         INT NOT NULL DEFAULT 0,
    graded_enrollment INT NOT NULL,

    CONSTRAINT fk_grade_distribution_section
        FOREIGN KEY (section_id)
        REFERENCES section(section_id)
);
