"""Session management endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from co.auth import get_current_user
from co.db.base import get_db
from co.services.sessions import SessionService
from co.schemas.sessions import SessionCreate, SessionUpdate, Session

router = APIRouter()


@router.post("", response_model=Session, status_code=201)
async def create_session(
    session_data: SessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> Session:
    """Create a new study or practice session."""
    service = SessionService(db)
    session = await service.create_session(
        user_id=user_id,
        **session_data.model_dump()
    )
    return session


@router.patch("/{session_id}", response_model=Session)
async def update_session(
    session_id: UUID,
    update_data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> Session:
    """Update a session (advance, retry, or give up)."""
    service = SessionService(db)
    
    # Verify session ownership
    session = await service.get_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update based on action
    if update_data.action == "advance":
        session = await service.advance_session(session_id)
    elif update_data.action == "retry":
        session = await service.retry_problem(session_id)
    elif update_data.action == "giveup":
        session = await service.abandon_session(session_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return session


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> Session:
    """Get session details."""
    service = SessionService(db)
    session = await service.get_session(session_id)
    
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session