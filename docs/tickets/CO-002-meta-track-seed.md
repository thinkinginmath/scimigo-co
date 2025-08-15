
# CO-002: Meta Coding Interview Track — Seed Data & Structure

**Priority**: P0 – Critical
**Type**: Feature
**Component**: Content/Curriculum
**Estimated Effort**: 3-4 hours
**Dependencies**: CO-001 (Schema Alignment)

## Objective

Import the existing Meta coding interview prep track from SciMigo Problem Bank into the Curriculum Orchestrator, creating the track structure and module references needed for the study path system.

---

## Current State

✅ **Problem Bank Ready**: 
- 2412 problems in `/scimigo-problem-bank/public-datasets/` (HumanEval, MBPP, Apps, etc.)
- 84 Meta-specific problems in `/scimigo-problem-bank/meta-problems/`
- **Total**: ~2500 problems available for Meta interview prep

✅ **Track Defined**: Complete track structure with 14 modules at `/scimigo-problem-bank/meta-problems/seed/tracks/meta-coding-interview.json`

**Missing**: CO track record and problem ID mappings from both sources

---

## Problem Storage Strategy

All **problem statements**, **visible tests**, and **hidden bundles** already exist in the **Problem Bank** service.

The **Curriculum Orchestrator (CO)** needs to:
* Import track structure from Problem Bank
* Store track metadata and module organization in CO database
* Reference Problem Bank IDs only (no duplicate problem storage)
* Enable study path system to query problems by module and difficulty

---

## Track Structure (From Problem Bank)

```json
{
  "slug": "coding-interview-meta",
  "subject": "coding", 
  "title": "Meta Coding Interview Preparation",
  "modules": [
    "introduction", "arrays-strings", "hashing", "linked-lists",
    "stacks-queues", "trees-graphs", "sorting-searching", "heaps", 
    "greedy", "dynamic-programming", "recursion-backtracking",
    "bit-manipulation", "math-geometry", "design"
  ]
}
```

14 modules with difficulty ranges 1-5, 136 estimated hours total.

---

## Implementation Steps

1. **Create Track Import Script** — `scripts/import_meta_track.py`
2. **Import Track Metadata** — Fetch track definition from Problem Bank API
3. **Create CO Track Record** — Insert into `tracks` table with proper module structure
4. **Map Problem Sources** — 
   - Meta-specific problems from `/meta-problems/` (84 problems)
   - Public dataset problems from `/public-datasets/` (2412 problems)  
   - Classify public problems by Meta interview topics (arrays-strings, trees-graphs, etc.)
5. **Create Module Mappings** — Map problems to modules based on topics and difficulty
6. **Validate Import** — Ensure all modules have sufficient problems across difficulty levels

---

## Success Criteria

* [ ] Meta track imported into CO `tracks` table with slug "coding-interview-meta"
* [ ] All 14 modules properly structured with topic tags and difficulty ranges
* [ ] Problem Bank integration working (CO can fetch problems by module)
* [ ] Track accessible via `/v1/tracks/coding-interview-meta` endpoint
* [ ] Ready for CO-003B study path implementation

