# CO-004: Spaced Review Scheduler Implementation

**Priority**: P1 - High  
**Type**: Feature  
**Component**: Background Tasks/Scheduling  
**Estimated Effort**: 5-6 hours  
**Dependencies**: CO-001

## Objective

Implement a background task scheduler for spaced repetition review, ensuring users revisit problems at optimal intervals based on their performance and forgetting curves.

## Background

The ReviewQueue model exists but lacks the scheduling logic to:
1. Process due reviews and notify users
2. Promote problems through spaced repetition buckets
3. Graduate problems from review after mastery
4. Inject review items into practice sessions

Spaced repetition intervals (Fibonacci-based):
- Bucket 0: Immediate (failed problems)
- Bucket 1: 1 day
- Bucket 2: 2 days  
- Bucket 3: 3 days
- Bucket 4: 5 days
- Bucket 5: 8 days
- Bucket 6: 13 days
- Bucket 7: 21 days (graduated)

## High-Level Design

### Architecture
```
ReviewScheduler (Celery/APScheduler)
    ├── process_due_reviews()     # Every 15 minutes
    ├── update_review_buckets()   # After each submission
    ├── inject_review_items()      # During session creation
    └── send_review_reminders()   # Daily at 9 AM user TZ

ReviewService
    ├── add_to_review()
    ├── get_due_reviews()
    ├── mark_reviewed()
    ├── promote_bucket()
    └── graduate_problem()
```

### Data Flow
1. User fails problem → Added to bucket 0
2. User passes problem → Promoted to next bucket
3. Scheduler runs → Finds due reviews
4. Session created → Injects due review items
5. Review completed → Updates bucket/due date

## Implementation Details

### 1. Install Dependencies
Update `pyproject.toml`:
```toml
[tool.poetry.dependencies]
celery = "^5.3.0"
redis = "^5.0.0"
celery-beat = "^2.5.0"
flower = "^2.0.0"  # Monitoring UI
```

### 2. Configure Celery
Create `src/co/tasks/celery_app.py`:
```python
from celery import Celery
from celery.schedules import crontab
from ..config import settings

app = Celery(
    'co',
    broker=settings.CO_REDIS_URL,
    backend=settings.CO_REDIS_URL,
    include=['co.tasks.review_tasks']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Scheduled tasks
    beat_schedule={
        'process-due-reviews': {
            'task': 'co.tasks.review_tasks.process_due_reviews',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
        'send-review-reminders': {
            'task': 'co.tasks.review_tasks.send_review_reminders',
            'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
        },
        'cleanup-old-reviews': {
            'task': 'co.tasks.review_tasks.cleanup_graduated',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        },
    }
)
```

### 3. Create Review Service
Create `src/co/services/review_service.py`:
```python
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from ..db.models import ReviewQueue, Submission, Session as UserSession
import logging

logger = logging.getLogger(__name__)

class ReviewService:
    """Manages spaced repetition review scheduling"""
    
    # Fibonacci-based intervals (in days)
    BUCKET_INTERVALS = [0, 1, 2, 3, 5, 8, 13, 21]
    GRADUATION_BUCKET = 7
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_to_review(
        self, 
        user_id: str, 
        problem_id: str,
        subject: str,
        initial_bucket: int = 0
    ) -> ReviewQueue:
        """Add a problem to user's review queue"""
        
        # Check if already in queue
        existing = self.db.query(ReviewQueue).filter(
            ReviewQueue.user_id == user_id,
            ReviewQueue.problem_id == problem_id
        ).first()
        
        if existing:
            # Reset to bucket 0 if failed again
            if initial_bucket == 0:
                existing.bucket = 0
                existing.due_at = datetime.utcnow()
                existing.review_count += 1
                self.db.commit()
                return existing
            else:
                return existing
        
        # Create new review item
        review = ReviewQueue(
            user_id=user_id,
            problem_id=problem_id,
            subject=subject,
            bucket=initial_bucket,
            due_at=self._calculate_due_date(initial_bucket),
            review_count=0
        )
        
        self.db.add(review)
        self.db.commit()
        
        logger.info(f"Added problem {problem_id} to review queue for user {user_id}")
        return review
    
    def get_due_reviews(
        self, 
        user_id: str,
        subject: Optional[str] = None,
        limit: int = 5
    ) -> List[ReviewQueue]:
        """Get problems due for review"""
        
        query = self.db.query(ReviewQueue).filter(
            ReviewQueue.user_id == user_id,
            ReviewQueue.due_at <= datetime.utcnow(),
            ReviewQueue.bucket < self.GRADUATION_BUCKET
        )
        
        if subject:
            query = query.filter(ReviewQueue.subject == subject)
        
        return query.order_by(
            ReviewQueue.bucket.asc(),  # Prioritize lower buckets
            ReviewQueue.due_at.asc()
        ).limit(limit).all()
    
    def process_submission(
        self, 
        submission: Submission
    ) -> Optional[ReviewQueue]:
        """Update review status based on submission result"""
        
        review = self.db.query(ReviewQueue).filter(
            ReviewQueue.user_id == submission.user_id,
            ReviewQueue.problem_id == submission.problem_id
        ).first()
        
        if not review:
            # First time seeing this problem
            if submission.status == "failed":
                return self.add_to_review(
                    submission.user_id,
                    submission.problem_id,
                    submission.subject,
                    initial_bucket=0
                )
            return None
        
        # Update existing review item
        if submission.status == "passed":
            # Promote to next bucket
            review = self._promote_bucket(review)
        else:
            # Demote to bucket 0
            review = self._demote_to_start(review)
        
        return review
    
    def _promote_bucket(self, review: ReviewQueue) -> ReviewQueue:
        """Promote problem to next spaced repetition bucket"""
        
        if review.bucket >= self.GRADUATION_BUCKET - 1:
            # Graduate from review
            review.bucket = self.GRADUATION_BUCKET
            review.due_at = None  # No longer needs review
            logger.info(f"Problem {review.problem_id} graduated for user {review.user_id}")
        else:
            # Move to next bucket
            review.bucket += 1
            review.due_at = self._calculate_due_date(review.bucket)
            logger.info(f"Problem {review.problem_id} promoted to bucket {review.bucket}")
        
        review.last_reviewed_at = datetime.utcnow()
        review.review_count += 1
        self.db.commit()
        
        return review
    
    def _demote_to_start(self, review: ReviewQueue) -> ReviewQueue:
        """Reset problem to bucket 0 after failure"""
        
        review.bucket = 0
        review.due_at = datetime.utcnow()
        review.last_reviewed_at = datetime.utcnow()
        review.review_count += 1
        self.db.commit()
        
        logger.info(f"Problem {review.problem_id} reset to bucket 0 for user {review.user_id}")
        return review
    
    def _calculate_due_date(self, bucket: int) -> datetime:
        """Calculate when problem is due for review"""
        
        if bucket >= len(self.BUCKET_INTERVALS):
            return None  # Graduated
        
        days = self.BUCKET_INTERVALS[bucket]
        return datetime.utcnow() + timedelta(days=days)
    
    def inject_review_items(
        self, 
        session: UserSession,
        max_items: int = 2
    ) -> List[str]:
        """Inject due review items into a practice session"""
        
        if session.mode != "practice":
            return []
        
        due_reviews = self.get_due_reviews(
            user_id=session.user_id,
            subject=session.subject,
            limit=max_items
        )
        
        problem_ids = [r.problem_id for r in due_reviews]
        
        if problem_ids:
            # Mark as injected
            for review in due_reviews:
                review.last_injected_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Injected {len(problem_ids)} review items into session {session.id}")
        
        return problem_ids
    
    def get_review_stats(self, user_id: str) -> dict:
        """Get user's review queue statistics"""
        
        reviews = self.db.query(ReviewQueue).filter(
            ReviewQueue.user_id == user_id
        ).all()
        
        stats = {
            "total": len(reviews),
            "due": 0,
            "by_bucket": {i: 0 for i in range(8)},
            "graduated": 0
        }
        
        now = datetime.utcnow()
        for review in reviews:
            stats["by_bucket"][review.bucket] += 1
            
            if review.bucket == self.GRADUATION_BUCKET:
                stats["graduated"] += 1
            elif review.due_at and review.due_at <= now:
                stats["due"] += 1
        
        return stats
```

### 4. Create Celery Tasks
Create `src/co/tasks/review_tasks.py`:
```python
from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings
from ..db.models import ReviewQueue, User
from ..services.review_service import ReviewService
from ..clients.notification_client import NotificationClient
import logging

logger = logging.getLogger(__name__)

# Create DB session for tasks
engine = create_engine(settings.CO_DB_URL)
SessionLocal = sessionmaker(bind=engine)

@shared_task
def process_due_reviews():
    """Process all due reviews and update their status"""
    
    db = SessionLocal()
    try:
        # Find all users with due reviews
        due_reviews = db.query(ReviewQueue).filter(
            ReviewQueue.due_at <= datetime.utcnow(),
            ReviewQueue.bucket < ReviewService.GRADUATION_BUCKET
        ).all()
        
        users_notified = set()
        for review in due_reviews:
            if review.user_id not in users_notified:
                # Send notification (once per user)
                notify_user_reviews.delay(str(review.user_id))
                users_notified.add(review.user_id)
        
        logger.info(f"Processed {len(due_reviews)} due reviews for {len(users_notified)} users")
        return {"reviews_processed": len(due_reviews), "users_notified": len(users_notified)}
    
    finally:
        db.close()

@shared_task
def notify_user_reviews(user_id: str):
    """Send review notification to a specific user"""
    
    db = SessionLocal()
    try:
        service = ReviewService(db)
        due_reviews = service.get_due_reviews(user_id)
        
        if not due_reviews:
            return
        
        # Get user info
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # Send notification
        notification = NotificationClient()
        notification.send_email(
            to=user.email,
            subject=f"You have {len(due_reviews)} problems ready for review",
            template="review_reminder",
            context={
                "user_name": user.name,
                "review_count": len(due_reviews),
                "problems": [
                    {
                        "id": r.problem_id,
                        "bucket": r.bucket,
                        "last_reviewed": r.last_reviewed_at
                    }
                    for r in due_reviews[:5]  # Show first 5
                ]
            }
        )
        
        logger.info(f"Sent review notification to user {user_id}")
    
    finally:
        db.close()

@shared_task  
def update_review_after_submission(submission_id: str):
    """Update review queue after a submission"""
    
    db = SessionLocal()
    try:
        from ..db.models import Submission
        
        submission = db.query(Submission).filter(
            Submission.id == submission_id
        ).first()
        
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return
        
        service = ReviewService(db)
        review = service.process_submission(submission)
        
        if review:
            logger.info(f"Updated review for problem {review.problem_id}, bucket: {review.bucket}")
            return {
                "problem_id": review.problem_id,
                "bucket": review.bucket,
                "due_at": review.due_at.isoformat() if review.due_at else None
            }
    
    finally:
        db.close()

@shared_task
def cleanup_graduated():
    """Clean up graduated reviews older than 30 days"""
    
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        deleted = db.query(ReviewQueue).filter(
            ReviewQueue.bucket == ReviewService.GRADUATION_BUCKET,
            ReviewQueue.last_reviewed_at < cutoff
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted} graduated review items")
        return {"deleted": deleted}
    
    finally:
        db.close()

@shared_task
def send_review_reminders():
    """Send daily review reminders to all users with due items"""
    
    db = SessionLocal()
    try:
        # Find users with due reviews
        users_with_reviews = db.query(ReviewQueue.user_id).filter(
            ReviewQueue.due_at <= datetime.utcnow(),
            ReviewQueue.bucket < ReviewService.GRADUATION_BUCKET
        ).distinct().all()
        
        for (user_id,) in users_with_reviews:
            notify_user_reviews.delay(str(user_id))
        
        logger.info(f"Queued review reminders for {len(users_with_reviews)} users")
        return {"users_notified": len(users_with_reviews)}
    
    finally:
        db.close()
```

### 5. Integrate with Session Creation
Update `src/co/services/session_service.py`:
```python
from .review_service import ReviewService

class SessionService:
    async def create_session(self, user_id: str, **kwargs) -> Session:
        # ... existing session creation logic ...
        
        # Inject review items for practice mode
        if session.mode == "practice":
            review_service = ReviewService(self.db)
            review_problems = review_service.inject_review_items(session)
            
            if review_problems:
                # Add to session's problem queue
                session.problem_queue = review_problems + session.problem_queue
                self.db.commit()
        
        return session
```

### 6. Add Review API Endpoints
Create `src/co/routes/reviews.py`:
```python
from fastapi import APIRouter, Depends
from ..services.review_service import ReviewService
from ..auth import get_current_user

router = APIRouter()

@router.get("/reviews/due")
async def get_due_reviews(
    subject: str = None,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Get user's due review items"""
    service = ReviewService(db)
    reviews = service.get_due_reviews(user.id, subject)
    
    return {
        "items": [
            {
                "problem_id": r.problem_id,
                "subject": r.subject,
                "bucket": r.bucket,
                "due_at": r.due_at.isoformat(),
                "review_count": r.review_count
            }
            for r in reviews
        ]
    }

@router.get("/reviews/stats")
async def get_review_stats(
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Get user's review queue statistics"""
    service = ReviewService(db)
    return service.get_review_stats(user.id)
```

### 7. Docker Compose Update
Update `docker/docker-compose.dev.yml`:
```yaml
services:
  # ... existing services ...
  
  celery-worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    command: celery -A co.tasks.celery_app worker --loglevel=info
    environment:
      # Same as API service
    depends_on: [db, redis]
  
  celery-beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    command: celery -A co.tasks.celery_app beat --loglevel=info
    environment:
      # Same as API service
    depends_on: [db, redis]
  
  flower:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    command: celery -A co.tasks.celery_app flower
    ports: ["5555:5555"]
    environment:
      # Same as API service
    depends_on: [redis]
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_review_service.py
def test_bucket_promotion():
    service = ReviewService(mock_db)
    review = ReviewQueue(bucket=2, due_at=datetime.utcnow())
    
    promoted = service._promote_bucket(review)
    assert promoted.bucket == 3
    assert promoted.due_at > datetime.utcnow()

def test_graduation():
    review = ReviewQueue(bucket=6)
    promoted = service._promote_bucket(review)
    assert promoted.bucket == 7
    assert promoted.due_at is None
```

### Integration Tests
```python
# tests/integration/test_review_flow.py
async def test_review_lifecycle():
    # Fail a problem
    submission = await submit_solution(status="failed")
    
    # Check it's in review queue
    reviews = await get_due_reviews(user_id)
    assert submission.problem_id in [r.problem_id for r in reviews]
    
    # Pass the problem
    submission2 = await submit_solution(status="passed")
    
    # Check bucket promoted
    review = get_review(problem_id)
    assert review.bucket == 1
```

## Success Criteria

- [ ] Celery workers process reviews every 15 minutes
- [ ] Failed problems added to bucket 0
- [ ] Passed problems promoted through buckets
- [ ] Due reviews injected into practice sessions
- [ ] Daily reminder emails sent at 9 AM
- [ ] Review stats API returns accurate counts
- [ ] Graduated problems cleaned up after 30 days
- [ ] Flower monitoring UI accessible at port 5555

## Performance Considerations

- Index `due_at` and `user_id` columns for fast queries
- Batch notification sending to avoid overwhelming email service
- Use Redis for caching user review stats
- Limit review injection to avoid overwhelming sessions

## Monitoring

- Track metrics: reviews processed, notifications sent, graduation rate
- Alert if review queue grows unbounded
- Monitor Celery queue depth and worker health

## Notes

- Consider timezone handling for daily reminders
- May need to adjust bucket intervals based on user feedback
- Future: Personalized intervals based on individual forgetting curves
- Future: Mobile push notifications in addition to email