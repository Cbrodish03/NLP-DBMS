import csv
import re
import sys
import argparse
from typing import List

from subject_map import SUBJECT_NAME_MAP


def load_classes_from_csv(file_path: str):
    """
    Loads class data from a CSV file.
    :param file_path: Path to the CSV file containing class data
    :return: list of rows (each row is a list of strings)
    """
    classes = []
    with open(file_path, "r", encoding="utf-8", newline="") as csvfile:
        reader = csv.reader(csvfile)
        # Skip header
        header = next(reader, None)
        for row in reader:
            # Normalize whitespace
            row = [col.strip() if isinstance(col, str) else col for col in row]
            # Skip empty rows defensively
            if not any(row):
                continue
            classes.append(row)
    return classes


def percentages_to_counts(percentages: List[float], graded_enrollment: int) -> List[int]:
    """
    Convert a list of percentages (0–100) into integer counts that sum exactly
    to graded_enrollment.

    Uses a "largest remainder" approach to distribute rounding error.
    """
    if graded_enrollment <= 0:
        return [0 for _ in percentages]

    # Raw fractional counts
    raw = [(p or 0.0) * graded_enrollment / 100.0 for p in percentages]
    floors = [int(x) for x in raw]
    total_floor = sum(floors)
    diff = graded_enrollment - total_floor

    # If we're already matching exactly, just return floors
    if diff == 0:
        return floors

    # Compute fractional parts
    fracs = [x - int(x) for x in raw]
    indexed = list(range(len(percentages)))

    # If we need to add people, give +1 to the largest fractional parts first
    if diff > 0:
        indexed.sort(key=lambda i: fracs[i], reverse=True)
        for i in indexed:
            if diff == 0:
                break
            floors[i] += 1
            diff -= 1
    else:
        # Need to remove |diff| people.
        # Remove from the smallest fractional parts first, but don't go below 0.
        indexed.sort(key=lambda i: fracs[i])
        for i in indexed:
            if diff == 0:
                break
            if floors[i] > 0:
                floors[i] -= 1
                diff += 1

    return floors


def convert_to_sql(classes):
    """
    Converts class data into SQL insert statements grouped by table.

    Tables:
        term(term_id, label, academic_year)
        subject(subject_code, name)
        course(course_id, subject_code, course_number, title, credits, level)
        instructor(instructor_id, name_display)
        section(section_id, course_id, term_id, instructor_id, credits, graded_enrollment)
        grade_distribution(section_id, gpa,
            a, a_minus, b_plus, b, b_minus, c_plus, c, c_minus,
            d_plus, d, d_minus, f, withdraws, graded_enrollment)
    """
    tables = {
        "subject": [],
        "term": [],
        "course": [],
        "instructor": [],
        "section": [],
        "grade_distribution": [],
    }

    # Deduplication / ID maps
    seen_subjects = set()
    seen_terms = set()
    course_ids = {}        # (subject_code, course_number) -> course_id
    instructor_ids = {}    # instructor name -> instructor_id
    seen_sections = set()
    seen_grade_dist = set()

    next_course_id = 1
    next_instructor_id = 1

    for cls in classes:
        # Expect 23 columns as per vt_class_data_* CSV
        if len(cls) < 23:
            raise ValueError(f"Expected 23 columns, got {len(cls)}: {cls}")

        acad_year_raw = cls[0]    # "2022-23"
        term_label_raw = cls[1]   # "Fall" or "Spring"
        subject_code = cls[2]
        course_number = cls[3]
        course_title = cls[4]
        instructor_name = cls[5]

        # GPA
        gpa = float(cls[6]) if cls[6] else 0.0

        # Percentages for letter grades
        def pf(idx):
            return float(cls[idx]) if cls[idx] not in (None, "") else 0.0

        a_p = pf(7)
        a_minus_p = pf(8)
        b_plus_p = pf(9)
        b_p = pf(10)
        b_minus_p = pf(11)
        c_plus_p = pf(12)
        c_p = pf(13)
        c_minus_p = pf(14)
        d_plus_p = pf(15)
        d_p = pf(16)
        d_minus_p = pf(17)
        f_p = pf(18)

        withdraws = int(cls[19]) if cls[19] else 0
        graded_enrollment = int(cls[20]) if cls[20] else 0
        crn = cls[21]
        credits = int(cls[22]) if cls[22] else None

        # Determine level from course number (0-4xxx = UG, >=5xxx = GR)
        level = "UG" if re.match(r"^[0-4]", course_number) else "GR"

        # --- SUBJECT ---
        subject_name = SUBJECT_NAME_MAP.get(subject_code, subject_code)
        if subject_code not in seen_subjects:
            seen_subjects.add(subject_code)
            tables["subject"].append(
                f"('{sql_escape(subject_code)}', '{sql_escape(subject_name)}')"
            )

        # --- TERM ---
        acad_year = normalize_academic_year(acad_year_raw)
        start_year_str, end_year_str = acad_year.split("-")
        start_year = int(start_year_str)
        end_year = int(end_year_str)

        term_label_clean = term_label_raw.strip().capitalize()
        tl = term_label_clean.lower()
        if "spring" in tl:
            cal_year = end_year
            half = "01"
        elif "fall" in tl:
            cal_year = start_year
            half = "02"
        else:
            raise ValueError(f"Unknown term label: {term_label_raw}")

        term_id = int(f"{cal_year}{half}")
        term_label = f"{term_label_clean} {cal_year}"

        if term_id not in seen_terms:
            seen_terms.add(term_id)
            tables["term"].append(
                f"({term_id}, '{sql_escape(term_label)}', '{acad_year}')"
            )

        # --- INSTRUCTOR ---
        if instructor_name not in instructor_ids:
            instructor_id = next_instructor_id
            instructor_ids[instructor_name] = instructor_id
            next_instructor_id += 1

            tables["instructor"].append(
                f"({instructor_id}, '{sql_escape(instructor_name)}')"
            )
        else:
            instructor_id = instructor_ids[instructor_name]

        # --- COURSE ---
        course_key = (subject_code, course_number)
        if course_key not in course_ids:
            course_id = next_course_id
            course_ids[course_key] = course_id
            next_course_id += 1

            tables["course"].append(
                f"({course_id}, '{sql_escape(subject_code)}', "
                f"'{sql_escape(course_number)}', '{sql_escape(course_title)}', "
                f"{credits if credits is not None else 'NULL'}, '{level}')"
            )
        else:
            course_id = course_ids[course_key]

        # --- SECTION ---
        section_id = int(crn)
        if section_id not in seen_sections:
            seen_sections.add(section_id)
            tables["section"].append(
                f"({section_id}, {course_id}, {term_id}, {instructor_id}, "
                f"{credits if credits is not None else 'NULL'}, {graded_enrollment})"
            )

        # --- GRADE DISTRIBUTION (percent -> counts) ---
        if section_id not in seen_grade_dist:
            seen_grade_dist.add(section_id)

            percentages = [
                a_p,
                a_minus_p,
                b_plus_p,
                b_p,
                b_minus_p,
                c_plus_p,
                c_p,
                c_minus_p,
                d_plus_p,
                d_p,
                d_minus_p,
                f_p,
            ]
            (
                a_c,
                a_minus_c,
                b_plus_c,
                b_c,
                b_minus_c,
                c_plus_c,
                c_c,
                c_minus_c,
                d_plus_c,
                d_c,
                d_minus_c,
                f_c,
            ) = percentages_to_counts(percentages, graded_enrollment)

            tables["grade_distribution"].append(
                f"({section_id}, {gpa:.2f}, "
                f"{a_c}, {a_minus_c}, {b_plus_c}, {b_c}, {b_minus_c}, "
                f"{c_plus_c}, {c_c}, {c_minus_c}, {d_plus_c}, {d_c}, "
                f"{d_minus_c}, {f_c}, {withdraws}, {graded_enrollment})"
            )

    return tables


def write_sql_to_file(output_file, sql_content):
    """
    Writes SQL content to a file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-- Auto-generated SQL insert statements\n\n")

        table_columns = {
            "subject": ["subject_code", "name"],
            "term": ["term_id", "label", "academic_year"],
            "course": [
                "course_id",
                "subject_code",
                "course_number",
                "title",
                "credits",
                "level",
            ],
            "instructor": ["instructor_id", "name_display"],
            "section": [
                "section_id",
                "course_id",
                "term_id",
                "instructor_id",
                "credits",
                "graded_enrollment",
            ],
            "grade_distribution": [
                "section_id",
                "gpa",
                "a",
                "a_minus",
                "b_plus",
                "b",
                "b_minus",
                "c_plus",
                "c",
                "c_minus",
                "d_plus",
                "d",
                "d_minus",
                "f",
                "withdraws",
                "graded_enrollment",
            ],
        }

        for table, entries in sql_content.items():
            if not entries:
                continue

            columns = table_columns[table]
            f.write(
                f"INSERT INTO {table} ({', '.join(columns)})\nVALUES\n"
            )

            for i, val in enumerate(entries):
                comma = "," if i < len(entries) - 1 else ""
                f.write(f"  {val}{comma}\n")

            f.write("ON CONFLICT DO NOTHING;\n\n")


def sql_escape(value: str) -> str:
    if value is None:
        return ""
    return value.replace("'", "''")


def normalize_academic_year(ay: str) -> str:
    """
    Normalizes academic year strings like '2022-23' to '2022-2023'.
    """
    ay = ay.strip()
    parts = ay.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid academic year format: {ay}")

    start, end = parts[0], parts[1]

    if len(start) == 2:
        start = "20" + start
    if len(end) == 2:
        end = "20" + end

    return f"{start}-{end}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert VT grade distribution CSV into SQL seed inserts."
    )

    parser.add_argument(
        "-i", "--in", "--input", dest="input_file", required=True,
        help="Path to the CSV file to process"
    )

    parser.add_argument(
        "-o", "--out", "--output", dest="output_file", required=False,
        help="Path to write the generated SQL file (default: input_name.sql)"
    )

    args = parser.parse_args()

    input_path = args.input_file

    # Default output name: if input is data.csv → output is data.sql
    if args.output_file:
        output_path = args.output_file
    else:
        if input_path.lower().endswith(".csv"):
            output_path = input_path[:-4] + ".sql"
        else:
            output_path = input_path + ".sql"

    print(f"[+] Loading CSV: {input_path}")
    rows = load_classes_from_csv(input_path)

    print(f"[+] Converting {len(rows)} rows to SQL…")
    sql_groups = convert_to_sql(rows)

    print(f"[+] Writing SQL to: {output_path}")
    write_sql_to_file(output_path, sql_groups)

    print("[:)] Completed successfully.")

