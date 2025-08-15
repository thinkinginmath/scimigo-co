# Study Path Task Tracking - Implementation Tickets

## Epic: Implement Study Path Task Tracking for Meta Interview Prep MVP

### Phase 1: Core Infrastructure (Sprint 1)

#### CO-003-001: Database Schema Setup
**Priority:** P0 - Critical
**Estimate:** 5 points
**Dependencies:** None

**Description:**
Create database migrations for study path tracking tables.

**Acceptance Criteria:**
- [ ] Create alembic migration for `study_paths` table
- [ ] Create alembic migration for `study_tasks` table  
- [ ] Create alembic migration for `task_events` table
- [ ] Create alembic migration for `task_evaluations` table
- [ ] Add proper indexes for performance
- [ ] Validate foreign key constraints
- [ ] Test rollback capability

**Technical Notes:**
```python
# Migration should include:
- UUID primary keys
- user_id as VARCHAR(255) for api.scimigo.com JWT sub claim
- JSONB columns for metadata storage
- Proper indexes as defined in design doc
```

---

#### CO-003-002: SQLAlchemy Models
**Priority:** P0 - Critical
**Estimate:** 3 points
**Dependencies:** CO-003-001

**Description:**
Create SQLAlchemy ORM models for study path tables.

**Acceptance Criteria:**
- [ ] Create `StudyPath` model in `co/models/study_path.py`
- [ ] Create `StudyTask` model in `co/models/study_task.py`
- [ ] Create `TaskEvent` model in `co/models/task_event.py`
- [ ] Create `TaskEvaluation` model in `co/models/task_evaluation.py`
- [ ] Add enum types for status and event_type
- [ ] Add model relationships and lazy loading
- [ ] Write unit tests for model creation

**Code Location:** `co/models/`

---

#### CO-003-003: JWT Auth Middleware Enhancement
**Priority:** P0 - Critical
**Estimate:** 2 points
**Dependencies:** None

**Description:**
Enhance existing JWT middleware to extract user_id from api.scimigo.com tokens.

**Acceptance Criteria:**
- [ ] Update `co/middleware/auth.py` to extract `sub` claim as user_id
- [ ] Add validation for api.scimigo.com issuer
- [ ] Create dependency injection for user_id in FastAPI routes
- [ ] Add error handling for invalid/expired tokens
- [ ] Write tests for auth middleware

**Technical Notes:**
```python
async def get_current_user(authorization: str = Header()) -> str:
    # Extract and validate JWT
    # Return user_id from sub claim
```

---

#### CO-003-004: Study Path Service Layer
**Priority:** P0 - Critical
**Estimate:** 5 points
**Dependencies:** CO-003-002

**Description:**
Create service layer for study path operations.

**Acceptance Criteria:**
- [ ] Create `StudyPathService` in `co/services/study_path.py`
- [ ] Implement `create_study_path(user_id, track_id, config)`
- [ ] Implement `get_active_path(user_id)`
- [ ] Implement `update_path_config(path_id, config)`
- [ ] Add caching with Redis for active paths
- [ ] Write comprehensive unit tests

---

### Phase 2: Problem Bank Integration (Sprint 2)

#### CO-003-005: Problem Bank Client Enhancement
**Priority:** P0 - Critical
**Estimate:** 3 points
**Dependencies:** None

**Description:**
Enhance problem bank client to fetch Meta interview problems by module.

**Acceptance Criteria:**
- [ ] Update `co/clients/problem_bank.py`
- [ ] Add method `get_problems_by_module(module, difficulty_range)`
- [ ] Add method `get_problem_metadata(problem_id)`
- [ ] Implement response caching
- [ ] Handle rate limiting and retries
- [ ] Mock problem bank responses for testing

**Technical Notes:**
```python
async def get_problems_by_module(
    module: str, 
    difficulty_range: Tuple[int, int],
    limit: int = 10
) -> List[Problem]
```

---

#### CO-003-006: Task Generation Service
**Priority:** P0 - Critical
**Estimate:** 8 points
**Dependencies:** CO-003-004, CO-003-005

**Description:**
Create service to generate personalized study tasks.

**Acceptance Criteria:**
- [ ] Create `TaskGenerationService` in `co/services/task_generation.py`
- [ ] Implement difficulty progression algorithm
- [ ] Implement module sequencing logic
- [ ] Create batch task creation for initial path
- [ ] Add topic diversity constraints
- [ ] Integrate with personalization weights from config
- [ ] Write tests with various user profiles

**Algorithm Requirements:**
- No more than 2 consecutive failures
- Difficulty jumps capped at +1
- Topic rotation within module

---

#### CO-003-007: Study Task Service
**Priority:** P0 - Critical
**Estimate:** 5 points
**Dependencies:** CO-003-002

**Description:**
Create service layer for study task operations.

**Acceptance Criteria:**
- [ ] Create `StudyTaskService` in `co/services/study_task.py`
- [ ] Implement `create_tasks_batch(path_id, tasks)`
- [ ] Implement `get_next_task(user_id)`
- [ ] Implement `update_task_status(task_id, status)`
- [ ] Implement `get_user_tasks(user_id, filters)`
- [ ] Add task expiration logic
- [ ] Write unit tests

---

### Phase 3: Evaluation Pipeline (Sprint 3)

#### CO-003-008: Task Submission Endpoint
**Priority:** P0 - Critical
**Estimate:** 5 points
**Dependencies:** CO-003-007

**Description:**
Create API endpoint for task submission and evaluation.

**Acceptance Criteria:**
- [ ] Create `POST /v1/study-tasks/{task_id}/submit` endpoint
- [ ] Validate task ownership and status
- [ ] Fetch hidden tests from problem bank
- [ ] Call eval service with code and tests
- [ ] Store results in task_evaluations table
- [ ] Update task status and metrics
- [ ] Emit evaluation events
- [ ] Handle timeouts and errors gracefully

**Request Schema:**
```python
{
    "language": "python" | "javascript",
    "code": "string"
}
```

---

#### CO-003-009: Event Logging System
**Priority:** P1 - High
**Estimate:** 3 points
**Dependencies:** CO-003-002

**Description:**
Implement append-only event logging for audit trail.

**Acceptance Criteria:**
- [ ] Create `EventService` in `co/services/events.py`
- [ ] Implement async event emission
- [ ] Add event types: created, started, submitted, evaluated, hint_requested, status_changed
- [ ] Ensure events are immutable
- [ ] Add batch event retrieval
- [ ] Test event ordering and completeness

---

#### CO-003-010: Evaluation Result Processing
**Priority:** P0 - Critical
**Estimate:** 5 points
**Dependencies:** CO-003-008

**Description:**
Process and store evaluation results with detailed metrics.

**Acceptance Criteria:**
- [ ] Parse eval service response
- [ ] Calculate score (0.0 to 1.0)
- [ ] Extract runtime and memory metrics
- [ ] Store test case pass/fail details
- [ ] Update mastery scores for topics
- [ ] Trigger review scheduling if needed
- [ ] Handle partial test results

---

### Phase 4: Progress Tracking (Sprint 4)

#### CO-003-011: Progress Analytics API
**Priority:** P1 - High
**Estimate:** 5 points
**Dependencies:** CO-003-007

**Description:**
Create endpoints for progress tracking and analytics.

**Acceptance Criteria:**
- [ ] Create `GET /v1/study-paths/{path_id}/progress` endpoint
- [ ] Return module completion percentages
- [ ] Calculate accuracy by topic
- [ ] Show difficulty progression over time
- [ ] Include time spent per module
- [ ] Add caching for expensive queries
- [ ] Create dashboard summary endpoint

**Response Schema:**
```python
{
    "modules": {
        "arrays-strings": {
            "completed": 15,
            "total": 25,
            "accuracy": 0.73,
            "avg_time_seconds": 1200
        }
    },
    "overall_accuracy": 0.68,
    "current_difficulty": 3
}
```

---

#### CO-003-012: Spaced Repetition Integration
**Priority:** P1 - High
**Estimate:** 5 points
**Dependencies:** CO-003-007

**Description:**
Integrate study tasks with existing review_queue system.

**Acceptance Criteria:**
- [ ] Create background job to check review_queue
- [ ] Generate study tasks for due reviews
- [ ] Update review intervals based on performance
- [ ] Mark reviews as completed
- [ ] Add review source tracking in task metadata
- [ ] Test spaced repetition scheduling

---

#### CO-003-013: Export Functionality
**Priority:** P2 - Medium
**Estimate:** 3 points
**Dependencies:** CO-003-011

**Description:**
Allow users to export their practice history.

**Acceptance Criteria:**
- [ ] Create `GET /v1/study-tasks/export` endpoint
- [ ] Support JSON and CSV formats
- [ ] Include all task details and evaluations
- [ ] Add date range filtering
- [ ] Implement streaming for large exports
- [ ] Add rate limiting

---

### Phase 5: Tutor Integration (Sprint 5)

#### CO-003-014: Hint Request Handler
**Priority:** P1 - High
**Estimate:** 5 points
**Dependencies:** CO-003-007

**Description:**
Integrate hint requests with tutor service.

**Acceptance Criteria:**
- [ ] Create `POST /v1/study-tasks/{task_id}/hint` endpoint
- [ ] Prepare context with problem and attempts
- [ ] Call tutor API to initiate SSE stream
- [ ] Track hint usage count
- [ ] Store hint content in events
- [ ] Rate limit hint requests
- [ ] Handle tutor service failures

---

#### CO-003-015: Tutor Context Preparation
**Priority:** P1 - High
**Estimate:** 3 points
**Dependencies:** CO-003-014

**Description:**
Prepare rich context for tutor LLM interactions.

**Acceptance Criteria:**
- [ ] Include problem statement and constraints
- [ ] Add user's current code
- [ ] Include past submission results
- [ ] Add module learning objectives
- [ ] Include user's mastery level
- [ ] Format context for optimal LLM understanding

---

### Phase 6: API Documentation & Testing (Sprint 6)

#### CO-003-016: OpenAPI Documentation
**Priority:** P1 - High
**Estimate:** 2 points
**Dependencies:** All API endpoints

**Description:**
Complete OpenAPI documentation for all study path endpoints.

**Acceptance Criteria:**
- [ ] Document all request/response schemas
- [ ] Add example requests and responses
- [ ] Include error response formats
- [ ] Document query parameters and filters
- [ ] Add authentication requirements
- [ ] Generate API client SDKs

---

#### CO-003-017: End-to-End Tests
**Priority:** P1 - High
**Estimate:** 5 points
**Dependencies:** All features

**Description:**
Create comprehensive E2E tests for study path flows.

**Acceptance Criteria:**
- [ ] Test complete path creation flow
- [ ] Test task progression from start to completion
- [ ] Test evaluation pipeline with real eval service
- [ ] Test hint request flow
- [ ] Test progress tracking accuracy
- [ ] Test concurrent user scenarios
- [ ] Add performance benchmarks

---

#### CO-003-018: Performance Optimization
**Priority:** P2 - Medium
**Estimate:** 3 points
**Dependencies:** CO-003-017

**Description:**
Optimize query performance and caching.

**Acceptance Criteria:**
- [ ] Profile slow queries with EXPLAIN ANALYZE
- [ ] Add missing database indexes
- [ ] Implement Redis caching for hot paths
- [ ] Optimize N+1 queries
- [ ] Add connection pooling tuning
- [ ] Document performance benchmarks

---

### Phase 7: Production Readiness (Sprint 7)

#### CO-003-019: Monitoring & Alerting
**Priority:** P1 - High
**Estimate:** 3 points
**Dependencies:** All features

**Description:**
Add monitoring and alerting for study path system.

**Acceptance Criteria:**
- [ ] Add Prometheus metrics for task completion rates
- [ ] Monitor evaluation service latency
- [ ] Track hint usage patterns
- [ ] Alert on high failure rates
- [ ] Add dashboard in Grafana
- [ ] Document SLIs and SLOs

---

#### CO-003-020: Data Migration Script
**Priority:** P1 - High
**Estimate:** 2 points
**Dependencies:** CO-003-001

**Description:**
Create script to migrate existing session data to study tasks.

**Acceptance Criteria:**
- [ ] Map existing sessions to study paths
- [ ] Convert submissions to task evaluations
- [ ] Preserve historical timestamps
- [ ] Add dry-run mode
- [ ] Create rollback capability
- [ ] Test with production data snapshot

---

## Technical Debt & Future Enhancements

### Backlog Items

#### CO-003-021: Versioned Paths
Support multiple personalization algorithm versions.

#### CO-003-022: Mock Interview Mode
Time-boxed sessions simulating real Meta interviews.

#### CO-003-023: Collaborative Features
Allow mentors to review and comment on tasks.

#### CO-003-024: Advanced Analytics Pipeline
Stream events to data warehouse for ML training.

#### CO-003-025: Peer Comparison
Anonymous performance percentiles by module.

---

## Risk Mitigation

### Identified Risks

1. **Problem Bank API Latency**
   - Mitigation: Aggressive caching, pre-fetch next problems
   
2. **Eval Service Timeouts**
   - Mitigation: Queue-based async evaluation, status polling

3. **Data Consistency**
   - Mitigation: Event sourcing, immutable events, transaction boundaries

4. **User ID Migration**
   - Mitigation: Graceful handling of both old and new user ID formats

---

## Success Metrics

- 95% of study tasks created successfully
- <2s latency for task retrieval
- <30s evaluation completion time
- 99.9% uptime for core endpoints
- 80% user engagement with generated tasks
- 60% task completion rate

---

## Team Assignments

- **Backend Lead:** Phase 1-3 (Core, Problem Bank, Evaluation)
- **ML Engineer:** Phase 2, 4 (Task Generation, Progress Tracking)
- **Platform Engineer:** Phase 3, 7 (Evaluation Pipeline, Production)
- **Full Stack:** Phase 5-6 (Tutor Integration, API/Testing)