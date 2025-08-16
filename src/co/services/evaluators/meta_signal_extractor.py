"""Meta interview signal extraction utilities used by CodingEvaluator."""

from __future__ import annotations

import ast
import asyncio
import re
import textwrap
from typing import Any, Dict


class MetaSignalExtractor:
    """Extract Meta interview signals from code submissions."""

    def __init__(self, use_llm: bool = True):
        """Initialize with optional LLM-based analysis.

        Args:
            use_llm: Whether to use LLM for complexity analysis (default: True)
        """
        self.use_llm = use_llm
        self.hybrid_analyzer = None
        if use_llm:
            try:
                from co.services.evaluators.llm_complexity_analyzer import (
                    HybridComplexityAnalyzer,
                )

                self.hybrid_analyzer = HybridComplexityAnalyzer()
            except ImportError:
                # Fallback if LLM analyzer not available
                self.use_llm = False

    async def extract_signals_async(
        self,
        code: str,
        language: str,
        test_results: Dict[str, Any],
        problem_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Async version that can use LLM for complexity analysis."""

        # Extract basic complexity signals using AST
        basic_complexity = self._extract_complexity_signals(code, language)

        # Use hybrid analyzer if available
        if self.use_llm and self.hybrid_analyzer:
            try:
                complexity = await self.hybrid_analyzer.analyze(
                    code, language, basic_complexity, problem_metadata
                )
            except Exception:
                # Fallback to basic analysis
                complexity = basic_complexity
        else:
            complexity = basic_complexity

        signals = {
            "correctness": self._extract_correctness_signals(test_results),
            "complexity": complexity,
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

    def extract_signals(
        self,
        code: str,
        language: str,
        test_results: Dict[str, Any],
        problem_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synchronous extraction method for backward compatibility."""

        # If LLM is enabled, run async version in event loop
        if self.use_llm:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, create a task
                    task = asyncio.create_task(
                        self.extract_signals_async(
                            code, language, test_results, problem_metadata
                        )
                    )
                    # Use a short timeout to prevent blocking
                    asyncio.wait_for(task, timeout=3.0)
                    return task.result()
                else:
                    # Run in new event loop
                    return asyncio.run(
                        self.extract_signals_async(
                            code, language, test_results, problem_metadata
                        )
                    )
            except (asyncio.TimeoutError, Exception):
                # Fallback to synchronous version
                pass

        # Synchronous fallback
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
    def _extract_correctness_signals(
        self, test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
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
    def _compute_pillar_scores(
        self, signals: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, int]:
        """Compute scores for Meta's five interview pillars."""

        scores = {
            "problem_understanding": 50,
            "algorithmic_correctness": int(
                signals["correctness"]["visible_pass_rate"] * 100
            ),
            "complexity_analysis": (
                100 if signals["complexity"]["estimated_time"] != "unknown" else 0
            ),
            "code_quality": 100 if signals["quality"]["has_docstring"] else 50,
            "communication": 100 if signals["structure"]["has_function_defs"] else 50,
        }
        return scores

    def _generate_feedback(
        self, pillar_scores: Dict[str, int], signals: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate feedback messages for each pillar."""

        feedback: Dict[str, str] = {}

        # Correctness feedback
        correctness_score = pillar_scores.get("algorithmic_correctness", 0)
        if correctness_score >= 90:
            feedback["algorithmic_correctness"] = (
                "Excellent! Solution passes all test cases."
            )
        elif correctness_score >= 70:
            feedback["algorithmic_correctness"] = (
                f"Good correctness ({correctness_score}%). Consider edge cases: {', '.join(signals['correctness'].get('categories_failed', []))}"
            )
        else:
            feedback["algorithmic_correctness"] = (
                f"Solution needs work ({correctness_score}%). Failed categories: {', '.join(signals['correctness'].get('categories_failed', []))}"
            )

        # Complexity feedback - enhanced if LLM analysis available
        complexity = signals.get("complexity", {})
        if complexity.get("method") == "llm" and complexity.get("explanation"):
            feedback["complexity_analysis"] = (
                f"Time: {complexity.get('estimated_time', 'unknown')}, Space: {complexity.get('estimated_space', 'unknown')}. {complexity.get('explanation', '')}"
            )

            # Add optimization suggestions if available
            if complexity.get("optimizations"):
                feedback[
                    "complexity_analysis"
                ] += f" Suggestions: {'; '.join(complexity['optimizations'][:2])}"
        else:
            # Fallback to basic feedback
            time_complexity = complexity.get("estimated_time", "unknown")
            feedback["complexity_analysis"] = f"Time complexity: {time_complexity}"
            if complexity.get("loop_depth", 0) > 2:
                feedback[
                    "complexity_analysis"
                ] += ". Consider reducing nested loops for better performance."

        # Quality feedback
        quality_score = pillar_scores.get("code_quality", 0)
        quality_tips = []
        if not signals["quality"].get("has_docstring"):
            quality_tips.append("add docstrings")
        if signals["quality"].get("comment_lines", 0) == 0:
            quality_tips.append("add comments for complex logic")

        if quality_score >= 80:
            feedback["code_quality"] = "Well-structured code with good practices."
        elif quality_tips:
            feedback["code_quality"] = (
                f"Code quality score: {quality_score}%. Consider: {', '.join(quality_tips)}"
            )
        else:
            feedback["code_quality"] = (
                f"Code quality: {quality_score}%. Focus on clarity and maintainability."
            )

        # Problem understanding feedback
        understanding_score = pillar_scores.get("problem_understanding", 0)
        if understanding_score >= 80:
            feedback["problem_understanding"] = (
                "Good problem understanding with edge case consideration."
            )
        else:
            feedback["problem_understanding"] = (
                "Consider edge cases: empty input, single element, duplicates, negative values."
            )

        # Communication feedback
        if signals["structure"].get("has_function_defs"):
            feedback["communication"] = (
                "Good code organization with clear function structure."
            )
        else:
            feedback["communication"] = (
                "Consider organizing code into functions for better readability."
            )

        return feedback

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _check_edge_case_handling(self, test_results: Dict[str, Any]) -> bool:
        return "edge_cases" not in test_results.get("categories", [])

    def _is_meta_track(self, metadata: Dict[str, Any]) -> bool:
        """Check if a problem belongs to the Meta interview track."""

        return "company:meta" in metadata.get("labels", [])
