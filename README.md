# VT Data Commons NLP Demo

Full‑stack demo that lets you query Virginia Tech Data Commons course/grade data with natural language. It uses **spaCy** for lightweight parsing, **FastAPI** for the API, **PostgreSQL** for storage, **Vite + React** for the UI, and **Adminer** for DB inspection.

---

## Quickstart

Prereqs: Docker + Docker Compose.

```bash
git clone https://github.com/Cbrodish03/NLP-DBMS.git
cd NLP-DBMS
docker compose up --build
```

Services (default ports):
- Frontend (Vite): http://localhost:3000
- Backend (FastAPI): http://localhost:8000
- Postgres: localhost:5433 (mapped to container 5432)
- Adminer: http://localhost:8081

Stop: `Ctrl+C` or `docker compose down` (add `-v` to drop the DB volume).

---

## Stack (at a glance)

| Component       | Tech                   | Purpose                                      |
|-----------------|------------------------|----------------------------------------------|
| Frontend        | React + Vite           | Single-page UI for natural-language queries  |
| Backend API     | FastAPI (Python) + spaCy | NLP parsing + REST API to Postgres           |
| Database        | PostgreSQL 16          | Stores subjects, courses, instructors, terms, sections, grades |
| Adminer         | Adminer (PHP)          | Web UI for DB inspection                     |
| Orchestration   | Docker Compose         | Runs all services together                   |

---

## Docker Compose layout

| Service   | Container name | Port(s)              | Volumes                             | Notes                                  |
|-----------|----------------|----------------------|-------------------------------------|----------------------------------------|
| db        | `nlp_db`       | 5433→5432            | `pgdata` (data), `./db/init` seeds  | Healthcheck ensures DB readiness       |
| backend   | `nlp_backend`  | 8000→8000            | `./backend:/app`                    | Uvicorn auto-reload                    |
| frontend  | `nlp_frontend` | 3000→5173            | `./frontend:/app`, `frontend_node_modules_v2` | Vite dev server with HMR                |
| adminer   | `nlp_adminer`  | 8081→8080            | —                                   | DB browser                             |

Stop/start: `docker compose down` / `docker compose up --build`. Add `-v` to drop the DB volume.

---

## Architecture

```
[React + Vite]  →  [FastAPI + spaCy]  →  [Postgres]
        ↑                       ↘
        │                        ↘
     User UI                 Adminer GUI
```

The frontend calls `/query` with free text; the backend parses and issues SQL; results are rendered in the UI. Adminer is available for direct DB browsing.

---

## Database Schema

- `subject(subject_code, name)`
- `term(term_id, label, academic_year)`
- `course(course_id, subject_code, course_number, title, credits, level)`
- `instructor(instructor_id, name_display)`
- `section(section_id, course_id, term_id, instructor_id, section_credits, section_graded_enrollment)`
- `grade_distribution(section_id, gpa, a, a_minus, b_plus, b, b_minus, c_plus, c, c_minus, d_plus, d, d_minus, f, withdraws, graded_enrollment)`

Loaded automatically from `db/init/001_schema.sql` and `db/init/002_seed.sql`.

---

## Example query flow

1) User types `CS 2104` in the frontend.  
2) Backend detects subject+course via regex/spaCy and builds a plan.  
3) SQL joins course, section, instructor, term, and grade data.  
4) Response includes sections, aggregates, and parser debug metadata.

---

## Backend API

**Health:** `GET /healthz` → `{ "status": "ok", "db_ok": true/false }`

**Query:** `POST /query`
```json
{ "query": "cs 2104" }
```
Returns:
```json
{
  "ok": true,
  "meta": { "query": "cs 2104", "intent": "course_lookup", "confidence": 1.0, "filters": { ... }, "debug": { ... } },
  "sections": [ { "section_id": 1, "course": { "subject_code": "CS", "course_number": "2104", "title": "...", "level": "UG" }, "term": { "label": "Fall 2023" }, "instructor": { "name_display": "..." }, "grades": { "gpa": 3.2, "graded_enrollment": 120, "breakdown": { ... } } } ],
  "aggregates": { "section_count": 1, "avg_gpa": 3.2, "total_graded_enrollment": 120 },
  "subjects": null
}
```

**Parser coverage (rule-based, spaCy + regex):**
- Subject + course: `CS 2104`, `MATH-1224`, `CS 2xxx`
- Subject-only: `cs`, `math`
- Course ranges/levels: `1000-2000`, `200 level`, `1000 level`
- GPA thresholds: `gpa above 3.5`, `gpa below 2.5`
- Terms: `Fall 2023`, `Spring '24`, `last spring`
- Instructors: `with Wyatt`, PERSON entities
- Titles: quoted phrases or meaningful leftover tokens
- Credits/enrollment bounds: `3 credits`, `enrollment between 50 and 120`
- Grade constraints: `5 students got an A`, `40% A or above`, `no Ds or Fs`, comparisons (`more A than B`)
- Ranking hints: `largest 5`, `smallest 3` (by enrollment)

If parsing fails to find strong filters, intent becomes `browse_subjects` and the frontend shows available subjects.

---

## Frontend

- Vite + React, served at http://localhost:3000 (proxied to backend on :8000).
- Query input with local sort/pagination; debug copy helper to inspect `meta` returned by the API.
- Routes: `/` (home/results), `/course/:id` (detail placeholder).
- Hot reload when running via Docker volumes (`./frontend:/app`).

---

## Backend notes

- FastAPI + Uvicorn with auto-reload (in Docker: `./backend:/app` volume).
- spaCy model: `en_core_web_sm` (downloaded during Docker build or via `python -m spacy download en_core_web_sm`).
- DB connection envs (see `docker-compose.yml`): `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`, `POSTGRES_DB=nlp`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`.

---

## Local development (without Docker)

Backend:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
export POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=nlp POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev -- --host --port 3000
```

Ensure Postgres is running with the seed data from `db/init/`.

---

## Data loader (CSV → SQL)

`db/tools/db_loader.py` converts CSV exports into conflict-safe INSERTs.
```bash
python3 db/tools/db_loader.py --in input.csv --out output.sql
```
If `--out` is omitted, a `.sql` file is created beside the CSV.

---

## Adminer

http://localhost:8081  
Login:
```
System: PostgreSQL
Server: db
Username: postgres
Password: postgres
Database: nlp
```

---

## Useful commands

- `docker compose up --build` — build and start all services
- `docker compose down` — stop and remove containers
- `docker compose down -v` — stop and remove containers + DB volume
- `docker compose logs -f backend` — tail backend logs
- `docker exec -it nlp_db psql -U postgres -d nlp` — psql inside the DB container
