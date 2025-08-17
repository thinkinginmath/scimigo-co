"""Personalization and recommendation service."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from co.clients.problem_bank import ProblemBankClient
from co.config import get_settings
from co.db.models import Mastery, ReviewQueue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PersonalizationService:
    """Service for personalized learning recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.problem_bank = ProblemBankClient()

    async def get_next_problem(
        self,
        user_id: UUID,
        subject: str,
        track_id: Optional[UUID] = None,
        exclude: Optional[List[str]] = None,
    ) -> str:
        """Get next recommended problem for user."""
        exclude = exclude or []

        # Check for due review items first
        review_problem = await self._get_due_review(user_id, subject)
        if review_problem and review_problem not in exclude:
            return review_problem

        # Get candidate problems
        candidates = await self.problem_bank.get_problems_by_subject(
            subject=subject,
            track_id=track_id,
        )

        # Filter out excluded and recently attempted
        candidates = [p for p in candidates if p["id"] not in exclude]

        # Score and rank candidates
        scored_candidates = []
        for candidate in candidates:
            score = await self._score_problem(user_id, candidate)
            scored_candidates.append((score, candidate))

        # Sort by score (higher is better)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        if scored_candidates:
            return scored_candidates[0][1]["id"]

        # Fallback to first available
        return candidates[0]["id"] if candidates else None

    async def _score_problem(self, user_id: UUID, problem: dict) -> float:
        """Score a problem for recommendation."""
        score = 0.0

        # Weakness matching
        topics = problem.get("topics", [])
        weakness_score = await self._calculate_weakness_score(user_id, topics)
        score += self.settings.weight_weakness * weakness_score

        # Novelty (not recently attempted)
        novelty_score = await self._calculate_novelty_score(user_id, problem["id"])
        score += self.settings.weight_novelty * novelty_score

        # Difficulty pacing
        difficulty_score = await self._calculate_difficulty_score(
            user_id, problem.get("difficulty", 50)
        )
        score += self.settings.weight_difficulty * difficulty_score

        # Recency diversification
        recency_score = await self._calculate_recency_score(user_id, topics)
        score += self.settings.weight_recency * recency_score

        return score

    async def _calculate_weakness_score(
        self, user_id: UUID, topics: List[str]
    ) -> float:
        """Calculate weakness score based on mastery."""
        if not topics:
            return 0.5

        # Get mastery scores for topics
        result = await self.db.execute(
            select(Mastery).where(
                Mastery.user_id == user_id,
                Mastery.key_type == "topic",
                Mastery.key_id.in_(topics),
            )
        )
        masteries = result.scalars().all()

        if not masteries:
            return 1.0  # New topics are high priority

        # Average inverse mastery (lower mastery = higher score)
        avg_mastery = sum(m.score for m in masteries) / len(masteries)
        return 1.0 - (avg_mastery / 100.0)

    async def _calculate_novelty_score(self, user_id: UUID, problem_id: str) -> float:
        """Calculate novelty score (not recently attempted)."""
        # Check submission history
        from co.db.models import Submission

        result = await self.db.execute(
            select(Submission)
            .where(
                Submission.user_id == user_id,
                Submission.problem_id == problem_id,
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
        last_submission = result.scalar_one_or_none()

        if not last_submission:
            return 1.0  # Never attempted

        # Score based on time since last attempt
        days_since = (datetime.utcnow() - last_submission.created_at).days
        if days_since > 30:
            return 1.0
        elif days_since > 7:
            return 0.7
        elif days_since > 1:
            return 0.3
        else:
            return 0.0

    async def _calculate_difficulty_score(
        self, user_id: UUID, difficulty: int
    ) -> float:
        """Calculate difficulty pacing score."""
        # Get user's recent performance
        from co.db.models import Submission

        result = await self.db.execute(
            select(Submission)
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc())
            .limit(5)
        )
        recent_submissions = result.scalars().all()

        if not recent_submissions:
            # Start with medium difficulty
            return 1.0 if 40 <= difficulty <= 60 else 0.5

        # Check recent success rate
        success_rate = sum(1 for s in recent_submissions if s.status == "passed") / len(
            recent_submissions
        )

        # Adjust difficulty based on performance
        if success_rate > 0.8:
            # Doing well, prefer harder problems
            return 1.0 if difficulty > 60 else 0.5
        elif success_rate < 0.4:
            # Struggling, prefer easier problems
            return 1.0 if difficulty < 40 else 0.3
        else:
            # Balanced, prefer medium difficulty
            return 1.0 if 40 <= difficulty <= 60 else 0.6

    async def _calculate_recency_score(self, user_id: UUID, topics: List[str]) -> float:
        """Calculate recency diversification score."""
        # Prefer topics not recently practiced
        return 0.5  # Simplified for now

    async def _get_due_review(self, user_id: UUID, subject: str) -> Optional[str]:
        """Get next due review item."""
        result = await self.db.execute(
            select(ReviewQueue)
            .where(
                ReviewQueue.user_id == user_id,
                ReviewQueue.next_due_at <= datetime.utcnow(),
            )
            .order_by(ReviewQueue.next_due_at)
            .limit(1)
        )
        review_item = result.scalar_one_or_none()

        return review_item.problem_id if review_item else None

    async def get_due_reviews(self, user_id: UUID, limit: int = 5) -> List[ReviewQueue]:
        """Return review queue items that are due."""
        result = await self.db.execute(
            select(ReviewQueue)
            .where(
                ReviewQueue.user_id == user_id,
                ReviewQueue.next_due_at <= datetime.utcnow(),
            )
            .order_by(ReviewQueue.next_due_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_mastery(
        self,
        user_id: UUID,
        problem_id: str,
        success: bool,
    ) -> None:
        """Update mastery scores based on submission result."""
        # Get problem topics
        problem_data = await self.problem_bank.get_problem(problem_id)
        topics = problem_data.get("topics", [])

        for topic in topics:
            # Get or create mastery record
            result = await self.db.execute(
                select(Mastery).where(
                    Mastery.user_id == user_id,
                    Mastery.key_type == "topic",
                    Mastery.key_id == topic,
                )
            )
            mastery = result.scalar_one_or_none()

            if not mastery:
                mastery = Mastery(
                    user_id=user_id,
                    key_type="topic",
                    key_id=topic,
                    score=50,
                    ema=0.5,
                )
                self.db.add(mastery)

            # Update score with EMA
            alpha = 0.2  # Learning rate
            new_value = 1.0 if success else 0.0
            mastery.ema = alpha * new_value + (1 - alpha) * mastery.ema
            mastery.score = int(mastery.ema * 100)
            mastery.updated_at = datetime.utcnow()

        await self.db.commit()

    async def add_to_review_queue(
        self,
        user_id: UUID,
        problem_id: str,
        reason: str,
    ) -> None:
        """Add problem to spaced review queue."""
        # Check if already in queue
        result = await self.db.execute(
            select(ReviewQueue).where(
                ReviewQueue.user_id == user_id,
                ReviewQueue.problem_id == problem_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Move to earlier bucket if failed
            if reason == "fail" and existing.bucket > 0:
                existing.bucket = max(0, existing.bucket - 1)
                existing.next_due_at = datetime.utcnow() + timedelta(
                    days=self.settings.review_buckets[existing.bucket]
                )
        else:
            # Add new review item
            review = ReviewQueue(
                user_id=user_id,
                problem_id=problem_id,
                reason=reason,
                bucket=0,
                next_due_at=datetime.utcnow() + timedelta(days=1),
            )
            self.db.add(review)

        await self.db.commit()

    async def mark_review_result(
        self, user_id: UUID, problem_id: str, success: bool
    ) -> None:
        """Update review queue entry based on task result."""
        result = await self.db.execute(
            select(ReviewQueue).where(
                ReviewQueue.user_id == user_id,
                ReviewQueue.problem_id == problem_id,
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            if not success:
                await self.add_to_review_queue(user_id, problem_id, "fail")
            return

        if success:
            item.bucket += 1
            if item.bucket >= len(self.settings.review_buckets):
                await self.db.delete(item)
            else:
                days = self.settings.review_buckets[item.bucket]
                item.next_due_at = datetime.utcnow() + timedelta(days=days)
        else:
            item.bucket = 0
            days = self.settings.review_buckets[0]
            item.next_due_at = datetime.utcnow() + timedelta(days=days)

        await self.db.commit()
