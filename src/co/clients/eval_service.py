"""Evaluation Service API client."""

from typing import Dict, Any

import httpx

from co.config import get_settings


class EvalServiceClient:
    """Client for code and math evaluation service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.eval_base
        self.timeout = httpx.Timeout(60.0)  # Longer timeout for code execution
    
    async def evaluate_code(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate code submission."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/evaluate/code",
                json=request,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def evaluate_math(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate math submission."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/evaluate/math",
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