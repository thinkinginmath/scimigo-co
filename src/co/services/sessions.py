"""Session management service."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from co.db.models import Session as SessionModel
from co.services.personalization import PersonalizationService
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class SessionService:
    """Service for managing learning sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.personalization = PersonalizationService(db)

    async def create_session(
        self,
        user_id: UUID,
        subject: str,
        mode: str,
        track_id: Optional[UUID] = None,
        problem_id: Optional[str] = None,
    ) -> SessionModel:
        """Create a new learning session."""
        # If no problem specified, get recommendation
        if not problem_id:
            problem_id = await self.personalization.get_next_problem(
                user_id=user_id,
                subject=subject,
                track_id=track_id,
            )

        session = SessionModel(
            user_id=user_id,
            subject=subject,
            mode=mode,
            track_id=track_id,
            problem_id=problem_id,
            status="active",
            last_hint_level=0,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def get_session(self, session_id: UUID) -> Optional[SessionModel]:
        """Get session by ID."""
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def advance_session(self, session_id: UUID) -> SessionModel:
        """Advance to next problem in session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        # Get next problem recommendation
        next_problem = await self.personalization.get_next_problem(
            user_id=session.user_id,
            subject=session.subject,
            track_id=session.track_id,
            exclude=[session.problem_id],
        )

        session.problem_id = next_problem
        session.last_hint_level = 0
        session.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def retry_problem(self, session_id: UUID) -> SessionModel:
        """Reset hint level for retry."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        session.last_hint_level = 0
        session.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def abandon_session(self, session_id: UUID) -> SessionModel:
        """Mark session as abandoned."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        session.status = "abandoned"
        session.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def update_hint_level(self, session_id: UUID, hint_level: int) -> None:
        """Update session hint level."""
        await self.db.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(last_hint_level=hint_level, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def record_success(self, session_id: UUID) -> None:
        """Record successful submission."""
        # Update mastery scores
        session = await self.get_session(session_id)
        if session:
            await self.personalization.update_mastery(
                user_id=session.user_id,
                problem_id=session.problem_id,
                success=True,
            )

    async def record_failure(self, session_id: UUID, categories: List[str]) -> None:
        """Record failed submission with failure categories."""
        session = await self.get_session(session_id)
        if session:
            # Update mastery
            await self.personalization.update_mastery(
                user_id=session.user_id,
                problem_id=session.problem_id,
                success=False,
            )

            # Add to review queue
            await self.personalization.add_to_review_queue(
                user_id=session.user_id,
                problem_id=session.problem_id,
                reason="fail",
            )
