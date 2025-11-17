import csv
import re

from subject_map import SUBJECT_NAME_MAP

def load_classes_from_csv(file_path):
    """
    Loads class data from a CSV file.
    :param file_path: Path to the CSV file containing class data
    :return: list of classes as dictionaries
    """
    classes = []
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames or []

        # for each class row, clean and store the data
        for row in reader:
            values = []
            for fn in fieldnames:
                v = row.get(fn)
                v = v.strip() if isinstance(v, str) else v
                values.append(v if v != '' else None)
            classes.append(values)

    return classes

def convert_to_sql(classes):
    """
    Converts class data into SQL insert statements.
    Data is organized into the following tables:
        term(term_id, label, academic_year)
        subject(subject_code, name)
        course (course_id, subject_code, course_number, title, credits, level)
        instructor (instructor_id, name_display)
        section (section_id, course_id, term_id, instructor_id, credits, graded_enrollment)
        grade_distribution (section_id, gpa, a, a_minus, b_plus, b, b_minus, c_plus,
            c, c_minus, d_plus, d, d_minus, f, withdraws, graded_enrollment)

    :param classes: List of class dictionaries
    :return: String containing SQL insert statements
    """
    # parses classes and generates SQL insert statements
    # for each class, generate insert statements for each table

    tables = {
        "subject": [],
        "term": [],
        "course": [],
        "instructor": [],
        "section": [],
        "grade_distribution": []
    }

    # Deduplication sets - track unique entries to avoid duplicates
    seen = {
        "subject": set(),
        "term": set(),
        "course": set(),
        "instructor": set(),
        "section": set(),
        "grade_distribution": set()
    }

    # maps for unique IDs
    instructor_ids = {}
    section_ids = {}

    next_instructor_id = 1
    next_section_id = 1

    # sql_statements = []
    for cls in classes:
        if not any(field.strip() for field in cls):
            continue  # skip empty rows

        acad_year = normalize_academic_year(cls[0])      # like "2024-2025"
        term_label = cls[1]     # like Fall 2025
        subject_code = cls[2]
        course_number = cls[3]
        course_title = cls[4]
        level = 'UG' if re.match(r'^[0-4]', course_number) else 'GR'
        instructor_name = cls[5]
        gpa = float(cls[6])
        a = float(cls[7])
        a_minus = float(cls[8])
        b_plus = float(cls[9])
        b = float(cls[10])
        b_minus = float(cls[11])
        c_plus = float(cls[12])
        c = float(cls[13])
        c_minus = float(cls[14])
        d_plus = float(cls[15])
        d = float(cls[16])
        d_minus = float(cls[17])
        f = float(cls[18])
        withdraws = int(cls[19])
        graded_enrollment = int(cls[20])
        course_id = cls[21]     # swap to CRN?
        credits = float(cls[22])

        # --- SUBJECT ---
        subject_name = SUBJECT_NAME_MAP.get(subject_code, subject_code)
        subj_key = subject_code

        if subj_key not in seen["subject"]:
            seen["subject"].add(subj_key)
            subject_code_esc = sql_escape(subject_code)
            subject_name_esc = sql_escape(subject_name)
            tables["subject"].append(f"('{subject_code_esc}', '{subject_name_esc}')")

        # --- TERM ---
        # Normalize academic year (e.g., "2023-24" → "2023-2024")
        acad_year = normalize_academic_year(acad_year)

        # Clean term label
        term_label_clean = term_label.strip().capitalize()

        # Compute deterministic VT-style term_id
        year_end = int(acad_year.split("-")[1])

        tl = term_label_clean.lower()
        if "spring" in tl:
            half = "01"
        elif "fall" in tl:
            half = "02"
        else:
            raise ValueError(f"Unknown term label: {term_label}")

        term_id = int(f"{year_end}{half}")

        # Deduplicate ONLY by term_id
        if term_id not in seen["term"]:
            seen["term"].add(term_id)
            tables["term"].append(
                f"({term_id}, '{sql_escape(term_label_clean)}', '{acad_year}')"
            )

        # --- INSTRUCTOR ---
        if instructor_name not in instructor_ids:
            instructor_ids[instructor_name] = next_instructor_id
            next_instructor_id += 1

            instructor_id = instructor_ids[instructor_name]
            instructor_name_esc = sql_escape(instructor_name)
            tables["instructor"].append(
                f"({instructor_id}, '{instructor_name_esc}')"
            )
        else:
            instructor_id = instructor_ids[instructor_name]

        # --- COURSE ---
        course_key = course_id
        # add check for subject and course number, remove check off course_id
        if course_key not in seen["course"]:
            seen["course"].add(course_key)
            course_title_esc = sql_escape(course_title)
            tables["course"].append(
                f"({course_id}, '{subject_code}', '{course_number}', "
                f"'{course_title_esc}', {credits}, '{level}')"
            )

        # --- SECTION ---
        section_key = (course_id, term_id, instructor_id)
        if section_key not in section_ids:
            section_ids[section_key] = next_section_id
            next_section_id += 1

            section_id = section_ids[section_key]
            tables["section"].append(
                f"({section_id}, {course_id}, {term_id}, {instructor_id}, "
                f"{credits}, {graded_enrollment})"
            )
        else:
            section_id = section_ids[section_key]

        # --- GRADE DISTRIBUTION ---
        gd_key = section_id  # 1:1 mapping, dedupe by section
        if gd_key not in seen["grade_distribution"]:
            seen["grade_distribution"].add(gd_key)
            tables["grade_distribution"].append(
                f"({section_id}, {gpa}, {a}, {a_minus}, {b_plus}, {b}, {b_minus}, "
                f"{c_plus}, {c}, {c_minus}, {d_plus}, {d}, {d_minus}, {f}, "
                f"{withdraws}, {graded_enrollment})"
            )

    return tables

def print_all_classes(classes):
    """
    Prints all classes in a formatted manner.
    :param classes: List of class dictionaries
    """
    # print header before printing classes
    print("Academic Year, Term, Subject, Course No., Course Title, Instructor, GPA, A(%), A-(%), B+(%), B(%), B-(%), "
          "C+(%), C(%), C-(%), D+(%), D(%), D-(%), F(%), Withdraws, Graded Enrollment, CRN, Credits")
    for cls in classes:
        print(cls)

def wrap_insert_block(table_name, columns, values_block):
    """
    Formats an insert block for SQL statements.
    :param table_name: Name of the table
    :param columns: List of column names
    :param values_block: String of values to insert
    :return: Formatted SQL insert statement
    """
    return (
        f"INSERT INTO {table_name} ({', '.join(columns)})\n"
        f"VALUES\n{values_block}\n"
        f"ON CONFLICT DO NOTHING;\n"
    )

def write_sql_to_file(output_file, sql_content):
    """
    Writes SQL content to a file.
    :param output_file: Path to the output SQL file
    :param sql_content: SQL content to write
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Auto-generated SQL insert statements\n")

        for table, entries in sql_content.items():
            if not entries:
                continue

            # map table -> columns
            columns = {
                "subject": ["subject_code", "name"],
                "term": ["term_id", "label", "academic_year"],
                "course": ["course_id", "subject_code", "course_number", "title", "credits", "level"],
                "instructor": ["instructor_id", "name_display"],
                "section": ["section_id", "course_id", "term_id", "instructor_id", "credits", "graded_enrollment"],
                "grade_distribution": [
                    "section_id", "gpa",
                    "a", "a_minus", "b_plus", "b", "b_minus", "c_plus", "c", "c_minus",
                    "d_plus", "d", "d_minus", "f",
                    "withdraws", "graded_enrollment"
                ]
            }[table]

            # Format VALUES block with indentation and commas
            formatted_values = ""
            last_index = len(entries) - 1
            for i, val in enumerate(entries):
                comma = "," if i != last_index else ""
                formatted_values += f"  {val}{comma}\n"

            # Write block
            f.write(
                f"INSERT INTO {table} ({', '.join(columns)})\n"
                f"VALUES\n"
                f"{formatted_values}"
                f"ON CONFLICT DO NOTHING;\n\n"
            )

def sql_escape(value: str) -> str:
    if value is None:
        return ""
    return value.replace("'", "''")

def get_term_id(term_name: str, academic_year: int) -> int:
    """
    Converts a term name and academic year into a term_id:
        Spring → XX01
        Fall   → XX02
    """
    name = term_name.lower()

    if "spring" in name:
        half = "01"
    elif "fall" in name:
        half = "02"
    else:
        raise ValueError(f"Unknown term name: {term_name}")

    return int(f"{academic_year}{half}")

def normalize_academic_year(ay: str) -> str:
    ay = ay.strip()
    parts = ay.split("-")

    if len(parts) != 2:
        raise ValueError(f"Invalid academic year format: {ay}")

    start = parts[0]
    end = parts[1]

    # Expand short years like "24" to "2024"
    if len(start) == 2:
        start = "20" + start
    if len(end) == 2:
        end = "20" + end

    return f"{start}-{end}"

if __name__ == "__main__":
    rows = load_classes_from_csv('vt_class_data_2025.csv')
    sql_groups = convert_to_sql(rows)
    write_sql_to_file('../db/init/003_seed.sql', sql_groups)
    print("SQL insert statements written to 003_seed.sql")