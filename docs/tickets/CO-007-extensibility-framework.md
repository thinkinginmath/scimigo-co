# CO-007: Subject Extensibility Framework

**Priority**: P2 - Medium  
**Type**: Architecture  
**Component**: Core Framework  
**Estimated Effort**: 6-8 hours  
**Dependencies**: CO-001, CO-003

## Objective

Design and implement a robust extensibility framework that allows easy addition of new subjects (e.g., UIUC Math, Physics, Chemistry) while maintaining consistency and reusing core orchestration logic.

## Background

The current system supports coding and math subjects, but adding new subjects like "UIUC CS 374" or "Physics 101" requires significant boilerplate. We need a plugin-like architecture that allows:
- Subject-specific evaluators
- Custom problem formats
- Specialized hint generation
- Subject-specific UI components
- Personalization algorithms per domain

## High-Level Design

### Plugin Architecture
```
SubjectFramework
    ├── SubjectPlugin (Abstract Base)
    │   ├── Evaluator
    │   ├── ProblemParser  
    │   ├── HintGenerator
    │   ├── PersonalizationWeights
    │   └── UIComponents
    ├── PluginRegistry
    ├── SubjectDetector
    └── UnifiedOrchestrator
```

### Subject Definitions
```yaml
# subjects/uiuc-math.yml
id: uiuc-math
name: "UIUC Mathematics"
description: "University of Illinois math courses"

evaluator_class: "UiucMathEvaluator"
problem_formats: ["step-by-step", "proof", "calculation"]
hint_styles: ["socratic", "worked-example"]

personalization:
  primary_signals: ["step_accuracy", "proof_rigor", "calculation_speed"]
  difficulty_factors: ["concept_mastery", "proof_complexity"]

ui_components:
  - "LatexRenderer"
  - "StepTracker" 
  - "ProofValidator"

course_integration:
  textbook: "Rudin Principles of Mathematical Analysis"
  syllabus_mapping: true
  professor_styles: ["theoretical", "applied"]
```

## Implementation Details

### 1. Abstract Subject Plugin
Create `src/co/subjects/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class SubjectConfig(BaseModel):
    """Configuration for a subject plugin"""
    id: str
    name: str
    description: str
    evaluator_class: str
    problem_formats: List[str]
    hint_styles: List[str]
    personalization: Dict[str, Any]
    ui_components: List[str]
    custom_settings: Dict[str, Any] = {}

class SubmissionPayload(BaseModel):
    """Subject-agnostic submission payload"""
    subject: str
    problem_id: str
    user_data: Dict[str, Any]  # Subject-specific content
    metadata: Dict[str, Any] = {}

class EvaluationResult(BaseModel):
    """Standardized evaluation result"""
    status: str  # passed, failed, partial
    score: float  # 0-100
    detailed_feedback: Dict[str, Any]
    categories: List[str]
    signals: Dict[str, Any]
    next_actions: List[str] = []

class SubjectPlugin(ABC):
    """Abstract base class for subject plugins"""
    
    def __init__(self, config: SubjectConfig):
        self.config = config
        self.id = config.id
        self.name = config.name
    
    @abstractmethod
    async def evaluate_submission(
        self, 
        payload: SubmissionPayload,
        problem_context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate a submission for this subject"""
        pass
    
    @abstractmethod
    async def generate_hints(
        self,
        problem_id: str,
        submission_history: List[Dict],
        hint_level: int,
        style: str = "default"
    ) -> Dict[str, Any]:
        """Generate subject-specific hints"""
        pass
    
    @abstractmethod
    async def parse_problem(
        self,
        raw_problem: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and validate problem format"""
        pass
    
    @abstractmethod  
    def get_personalization_weights(self) -> Dict[str, float]:
        """Return subject-specific personalization weights"""
        pass
    
    @abstractmethod
    def get_ui_requirements(self) -> Dict[str, Any]:
        """Return UI component requirements"""
        pass
    
    # Optional hooks with default implementations
    def validate_problem(self, problem: Dict[str, Any]) -> List[str]:
        """Validate problem format - return list of issues"""
        return []
    
    def extract_topics(self, problem: Dict[str, Any]) -> List[str]:
        """Extract topics/tags from problem"""
        return problem.get("topics", [])
    
    def compute_difficulty(self, problem: Dict[str, Any]) -> int:
        """Compute difficulty score 1-5"""
        return problem.get("difficulty", 3)
    
    def format_feedback(self, result: EvaluationResult) -> str:
        """Format user-friendly feedback"""
        return result.detailed_feedback.get("summary", "No feedback available")
```

### 2. Plugin Registry
Create `src/co/subjects/registry.py`:
```python
import importlib
import yaml
from pathlib import Path
from typing import Dict, Type, Optional
from .base import SubjectPlugin, SubjectConfig

class SubjectRegistry:
    """Registry for managing subject plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, SubjectPlugin] = {}
        self.configs: Dict[str, SubjectConfig] = {}
        self.plugin_classes: Dict[str, Type[SubjectPlugin]] = {}
    
    def load_subjects_from_config(self, config_dir: str = "config/subjects"):
        """Load all subject configurations"""
        
        config_path = Path(config_dir)
        if not config_path.exists():
            return
        
        for config_file in config_path.glob("*.yml"):
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
            
            config = SubjectConfig(**config_data)
            self.register_subject_config(config)
    
    def register_subject_config(self, config: SubjectConfig):
        """Register a subject configuration"""
        self.configs[config.id] = config
        
        # Load plugin class
        if config.evaluator_class:
            plugin_class = self._load_plugin_class(config.evaluator_class)
            self.plugin_classes[config.id] = plugin_class
    
    def get_plugin(self, subject_id: str) -> Optional[SubjectPlugin]:
        """Get instantiated plugin for subject"""
        
        if subject_id in self.plugins:
            return self.plugins[subject_id]
        
        # Lazy instantiation
        if subject_id in self.plugin_classes:
            config = self.configs[subject_id]
            plugin_class = self.plugin_classes[subject_id]
            plugin = plugin_class(config)
            self.plugins[subject_id] = plugin
            return plugin
        
        return None
    
    def list_subjects(self) -> List[SubjectConfig]:
        """List all available subjects"""
        return list(self.configs.values())
    
    def detect_subject(self, problem_data: Dict[str, Any]) -> Optional[str]:
        """Auto-detect subject from problem data"""
        
        # Try explicit subject field
        if "subject" in problem_data:
            subject = problem_data["subject"]
            if subject in self.configs:
                return subject
        
        # Try pattern matching
        for subject_id, config in self.configs.items():
            plugin = self.get_plugin(subject_id)
            if plugin and self._matches_subject_pattern(problem_data, config):
                return subject_id
        
        return None
    
    def _load_plugin_class(self, class_path: str) -> Type[SubjectPlugin]:
        """Dynamically load plugin class"""
        
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    
    def _matches_subject_pattern(
        self, 
        problem_data: Dict[str, Any],
        config: SubjectConfig
    ) -> bool:
        """Check if problem matches subject patterns"""
        
        # Check problem format
        problem_format = problem_data.get("format", "unknown")
        if problem_format in config.problem_formats:
            return True
        
        # Check keywords
        text = str(problem_data).lower()
        subject_keywords = config.custom_settings.get("keywords", [])
        
        return any(keyword in text for keyword in subject_keywords)

# Global registry instance
subject_registry = SubjectRegistry()
```

### 3. UIUC Math Plugin Example
Create `src/co/subjects/plugins/uiuc_math.py`:
```python
from ..base import SubjectPlugin, SubmissionPayload, EvaluationResult
from typing import Dict, List, Any
import re

class UiucMathEvaluator(SubjectPlugin):
    """UIUC Mathematics course evaluator"""
    
    async def evaluate_submission(
        self, 
        payload: SubmissionPayload,
        problem_context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate math submission"""
        
        user_solution = payload.user_data
        problem_type = problem_context.get("type", "calculation")
        
        if problem_type == "proof":
            return await self._evaluate_proof(user_solution, problem_context)
        elif problem_type == "calculation":
            return await self._evaluate_calculation(user_solution, problem_context)
        elif problem_type == "step-by-step":
            return await self._evaluate_steps(user_solution, problem_context)
        else:
            raise ValueError(f"Unknown problem type: {problem_type}")
    
    async def _evaluate_proof(
        self,
        solution: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate mathematical proof"""
        
        proof_steps = solution.get("steps", [])
        reasoning = solution.get("reasoning", "")
        
        signals = {
            "step_count": len(proof_steps),
            "logical_flow": self._check_logical_flow(proof_steps),
            "rigor_score": self._assess_rigor(proof_steps, reasoning),
            "notation_correct": self._check_notation(proof_steps)
        }
        
        # Score based on signals
        score = (
            signals["logical_flow"] * 40 +
            signals["rigor_score"] * 30 +
            signals["notation_correct"] * 20 +
            (min(signals["step_count"] / 5, 1) * 10)  # Completeness
        )
        
        status = "passed" if score >= 70 else "partial" if score >= 40 else "failed"
        
        categories = []
        if signals["logical_flow"] < 0.7:
            categories.append("logical_gaps")
        if signals["rigor_score"] < 0.6:
            categories.append("insufficient_rigor")
        if signals["notation_correct"] < 0.8:
            categories.append("notation_errors")
        
        return EvaluationResult(
            status=status,
            score=score,
            detailed_feedback={
                "summary": f"Proof {'accepted' if status == 'passed' else 'needs revision'}",
                "step_analysis": self._analyze_proof_steps(proof_steps),
                "rigor_feedback": self._rigor_feedback(signals["rigor_score"]),
                "notation_feedback": self._notation_feedback(signals["notation_correct"])
            },
            categories=categories,
            signals=signals,
            next_actions=self._suggest_proof_improvements(signals)
        )
    
    async def _evaluate_calculation(
        self,
        solution: Dict[str, Any],
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate numerical calculation"""
        
        user_answer = solution.get("final_answer")
        expected_answer = context.get("expected_answer")
        work_shown = solution.get("work", [])
        
        # Check numerical accuracy
        is_correct = self._check_numerical_answer(user_answer, expected_answer)
        
        # Analyze work
        signals = {
            "answer_correct": is_correct,
            "work_shown": len(work_shown) > 0,
            "method_appropriate": self._check_method(work_shown, context),
            "calculation_errors": self._count_calc_errors(work_shown)
        }
        
        if is_correct and signals["work_shown"]:
            score = 100
            status = "passed"
        elif is_correct:
            score = 80  # Right answer, no work
            status = "passed"
        elif signals["method_appropriate"] and signals["calculation_errors"] <= 1:
            score = 60  # Right method, minor errors
            status = "partial"
        else:
            score = 30
            status = "failed"
        
        return EvaluationResult(
            status=status,
            score=score,
            detailed_feedback={
                "summary": f"Answer: {'Correct' if is_correct else 'Incorrect'}",
                "work_feedback": self._analyze_calculation_work(work_shown),
                "method_feedback": self._method_feedback(signals["method_appropriate"])
            },
            categories=["calculation_error"] if not is_correct else [],
            signals=signals
        )
    
    async def generate_hints(
        self,
        problem_id: str,
        submission_history: List[Dict],
        hint_level: int,
        style: str = "socratic"
    ) -> Dict[str, Any]:
        """Generate math-specific hints"""
        
        if style == "socratic":
            return await self._socratic_hints(problem_id, submission_history, hint_level)
        elif style == "worked-example":
            return await self._worked_example_hints(problem_id, hint_level)
        else:
            return {"hint": "Consider the problem structure and key concepts."}
    
    async def _socratic_hints(
        self,
        problem_id: str,
        history: List[Dict],
        level: int
    ) -> Dict[str, Any]:
        """Generate Socratic-method hints"""
        
        hints = {
            1: "What mathematical concepts are involved in this problem?",
            2: "Can you identify the key relationships between the given information?",
            3: "What theorem or formula applies to this type of problem?"
        }
        
        # Customize based on submission history
        if history:
            latest = history[-1]
            failed_categories = latest.get("categories", [])
            
            if "logical_gaps" in failed_categories:
                hints[level] = "Focus on the logical connections between your statements."
            elif "notation_errors" in failed_categories:
                hints[level] = "Check your mathematical notation and definitions."
        
        return {
            "hint": hints.get(level, hints[3]),
            "type": "question",
            "follow_up": "Take time to think through this before proceeding."
        }
    
    async def parse_problem(self, raw_problem: Dict[str, Any]) -> Dict[str, Any]:
        """Parse UIUC Math problem format"""
        
        parsed = {
            "id": raw_problem["id"],
            "statement": raw_problem["statement"],
            "type": raw_problem.get("type", "calculation"),
            "course": raw_problem.get("course", "unknown"),
            "chapter": raw_problem.get("chapter"),
            "concepts": raw_problem.get("concepts", []),
            "difficulty": raw_problem.get("difficulty", 3)
        }
        
        # Parse expected format
        if parsed["type"] == "proof":
            parsed["proof_structure"] = raw_problem.get("proof_structure", "direct")
            parsed["key_theorems"] = raw_problem.get("key_theorems", [])
        elif parsed["type"] == "calculation":
            parsed["expected_answer"] = raw_problem.get("answer")
            parsed["units"] = raw_problem.get("units")
            parsed["tolerance"] = raw_problem.get("tolerance", 0.01)
        
        return parsed
    
    def get_personalization_weights(self) -> Dict[str, float]:
        """UIUC Math personalization weights"""
        return {
            "proof_mastery": 0.3,
            "calculation_accuracy": 0.25,
            "concept_understanding": 0.25,
            "notation_fluency": 0.1,
            "problem_solving_speed": 0.1
        }
    
    def get_ui_requirements(self) -> Dict[str, Any]:
        """UI requirements for math problems"""
        return {
            "required_components": ["LatexRenderer", "EquationEditor"],
            "optional_components": ["GraphingTool", "StepTracker"],
            "input_types": ["latex", "text", "file_upload"],
            "preview_math": True
        }
    
    # Helper methods
    def _check_logical_flow(self, steps: List[str]) -> float:
        """Assess logical flow of proof steps"""
        # Simplified - in practice would use NLP/LLM analysis
        if len(steps) < 2:
            return 0.0
        
        # Check for logical connectors
        connectors = ["therefore", "thus", "hence", "because", "since", "so"]
        has_connectors = any(
            any(conn in step.lower() for conn in connectors)
            for step in steps
        )
        
        return 0.8 if has_connectors else 0.4
    
    def _assess_rigor(self, steps: List[str], reasoning: str) -> float:
        """Assess mathematical rigor"""
        rigor_indicators = [
            "definition", "theorem", "lemma", "proof", "contradiction",
            "assume", "suppose", "let", "given", "qed"
        ]
        
        text = " ".join(steps + [reasoning]).lower()
        indicator_count = sum(1 for indicator in rigor_indicators if indicator in text)
        
        return min(indicator_count / 3, 1.0)  # Normalize to 0-1
    
    def _check_notation(self, steps: List[str]) -> float:
        """Check mathematical notation correctness"""
        # Check for common notation patterns
        good_patterns = [
            r"\$.*\$",  # LaTeX math
            r"\\[a-zA-Z]+",  # LaTeX commands
            r"[∀∃∈∉⊆⊇∪∩]",  # Unicode math symbols
        ]
        
        text = " ".join(steps)
        pattern_matches = sum(
            1 for pattern in good_patterns 
            if re.search(pattern, text)
        )
        
        return min(pattern_matches / 2, 1.0)
    
    def _check_numerical_answer(
        self, 
        user_answer: Any, 
        expected: Any,
        tolerance: float = 0.01
    ) -> bool:
        """Check if numerical answer is correct within tolerance"""
        try:
            user_val = float(user_answer)
            expected_val = float(expected)
            return abs(user_val - expected_val) <= tolerance
        except (ValueError, TypeError):
            return str(user_answer).strip() == str(expected).strip()
```

### 4. Unified Orchestrator
Update `src/co/services/session_service.py`:
```python
from ..subjects.registry import subject_registry

class SessionService:
    async def evaluate_submission(
        self,
        submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Subject-agnostic submission evaluation"""
        
        subject = submission_data.get("subject")
        if not subject:
            # Auto-detect subject
            subject = subject_registry.detect_subject(submission_data)
            if not subject:
                raise ValueError("Could not determine problem subject")
        
        # Get subject plugin
        plugin = subject_registry.get_plugin(subject)
        if not plugin:
            raise ValueError(f"No plugin available for subject: {subject}")
        
        # Convert to plugin format
        payload = SubmissionPayload(
            subject=subject,
            problem_id=submission_data["problem_id"],
            user_data=submission_data["payload"]
        )
        
        # Get problem context
        problem_context = await self.get_problem_context(
            submission_data["problem_id"]
        )
        
        # Evaluate using plugin
        result = await plugin.evaluate_submission(payload, problem_context)
        
        # Store result in unified format
        submission = await self.create_submission_record(
            submission_data,
            result
        )
        
        return {
            "id": str(submission.id),
            "status": result.status,
            "score": result.score,
            "feedback": plugin.format_feedback(result),
            "categories": result.categories,
            "next_actions": result.next_actions,
            "subject_specific": result.detailed_feedback
        }
```

### 5. Subject Configuration Files
Create `config/subjects/uiuc-math.yml`:
```yaml
id: uiuc-math
name: "UIUC Mathematics"
description: "University of Illinois mathematics courses"

evaluator_class: "co.subjects.plugins.uiuc_math.UiucMathEvaluator"
problem_formats: ["proof", "calculation", "step-by-step"]
hint_styles: ["socratic", "worked-example"]

personalization:
  primary_signals: ["proof_mastery", "calculation_accuracy", "concept_understanding"]
  difficulty_factors: ["concept_complexity", "proof_length", "calculation_steps"]
  adaptation_rate: 0.1

ui_components:
  - "LatexRenderer"
  - "EquationEditor"
  - "StepTracker"
  - "ProofValidator"

custom_settings:
  keywords: ["theorem", "proof", "derivative", "integral", "limit"]
  course_codes: ["MATH 241", "MATH 347", "MATH 417"]
  textbooks: ["Rudin", "Apostol", "Spivak"]
  
grading:
  proof_weight: 0.6
  calculation_weight: 0.4
  partial_credit: true
  minimum_passing: 60

integration:
  lms_sync: true
  gradebook_export: true
  academic_calendar: true
```

Create `config/subjects/physics-101.yml`:
```yaml
id: physics-101
name: "Physics 101"
description: "Introductory Physics"

evaluator_class: "co.subjects.plugins.physics.PhysicsEvaluator"
problem_formats: ["numerical", "conceptual", "lab-analysis"]
hint_styles: ["dimensional-analysis", "concept-map"]

personalization:
  primary_signals: ["formula_application", "unit_conversion", "concept_grasp"]
  difficulty_factors: ["formula_complexity", "multi_step", "abstract_thinking"]

ui_components:
  - "EquationEditor"
  - "UnitConverter"
  - "DiagramTool"
  - "GraphPlotter"

custom_settings:
  keywords: ["force", "velocity", "acceleration", "energy", "momentum"]
  common_units: ["m/s", "N", "J", "W", "kg"]
  formula_bank: true
```

### 6. API Extensions
Update `src/co/routes/subjects.py`:
```python
from ..subjects.registry import subject_registry

@router.get("/subjects")
async def list_subjects():
    """List all available subjects"""
    subjects = subject_registry.list_subjects()
    return {
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "problem_formats": s.problem_formats,
                "ui_components": s.ui_components
            }
            for s in subjects
        ]
    }

@router.get("/subjects/{subject_id}/requirements")
async def get_subject_requirements(subject_id: str):
    """Get UI and technical requirements for subject"""
    plugin = subject_registry.get_plugin(subject_id)
    if not plugin:
        raise HTTPException(404, "Subject not found")
    
    return {
        "ui_requirements": plugin.get_ui_requirements(),
        "personalization_weights": plugin.get_personalization_weights(),
        "supported_formats": plugin.config.problem_formats,
        "hint_styles": plugin.config.hint_styles
    }
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_subject_registry.py
def test_plugin_loading():
    registry = SubjectRegistry()
    config = SubjectConfig(
        id="test-subject",
        name="Test",
        description="Test subject",
        evaluator_class="test_plugin.TestEvaluator",
        problem_formats=["test"],
        hint_styles=["test"]
    )
    
    registry.register_subject_config(config)
    plugin = registry.get_plugin("test-subject")
    assert plugin is not None

# tests/unit/test_uiuc_math.py
async def test_proof_evaluation():
    plugin = UiucMathEvaluator(mock_config)
    
    payload = SubmissionPayload(
        subject="uiuc-math",
        problem_id="proof-1",
        user_data={
            "steps": ["Assume x > 0", "Therefore x^2 > 0", "QED"],
            "reasoning": "Direct proof using properties of positive numbers"
        }
    )
    
    result = await plugin.evaluate_submission(payload, mock_context)
    assert result.status in ["passed", "partial", "failed"]
    assert 0 <= result.score <= 100
```

### Integration Tests
```python
# tests/integration/test_multi_subject.py
async def test_subject_switching():
    # Submit coding problem
    coding_response = await client.post("/v1/submissions", json={
        "subject": "coding",
        "problem_id": "two-sum",
        "payload": {"code": "def solution...", "language": "python"}
    })
    
    # Submit math problem
    math_response = await client.post("/v1/submissions", json={
        "subject": "uiuc-math", 
        "problem_id": "proof-1",
        "payload": {"steps": [...], "reasoning": "..."}
    })
    
    assert coding_response.json()["subject_specific"]["exec_ms"]
    assert math_response.json()["subject_specific"]["rigor_score"]
```

## Success Criteria

- [ ] Subject plugins can be loaded from YAML configuration
- [ ] New subjects can be added without modifying core CO code
- [ ] Evaluation routing works correctly for all subjects
- [ ] Personalization weights are subject-specific
- [ ] UI requirements are properly communicated to frontend
- [ ] Hint generation adapts to subject pedagogy
- [ ] Auto-detection works for subjects with clear patterns

## Future Enhancements

1. **Plugin Marketplace** - Allow third-party plugin distribution
2. **Subject Versioning** - Support plugin updates and migration
3. **Cross-Subject Learning** - Identify transferable skills across domains
4. **A/B Testing Framework** - Test different pedagogical approaches
5. **Analytics Dashboard** - Subject-specific learning analytics

## Notes

- Start with 2-3 subjects to validate the framework
- Consider subject inheritance (e.g., "UIUC Math 241" extends "Math")
- Plugin sandboxing for security in production
- Documentation templates for plugin authors