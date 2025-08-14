"""Math problem evaluator service."""

import hashlib
import json
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from co.clients.problem_bank import ProblemBankClient
from co.clients.eval_service import EvalServiceClient
from co.db.models import Submission as SubmissionModel
from co.schemas.submissions import SubmissionResult, VisibleResults, HiddenResults


class MathEvaluator:
    """Evaluator for math problems."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.problem_bank = ProblemBankClient()
        self.eval_service = EvalServiceClient()
    
    async def evaluate(
        self,
        session_id: UUID,
        problem_id: str,
        steps: Optional[List[str]],
        expression: Optional[str],
        user_id: UUID,
    ) -> SubmissionResult:
        """Evaluate a math submission."""
        # Fetch problem metadata and solution
        problem_data = await self.problem_bank.get_problem(problem_id)
        
        # Prepare evaluation request for math adapter
        eval_request = {
            "problem_id": problem_id,
            "problem_type": problem_data.get("type", "expression"),
            "user_answer": expression,
            "user_steps": steps,
            "expected_answer": problem_data.get("solution"),
            "tolerance": problem_data.get("tolerance", 0.001),
        }
        
        # Run evaluation through math adapter
        eval_result = await self.eval_service.evaluate_math(eval_request)
        
        # Process results
        visible_results = VisibleResults(
            passed=1 if eval_result["correct"] else 0,
            total=1,
            details=[{
                "correct": eval_result["correct"],
                "feedback": eval_result.get("feedback"),
            }],
        )
        
        hidden_results = HiddenResults(
            passed=1 if eval_result["correct"] else 0,
            total=1,
            categories=self._extract_math_categories(eval_result),
        )
        
        # Store submission
        payload_content = json.dumps({"steps": steps, "expression": expression})
        submission = SubmissionModel(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            subject="math",
            language=None,
            status="passed" if eval_result["correct"] else "failed",
            visible_passed=visible_results.passed,
            visible_total=visible_results.total,
            hidden_passed=hidden_results.passed,
            hidden_total=hidden_results.total,
            categories=hidden_results.categories,
            exec_ms=eval_result.get("exec_ms", 0),
            payload_sha256=hashlib.sha256(payload_content.encode()).hexdigest(),
        )
        
        self.db.add(submission)
        await self.db.commit()
        
        return SubmissionResult(
            status="passed" if eval_result["correct"] else "failed",
            visible=visible_results,
            hidden=hidden_results,
            exec_ms=eval_result.get("exec_ms", 0),
        )
    
    def _extract_math_categories(self, eval_result: dict) -> List[str]:
        """Extract failure categories for math problems."""
        if eval_result["correct"]:
            return []
        
        categories = []
        error_type = eval_result.get("error_type")
        
        if error_type == "wrong_answer":
            categories.append("incorrect_answer")
        elif error_type == "incomplete":
            categories.append("incomplete_solution")
        elif error_type == "method_error":
            categories.append("incorrect_method")
        else:
            categories.append("unknown_error")
        
        return categories