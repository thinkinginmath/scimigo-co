"""Tutor orchestration service."""

import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

import aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from co.config import get_settings
from co.clients.tutor_api import TutorAPIClient
from co.clients.problem_bank import ProblemBankClient


class TutorService:
    """Service for orchestrating tutor interactions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.tutor_client = TutorAPIClient()
        self.problem_bank = ProblemBankClient()
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if not self._redis:
            self._redis = await aioredis.from_url(self.settings.redis_url)
        return self._redis
    
    async def count_active_streams(self, user_id: UUID) -> int:
        """Count active SSE streams for user."""
        redis = await self._get_redis()
        key = f"sse:streams:{user_id}"
        count = await redis.scard(key)
        return count or 0
    
    async def create_tutor_turn(
        self,
        session_id: UUID,
        problem_id: str,
        hint_level: int,
        last_eval: Optional[Dict[str, Any]],
        user_id: UUID,
    ) -> Dict[str, str]:
        """Create a new tutor turn and return stream info."""
        # Fetch problem content
        problem = await self.problem_bank.get_problem(problem_id)
        
        # Build context for tutor
        context = {
            "session_id": str(session_id),
            "problem_id": problem_id,
            "problem_content": problem.get("content"),
            "problem_type": problem.get("type"),
            "hint_level": hint_level,
            "last_evaluation": last_eval,
            "user_id": str(user_id),
        }
        
        # Map hint level to instruction
        hint_instructions = {
            1: "Provide a gentle nudge without revealing the solution",
            2: "Give a more detailed hint with conceptual guidance",
            3: "Provide step-by-step guidance toward the solution",
        }
        
        # Create tutor request
        tutor_request = {
            "context": context,
            "instruction": hint_instructions.get(hint_level, hint_instructions[1]),
            "stream": True,
        }
        
        # Initialize tutor turn
        response = await self.tutor_client.create_turn(tutor_request)
        
        # Register stream in Redis
        redis = await self._get_redis()
        stream_key = f"sse:streams:{user_id}"
        await redis.sadd(stream_key, response["token"])
        await redis.expire(stream_key, 300)  # 5 minute TTL
        
        return {
            "stream_url": f"{self.settings.api_base}/v1/tutor/stream",
            "token": response["token"],
        }
    
    async def cleanup_stream(self, user_id: UUID, token: str) -> None:
        """Clean up completed stream."""
        redis = await self._get_redis()
        stream_key = f"sse:streams:{user_id}"
        await redis.srem(stream_key, token)