# CO-001: Database Schema Alignment

**Priority**: P0 - Critical  
**Type**: Bug Fix  
**Component**: Database/Models  
**Estimated Effort**: 2-3 hours  

## Problem Statement

There is a critical mismatch between the SQLAlchemy models in `src/co/db/models.py` and the Alembic migration in `migrations/versions/001_initial_schema.py`. This will cause runtime errors when the application tries to interact with the database.

### Key Discrepancies

1. **Track Model**:
   - Models define: `slug`, `labels`, `version`, `created_at`
   - Migration defines: `description`, `difficulty`, `outcomes`, `is_published`, `updated_at`

2. **Session Model**:
   - Models use: `subject`, `mode`, `track_id` (UUID FK), `problem_id`, `status`, `last_hint_level`
   - Migration uses: `track_id` (String FK), `config` (JSONB), `state` (JSONB), `completed_at`

3. **Submission Model**:
   - Models have: `visible_passed`, `hidden_passed`, `categories`, `exec_ms`, `payload_sha256`
   - Migration has: generic `payload` (JSONB), `result` (JSONB), `score` (Float)

## Proposed Solution

Create a new migration that aligns the database schema with the current models, as the models represent the intended design based on the architecture documents.

## Implementation Steps

1. **Backup current schema** (if any data exists)
   ```bash
   pg_dump -s co > schema_backup.sql
   ```

2. **Create new migration**
   ```bash
   alembic revision --autogenerate -m "align_schema_with_models"
   ```

3. **Review and adjust the auto-generated migration**
   - Ensure all model fields are properly reflected
   - Add appropriate indexes for foreign keys and commonly queried fields
   - Set proper constraints and defaults

4. **Key Schema Requirements**:
   ```sql
   -- Tracks table should have:
   - slug (unique, indexed)
   - subject (indexed)
   - labels (JSONB with GIN index for containment queries)
   - modules (JSONB)
   - version
   
   -- Sessions table should have:
   - user_id (UUID, indexed)
   - track_id (UUID FK, indexed)
   - subject (indexed)
   - mode (indexed)
   - problem_id
   - status
   - last_hint_level
   
   -- Submissions table should have:
   - session_id (UUID FK, indexed)
   - user_id (UUID, indexed)
   - problem_id (indexed)
   - subject
   - visible_passed, visible_total
   - hidden_passed, hidden_total
   - categories (JSONB)
   - exec_ms
   - payload_sha256 (for deduplication)
   ```

5. **Add composite indexes for common queries**:
   ```sql
   CREATE INDEX idx_sessions_user_subject ON sessions(user_id, subject);
   CREATE INDEX idx_submissions_user_problem ON submissions(user_id, problem_id);
   CREATE INDEX idx_tracks_labels ON tracks USING GIN (labels);
   ```

6. **Run migration**
   ```bash
   alembic upgrade head
   ```

7. **Verify schema**
   ```bash
   psql co -c "\d+ tracks"
   psql co -c "\d+ sessions"
   psql co -c "\d+ submissions"
   ```

## Testing

1. **Unit tests for models**
   ```python
   # tests/unit/test_models.py
   def test_track_creation():
       track = Track(
           slug="test-track",
           subject="coding",
           title="Test Track",
           labels=["test"],
           modules=[]
       )
       assert track.slug == "test-track"
   ```

2. **Integration test for CRUD operations**
   ```python
   # tests/integration/test_db_operations.py
   async def test_track_crud():
       # Create, read, update, delete operations
       pass
   ```

## Rollback Plan

If issues are discovered after migration:
```bash
alembic downgrade -1
```

## Success Criteria

- [ ] All SQLAlchemy models can be instantiated without errors
- [ ] Database operations (CRUD) work correctly
- [ ] All existing API endpoints function properly
- [ ] No runtime errors related to missing or mismatched columns

## Dependencies

None - this is a foundational fix required before other work can proceed.

## Notes

- This fix is blocking all other database-related development
- Consider adding a CI check to ensure models and migrations stay in sync
- Document the canonical schema in a separate markdown file for reference