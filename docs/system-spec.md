# Curriculum Orchestrator System Specification

## Overview
The Curriculum Orchestrator (CO) is a FastAPI-based service that coordinates learning
tracks, sessions, submissions, and tutoring for the Scimigo platform. It integrates
with external evaluation, problem bank, and tutor services while persisting state in a
PostgreSQL database and using Redis for caching and rate limiting.

## Architecture
- **Application Factory** – `src/co/server.py` creates the FastAPI app, sets up CORS and
  custom middleware, and registers routers for tracks, sessions, study tasks,
  submissions, and tutor endpoints【F:src/co/server.py†L40-L61】.
- **Configuration** – Runtime settings (database, Redis, service URLs, rate limits, and
  feature flags) are defined via Pydantic settings and environment variables in
  `src/co/config.py`【F:src/co/config.py†L19-L68】.
- **Middleware** – Authentication, request ID injection, and in-memory rate limiting
  are implemented in `src/co/middleware.py`【F:src/co/middleware.py†L15-L110】.
- **External Clients** – HTTP clients provide access to the evaluation service, problem
  bank, and tutor API (`src/co/clients/`).

## Services
- **TrackService** – Lists and retrieves track definitions from the database
  (`src/co/services/tracks.py`).
- **SessionService** – Manages learning sessions, handles problem advancement, retries,
  and mastery updates on success or failure【F:src/co/services/sessions.py†L13-L74】【F:src/co/services/sessions.py†L86-L117】.
- **StudyTaskService** – Creates batches of scheduled tasks, lists pending work, and
  records evaluation results with events for auditing【F:src/co/services/study_task.py†L22-L93】【F:src/co/services/study_task.py†L95-L145】.
- **PersonalizationService** – Recommends the next problem and maintains user mastery
  and spaced‑repetition review queues【F:src/co/services/personalization.py†L14-L60】【F:src/co/services/personalization.py†L210-L316】.
- **TutorService** – Provisions tutor turns by fetching problem context, calling the
  tutor API, and tracking active SSE streams in Redis【F:src/co/services/tutor.py†L13-L85】.
- **Evaluators** – `CodingEvaluator` and `MathEvaluator` call the evaluation service,
  persist submission results, and categorize failures【F:src/co/services/evaluators/coding.py†L15-L105】【F:src/co/services/evaluators/math.py†L15-L92】.

## Data Model
- **Core Entities** – Tracks, sessions, submissions, mastery scores, review queue items
  and rubrics are defined in `src/co/db/models.py`【F:src/co/db/models.py†L27-L173】.
- **Study Path Tracking** – Separate models represent study paths, tasks, evaluations,
  and task events for personalized study flows (`src/co/models/`).

## API Surface
All routes are versioned under `/v1`:
- `/v1/tracks` – list or retrieve tracks.
- `/v1/sessions` – create, update, or fetch sessions.
- `/v1/study-tasks` – manage scheduled study tasks and review queues.
- `/v1/submissions` – submit coding or math attempts for evaluation.
- `/v1/tutor/messages` – start tutor turns and receive stream tokens.
- `/health` – service health check.

## External Dependencies
- **PostgreSQL** for persistence and **Redis** for caching and rate limiting.
- **Problem Bank**, **Evaluation Service**, and **Tutor API** for problem metadata,
  code/math grading, and LLM-based tutoring.

## Authentication & Security
User identity is validated via JWT tokens. `AuthMiddleware` attaches the user ID to each
request, and `get_current_user` enforces token validity on protected endpoints
(`src/co/auth.py`). Rate limiting and request identifiers provide additional safeguards.

