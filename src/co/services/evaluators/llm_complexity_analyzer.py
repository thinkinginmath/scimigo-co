"""LLM-based complexity analysis for more accurate signal extraction."""

import asyncio
import json
from typing import Any, Dict, Optional

from co.clients.tutor_api import TutorAPIClient


class LLMComplexityAnalyzer:
    """Analyze code complexity using LLM for more sophisticated understanding."""

    def __init__(self):
        self.tutor_client = TutorAPIClient()
        self.timeout = 2.0  # 2 second timeout for LLM analysis

    async def analyze_complexity(
        self, code: str, language: str, problem_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze code complexity using LLM.

        Returns:
            Dict with time_complexity, space_complexity, and explanation
        """

        prompt = self._build_complexity_prompt(code, language, problem_context)

        try:
            # Use asyncio timeout to prevent blocking
            async with asyncio.timeout(self.timeout):
                response = await self.tutor_client.analyze_code(
                    prompt=prompt, response_format="json"
                )

            return self._parse_llm_response(response)

        except asyncio.TimeoutError:
            # Fallback to basic analysis if LLM times out
            return {
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "explanation": "Analysis timed out",
                "confidence": 0,
            }
        except Exception as e:
            # Log error and return fallback
            print(f"LLM complexity analysis failed: {e}")
            return {
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "explanation": str(e),
                "confidence": 0,
            }

    def _build_complexity_prompt(
        self, code: str, language: str, problem_context: Optional[str]
    ) -> str:
        """Build prompt for LLM complexity analysis."""

        context = f"Problem: {problem_context}\n\n" if problem_context else ""

        return f"""Analyze the time and space complexity of this {language} code.

{context}Code:
```{language}
{code}
```

Provide a JSON response with:
1. time_complexity: Big-O notation (e.g., "O(n)", "O(n log n)", "O(n^2)")
2. space_complexity: Big-O notation
3. explanation: Brief explanation of the analysis
4. confidence: 0-100 score of analysis confidence
5. bottlenecks: List of performance bottlenecks if any
6. optimizations: Suggested optimizations if applicable

Focus on the dominant complexity and consider:
- Loop nesting and iterations
- Recursive calls and their depth
- Data structure operations (sorting, searching, etc.)
- Space used by data structures and recursion stack

JSON Response:"""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""

        try:
            # Extract JSON from response
            result = json.loads(response)

            # Validate and normalize the response
            return {
                "time_complexity": result.get("time_complexity", "O(n)"),
                "space_complexity": result.get("space_complexity", "O(1)"),
                "explanation": result.get("explanation", ""),
                "confidence": result.get("confidence", 50),
                "bottlenecks": result.get("bottlenecks", []),
                "optimizations": result.get("optimizations", []),
            }

        except json.JSONDecodeError:
            # Try to extract complexity from text
            import re

            time_match = re.search(r"O\([^)]+\)", response)
            time_complexity = time_match.group(0) if time_match else "O(n)"

            return {
                "time_complexity": time_complexity,
                "space_complexity": "O(1)",
                "explanation": response[:200],
                "confidence": 30,
            }


class HybridComplexityAnalyzer:
    """Combines AST-based and LLM-based analysis for best results."""

    def __init__(self):
        self.llm_analyzer = LLMComplexityAnalyzer()

    async def analyze(
        self,
        code: str,
        language: str,
        ast_analysis: Dict[str, Any],
        problem_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform hybrid analysis using both AST and LLM.

        Priority:
        1. Use LLM if confidence > 70
        2. Use AST for simple cases (single loops, no recursion)
        3. Combine both for validation
        """

        # Get problem context if available
        problem_context = None
        if problem_metadata:
            problem_context = problem_metadata.get("statement", "")[:500]

        # Run LLM analysis asynchronously
        llm_result = await self.llm_analyzer.analyze_complexity(
            code, language, problem_context
        )

        # If LLM has high confidence, use it
        if llm_result.get("confidence", 0) > 70:
            return {
                "estimated_time": llm_result["time_complexity"],
                "estimated_space": llm_result["space_complexity"],
                "explanation": llm_result["explanation"],
                "method": "llm",
                "confidence": llm_result["confidence"],
                "loop_depth": ast_analysis.get("loop_depth", 0),
                "bottlenecks": llm_result.get("bottlenecks", []),
                "optimizations": llm_result.get("optimizations", []),
            }

        # For simple cases, trust AST analysis
        if ast_analysis.get("loop_depth", 0) <= 1 and not ast_analysis.get(
            "has_recursion"
        ):
            return {
                "estimated_time": ast_analysis.get("estimated_time", "O(n)"),
                "estimated_space": "O(1)",
                "explanation": "Simple iterative solution",
                "method": "ast",
                "confidence": 80,
                "loop_depth": ast_analysis.get("loop_depth", 0),
            }

        # For complex cases, prefer LLM even with lower confidence
        if llm_result.get("confidence", 0) > 30:
            return {
                "estimated_time": llm_result["time_complexity"],
                "estimated_space": llm_result["space_complexity"],
                "explanation": llm_result["explanation"],
                "method": "llm_fallback",
                "confidence": llm_result["confidence"],
                "loop_depth": ast_analysis.get("loop_depth", 0),
            }

        # Ultimate fallback to AST
        return {
            "estimated_time": ast_analysis.get("estimated_time", "unknown"),
            "estimated_space": "unknown",
            "explanation": "Unable to determine complexity accurately",
            "method": "ast_fallback",
            "confidence": 20,
            "loop_depth": ast_analysis.get("loop_depth", 0),
        }
