# Study Path Task Tracking — System Design

**Goal.** Provide persistent records of a learner's study path by capturing all tasks issued by the Curriculum Orchestrator (CO) and their outcomes. Users can revisit any past session, filter tasks by track or module, and audit their progress over time. This system supports the Meta Interview Prep tutor MVP with comprehensive tracking of 2000+ coding problems across 14 modules.

---

## 1. Functional Requirements

1. **Task Recording**  
   - Every recommended activity (problem solving, review item, lesson) becomes a `StudyTask`.  
   - Task metadata includes module, topic tags, difficulty, scheduled timestamp, and problem_id linking to problem bank.
   - Support Meta interview-specific modules (arrays-strings, trees-graphs, dynamic-programming, etc.).
2. **Status Tracking**  
   - Track lifecycle states: `scheduled → in_progress → completed | skipped | expired`.  
   - Preserve evaluation metrics (pass/fail, runtime, memory usage, test cases passed, hints used).
   - Store eval service results including sandbox execution details.
3. **History Review**  
   - Users can fetch their entire task history, filterable by date, module, difficulty, or status.  
   - Summaries: counts per status, accuracy by topic, upcoming reviews, module completion rates.
   - Support exporting practice sessions for offline review.
4. **Audit & Recovery**  
   - Immutable event log for troubleshooting or rebuilding progress if models change.
   - Track tutor interactions and hint sequences for learning analytics.
5. **Spaced Repetition Integration**  
   - Sync with existing `review_queue` table for scheduled reviews.
   - Generate study tasks when review items become due.

---

## 2. Data Model

### Tables

| Table | Key Fields | Notes |
|-------|------------|-------|
| `study_paths` | `id`, `user_id` (string from api.scimigo.com), `track_id`, `config` (jsonb), `created_at`, `updated_at` | Personalized path instance for Meta interview prep track. Config stores personalization params. |
| `study_tasks` | `id`, `path_id`, `problem_id`, `module`, `topic_tags[]`, `difficulty` (1-5), `scheduled_at`, `started_at`, `completed_at`, `status`, `score`, `metadata` (jsonb) | One row per task. Metadata stores eval results, hints used, etc. |
| `task_events` | `id`, `task_id`, `event_type`, `payload` (jsonb), `created_at` | Append-only log; event_type includes: `created`, `started`, `submitted`, `evaluated`, `hint_requested`, `tutor_interaction`, `status_changed`. |
| `task_evaluations` | `id`, `task_id`, `submission_id`, `language`, `code`, `test_cases_passed`, `test_cases_total`, `runtime_ms`, `memory_mb`, `error_message`, `created_at` | Detailed evaluation results from eval service. |

### Schema Details

```sql
-- study_paths table
CREATE TABLE study_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL, -- JWT sub claim from api.scimigo.com
    track_id VARCHAR(100) NOT NULL DEFAULT 'coding-interview-meta',
    config JSONB DEFAULT '{}', -- personalization weights, difficulty progression
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_study_paths_user (user_id, created_at DESC)
);

-- study_tasks table with Meta interview modules
CREATE TABLE study_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id UUID REFERENCES study_paths(id) ON DELETE CASCADE,
    problem_id VARCHAR(100) NOT NULL, -- links to problem bank
    module VARCHAR(50) NOT NULL, -- e.g., 'arrays-strings', 'dynamic-programming'
    topic_tags TEXT[] DEFAULT '{}', -- e.g., ['two-pointers', 'sliding-window']
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    scheduled_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    score FLOAT, -- 0.0 to 1.0, null if not completed
    time_spent_seconds INTEGER,
    hints_used INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_study_tasks_path_schedule (path_id, scheduled_at),
    INDEX idx_study_tasks_user_module (path_id, module, status),
    INDEX idx_study_tasks_problem (problem_id)
);
```

### Status Enum

```text
scheduled -> in_progress -> completed (success/failure)
                       -> skipped (user choice)
                       -> expired (scheduled time passed without start)
```

### Module Enum (Meta Interview Prep)

```text
introduction | arrays-strings | hashing | linked-lists | stacks-queues |
trees-graphs | sorting-searching | heaps | greedy | dynamic-programming |
recursion-backtracking | bit-manipulation | math-geometry | design
```

### Indexing Strategy

- `study_tasks (path_id, scheduled_at)` for chronological retrieval
- `study_tasks (path_id, module, status)` for module progress tracking
- `study_tasks (path_id, status, scheduled_at)` for upcoming tasks
- `task_events (task_id, created_at)` for event replay
- `task_evaluations (task_id, created_at)` for submission history

---

## 3. API Endpoints

### Core Task Management

| Method & Path | Description | Request/Response |
|---------------|-------------|------------------|
| `POST /v1/study-paths` | Create new personalized study path | Request: `{track_id, config}` |
| `GET /v1/study-paths/current` | Get user's active study path | Returns path with progress stats |
| `POST /v1/study-tasks/batch` | CO creates batch of upcoming tasks | Request: `{path_id, tasks[]}` |
| `GET /v1/study-tasks/next` | Get next scheduled task for user | Returns task with problem details |
| `PATCH /v1/study-tasks/{task_id}` | Update task status and metrics | Request: `{status, metadata}` |
| `POST /v1/study-tasks/{task_id}/start` | Mark task as started | Records started_at timestamp |
| `POST /v1/study-tasks/{task_id}/submit` | Submit solution for evaluation | Request: `{language, code}` |

### History & Analytics

| Method & Path | Description | Query Parameters |
|---------------|-------------|------------------|
| `GET /v1/study-tasks` | List user's tasks with filtering | `?module=`, `?status=`, `?from=`, `?to=`, `?limit=` |
| `GET /v1/study-tasks/{task_id}/events` | Get task event timeline | Returns all events chronologically |
| `GET /v1/study-paths/{path_id}/progress` | Module completion & accuracy stats | Returns progress by module |
| `GET /v1/study-tasks/export` | Export practice history | `?format=json|csv`, `?from=`, `?to=` |

### Integration Endpoints

| Method & Path | Description | Notes |
|---------------|-------------|-------|
| `POST /v1/study-tasks/{task_id}/hint` | Request hint from tutor | Triggers tutor SSE stream |
| `POST /v1/study-tasks/{task_id}/evaluate` | Trigger evaluation | Calls eval service internally |
| `GET /v1/study-tasks/review-due` | Get tasks due for review | Integrates with review_queue |

All endpoints require JWT Bearer token from api.scimigo.com with user_id extracted from `sub` claim.

---

## 4. Sequence Flow

### Initial Path Creation
```mermaid
User → Frontend → CO: Start Meta Interview Prep
CO → study_paths: Create path with user_id, track_id='coding-interview-meta'
CO → Personalization: Get initial task recommendations
CO → Problem Bank: Fetch problems for arrays-strings module (difficulty 1-2)
CO → study_tasks: Create 5-10 initial tasks (status=scheduled)
CO → Frontend: Return path_id and first task
```

### Task Execution Flow
1. **Task Start**
   - Frontend calls `GET /v1/study-tasks/next`
   - CO returns next scheduled task with problem details from Problem Bank
   - Frontend calls `POST /v1/study-tasks/{id}/start`
   - CO updates `started_at`, `status=in_progress`, emits `started` event

2. **Solution Submission**
   - User submits code via `POST /v1/study-tasks/{id}/submit`
   - CO fetches hidden tests from Problem Bank (server-side only)
   - CO calls Eval Service with code + test cases
   - Eval Service returns: test results, runtime, memory usage
   - CO stores in `task_evaluations` table
   - CO updates task: `completed_at`, `status=completed`, `score`, `metadata`
   - CO emits `evaluated` event with results

3. **Hint/Tutor Request**
   - User requests hint via `POST /v1/study-tasks/{id}/hint`
   - CO prepares context: problem, current code, past attempts
   - CO calls Tutor API to initiate SSE stream
   - CO tracks hint usage in `hints_used` counter
   - CO emits `hint_requested` event

4. **Progress Tracking**
   - After task completion, CO updates `mastery` table for topics
   - If score < 0.5, CO may schedule easier problems
   - If consecutive successes, CO increases difficulty
   - CO checks `review_queue` for due items, creates tasks if needed

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

## 7. Service Integration Architecture

### External Service Dependencies

```yaml
# api.scimigo.com (User Management & Auth)
- JWT issuer for authentication
- User profile and preferences
- LLM upstream for advanced tutoring
- SymPy integration for math problems

# scimigo-problem-bank (Problem Repository)
- 2000+ Meta interview problems
- Problem metadata and difficulty ratings
- Visible test cases (public)
- Hidden test bundles (internal API only)

# Eval Service (Code Execution)
- Sandboxed Python/JavaScript execution
- Memory and time limit enforcement
- Test case evaluation
- Security isolation

# Frontend (Next.js)
- User interface for practice sessions
- Real-time progress visualization
- SSE stream handling for tutor
- Code editor with syntax highlighting
```

### Authentication Flow
```python
# JWT validation in CO
def validate_request(authorization_header):
    token = authorization_header.replace("Bearer ", "")
    claims = jwt.decode(token, verify=True, issuer="api.scimigo.com")
    user_id = claims["sub"]  # Use this as user_id in study_paths
    return user_id
```

### Service Client Configuration
```python
# co/config.py additions
PROBLEM_BANK_API_KEY = os.getenv("PROBLEM_BANK_API_KEY")
EVAL_SERVICE_TIMEOUT = 30  # seconds
TUTOR_STREAM_TIMEOUT = 300  # 5 minutes for SSE
MAX_CONCURRENT_EVALUATIONS = 2  # per user
```

## 8. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- Database schema creation (study_paths, study_tasks, task_events)
- Basic CRUD operations for study paths and tasks
- JWT authentication middleware
- Integration with existing CO session/submission models

### Phase 2: Problem Bank Integration (Week 2-3)
- Client for fetching Meta interview problems
- Module-based problem selection
- Difficulty progression logic
- Hidden test bundle retrieval (server-side only)

### Phase 3: Evaluation Pipeline (Week 3-4)
- Task submission endpoint
- Eval service integration for code execution
- Result storage in task_evaluations
- Event emission for audit trail

### Phase 4: Progress Tracking (Week 4-5)
- Mastery calculation updates
- Spaced repetition integration
- Module completion tracking
- Performance analytics endpoints

### Phase 5: Tutor Integration (Week 5-6)
- Hint request handling
- Context preparation for LLM
- SSE stream management
- Hint usage tracking

### Phase 6: Frontend & Polish (Week 6-7)
- API documentation
- Export functionality
- Performance optimization
- Error handling and retry logic

## 9. Future Extensions

- **Versioned Paths**: Keep history when personalization algorithm changes
- **Collaborative Learning**: Allow mentors to review and comment on tasks
- **Advanced Analytics**: Stream events to data warehouse for ML model training
- **Mock Interviews**: Time-boxed sessions simulating real Meta interviews
- **Peer Comparison**: Anonymous performance percentiles by module
- **Custom Problem Sets**: Let users create focused practice sessions

---

With this design, the Meta Interview Prep tutor provides comprehensive tracking of every learner's journey through 2000+ problems across 14 modules, enabling personalized learning paths, detailed progress analytics, and seamless integration with existing SciMigo services.
