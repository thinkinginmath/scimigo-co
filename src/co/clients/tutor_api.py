"""Tutor API client for LLM interactions."""

from typing import Any, Dict

import httpx
from co.config import get_settings


class TutorAPIClient:
    """Client for tutor/LLM service."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.tutor_base
        self.timeout = httpx.Timeout(30.0)

    async def create_turn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tutor turn."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/turns",
                json=request,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API calls."""
        return {
            "X-Service": "curriculum-orchestrator",
            "Content-Type": "application/json",
        }
