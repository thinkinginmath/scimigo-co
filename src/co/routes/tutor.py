"""Tutor interaction endpoints."""

from uuid import UUID

from co.auth import get_current_user
from co.db.base import get_db
from co.schemas.tutor import TutorMessageCreate, TutorStreamResponse
from co.services.tutor import TutorService
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/messages", response_model=TutorStreamResponse)
async def create_tutor_message(
    message: TutorMessageCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> TutorStreamResponse | JSONResponse:
    """Start a tutor turn for a session."""
    service = TutorService(db)

    # Verify session ownership
    from co.services.sessions import SessionService

    session_service = SessionService(db)
    session = await session_service.get_session(message.session_id)

    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check concurrent SSE streams
    active_streams = await service.count_active_streams(user_id)
    if active_streams >= 2:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "MAX_STREAMS",
                    "message": "Maximum concurrent tutor streams reached",
                    "details": {"max_streams": 2, "active": active_streams},
                }
            },
        )

    # Initialize tutor turn
    stream_data = await service.create_tutor_turn(
        session_id=message.session_id,
        problem_id=message.problem_id,
        hint_level=message.hint_level,
        last_eval=message.last_eval,
        user_id=user_id,
    )

    # Update session hint level
    await session_service.update_hint_level(message.session_id, message.hint_level)

    return TutorStreamResponse(
        stream_url=stream_data["stream_url"],
        token=stream_data["token"],
    )
