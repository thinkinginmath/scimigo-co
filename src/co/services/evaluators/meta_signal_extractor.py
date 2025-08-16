from __future__ import annotations

"""Meta interview signal extraction utilities used by CodingEvaluator."""

from typing import Any, Dict

import ast
import re
import textwrap


class MetaSignalExtractor:
    """Extract Meta interview signals from code submissions."""

    def extract_signals(
        self,
        code: str,
        language: str,
        test_results: Dict[str, Any],
        problem_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Main extraction method returning pillar scores, raw signals and feedback."""

        signals = {
            "correctness": self._extract_correctness_signals(test_results),
            "complexity": self._extract_complexity_signals(code, language),
            "quality": self._extract_quality_signals(code, language),
            "test_hygiene": self._extract_test_signals(code, language),
            "structure": self._extract_structure_signals(code, language),
        }

        pillar_scores = self._compute_pillar_scores(signals, problem_metadata)
        feedback = self._generate_feedback(pillar_scores, signals)

        return {
            "pillar_scores": pillar_scores,
            "signals": signals,
            "feedback": feedback,
        }

    # ------------------------------------------------------------------
    # Signal extraction helpers
    # ------------------------------------------------------------------
    def _extract_correctness_signals(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results for correctness signals."""

        visible_total = max(test_results.get("visible_total", 0), 1)
        hidden_total = max(test_results.get("hidden_total", 0), 1)

        return {
            "visible_pass_rate": test_results.get("visible_passed", 0) / visible_total,
            "hidden_pass_rate": test_results.get("hidden_passed", 0) / hidden_total,
            "categories_failed": test_results.get("categories", []),
            "has_runtime_errors": "error" in test_results.get("status", ""),
            "handles_edge_cases": self._check_edge_case_handling(test_results),
        }

    def _extract_complexity_signals(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze algorithmic complexity."""

        if language == "python":
            return self._analyze_python_complexity(code)
        if language == "javascript":
            return self._analyze_javascript_complexity(code)
        return {"estimated_time": "unknown", "loop_depth": 0}

    # ------------------------------------------------------------------
    # Language specific complexity helpers
    # ------------------------------------------------------------------
    def _analyze_python_complexity(self, code: str) -> Dict[str, Any]:
        """Very rough Python complexity analysis based on loop depth."""

        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return {"estimated_time": "unknown", "loop_depth": 0}

        class LoopDepthVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.max_depth = 0
                self.current = 0

            def generic_visit(self, node):
                super().generic_visit(node)

            def visit_For(self, node):  # type: ignore[override]
                self.current += 1
                self.max_depth = max(self.max_depth, self.current)
                self.generic_visit(node)
                self.current -= 1

            def visit_While(self, node):  # type: ignore[override]
                self.visit_For(node)

        visitor = LoopDepthVisitor()
        visitor.visit(tree)
        depth = visitor.max_depth

        if depth == 0:
            estimate = "O(1)"
        elif depth == 1:
            estimate = "O(n)"
        else:
            estimate = f"O(n^{depth})"
        return {"estimated_time": estimate, "loop_depth": depth}

    def _analyze_javascript_complexity(self, code: str) -> Dict[str, Any]:
        """Placeholder complexity analysis for JavaScript."""

        loop_count = len(re.findall(r"for\s*\(|while\s*\(", code))
        if loop_count == 0:
            return {"estimated_time": "O(1)", "loop_depth": 0}
        if loop_count == 1:
            return {"estimated_time": "O(n)", "loop_depth": 1}
        return {"estimated_time": f"O(n^{loop_count})", "loop_depth": loop_count}

    # ------------------------------------------------------------------
    # Additional signal extraction helpers
    # ------------------------------------------------------------------
    def _extract_quality_signals(self, code: str, language: str) -> Dict[str, Any]:
        """Simple code quality metrics."""

        if language == "python":
            comment_lines = len(re.findall(r"^\s*#", code, re.MULTILINE))
            has_docstring = bool(re.search(r'"""|\'\'\'', code))
        else:
            comment_lines = len(re.findall(r"//", code))
            has_docstring = False
        return {"comment_lines": comment_lines, "has_docstring": has_docstring}

    def _extract_test_signals(self, code: str, language: str) -> Dict[str, Any]:
        """Detect testing related signals in submission code."""

        if language == "python":
            uses_assert = "assert" in code
        else:
            uses_assert = "assert" in code or "expect(" in code
        return {"uses_asserts": uses_assert}

    def _extract_structure_signals(self, code: str, language: str) -> Dict[str, Any]:
        """Detect structural aspects of the solution."""

        if language == "python":
            try:
                tree = ast.parse(code)
            except SyntaxError:
                return {"has_function_defs": False}
            has_fn = any(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
        else:
            has_fn = bool(re.search(r"function\s+\w+|=>", code))
        return {"has_function_defs": has_fn}

    # ------------------------------------------------------------------
    # Scoring and feedback
    # ------------------------------------------------------------------
    def _compute_pillar_scores(self, signals: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, int]:
        """Compute scores for Meta's five interview pillars."""

        scores = {
            "problem_understanding": 50,
            "algorithmic_correctness": int(
                signals["correctness"]["visible_pass_rate"] * 100
            ),
            "complexity_analysis": 100
            if signals["complexity"]["estimated_time"] != "unknown"
            else 0,
            "code_quality": 100 if signals["quality"]["has_docstring"] else 50,
            "communication": 100 if signals["structure"]["has_function_defs"] else 50,
        }
        return scores

    def _generate_feedback(
        self, pillar_scores: Dict[str, int], signals: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate simple feedback messages for each pillar."""

        feedback: Dict[str, str] = {}
        for pillar, score in pillar_scores.items():
            if score >= 80:
                message = "Great job"
            elif score >= 50:
                message = "Good progress"
            else:
                message = "Needs improvement"
            feedback[pillar] = message
        return feedback

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _check_edge_case_handling(self, test_results: Dict[str, Any]) -> bool:
        return "edge_cases" not in test_results.get("categories", [])

    def _is_meta_track(self, metadata: Dict[str, Any]) -> bool:
        """Check if a problem belongs to the Meta interview track."""

        return "company:meta" in metadata.get("labels", [])
