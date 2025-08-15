# CO-003: Meta Interview Signal Extraction & Scoring

**Priority**: P1 - High  
**Type**: Feature  
**Component**: Evaluation/Scoring  
**Estimated Effort**: 4-5 hours  
**Dependencies**: CO-001, CO-002

## Objective

Extend the existing CodingEvaluator to extract and score Meta-specific interview signals (5 pillars) from code submissions, providing detailed feedback aligned with Meta's interview rubric.

## Background

Meta interviews evaluate candidates on 5 key pillars:
1. **Problem Understanding & Examples** - Did they clarify requirements and test understanding?
2. **Algorithmic Correctness** - Is the solution logically sound and correctly implemented?
3. **Time/Space Complexity** - Can they analyze and optimize complexity?
4. **Code Quality & Test Hygiene** - Is the code clean, maintainable, with good test coverage?
5. **Communication & Iteration** - How well do they explain their approach and incorporate feedback?

## High-Level Design

### Architecture
```
CodingEvaluator (existing)
    ├── MetaSignalExtractor (new)
    │   ├── extract_correctness_signals()
    │   ├── extract_complexity_signals()
    │   ├── extract_quality_signals()
    │   └── compute_pillar_scores()
    ├── CategoryMapper (enhance)
    │   └── map_to_meta_categories()
    └── FeedbackGenerator (new)
        └── generate_pillar_feedback()
```

### Data Flow
1. Submission arrives with code, language, problem_id
2. Standard evaluation runs (existing flow)
3. MetaSignalExtractor analyzes code and test results
4. Pillar scores computed (0-100 scale)
5. Feedback generated for each pillar
6. Results stored with submission

## Implementation Details

### 1. Extend Submission Model
Add to `src/co/db/models.py`:
```python
class Submission(Base):
    # ... existing fields ...
    
    # New fields for Meta signals
    pillar_scores = Column(JSON, nullable=True)  
    # Format: {"problem_understanding": 85, "correctness": 70, ...}
    
    signal_metadata = Column(JSON, nullable=True)
    # Detailed signal data for analysis
    
    feedback = Column(JSON, nullable=True)
    # Pillar-specific feedback messages
```

### 2. Create MetaSignalExtractor
Create `src/co/services/evaluators/meta_signal_extractor.py`:
```python
from typing import Dict, List, Any
import ast
import re

class MetaSignalExtractor:
    """Extract Meta interview signals from code submissions"""
    
    def extract_signals(
        self, 
        code: str, 
        language: str,
        test_results: Dict[str, Any],
        problem_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Main extraction method"""
        
        signals = {
            "correctness": self._extract_correctness_signals(test_results),
            "complexity": self._extract_complexity_signals(code, language),
            "quality": self._extract_quality_signals(code, language),
            "test_hygiene": self._extract_test_signals(code, language),
            "structure": self._extract_structure_signals(code, language)
        }
        
        pillar_scores = self._compute_pillar_scores(signals, problem_metadata)
        feedback = self._generate_feedback(pillar_scores, signals)
        
        return {
            "pillar_scores": pillar_scores,
            "signals": signals,
            "feedback": feedback
        }
    
    def _extract_correctness_signals(self, test_results: Dict) -> Dict:
        """Analyze test results for correctness signals"""
        return {
            "visible_pass_rate": test_results["visible_passed"] / max(test_results["visible_total"], 1),
            "hidden_pass_rate": test_results["hidden_passed"] / max(test_results["hidden_total"], 1),
            "categories_failed": test_results.get("categories", []),
            "has_runtime_errors": "error" in test_results.get("status", ""),
            "handles_edge_cases": self._check_edge_case_handling(test_results)
        }
    
    def _extract_complexity_signals(self, code: str, language: str) -> Dict:
        """Analyze algorithmic complexity"""
        
        if language == "python":
            return self._analyze_python_complexity(code)
        elif language == "javascript":
            return self._analyze_javascript_complexity(code)
        
        return {"estimated_time": "unknown", "estimated_space": "unknown"}
    
    def _analyze_python_complexity(self, code: str) -> Dict:
        """Python-specific complexity analysis"""
        
        tree = ast.parse(code)
        
        # Check for nested loops
        loop_depth = self._get_max_loop_depth(tree)
        
        # Check for recursion
        has_recursion = self._has_recursion(tree)
        
        # Check for data structure usage
        uses_hashmap = "dict" in code or "{" in code
        uses_set = "set(" in code
        uses_heap = "heapq" in code or "heappush" in code
        
        # Estimate complexity based on patterns
        if loop_depth >= 3:
            time_complexity = "O(n^3)"
        elif loop_depth == 2:
            time_complexity = "O(n^2)"
        elif has_recursion:
            time_complexity = "O(2^n)" if "memo" not in code else "O(n)"
        else:
            time_complexity = "O(n)"
        
        space_complexity = "O(n)" if uses_hashmap or uses_set else "O(1)"
        
        return {
            "estimated_time": time_complexity,
            "estimated_space": space_complexity,
            "loop_depth": loop_depth,
            "has_recursion": has_recursion,
            "data_structures": {
                "hashmap": uses_hashmap,
                "set": uses_set,
                "heap": uses_heap
            }
        }
    
    def _extract_quality_signals(self, code: str, language: str) -> Dict:
        """Analyze code quality"""
        
        lines = code.split('\n')
        
        return {
            "line_count": len(lines),
            "avg_line_length": sum(len(line) for line in lines) / max(len(lines), 1),
            "has_comments": any('//' in line or '#' in line or '/*' in line for line in lines),
            "variable_naming": self._check_variable_naming(code, language),
            "function_count": code.count('def ') if language == 'python' else code.count('function'),
            "has_helper_functions": self._has_helper_functions(code, language),
            "follows_conventions": self._check_conventions(code, language)
        }
    
    def _extract_test_signals(self, code: str, language: str) -> Dict:
        """Check for test-related patterns"""
        
        return {
            "has_custom_tests": "assert" in code or "expect" in code,
            "has_edge_case_checks": any(
                pattern in code.lower() 
                for pattern in ["empty", "null", "none", "zero", "single"]
            ),
            "has_validation": "if not" in code or "if !" in code or "throw" in code
        }
    
    def _compute_pillar_scores(
        self, 
        signals: Dict[str, Any], 
        problem_metadata: Dict[str, Any]
    ) -> Dict[str, float]:
        """Compute scores for each pillar (0-100)"""
        
        # Problem Understanding (based on edge case handling and validation)
        understanding_score = 50  # Base score
        if signals["test_hygiene"]["has_edge_case_checks"]:
            understanding_score += 25
        if signals["test_hygiene"]["has_validation"]:
            understanding_score += 25
        
        # Algorithmic Correctness
        correctness = signals["correctness"]
        correctness_score = (
            correctness["visible_pass_rate"] * 40 +
            correctness["hidden_pass_rate"] * 60
        ) * 100
        
        # Complexity Analysis
        complexity = signals["complexity"]
        target_complexity = problem_metadata.get("target_complexity", "O(n)")
        complexity_score = 100 if complexity["estimated_time"] == target_complexity else 70
        
        # Code Quality
        quality = signals["quality"]
        quality_score = 50  # Base
        if quality["has_comments"]:
            quality_score += 10
        if quality["variable_naming"] == "good":
            quality_score += 15
        if quality["has_helper_functions"]:
            quality_score += 15
        if quality["follows_conventions"]:
            quality_score += 10
        
        # Communication (placeholder - would need session context)
        communication_score = 75  # Default pending session analysis
        
        return {
            "problem_understanding": min(understanding_score, 100),
            "algorithmic_correctness": correctness_score,
            "complexity_analysis": complexity_score,
            "code_quality": min(quality_score, 100),
            "communication": communication_score
        }
    
    def _generate_feedback(
        self, 
        pillar_scores: Dict[str, float],
        signals: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate feedback for each pillar"""
        
        feedback = {}
        
        # Correctness feedback
        if pillar_scores["algorithmic_correctness"] < 70:
            failed_categories = signals["correctness"]["categories_failed"]
            feedback["correctness"] = f"Solution fails on: {', '.join(failed_categories)}. Review these test categories."
        else:
            feedback["correctness"] = "Solution handles most test cases correctly."
        
        # Complexity feedback
        complexity = signals["complexity"]
        feedback["complexity"] = f"Time: {complexity['estimated_time']}, Space: {complexity['estimated_space']}"
        if complexity["loop_depth"] > 2:
            feedback["complexity"] += " Consider optimizing nested loops."
        
        # Quality feedback
        quality = signals["quality"]
        quality_issues = []
        if not quality["has_comments"]:
            quality_issues.append("Add comments for complex logic")
        if quality["variable_naming"] != "good":
            quality_issues.append("Use more descriptive variable names")
        if not quality["has_helper_functions"] and quality["line_count"] > 30:
            quality_issues.append("Consider breaking into helper functions")
        
        feedback["quality"] = ". ".join(quality_issues) if quality_issues else "Good code structure and clarity."
        
        return feedback
    
    # Helper methods
    def _get_max_loop_depth(self, tree) -> int:
        """Calculate maximum loop nesting depth"""
        # Implementation details...
        pass
    
    def _has_recursion(self, tree) -> bool:
        """Check if code contains recursion"""
        # Implementation details...
        pass
    
    def _check_variable_naming(self, code: str, language: str) -> str:
        """Evaluate variable naming quality"""
        # Check for single letters, descriptive names, etc.
        pass
    
    def _has_helper_functions(self, code: str, language: str) -> bool:
        """Check if code is properly modularized"""
        # Implementation details...
        pass
    
    def _check_conventions(self, code: str, language: str) -> bool:
        """Check language-specific conventions"""
        # PEP8 for Python, ESLint rules for JS, etc.
        pass
    
    def _check_edge_case_handling(self, test_results: Dict) -> bool:
        """Check if edge cases are handled"""
        edge_categories = ["empty", "single_element", "duplicates", "negative", "zero"]
        failed = test_results.get("categories", [])
        return not any(cat in failed for cat in edge_categories)
```

### 3. Enhance CodingEvaluator
Update `src/co/services/evaluators/coding_evaluator.py`:
```python
from .meta_signal_extractor import MetaSignalExtractor

class CodingEvaluator:
    def __init__(self):
        self.meta_extractor = MetaSignalExtractor()
    
    async def evaluate(self, submission_data: Dict) -> Dict:
        # ... existing evaluation logic ...
        
        # Extract Meta signals if applicable
        problem_metadata = await self._get_problem_metadata(submission_data["problem_id"])
        
        if self._is_meta_track(problem_metadata):
            meta_signals = self.meta_extractor.extract_signals(
                code=submission_data["payload"]["code"],
                language=submission_data["payload"]["language"],
                test_results=evaluation_result,
                problem_metadata=problem_metadata
            )
            
            # Add to result
            evaluation_result["pillar_scores"] = meta_signals["pillar_scores"]
            evaluation_result["feedback"] = meta_signals["feedback"]
            evaluation_result["signal_metadata"] = meta_signals["signals"]
        
        return evaluation_result
    
    def _is_meta_track(self, metadata: Dict) -> bool:
        """Check if problem belongs to Meta track"""
        return "company:meta" in metadata.get("labels", [])
```

### 4. API Response Enhancement
Update submission response to include pillar scores:
```python
# src/co/routes/submissions.py
@router.post("/submissions")
async def submit_attempt(payload: SubmissionCreate) -> SubmissionResponse:
    # ... existing logic ...
    
    response = {
        "id": str(submission.id),
        "status": submission.status,
        "visible": {
            "passed": submission.visible_passed,
            "total": submission.visible_total
        },
        "hidden": {
            "passed": submission.hidden_passed,
            "total": submission.hidden_total,
            "categories": submission.categories
        },
        "exec_ms": submission.exec_ms
    }
    
    # Add Meta signals if present
    if submission.pillar_scores:
        response["pillar_scores"] = submission.pillar_scores
        response["feedback"] = submission.feedback
    
    return response
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_meta_signal_extractor.py
def test_extract_correctness_signals():
    extractor = MetaSignalExtractor()
    test_results = {
        "visible_passed": 3,
        "visible_total": 4,
        "hidden_passed": 8,
        "hidden_total": 10,
        "categories": ["edge_cases"]
    }
    
    signals = extractor._extract_correctness_signals(test_results)
    assert signals["visible_pass_rate"] == 0.75
    assert signals["hidden_pass_rate"] == 0.8
    assert "edge_cases" in signals["categories_failed"]

def test_complexity_analysis_nested_loops():
    code = """
    def solution(arr):
        for i in range(len(arr)):
            for j in range(len(arr)):
                for k in range(len(arr)):
                    process(arr[i], arr[j], arr[k])
    """
    
    signals = extractor._analyze_python_complexity(code)
    assert signals["estimated_time"] == "O(n^3)"
    assert signals["loop_depth"] == 3
```

### Integration Tests
```python
# tests/integration/test_meta_evaluation.py
async def test_meta_track_evaluation():
    # Submit a Meta track problem
    submission = await submit_coding_solution(
        problem_id="meta-two-sum-variant",
        code=sample_solution,
        language="python"
    )
    
    # Verify pillar scores are present
    assert "pillar_scores" in submission
    assert all(
        pillar in submission["pillar_scores"]
        for pillar in ["problem_understanding", "algorithmic_correctness", 
                       "complexity_analysis", "code_quality", "communication"]
    )
    
    # Verify feedback is generated
    assert "feedback" in submission
    assert "correctness" in submission["feedback"]
```

## Success Criteria

- [ ] MetaSignalExtractor correctly analyzes Python and JavaScript code
- [ ] All 5 pillar scores computed for Meta track submissions
- [ ] Feedback messages are helpful and specific
- [ ] Complexity analysis is accurate for common patterns
- [ ] Code quality metrics align with Meta standards
- [ ] API returns pillar scores for Meta track problems
- [ ] Non-Meta problems continue to work without signals

## Performance Considerations

- Signal extraction should add <100ms to evaluation time
- Consider caching problem metadata to avoid repeated lookups
- AST parsing for complexity analysis should timeout after 1 second
- Store signal metadata for later analysis but don't block response

## Future Enhancements

1. **ML-based complexity analysis** - Train model on labeled complexity data
2. **Communication scoring** - Analyze session transcript for explanation quality
3. **Comparative feedback** - "Your solution is in the top 20% for this problem"
4. **Trend analysis** - Track pillar score improvements over time
5. **LLM-assisted feedback** - Generate more nuanced, personalized feedback

## Notes

- Start with deterministic signal extraction before adding ML/LLM components
- Ensure backward compatibility for non-Meta tracks
- Consider making signal extraction pluggable for other company styles
- Store raw signals for future reprocessing as algorithms improve