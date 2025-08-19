"""Coding problem evaluator service."""

import hashlib
from typing import Any, Dict, cast
from uuid import UUID

from co.clients.eval_service import EvalServiceClient
from co.clients.problem_bank import ProblemBankClient
from co.db.models import Submission as SubmissionModel
from co.schemas.submissions import HiddenResults, SubmissionResult, VisibleResults
from co.services.evaluators.meta_signal_extractor import MetaSignalExtractor
from sqlalchemy.ext.asyncio import AsyncSession


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
        # Check if this is a Meta track problem and extract signals
        problem_metadata = await self.problem_bank.get_problem(problem_id)
        extractor = MetaSignalExtractor()

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

        if extractor._is_meta_track(problem_metadata):
            test_results = {
                "visible_passed": visible_results.passed,
                "visible_total": visible_results.total,
                "hidden_passed": hidden_results.passed,
                "hidden_total": hidden_results.total,
                "categories": hidden_results.categories,
                "status": eval_result["status"],
            }
            meta_data = extractor.extract_signals(
                code, language, test_results, problem_metadata
            )
            submission.pillar_scores = meta_data["pillar_scores"]
            submission.signal_metadata = meta_data["signals"]
            submission.feedback = meta_data["feedback"]

        self.db.add(submission)
        await self.db.commit()

        return SubmissionResult(
            status=eval_result["status"],
            visible=visible_results,
            hidden=hidden_results,
            exec_ms=eval_result.get("exec_ms", 0),
            pillar_scores=cast(dict[str, int] | None, submission.pillar_scores),
            feedback=cast(dict[str, Any] | None, submission.feedback),
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
