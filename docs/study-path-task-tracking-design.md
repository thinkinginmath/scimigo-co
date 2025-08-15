# Study Path Task Tracking — System Design

**Goal.** Provide persistent records of a learner's study path by capturing all tasks issued by the Curriculum Orchestrator (CO) and their outcomes. Users can revisit any past session, filter tasks by track or module, and audit their progress over time.

---

## 1. Functional Requirements

1. **Task Recording**  
   - Every recommended activity (problem solving, review item, lesson) becomes a `StudyTask`.  
   - Task metadata includes module, topic tags, difficulty, and scheduled timestamp.
2. **Status Tracking**  
   - Track lifecycle states: `scheduled → in_progress → completed | skipped | expired`.  
   - Preserve evaluation metrics (pass/fail, runtime, hints used) for completed tasks.
3. **History Review**  
   - Users can fetch their entire task history, filterable by date, module, difficulty, or status.  
   - Summaries: counts per status, accuracy by topic, upcoming reviews.
4. **Audit & Recovery**  
   - Immutable event log for troubleshooting or rebuilding progress if models change.

---

## 2. Data Model

### Tables

| Table | Key Fields | Notes |
|-------|------------|-------|
| `study_paths` | `id`, `user_id`, `track_id`, `created_at` | Represents a personalized path instance. |
| `study_tasks` | `id`, `path_id`, `module`, `topic_tags[]`, `difficulty`, `scheduled_at`, `status`, `score` | One row per task surfaced to the learner. |
| `task_events` | `id`, `task_id`, `event_type`, `payload`, `created_at` | Append-only log; `event_type` = `created`, `started`, `submitted`, `evaluated`, `status_changed`. |

### Status Enum

```text
scheduled -> in_progress -> completed
                       -> skipped
                       -> expired (scheduled time passed without start)
```

### Indexing

- `study_tasks (path_id, scheduled_at)` for chronological retrieval.  
- `study_tasks (user_id, status)` for dashboards.  
- `task_events (task_id, created_at)` for replay.

---

## 3. API Endpoints

| Method & Path | Description |
|---------------|-------------|
| `POST /v1/study-paths/{path_id}/tasks` | CO creates a batch of upcoming tasks. |
| `PATCH /v1/study-tasks/{task_id}` | Update `status` and store evaluation metrics. |
| `GET /v1/users/{user_id}/tasks` | List tasks with filters (`status`, `module`, `date_range`). |
| `GET /v1/study-tasks/{task_id}/events` | Retrieve full event timeline for a task. |

All endpoints require JWT authentication and enforce user ownership.

---

## 4. Sequence Flow

1. **Path Realization**  
   When personalization generates a study path, CO inserts a `study_paths` row and seeds initial `study_tasks` with `status=scheduled`.
2. **Session Start**  
   Client requests next task. CO marks the task `in_progress` and emits a `started` event.
3. **Submission & Evaluation**  
   Learner submits a solution. CO records `submitted` event, evaluates the attempt, then records `evaluated` event with result metrics.
4. **Completion**  
   Depending on evaluation:  
   - Success → `status=completed`, `score=1`.  
   - Failure with retries or timeout → `status=completed`, `score=0`.  
   - User skips → `status=skipped`.  
   A final `status_changed` event is appended.
5. **Review**  
   History endpoints aggregate `study_tasks` and `task_events` to build timelines and performance dashboards.

---

## 5. Review UI Considerations

- **Timeline view** showing each task with icons for status and difficulty.  
- **Module filter** to analyze strengths/weaknesses.  
- **Task detail drawer** displaying event log, code submissions, and tutor interactions.  
- **Export** capability (CSV/JSON) for offline analysis.

---

## 6. Data Retention & Privacy

- Retain `study_tasks` indefinitely for user reference unless deletion is requested.  
- `task_events` can be archived after N months; maintain aggregates in `study_tasks`.  
- Sensitive payloads (e.g., user code) stored with encryption at rest and access controls.

---

## 7. Future Extensions

- **Versioned Paths**: keep history when the personalization algorithm changes.  
- **Collaboration**: allow mentors to comment on `study_tasks`.  
- **Analytics Warehouse**: stream `task_events` to a warehouse for deeper cohort analysis.

---

With this design, every learner's journey becomes traceable and reviewable, enabling transparency, progress auditing, and richer analytics for personalized learning.
