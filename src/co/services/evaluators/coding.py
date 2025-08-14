"""Coding problem evaluator service."""

import hashlib
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from co.clients.problem_bank import ProblemBankClient
from co.clients.eval_service import EvalServiceClient
from co.db.models import Submission as SubmissionModel
from co.schemas.submissions import SubmissionResult, VisibleResults, HiddenResults


class CodingEvaluator:
    """Evaluator for coding problems."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.problem_bank = ProblemBankClient()
        self.eval_service = EvalServiceClient()
    
    async def evaluate(
        self,
        session_id: UUID,
        problem_id: str,
        language: str,
        code: str,
        user_id: UUID,
    ) -> SubmissionResult:
        """Evaluate a coding submission."""
        # Fetch hidden test bundle from problem bank
        hidden_bundle = await self.problem_bank.get_hidden_bundle(problem_id)
        
        # Prepare evaluation request
        eval_request = {
            "problem_id": problem_id,
            "language": language,
            "code": code,
            "test_bundle": hidden_bundle,
            "timeout_ms": 5000,
        }
        
        # Run evaluation
        eval_result = await self.eval_service.evaluate_code(eval_request)
        
        # Process results
        visible_results = VisibleResults(
            passed=eval_result["visible"]["passed"],
            total=eval_result["visible"]["total"],
            details=eval_result["visible"].get("details", []),
        )
        
        hidden_results = HiddenResults(
            passed=eval_result["hidden"]["passed"],
            total=eval_result["hidden"]["total"],
            categories=self._extract_failure_categories(eval_result),
        )
        
        # Store submission
        submission = SubmissionModel(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            subject="coding",
            language=language,
            status=eval_result["status"],
            visible_passed=visible_results.passed,
            visible_total=visible_results.total,
            hidden_passed=hidden_results.passed,
            hidden_total=hidden_results.total,
            categories=hidden_results.categories,
            exec_ms=eval_result.get("exec_ms", 0),
            payload_sha256=hashlib.sha256(code.encode()).hexdigest(),
        )
        
        self.db.add(submission)
        await self.db.commit()
        
        return SubmissionResult(
            status=eval_result["status"],
            visible=visible_results,
            hidden=hidden_results,
            exec_ms=eval_result.get("exec_ms", 0),
        )
    
    def _extract_failure_categories(self, eval_result: Dict[str, Any]) -> list[str]:
        """Extract failure categories from evaluation result."""
        categories = []
        
        if eval_result["status"] == "timeout":
            categories.append("timeout")
        elif eval_result["status"] == "error":
            categories.append("runtime_error")
        elif eval_result["status"] == "failed":
            # Analyze failure patterns
            if eval_result["hidden"]["passed"] == 0:
                categories.append("logic_error")
            elif eval_result["hidden"]["passed"] < eval_result["hidden"]["total"] / 2:
                categories.append("edge_cases")
            else:
                categories.append("minor_issues")
        
        return categories