"""Problem Bank API client."""

from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx

from co.config import get_settings


class ProblemBankClient:
    """Client for interacting with Problem Bank service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.problem_bank_base
        self.timeout = httpx.Timeout(30.0)
    
    async def get_problem(self, problem_id: str) -> Dict[str, Any]:
        """Get problem metadata and content."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/internal/problems/{problem_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def get_hidden_bundle(self, problem_id: str) -> Dict[str, Any]:
        """Get hidden test bundle for a problem (internal only)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/internal/problems/{problem_id}/hidden-bundle",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def get_problems_by_subject(
        self,
        subject: str,
        track_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get problems filtered by subject and optional track."""
        params = {
            "subject": subject,
            "limit": limit,
        }
        if track_id:
            params["track_id"] = str(track_id)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/internal/problems",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()["items"]

    async def get_track(self, slug: str) -> Dict[str, Any]:
        """Fetch a track definition by slug from Problem Bank."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/internal/tracks/{slug}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for internal API calls."""
        return {
            "X-Service": "curriculum-orchestrator",
            "Content-Type": "application/json",
        }