# CO Implementation Guide — First Sprint Plan, Stubs & Seeds (v0.2)

This is a practical, copy‑pasteable guide to bring the Curriculum Orchestrator (CO) online and make it useful **even if your Problem Bank is empty** today. It includes infra bootstrap, minimal FastAPI stubs, migrations, seed content, and E2E tests.

---

## 0) High‑level sprint goals (7–10 days)

1. **Run CO locally** with Postgres + Redis + OpenTelemetry, behind one container.
2. Expose **/v1/tracks, /v1/sessions, /v1/submissions, /v1/tutor/messages** with working logic.
3. Wire **Eval client** (scimigo‑eval) and **Problem Bank client** (internal). Provide fallbacks when bank is empty.
4. Create a **private seed** of 8–12 coding problems via CoursePack (no public dataset needed).
5. Ship a **thin UI** hookup from coding.scimigo.com to CO for a single track.

---

## 1) Local dev stack

**docker/docker-compose.dev.yml**

```yaml
version: '3.9'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: co
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    environment:
      CO_DB_URL: postgresql+psycopg2://postgres:postgres@db:5432/co
      CO_REDIS_URL: redis://redis:6379/0
      API_BASE: http://host.docker.internal:9000   # api.scimigo.com dev
      EVAL_BASE: http://host.docker.internal:9100  # scimigo-eval-services dev
      PROBLEM_BANK_BASE: http://host.docker.internal:9200
      TUTOR_BASE: http://host.docker.internal:9000
      OTEL_EXPORTER_OTLP_ENDPOINT: http://host.docker.internal:4317
    ports: ["8080:8080"]
    depends_on: [db, redis]
```

**docker/Dockerfile.api**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir uvicorn gunicorn
RUN pip install --no-cache-dir fastapi pydantic-settings pydantic[dotenv] sqlalchemy alembic psycopg2-binary httpx redis opentelemetry-sdk opentelemetry-exporter-otlp
COPY src/ /app/src/
COPY alembic.ini /app/
COPY migrations/ /app/migrations/
ENV PYTHONPATH=/app
CMD ["uvicorn","src.co.server:app","--host","0.0.0.0","--port","8080"]
```

---

## 2) App skeleton (FastAPI)

**src/co/server.py**

```python
from fastapi import FastAPI
from .routes import tracks, sessions, submissions, tutor
from .config import settings

app = FastAPI(title="Scimigo CO", version="0.1.0")
app.include_router(tracks.router, prefix="/v1")
app.include_router(sessions.router, prefix="/v1")
app.include_router(submissions.router, prefix="/v1")
app.include_router(tutor.router, prefix="/v1")
```

**src/co/config.py**

```python
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    CO_DB_URL: str
    CO_REDIS_URL: str
    API_BASE: str
    EVAL_BASE: str
    PROBLEM_BANK_BASE: str
    TUTOR_BASE: str
    class Config:
        env_file = ".env"
settings = Settings()
```

---

## 3) DB models + migrations

**src/co/db/base.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config import settings

engine = create_engine(settings.CO_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
```

**src/co/db/models.py** (subset)

```python
from sqlalchemy import Column, String, Integer, JSON, TIMESTAMP, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class Track(Base):
    __tablename__ = "tracks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    labels = Column(JSON, nullable=False, default=list)
    modules = Column(JSON, nullable=False, default=list)
    version = Column(String, nullable=False, default="v1")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    subject = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    problem_id = Column(Text)
    status = Column(String, nullable=False, default="active")
    last_hint_level = Column(Integer, nullable=False, default=0)
    started_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    problem_id = Column(Text, nullable=False)
    subject = Column(String, nullable=False)
    language = Column(String)
    status = Column(String, nullable=False)
    visible_passed = Column(Integer, nullable=False, default=0)
    visible_total = Column(Integer, nullable=False, default=0)
    hidden_passed = Column(Integer, nullable=False, default=0)
    hidden_total = Column(Integer, nullable=False, default=0)
    categories = Column(JSON, nullable=False, default=list)
    exec_ms = Column(Integer, nullable=False, default=0)
    payload_sha256 = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
```

**Alembic migration**: generate from the SQL you already have in the seed doc (copy those tables as‑is).

---

## 4) Routes — minimal working endpoints

**src/co/routes/tracks.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.base import SessionLocal
from ..db import models

router = APIRouter()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/tracks")
def list_tracks(subject: str | None = None, label: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Track)
    if subject: q = q.filter(models.Track.subject == subject)
    if label: q = q.filter(models.Track.labels.contains([label]))
    items = [
        {
            "id": str(t.id),
            "slug": t.slug,
            "subject": t.subject,
            "title": t.title,
            "labels": t.labels,
            "modules": t.modules,
        } for t in q.all()
    ]
    return {"items": items}
```

**src/co/routes/sessions.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.base import SessionLocal
from ..db import models
import uuid

router = APIRouter()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.post("/sessions")
def create_session(payload: dict, db: Session = Depends(get_db)):
    sess = models.Session(
        user_id=uuid.UUID(payload.get("user_id","00000000-0000-0000-0000-000000000000")),
        subject=payload["subject"],
        mode=payload.get("mode","practice"),
        track_id=uuid.UUID(payload["track_id"]) if payload.get("track_id") else None,
        problem_id=payload.get("problem_id")
    )
    db.add(sess); db.commit(); db.refresh(sess)
    return {"id": str(sess.id), "status": sess.status, "subject": sess.subject, "mode": sess.mode}
```

**src/co/routes/submissions.py** (stub)

```python
from fastapi import APIRouter
router = APIRouter()

@router.post("/submissions")
async def submit_attempt(payload: dict):
    # TODO: 1) fetch hidden tests via Problem Bank client
    #       2) call Eval service and map result → categories
    #       3) persist Submission
    # For now, return a mocked failure to prove UI wiring
    return {
        "status": "failed",
        "visible": {"passed": 2, "total": 4, "details": []},
        "hidden": {"passed": 1, "total": 3, "categories": ["duplicates"]},
        "exec_ms": 120
    }
```

**src/co/routes/tutor.py** (stub)

```python
from fastapi import APIRouter
router = APIRouter()

@router.post("/tutor/messages")
async def start_tutor_turn(payload: dict):
    # TODO: forward to api.scimigo.com tutor endpoint and return stream token/URL
    return {"stream_url": "/v1/tutor/stream?token=dummy", "token": "dummy"}
```

---

## 5) Problem Bank client (works when empty)

**src/co/clients/problem\_bank.py**

```python
import httpx, os
BASE = os.getenv("PROBLEM_BANK_BASE")

async def get_problem_bundle(problem_id: str) -> dict | None:
    # expected to return {statement, visible_tests, hidden_spec}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{BASE}/internal/problems/{problem_id}/bundle")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception:
        return None
```

**Behavior when empty:** `get_problem_bundle` returns `None`; `/submissions` can short‑circuit with a friendly error or fallback to **LLM coaching only** (no hidden tests), so you can demo the flow before seeding.

---

## 6) Seeding without a public dataset

Create a **private CoursePack** with 8–12 problems and ingest via a simple script.

**seed/track.meta.json**

```json
{
  "slug": "coding-interview-meta",
  "subject": "coding",
  "title": "Meta Coding Interview Prep (Pilot)",
  "labels": ["company:meta"],
  "modules": [
    {"id": "arrays-strings", "title": "Arrays & Strings", "outcomes": ["two-pointers","sliding-window"]},
    {"id": "hashing", "title": "Hash Maps & Sets", "outcomes": ["hash-map"]}
  ]
}
```

**scripts/seed\_tracks.py**

```python
import json, uuid
from src.co.db.base import SessionLocal
from src.co.db.models import Track

with open("seed/track.meta.json") as f:
    meta = json.load(f)

db = SessionLocal()
try:
    t = Track(slug=meta["slug"], subject=meta["subject"], title=meta["title"], labels=meta["labels"], modules=meta["modules"]) 
    db.add(t); db.commit()
finally:
    db.close()
print("Seeded track")
```

**Minimal Problem Bank seed** (temporary endpoint): stand up a tiny Node/Express or FastAPI app that serves `GET /internal/problems/:id/bundle` from local JSON files.

`problem-bank-dev/problems/two-sum.bundle.json`

```json
{
  "id": "two-sum",
  "statement": "Return indices i<j such that nums[i]+nums[j]==t; lexicographically smallest pair or (-1,-1).",
  "visible_tests": [
    {"input": {"nums": [2,7,11,15], "t": 9}, "expect": [0,1]},
    {"input": {"nums": [3,3], "t": 6}, "expect": [0,1]}
  ],
  "hidden_spec": {
    "generator": {"seeds": [1,2], "cases": ["duplicates","negatives","large-n"]},
    "time_limit_ms": 200, "mem_limit_mb": 128
  }
}
```

---

## 7) Eval client stub

**src/co/clients/eval\_service.py**

```python
import httpx, os
BASE = os.getenv("EVAL_BASE")

async def run_code(language: str, code: str, harness: dict, hidden_spec: dict) -> dict:
    payload = {"language": language, "code": code, "harness": harness, "hidden_spec": hidden_spec}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE}/code/eval", json=payload)
        r.raise_for_status()
        return r.json()
```

---

## 8) Wiring /submissions (pseudo)

```python
bundle = await problem_bank.get_problem_bundle(problem_id)
if not bundle: return HTTP 409 { error: "Problem repository not ready" }
result = await eval_service.run_code(language, code, bundle["visible_tests"], bundle["hidden_spec"])
# map result → categories, persist Submission, return SubmissionResult
```

---

## 9) E2E smoke tests (pytest)

**tests/e2e/test\_tracks.py**

```python
import httpx

def test_list_tracks_local():
    r = httpx.get("http://localhost:8080/v1/tracks")
    assert r.status_code == 200
```

**tests/e2e/test\_sessions.py**

```python
import httpx, uuid

def test_create_session():
    payload = {"user_id": str(uuid.uuid4()), "subject": "coding", "mode": "practice"}
    r = httpx.post("http://localhost:8080/v1/sessions", json=payload)
    assert r.status_code == 200 or r.status_code == 201
```

---

## 10) Frontend wiring (coding.scimigo.com)

* **Fetch tracks**: `GET /v1/tracks?subject=coding&label=company:meta`
* **Start session**: `POST /v1/sessions`
* **Load problem**: your IDE reads `statement` and `visible_tests` from **Problem Bank public** endpoint (or CO can proxy this later).
* **Submit**: `POST /v1/submissions` with `{ session_id, problem_id, subject:'coding', payload:{ language, code } }`.
* **Tutor**: `POST /v1/tutor/messages` → use returned `stream_url` (SSE).

---

## 11) Telemetry

Emit events from CO with a common shape: `{event, user_id, session_id, problem_id, ts, attrs}` for `problem_open`, `attempt_run`, `attempt_submit`, `hint_request(level)`, `mock_finish`, `recommendation_served`.

---

## 12) Next steps after MVP

* Replace stubbed `/submissions` with real eval + hidden categories mapping.
* Implement **personalization**: compute mastery deltas and select next item.
* Build **CourseKit ingestion**: validate CoursePack, publish to tracks/modules/units.
* Harden auth & quotas; add org/tenant s

