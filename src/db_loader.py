import csv
import re

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
    sql_statements = []
    for cls in classes:
        acad_year = cls[0]
        term = cls[1]
        subject_code = cls[2]
        subject_name = cls[2]
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
        course_id = cls[21]
        credits = float(cls[22])

        sql_statements.append(sql_for_term(1,term, acad_year))
        sql_statements.append(sql_for_subject(subject_code, subject_name))
        sql_statements.append(sql_for_course(course_id, subject_code, course_number,
                                            course_title, credits, level))
        sql_statements.append(sql_for_instructor(1, instructor_name))
        sql_statements.append(sql_for_section(course_id, 1, 1, credits, graded_enrollment))
        sql_statements.append(sql_for_grade_distribution(course_id, gpa, a, a_minus, b_plus, b, b_minus,
                                                        c_plus, c, c_minus, d_plus, d, d_minus, f,
                                                        withdraws, graded_enrollment))
        # TODO: figure out how to determine term_id, instructor_id, section_id, and subject_name properly.

    return "\n".join(sql_statements)

def sql_for_subject(subject_code, name):
    """
    Generates SQL insert statement for subject table.
    """
    return f"INSERT INTO subject (subject_code, name) VALUES ('{subject_code}', '{name}');"

def sql_for_term(term_id, label, academic_year):
    """
    Generates SQL insert statement for term table.
    """
    return f"INSERT INTO term (term_id, label, academic_year) " \
           f"VALUES ({term_id}, '{label}', '{academic_year}');"

def sql_for_course(course_id, subject_code, course_number, title, credits, level):
    """
    Generates SQL insert statement for course table.
    """
    return f"INSERT INTO course (course_id, subject_code, course_number, title, credits, level) "\
           f"VALUES ({course_id}, '{subject_code}', '{course_number}', '{title}', {credits}, '{level}');"

def sql_for_instructor(instructor_id, name_display):
    """
    Generates SQL insert statement for instructor table.
    """
    return f"INSERT INTO instructor (instructor_id, name_display) "\
           f"VALUES ({instructor_id}, '{name_display}');"

def sql_for_section(course_id, term_id, instructor_id, credits, graded_enrollment):
    """
    Generates SQL insert statement for section table.
    """
    return f"INSERT INTO section (course_id, term_id, instructor_id, credits, graded_enrollment) "\
           f"VALUES ({course_id}, {term_id}, {instructor_id}, {credits}, {graded_enrollment});"

def sql_for_grade_distribution(section_id, gpa, a, a_minus, b_plus, b, b_minus,
                               c_plus, c, c_minus, d_plus, d, d_minus, f,
                               withdraws, graded_enrollment):
    """
    Generates SQL insert statement for grade_distribution table.
    """
    return f"INSERT INTO grade_distribution (section_id, gpa, a, a_minus, b_plus, b, b_minus, c_plus, "\
           f"c, c_minus, d_plus, d, d_minus, f, withdraws, graded_enrollment) "\
           f"VALUES ({section_id}, {gpa}, {a}, {a_minus}, {b_plus}, {b}, {b_minus}, {c_plus}, "\
           f"{c}, {c_minus}, {d_plus}, {d}, {d_minus}, {f}, {withdraws}, {graded_enrollment});"

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

if __name__ == "__main__":
    rows = load_classes_from_csv('vt_class_data_2025.csv')
    print_all_classes(rows[:1])  # Print first 5 classes for brevity
    sql_output = convert_to_sql(rows[:1])  # Convert first 5 classes to SQL for brevity
    print(sql_output)