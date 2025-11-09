import os
import re
from typing import List, Dict, Any

import spacy
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

app = FastAPI(title="VT UDC NLP API")

# CORS: frontend runs at http://localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB helper ----------

def get_db_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "nlp"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


# ---------- Models ----------

class QueryRequest(BaseModel):
    query: str


# ---------- Routes ----------

@app.get("/healthz")
def health():
    # quick DB connectivity check
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    return {"status": "ok", "db_ok": db_ok}


@app.post("/query")
def query_endpoint(req: QueryRequest):
    """
    Full-stack demo:
    - Use spaCy to tokenize the query
    - Extract something that looks like 'CS 2104'
    - If found, query course + section + grade distribution
    - If not, just return all subjects
    """

    doc = nlp(req.query)
    tokens = [t.text for t in doc]

    text_up = req.query.upper()

    # Try to find something like "CS 2104"
    m = re.search(r"\b([A-Z]{2,4})\s*([0-9]{4})\b", text_up)
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        if m:
            subject_code, course_number = m.group(1), m.group(2)

            sql = """
                SELECT
                    s.subject_code,
                    c.course_number,
                    c.title,
                    t.label AS term_label,
                    i.name_display AS instructor,
                    gd.gpa,
                    gd.a, gd.a_minus, gd.b_plus, gd.b, gd.b_minus,
                    gd.c_plus, gd.c, gd.c_minus,
                    gd.d_plus, gd.d, gd.d_minus,
                    gd.f,
                    gd.withdraws,
                    gd.graded_enrollment
                FROM subject s
                JOIN course c ON c.subject_code = s.subject_code
                JOIN section sec ON sec.course_id = c.course_id
                JOIN term t ON t.term_id = sec.term_id
                JOIN instructor i ON i.instructor_id = sec.instructor_id
                JOIN grade_distribution gd ON gd.section_id = sec.section_id
                WHERE s.subject_code = %s AND c.course_number = %s
                ORDER BY t.term_id DESC;
            """

            cur.execute(sql, (subject_code, course_number))
            rows = cur.fetchall()

            cols = [desc[0] for desc in cur.description]
            results: List[Dict[str, Any]] = [
                dict(zip(cols, row)) for row in rows
            ]

            cur.close()
            conn.close()

            return {
                "ok": True,
                "mode": "course_lookup",
                "query": req.query,
                "course_matches": results,
                "debug": {
                    "subject_code": subject_code,
                    "course_number": course_number,
                    "tokens": tokens,
                },
            }

        # Fallback: show all subjects
        cur.execute("SELECT subject_code, name FROM subject ORDER BY subject_code;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        subjects = [{"subject_code": r[0], "name": r[1]} for r in rows]

        return {
            "ok": True,
            "mode": "subjects",
            "query": req.query,
            "subjects": subjects,
            "tokens": tokens,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "query": req.query,
            "tokens": tokens,
        }
