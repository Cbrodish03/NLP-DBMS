# VT Data Commons NLP Demo

A full-stack containerized application that allows users to query **Virginia Tech Data Commons** course and grade data using **natural language**.  
It uses **spaCy** for lightweight NLP, **FastAPI** for the backend, **PostgreSQL** for structured storage, **Vite + React** for the frontend, and **Adminer** for database inspection.

---

## Overview

### Stack
| Component | Tech | Purpose |
|------------|------|----------|
| **Frontend** | React + Vite | Interactive single-page UI with a simple query box |
| **Backend API** | FastAPI (Python) + spaCy | NLP parsing and SQL querying |
| **Database** | PostgreSQL 16 | Stores terms, subjects, courses, instructors, sections, and grade distributions |
| **Adminer** | Adminer (PHP GUI) | Visual DB browser / SQL console |
| **Orchestration** | Docker Compose | Runs all services in isolated containers |

---

## Architecture

```
[React + Vite]  →  [FastAPI + spaCy]  →  [Postgres]
        ↑                       ↘
        │                        ↘
     User UI                 Adminer GUI
```

- The **frontend** sends text queries (e.g. “show CS 2104”) to `/query` on the backend.
- The **backend** uses spaCy to tokenize and extract course identifiers, then runs SQL queries against Postgres.
- The **database** returns course and grade information which is rendered in the UI.
- **Adminer** lets you visually browse and verify the schema or data.

---

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/Cbrodish03/NLP-DBMS.git
cd NLP-DBMS
```

### 2. Build and start the stack

```bash
docker compose up --build
```

That launches:

| Service | URL | Description |
|----------|-----|--------------|
| **Frontend (Vite)** | http://localhost:3000 | React app with the query UI |
| **Backend (FastAPI)** | http://localhost:8000 | REST API + spaCy NLP engine |
| **Database (Postgres)** | localhost:5432 | Core UDC schema + seed data |
| **Adminer** | http://localhost:8080 | Web-based DB viewer |

*(Use `Ctrl+C` to stop, or `docker compose down` to clean up.)*

---

## Database Schema

**Entities:**
- `subject(subject_code, name)`
- `term(term_id, label, academic_year)`
- `course(course_id, subject_code, course_number, title, credits, level)`
- `instructor(instructor_id, name_display)`
- `section(section_id, course_id, term_id, instructor_id, credits, graded_enrollment)`
- `grade_distribution(section_id, gpa, a, a_minus, b_plus, …, withdraws, graded_enrollment)`

All schema and seed data are automatically loaded from:
```
db/init/001_schema.sql
db/init/002_seed.sql
```

---

## Example Query Flow

1. In the browser, type:
   ```
   CS 2104
   ```
2. The backend detects `CS` (subject) and `2104` (course number) via regex and spaCy tokenization.
3. A SQL query joins course, section, instructor, term, and grade data.
4. The result is rendered in the frontend:

```json
{
  "subject_code": "CS",
  "course_number": "2104",
  "title": "Intro to Problem Solving in CS",
  "term_label": "Spring 2024",
  "instructor": "Boyer, John",
  "gpa": 3.2,
  "graded_enrollment": 100
}
```

---

## Development Notes

### Frontend (Vite + React)
- Hot reload enabled via volume mount (`./frontend:/app`)
- Dev server runs on port **5173** inside container → mapped to **localhost:3000**

### Backend (FastAPI + spaCy)
- Uvicorn runs in auto-reload mode.
- Environment variables are injected via `docker-compose.yml`:
  ```bash
  POSTGRES_HOST=db
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_DB=vt_nlp
  ```

### Database (PostgreSQL)
- Persistent volume `pgdata` stores data across restarts.
- Health check ensures the DB is ready before the backend connects.

### Adminer
- Visit [http://localhost:8080](http://localhost:8080)
- Login:
  ```
  System: PostgreSQL
  Server: db
  Username: postgres
  Password: postgres
  Database: vt_nlp
  ```

---

## Testing the Stack

After running `docker compose up`:

- Frontend: open **http://localhost:3000**
- Type **`CS 2104`** and click **Run query**
- You should see the demo course and grade info from the seed data.

---

## Useful Commands

| Command | Description |
|----------|-------------|
| `docker compose up --build` | Build and start all containers |
| `docker compose down` | Stop and remove containers |
| `docker compose down -v` | Stop and remove containers + database volume |
| `docker compose logs -f backend` | Tail backend logs |
| `docker exec -it vt_nlp_db psql -U postgres -d vt_nlp` | Open psql shell inside DB |

---
