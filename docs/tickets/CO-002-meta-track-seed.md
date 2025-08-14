# CO-002: Meta Coding Interview Track - Seed Data & Structure

**Priority**: P0 - Critical  
**Type**: Feature  
**Component**: Content/Curriculum  
**Estimated Effort**: 3-4 hours  
**Dependencies**: CO-001 (Schema Alignment)

## Objective

Create the initial Meta coding interview prep track with proper curriculum structure, including 10 progressive modules and seed problems for pilot testing.

## High-Level Design

### Track Structure (Aligned with LeetCode Course)
```
Track: coding-interview-meta
├── Module 0: Introduction & Fundamentals
├── Module 1: Arrays & Strings
├── Module 2: Hashing
├── Module 3: Linked Lists
├── Module 4: Stacks & Queues
├── Module 5: Trees
├── Module 6: Graphs
├── Module 7: Heaps
├── Module 8: Greedy
├── Module 9: Binary Search
├── Module 10: Backtracking
├── Module 11: Dynamic Programming
└── Module 12: Interview Tools & Advanced Topics
```

### Signal Pillars (Meta Interview Scorecard)
1. **Problem Understanding & Examples** - Clarification, edge cases, examples
2. **Algorithmic Correctness** - Logic, implementation accuracy
3. **Time/Space Complexity** - Analysis and optimization
4. **Code Quality & Test Hygiene** - Clean code, testing discipline
5. **Communication & Iteration** - Explaining approach, incorporating feedback

## Implementation Steps

### 1. Create Track Definition File
Create `seed/tracks/meta-coding-interview.json`:
```json
{
  "slug": "coding-interview-meta",
  "subject": "coding",
  "title": "Meta Coding Interview Preparation",
  "labels": ["company:meta", "interview:coding", "level:intermediate"],
  "version": "v1.0",
  "metadata": {
    "pillars": [
      "problem_understanding",
      "algorithmic_correctness", 
      "complexity_analysis",
      "code_quality",
      "communication"
    ],
    "target_audience": "Meta interview candidates",
    "duration_weeks": 8,
    "problems_per_week": 10
  },
  "modules": [
    {
      "id": "introduction",
      "title": "Introduction & Fundamentals",
      "description": "Big O, problem-solving framework, coding interview basics",
      "outcomes": ["complexity-analysis", "problem-solving-process", "coding-style"],
      "topics": ["time-complexity", "space-complexity", "interview-mindset"],
      "difficulty_range": [1, 2],
      "estimated_hours": 4
    },
    {
      "id": "arrays-strings",
      "title": "Arrays & Strings",
      "description": "Two pointers, sliding window, frequency maps",
      "outcomes": ["two-pointers", "sliding-window", "string-manipulation"],
      "topics": ["array-traversal", "string-matching", "subarray-sum"],
      "difficulty_range": [1, 3],
      "estimated_hours": 8
    },
    {
      "id": "hashing",
      "title": "Hashing",
      "description": "Hash maps, hash sets, frequency counting",
      "outcomes": ["hash-map-usage", "set-operations", "collision-handling"],
      "topics": ["frequency-counting", "anagram-grouping", "pair-finding"],
      "difficulty_range": [1, 3],
      "estimated_hours": 6
    },
    {
      "id": "linked-lists",
      "title": "Linked Lists",
      "description": "Fast/slow pointers, in-place reversal, cycle detection",
      "outcomes": ["pointer-manipulation", "cycle-detection", "list-reversal"],
      "topics": ["two-pointer-technique", "dummy-nodes", "linked-list-operations"],
      "difficulty_range": [2, 4],
      "estimated_hours": 6
    },
    {
      "id": "stacks-queues",
      "title": "Stacks & Queues",
      "description": "Monotonic stacks, parentheses matching, BFS patterns",
      "outcomes": ["stack-operations", "queue-operations", "monotonic-patterns"],
      "topics": ["balanced-parentheses", "next-greater-element", "level-order-traversal"],
      "difficulty_range": [2, 4],
      "estimated_hours": 7
    },
    {
      "id": "trees",
      "title": "Trees",
      "description": "DFS/BFS, recursion patterns, tree traversals",
      "outcomes": ["tree-traversal", "recursion-patterns", "tree-construction"],
      "topics": ["binary-trees", "bst-operations", "tree-serialization"],
      "difficulty_range": [2, 4],
      "estimated_hours": 8
    },
    {
      "id": "graphs",
      "title": "Graphs",
      "description": "BFS/DFS, topological sort, union-find, shortest paths",
      "outcomes": ["graph-traversal", "connectivity", "shortest-path"],
      "topics": ["graph-representation", "cycle-detection", "dijkstra"],
      "difficulty_range": [3, 5],
      "estimated_hours": 10
    },
    {
      "id": "heaps",
      "title": "Heaps",
      "description": "Priority queues, k-way merge, top-k problems",
      "outcomes": ["heap-operations", "priority-queue-usage", "k-problems"],
      "topics": ["min-heap", "max-heap", "heap-sort"],
      "difficulty_range": [2, 4],
      "estimated_hours": 6
    },
    {
      "id": "greedy",
      "title": "Greedy",
      "description": "Greedy choice property, interval scheduling, optimization",
      "outcomes": ["greedy-strategy", "interval-problems", "optimization"],
      "topics": ["activity-selection", "fractional-knapsack", "huffman-coding"],
      "difficulty_range": [3, 5],
      "estimated_hours": 7
    },
    {
      "id": "binary-search",
      "title": "Binary Search",
      "description": "Search space reduction, boundary conditions, answer searching",
      "outcomes": ["binary-search-patterns", "search-space-design", "boundary-handling"],
      "topics": ["sorted-arrays", "rotated-arrays", "search-for-range"],
      "difficulty_range": [2, 4],
      "estimated_hours": 6
    },
    {
      "id": "backtracking",
      "title": "Backtracking",
      "description": "Recursive exploration, constraint satisfaction, pruning",
      "outcomes": ["backtrack-patterns", "state-space-search", "pruning-strategies"],
      "topics": ["permutations", "combinations", "sudoku-solver"],
      "difficulty_range": [3, 5],
      "estimated_hours": 8
    },
    {
      "id": "dynamic-programming",
      "title": "Dynamic Programming",
      "description": "1D/2D DP, knapsack patterns, interval DP",
      "outcomes": ["dp-patterns", "memoization", "state-transitions"],
      "topics": ["fibonacci", "knapsack", "longest-subsequence"],
      "difficulty_range": [3, 5],
      "estimated_hours": 12
    },
    {
      "id": "interview-tools",
      "title": "Interview Tools & Advanced Topics",
      "description": "Mock interviews, system design basics, behavioral prep",
      "outcomes": ["interview-technique", "communication", "time-management"],
      "topics": ["mock-practice", "whiteboard-coding", "system-design-intro"],
      "difficulty_range": [1, 3],
      "estimated_hours": 6
    }
  ]
}
```

### 2. Create Problem Metadata Structure
Create `seed/problems/meta/problem-metadata.json`:
```json
{
  "problems": [
    {
      "id": "meta-two-sum-variant",
      "module": "arrays-strings",
      "topics": ["hash-map", "two-pointers"],
      "difficulty": 1,
      "minutes_target": 15,
      "pillars_focus": ["correctness", "complexity"],
      "company_style": "meta",
      "categories": ["duplicates", "negative-numbers", "lexicographic-order"]
    },
    // ... more problems
  ]
}
```

### 3. Create Seed Problems (Initial 48)
Structure: 4 problems per module for first 12 modules (aligned with LeetCode sequence)
```
seed/problems/meta/
├── introduction/
│   ├── big-o-analysis.yml
│   ├── coding-interview-tips.yml
│   ├── complexity-comparison.yml
│   └── problem-solving-framework.yml
├── arrays-strings/
│   ├── two-sum-variant.yml
│   ├── sliding-window-max.yml
│   ├── longest-substring.yml
│   └── valid-palindrome.yml
├── hashing/
│   ├── group-anagrams.yml
│   ├── first-unique.yml
│   ├── subarray-sum-k.yml
│   └── longest-consecutive.yml
├── linked-lists/
│   ├── reverse-linked-list.yml
│   ├── cycle-detection.yml
│   ├── merge-two-lists.yml
│   └── remove-nth-node.yml
├── stacks-queues/
│   ├── valid-parentheses.yml
│   ├── next-greater-element.yml
│   ├── daily-temperatures.yml
│   └── sliding-window-maximum.yml
├── trees/
│   ├── binary-tree-traversal.yml
│   ├── max-depth.yml
│   ├── path-sum.yml
│   └── validate-bst.yml
├── graphs/
│   ├── number-of-islands.yml
│   ├── clone-graph.yml
│   ├── course-schedule.yml
│   └── shortest-path.yml
├── heaps/
│   ├── kth-largest.yml
│   ├── merge-k-lists.yml
│   ├── top-k-frequent.yml
│   └── median-finder.yml
├── greedy/
│   ├── jump-game.yml
│   ├── meeting-rooms.yml
│   ├── gas-station.yml
│   └── candy-distribution.yml
├── binary-search/
│   ├── search-rotated-array.yml
│   ├── find-minimum.yml
│   ├── search-2d-matrix.yml
│   └── first-bad-version.yml
├── backtracking/
│   ├── generate-parentheses.yml
│   ├── permutations.yml
│   ├── word-search.yml
│   └── sudoku-solver.yml
└── dynamic-programming/
    ├── climbing-stairs.yml
    ├── house-robber.yml
    ├── coin-change.yml
    └── longest-increasing-subsequence.yml
```

### 4. Problem YAML Format
```yaml
# seed/problems/meta/arrays-strings/two-sum-variant.yml
metadata:
  id: meta-two-sum-variant
  subject: coding
  module: arrays-strings
  topics: [hash-map, two-pointers]
  difficulty: 1
  minutes_target: 15
  pillars: [correctness, complexity, code-quality]

statement: |
  Given an integer array `nums` and target `t`, return indices (i,j) 
  where i < j and nums[i] + nums[j] == t. Return lexicographically 
  smallest pair, or (-1,-1) if none exists.

constraints:
  - 2 <= nums.length <= 10^4
  - -10^9 <= nums[i] <= 10^9
  - -10^9 <= t <= 10^9

examples:
  - input: {nums: [2,7,11,15], t: 9}
    output: [0,1]
    explanation: nums[0] + nums[1] = 2 + 7 = 9
  - input: {nums: [3,3], t: 6}
    output: [0,1]
    explanation: nums[0] + nums[1] = 3 + 3 = 6

test_harness:
  languages: [python, javascript]
  python_signature: "def twoSum(nums: List[int], t: int) -> List[int]:"
  javascript_signature: "function twoSum(nums, t)"

visible_tests:
  - {input: {nums: [2,7,11,15], t: 9}, expect: [0,1]}
  - {input: {nums: [3,3], t: 6}, expect: [0,1]}
  - {input: {nums: [1,2,3], t: 7}, expect: [-1,-1]}

hidden_tests:
  categories:
    - duplicates: "Multiple valid pairs"
    - negatives: "Negative numbers and targets"
    - large_n: "n = 10^4 performance"
    - no_solution: "No valid pair exists"
    - lexicographic: "Ensure smallest indices returned"

hints:
  L1: "What data structure allows O(1) complement lookup?"
  L2: "As you iterate, store seen values with their indices"
  L3: "Check if (t - current) exists in your hash map"

solution_notes: |
  Use hash map to store {value: index}. For each element,
  check if complement exists. O(n) time, O(n) space.
```

### 5. Seeding Script
Create `scripts/seed_meta_track.py`:
```python
import json
import yaml
from pathlib import Path
from src.co.db.base import SessionLocal
from src.co.db.models import Track
from src.co.clients.problem_bank import ProblemBankClient

async def seed_meta_track():
    # Load track definition
    with open("seed/tracks/meta-coding-interview.json") as f:
        track_data = json.load(f)
    
    # Create track in database
    db = SessionLocal()
    try:
        track = Track(**track_data)
        db.add(track)
        db.commit()
        print(f"Created track: {track.slug}")
    finally:
        db.close()
    
    # Upload problems to Problem Bank
    problem_bank = ProblemBankClient()
    problems_dir = Path("seed/problems/meta")
    
    for module_dir in problems_dir.iterdir():
        if module_dir.is_dir():
            for problem_file in module_dir.glob("*.yml"):
                with open(problem_file) as f:
                    problem = yaml.safe_load(f)
                
                # Transform to Problem Bank format
                await problem_bank.create_problem({
                    "id": problem["metadata"]["id"],
                    "subject": problem["metadata"]["subject"],
                    "statement": problem["statement"],
                    "visible_tests": problem["visible_tests"],
                    "hidden_bundle": {
                        "tests": problem["hidden_tests"],
                        "harness": problem["test_harness"]
                    },
                    "metadata": problem["metadata"]
                })
                print(f"Created problem: {problem['metadata']['id']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_meta_track())
```

### 6. Validation & Quality Checks
Create `scripts/validate_meta_content.py`:
```python
def validate_problem(problem_data):
    """Validate problem structure and content"""
    checks = []
    
    # Required fields
    required = ["metadata", "statement", "examples", "visible_tests", "hidden_tests"]
    for field in required:
        if field not in problem_data:
            checks.append(f"Missing required field: {field}")
    
    # Difficulty in range
    if not 1 <= problem_data["metadata"]["difficulty"] <= 5:
        checks.append("Difficulty must be 1-5")
    
    # Time target reasonable
    if not 5 <= problem_data["metadata"]["minutes_target"] <= 45:
        checks.append("Time target should be 5-45 minutes")
    
    # Has test categories
    if len(problem_data["hidden_tests"]["categories"]) < 3:
        checks.append("Should have at least 3 test categories")
    
    return checks
```

## Testing Plan

1. **Unit Tests**
   - Track creation and retrieval
   - Module structure validation
   - Problem metadata parsing

2. **Integration Tests**
   - Seed script execution
   - Problem Bank synchronization
   - Track API endpoints

3. **Content Validation**
   - All problems compile and run
   - Test cases are correct
   - Hints are progressive and helpful

## Success Criteria

- [ ] Track created with 13 modules (aligned with LeetCode curriculum)
- [ ] 48 seed problems created (4 per module for all 12 modules)
- [ ] All problems have complete metadata including pillars
- [ ] Problems cover difficulty range 1-5 (expanded range)
- [ ] Test harnesses work for Python and JavaScript
- [ ] Track accessible via `/v1/tracks?subject=coding&label=company:meta`
- [ ] Module sequencing matches industry-standard learning progression
- [ ] Introduction module provides foundational concepts
- [ ] Backtracking module included as separate focus area

## Future Enhancements

1. Add remaining 4 modules with problems
2. Increase difficulty range to include 4-5
3. Add problem variants and parameterization
4. Create mock interview sequences
5. Add video explanations and solution walkthroughs

## Notes

- Start with well-known patterns, but ensure problems are sufficiently different from public versions
- Each problem should map clearly to Meta interview signals
- Focus on clarity and real-world applicability
- Ensure progressive difficulty within each module