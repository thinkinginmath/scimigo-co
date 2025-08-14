# Meta Coding Interview Prep — Curriculum Design within CO (v0.1)

**Goal.** Define how the Curriculum Orchestrator (CO) represents, serves, and adapts a company‑style interview curriculum (e.g., Meta), including problem sourcing (LLM‑assisted + curated), evaluation, and coaching.

---

## 1) Curriculum Shape (Tracks → Modules → Units → Problems)

**Track:** `coding-interview-meta`

* **Signal pillars** (scorecards tracked across problems):

  1. Problem understanding & examples
  2. Algorithmic correctness
  3. Time/space complexity
  4. Code quality & test hygiene
  5. Communication & iteration

**Modules (LeetCode-aligned progression)**

0. **Introduction** — Big O analysis, problem-solving framework, interview basics
1. **Arrays & Strings** — two pointers, sliding window, frequency maps
2. **Hashing** — hash maps, hash sets, frequency counting
3. **Linked Lists** — fast/slow pointers, in‑place reverse, cycles
4. **Stacks & Queues** — monotonic stacks, parentheses, BFS patterns
5. **Trees** — DFS/BFS, recursion patterns, tree traversals
6. **Graphs** — BFS/DFS, topological sort, union‑find, shortest paths
7. **Heaps** — priority queues, k-way merge, top-k problems
8. **Greedy** — greedy choice property, interval scheduling, optimization
9. **Binary Search** — search space reduction, boundary conditions
10. **Backtracking** — recursive exploration, constraint satisfaction, pruning
11. **Dynamic Programming** — 1D/2D DP, knapsack/partition, interval DP
12. **Interview Tools** — mock interviews, system design basics, behavioral prep

Each module contains **Units** (e.g., `sliding-window-basics`, `variable-size-window`, `at-most-k`) that map to **topics** for personalization.

---

## 2) Problem Sourcing Strategy

### A. Curated (primary)

* Start with vetted problems from **licensed or original** content. For public‑domain‑like ideas, **rephrase** and **parameterize** to avoid 1:1 clones.
* Maintain provenance (`content_provenance` table) and SPDX‑style licensing.

### B. LLM‑Assisted Authoring (secondary, controlled)

Use LLMs to **propose variants** and **generate scaffolding**, not as the sole source of truth.

**Pipeline**

1. **Spec → Draft**: Author writes an **intent spec** (pattern, constraints, target pitfalls, complexity band). LLM generates 2–3 variants and **starter tests**.
2. **Auto‑QA**:

   * Duplicate detector (embedding + near‑dup search vs. existing bank)
   * Solvability checker (executor runs reference solver; time bounds)
   * Hidden‑case fuzzer (random/adversarial generators)
   * Leak scan (avoid copyrighted titles/wording; remove known identifiers)
3. **Human review**: ensure novelty, clarity, correct difficulty and company style.
4. **Finalize**: lock **hidden tests** server‑side; store solution notes & hint ladders.

**When to rely more on LLMs**: producing **parameterized families** around a pattern (e.g., sliding window) and generating **explanatory rationales** / wrong‑answer analyses.

---

## 3) Problem Specification (authoring format)

`problems/two-sum-variant-A.md`

```markdown
---
id: meta-two-sum-var-a
subject: coding
module: arrays-strings
topics: [hash-map, two-sum]
difficulty: 1
pillars: [correctness, complexity, code-quality]
minutes_target: 15
company_style: meta
---
Given an integer array `nums` and a target `t`, return the indices `(i,j)` with `i < j` such that `nums[i] + nums[j] == t`. If multiple pairs exist, return the lexicographically smallest pair. If none, return `(-1,-1)`.
```

`problems/two-sum-variant-A.tests.yml`

```yaml
harness:
  language: python
  signature: "def solve(nums: List[int], t: int) -> Tuple[int,int]:"
visible:
  - input: { nums: [2,7,11,15], t: 9 }
    expect: [0,1]
  - input: { nums: [3,3], t: 6 }
    expect: [0,1]
hidden:
  generator:
    seeds: [1,2,3]
    cases:
      - kind: duplicates
      - kind: negatives
      - kind: large-n ~ 1e5 bounded range
categories:
  - duplicates
  - negatives
  - stability-lexicographic
metrics:
  time_limit_ms: 200
  mem_limit_mb: 128
```

**Coach content** (`hints/two-sum-variant-A.yml`)

```yaml
hints:
  L1: "What structure lets you check a complement in O(1)?"
  L2: "Iterate `i`, compute `t-nums[i]`, check map of prior indices."
  L3: "Maintain first occurrence index to keep lexicographic order."
explanations:
  pitfalls:
    - "Not constraining to i<j or lexicographic order."
  complexity: "O(n) time, O(n) space"
```

---

## 4) Evaluation & Signal Extraction (CO ↔ Eval Service)

**Execution harness** (visible + hidden) via `scimigo-eval-services`:

* **Verdict**: passed/failed/timeout/error
* **Categories**: failure labels (e.g., `off-by-one`, `overflow`, `lexicographic`)
* **Performance**: `exec_ms`, optional asymptotic **estimator** (LLM+static sampling)
* **Quality**: lint checks (basic), test hygiene (did the candidate add tests if allowed?)

**LLM‑based critique** (optional, post‑eval):

* Summarize **approach**, identify **trade‑offs**, propose **micro‑improvements**.
* Enforce safe coaching: avoid revealing full solutions at L1/L2.

---

## 5) Adaptive Policy (per learner)

Maintain a **mastery vector** over topics + a **pace profile** (time vs. target).

**Target success band**: 60–75% after hints L1–L2 within target minutes.

**Selection score**

```
score(p) = w1*weakness(user, p.topics)
         + w2*difficulty_match(user, p.difficulty)
         + w3*novelty(user, p.id)
         + w4*coverage_gap(user, pillars)
         + w5*time_fit(user, p.minutes_target)
```

**Guardrails**: no >2 consecutive fails; difficulty jump ≤ +1; inject due **spaced review** items (`review_queue`).

**Updates**

* **Mastery↑** for first‑try passes within time; smaller ↑ with hints; **↓** on failures/slow solves.
* Track **hint reliance** and **category heatmap** per topic to drive remediation drills.

---

## 6) Session UX (what CO orchestrates)

1. **Warm‑up** (3–5 min easy) → calibrate pace & anxiety.
2. **Core problem** (15–25 min):

   * IDE pane with visible tests; run locally
   * Submit → server evaluates hidden tests; returns categories & metrics
   * Tutor hints L1→L3 gated by attempt count/time
3. **Retro** (2–3 min):

   * Complexity statement; approach summary
   * Micro‑drill offer based on failures (e.g., “duplicates in hash map”)
4. **Queue update**: mastery, spaced review scheduling

**Mock interview mode**: timer + proctor; coaching muted until after the interview; final report with pillar scores and next plan.

---

## 7) “Meta Style” Calibration

* **Prompting & UI copy** emulate Meta tone: emphasize clarity, example‑driven thinking, and trade‑off discussion.
* **Constraints**: prefer O(n) / O(log n) solutions, in‑place where possible; enforce bounds (n up to 1e5–1e6 depending on pattern).
* **Signals** include: clarifying questions, small examples, stepwise refinement, and test‑driven iteration.

---

## 8) LLM Use: Where & How (safely)

**Good uses**

* Variant generation from a human‑written spec
* Wrong‑answer rationales; distractor MC options
* Hint ladder polish and Socratic prompts
* Post‑eval critique summaries

**Avoid**

* Directly trusting LLM‑invented tests/solutions without auto‑QA + human review
* Mirroring named problems/titles from paid sites

**Auto‑QA gates** (required):

* Duplicate/near‑dup detector
* Reference solver + stress tests
* Performance budget check
* Leakage scan (phrase‑level + embedding)

---

## 9) Data & APIs (CO side)

* Track labeled `company:meta` and `interview:coding` for discoverability.
* Problems carry `pillars[]`, `topics[]`, `difficulty`, `minutes_target`.
* Submissions return: `{status, visible, hidden{categories}, exec_ms, complexity_estimate?, code_quality?}`.
* Tutor: `hint_level` gates; L3 reveal requires either failed attempt count or time threshold.

---

## 10) Telemetry & Benchmarks

* **KPIs**: time‑to‑first‑AC, pass‑rate in target band, hint ladder efficiency, pillar score lift, mock→real success correlation.
* **Content health**: item difficulty (Elo/IRT), discrimination, drift; retire or re‑seed items as needed.

---

## 11) Rollout Plan (Meta Track)

1. **Seed set**: 13 modules × 4 problems (52 total) across difficulty 1–5, aligned with LeetCode curriculum
2. **Authoring**: human‑spec → LLM variants → auto‑QA → review
3. **Pilot**: 50 users; tune time budgets and hint policies based on LeetCode best practices
4. **Scale**: expand to 8-10 problems per module, add mock interview mode, and micro‑drills per category

---

## 12) Example Adaptive Step (pseudo)

```python
candidates = catalog.filter(subject='coding', labels=['company:meta'])
for p in candidates:
    s = w1*weakness(user, p.topics) + w2*difficulty_match(user, p.difficulty) \
        + w3*novelty(user,p.id) + w4*coverage_gap(user,pillars=p.pillars) \
        + w5*time_fit(user,p.minutes_target)
select argmax s with guardrails
```

---

## 13) Integrity & IP

* Keep **hidden tests** internal; only categories leave the server.
* Parameterize and rename problems; avoid protected identifiers/titles.
* Watermark content with internal IDs and store provenance.

---

## 14) Open Questions

* How many “explain aloud” prompts should we inject before the timer starts in mock mode?
* Do we want rubric‑scored code style (lint) to affect mastery or just feedback?
* Should module unlocks depend on pillar scores or topic mastery only?

