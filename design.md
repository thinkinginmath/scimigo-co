# CO Repo Scaffold, OpenAPI, and Seed SQL (v0.1)

## A) Repository tree (FastAPI + Postgres + Redis)

```
scimigo-curriculum-orchestrator/
├─ .github/
│  └─ workflows/
│     ├─ ci.yml                     # lint, typecheck, tests
│     └─ cd.yml                     # deploy to staging/prod
├─ infra/
│  ├─ cdk/                          # or terraform/ — pick one
│  └─ k8s/                          # manifests/helm (if k8s)
├─ docker/
│  ├─ Dockerfile.api
│  ├─ Dockerfile.migrations
│  └─ docker-compose.dev.yml        # api + pg + redis + adminer
├─ migrations/
│  └─ versions/                     # Alembic migration scripts
├─ src/
│  ├─ co/__init__.py
│  ├─ co/config.py                  # env, settings
│  ├─ co/server.py                  # FastAPI app factory
│  ├─ co/routes/
│  │  ├─ tracks.py                  # GET /v1/tracks, /v1/tracks/{id}
│  │  ├─ sessions.py                # POST/PATCH /v1/sessions
│  │  ├─ submissions.py             # POST /v1/submissions
│  │  └─ tutor.py                   # POST /v1/tutor/messages, GET /v1/tutor/stream (proxy)
│  ├─ co/services/
│  │  ├─ tracks.py                  # Track Manager
│  │  ├─ sessions.py                # Session Engine
│  │  ├─ evaluators/
│  │  │  ├─ coding.py               # adapter → scimigo-eval-services
│  │  │  └─ math.py                 # adapter → api.scimigo tools (SymPy, etc.)
│  │  ├─ tutor.py                   # orchestrator client (SSE producer)
│  │  ├─ personalization.py         # mastery, recommendations
│  │  └─ remediation.py             # failure→drill mapping
│  ├─ co/clients/
│  │  ├─ problem_bank.py            # internal-only: fetch hidden bundles
│  │  ├─ eval_service.py            # code runner client
│  │  └─ tutor_api.py               # LLM/tutor API client
│  ├─ co/db/
│  │  ├─ base.py                    # SQLAlchemy engine/session
│  │  ├─ models.py                  # ORM models
│  │  └─ repo.py                    # query helpers (sessions/submissions/...)
│  ├─ co/schemas/
│  │  ├─ common.py                  # Pydantic models (Problem, Submission, ...)
│  │  ├─ tracks.py
│  │  ├─ sessions.py
│  │  ├─ submissions.py
│  │  ├─ tutor.py
│  │  └─ progress.py
│  ├─ co/auth.py                    # JWT verify (api.scimigo.com issuer)
│  ├─ co/middleware.py              # request id, rate limit, CORS
│  ├─ co/telemetry.py               # OpenTelemetry/metrics/events
│  └─ co/tasks/
│     └─ scheduler.py               # spaced review queue worker (RQ/Celery)
├─ tests/
│  ├─ e2e/
│  └─ unit/
├─ openapi/
│  └─ co.v1.yaml                    # spec kept in-repo
├─ pyproject.toml
├─ alembic.ini
├─ README.md
└─ LICENSE
```

**Notes**

* Keep public endpoints under `/v1/*` and mirror the unified portal contracts (subject‑agnostic submissions, tutor SSE events).
* SSE stream can be proxied here or remain in `api.scimigo.com`; CO should at least expose `/v1/tutor/messages` to initiate a turn and return a stream token.

---

## B) Tiny OpenAPI (first endpoints)

```yaml
openapi: 3.0.3
info:
  title: Scimigo Curriculum Orchestrator API
  version: 0.1.0
servers:
  - url: https://co.scimigo.com/v1
paths:
  /tracks:
    get:
      summary: List tracks
      parameters:
        - in: query
          name: subject
          schema: { type: string, enum: [coding, math, systems] }
        - in: query
          name: label
          schema: { type: string }
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items: { $ref: '#/components/schemas/Track' }
  /tracks/{id}:
    get:
      summary: Get a track by id or slug
      parameters:
        - in: path
          name: id
          required: true
          schema: { type: string }
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Track' }
  /sessions:
    post:
      summary: Create a study or practice session
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SessionCreate'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Session' }
  /sessions/{id}:
    patch:
      summary: Update a session
      parameters:
        - in: path
          name: id
          required: true
          schema: { type: string }
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                action:
                  type: string
                  enum: [advance, retry, giveup]
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Session' }
  /submissions:
    post:
      summary: Submit an attempt (subject‑agnostic)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/SubmissionCodingCreate'
                - $ref: '#/components/schemas/SubmissionMathCreate'
      responses:
        '200':
          description: Evaluation result
          content:
            application/json:
              schema: { $ref: '#/components/schemas/SubmissionResult' }
  /tutor/messages:
    post:
      summary: Start a tutor turn for a session
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/TutorMessageCreate' }
      responses:
        '202':
          description: Accepted; stream token issued
          content:
            application/json:
              schema:
                type: object
                properties:
                  stream_url: { type: string }
                  token: { type: string }
components:
  schemas:
    Track:
      type: object
      properties:
        id: { type: string }
        slug: { type: string }
        subject: { type: string }
        title: { type: string }
        modules:
          type: array
          items:
            type: object
            properties:
              id: { type: string }
              title: { type: string }
              outcomes: { type: array, items: { type: string } }
    SessionCreate:
      type: object
      required: [subject]
      properties:
        subject: { type: string, enum: [coding, math, systems] }
        mode: { type: string, enum: [practice, mock, track] }
        track_id: { type: string }
        problem_id: { type: string }
    Session:
      type: object
      properties:
        id: { type: string }
        user_id: { type: string }
        subject: { type: string }
        mode: { type: string }
        status: { type: string }
        last_hint_level: { type: integer }
        created_at: { type: string, format: date-time }
    SubmissionCodingCreate:
      type: object
      required: [session_id, problem_id, subject, payload]
      properties:
        session_id: { type: string }
        problem_id: { type: string }
        subject: { type: string, enum: [coding] }
        payload:
          type: object
          properties:
            language: { type: string, enum: [python, javascript] }
            code: { type: string }
    SubmissionMathCreate:
      type: object
      required: [session_id, problem_id, subject, payload]
      properties:
        session_id: { type: string }
        problem_id: { type: string }
        subject: { type: string, enum: [math] }
        payload:
          type: object
          properties:
            steps: { type: array, items: { type: string } }
            expression: { type: string }
    SubmissionResult:
      type: object
      properties:
        status: { type: string, enum: [passed, failed, timeout, error] }
        visible:
          type: object
          properties:
            passed: { type: integer }
            total: { type: integer }
            details: { type: array, items: { type: object } }
        hidden:
          type: object
          properties:
            passed: { type: integer }
            total: { type: integer }
            categories: { type: array, items: { type: string } }
        exec_ms: { type: integer }
    TutorMessageCreate:
      type: object
      required: [session_id, problem_id, hint_level]
      properties:
        session_id: { type: string }
        problem_id: { type: string }
        hint_level: { type: integer, minimum: 1, maximum: 3 }
        last_eval: { type: object }
```

---

## C) Seed SQL (Postgres) — sessions, submissions, mastery, review\_queue, rubrics

```sql
-- UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users table is assumed to live upstream; we store the user_id as UUID

-- Tracks (published by CourseKit or generic tracks)
CREATE TABLE IF NOT EXISTS tracks (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         TEXT UNIQUE NOT NULL,
  subject      TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  title        TEXT NOT NULL,
  labels       JSONB NOT NULL DEFAULT '[]',  -- e.g., ["course:UIUC-MATH-241"]
  modules      JSONB NOT NULL DEFAULT '[]',  -- denormalized module index
  version      TEXT NOT NULL DEFAULT 'v1',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL,
  subject         TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  mode            TEXT NOT NULL CHECK (mode IN ('practice','mock','track')),
  track_id        UUID REFERENCES tracks(id),
  problem_id      TEXT,
  status          TEXT NOT NULL DEFAULT 'active', -- active|completed|abandoned
  last_hint_level INT  NOT NULL DEFAULT 0,
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_track ON sessions(track_id);

-- Submissions
CREATE TABLE IF NOT EXISTS submissions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id        UUID NOT NULL,
  problem_id     TEXT NOT NULL,
  subject        TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  language       TEXT,                 -- for coding
  status         TEXT NOT NULL CHECK (status IN ('passed','failed','timeout','error')),
  visible_passed INT  NOT NULL DEFAULT 0,
  visible_total  INT  NOT NULL DEFAULT 0,
  hidden_passed  INT  NOT NULL DEFAULT 0,
  hidden_total   INT  NOT NULL DEFAULT 0,
  categories     JSONB NOT NULL DEFAULT '[]',  -- failure categories
  exec_ms        INT  NOT NULL DEFAULT 0,
  payload_sha256 TEXT,                 -- hash of user code or math content
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_submissions_session ON submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);

-- Mastery (topic- and outcome-based)
CREATE TABLE IF NOT EXISTS mastery (
  user_id     UUID NOT NULL,
  key_type    TEXT NOT NULL CHECK (key_type IN ('topic','outcome')),
  key_id      TEXT NOT NULL,        -- e.g., topic 'sliding-window' or outcome 'LO1'
  score       INT  NOT NULL CHECK (score BETWEEN 0 AND 100),
  ema         REAL NOT NULL DEFAULT 0.0,       -- optional EMA for stability
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, key_type, key_id)
);
CREATE INDEX IF NOT EXISTS idx_mastery_user ON mastery(user_id);

-- Review queue (spaced repetition)
CREATE TABLE IF NOT EXISTS review_queue (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  problem_id  TEXT NOT NULL,
  reason      TEXT NOT NULL,          -- fail|slow|heavy-hint|mock-gap
  next_due_at TIMESTAMPTZ NOT NULL,
  bucket      INT NOT NULL DEFAULT 0, -- 0,1,2,3 for 1d/3d/7d/21d
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, problem_id)
);
CREATE INDEX IF NOT EXISTS idx_review_due ON review_queue(next_due_at);

-- Rubrics (LLM-graded, for systems/math proof-sketch)
CREATE TABLE IF NOT EXISTS rubrics (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain      TEXT NOT NULL,          -- 'systems'|'math'
  title       TEXT NOT NULL,
  dimensions  JSONB NOT NULL,         -- [{id, name, scale:0..3, desc}]
  metadata    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rubric scores per submission (optional)
CREATE TABLE IF NOT EXISTS rubric_scores (
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  rubric_id     UUID NOT NULL REFERENCES rubrics(id),
  scores        JSONB NOT NULL,       -- {dim_id: score}
  feedback      JSONB NOT NULL,       -- structured gap statements
  PRIMARY KEY (submission_id, rubric_id)
);

-- Basic triggers
CREATE OR REPLACE FUNCTION touch_sessions_updated()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sessions_touch
BEFORE UPDATE ON sessions
FOR EACH ROW EXECUTE PROCEDURE touch_sessions_updated();
```

---

## D) Default recommendation logic (pseudo)

```
score(candidate) = w1*weakness(user, candidate.topics)
                 + w2*novelty(user, candidate.id)
                 + w3*difficulty_pacing(user, candidate.difficulty)
                 + w4*recency_diversification(user)
```

Guardrails: no >2 consecutive fails; cap difficulty jumps to +1; inject review items when due.

---

## E) Environment & Ops

* **Config:** `CO_DB_URL`, `CO_REDIS_URL`, `API_BASE=https://api.scimigo.com`, `EVAL_BASE`, `PROBLEM_BANK_BASE`, `TUTOR_BASE`.
* **CORS:** allow `https://coding.scimigo.com` and `https://app.scimigo.com`.
* **Auth:** verify JWTs issued by `api.scimigo.com`.
* **Rate limits:** 60 req/min/user; SSE: 2 concurrent streams.

