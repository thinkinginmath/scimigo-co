Here’s the 10,000‑ft view for your coding agent. Think of the **Curriculum Orchestrator (CO)** as the brains that decide *what the learner should do next* and *how to run a learning session*, while reusing existing services for problems, evaluation, and tutoring.

# What CO owns vs. what it calls

* **CO (new service)**

  * Tracks/curricula: exposes lists of tracks/modules/units for each domain/course.
  * Sessions: creates/updates practice/mock/track sessions and keeps simple session state.
  * Personalization: picks next problems (mastery, pacing, spaced review), maps failures → remediation.
  * Orchestration: when a submission lands, CO calls the right evaluator and shapes the tutor turn (hint levels, context).
  * Public surface you’ll hit from the frontend: `/v1/tracks`, `/v1/sessions`, `/v1/submissions`, `/v1/tutor/messages` (same unified shapes you already use).

* **Problem Bank (existing)**

  * Source of truth for problem metadata + **visible tests** (public) and **hidden bundles** (internal‑only). CO fetches hidden bundles server‑side; the UI never sees them.

* **Eval Service (existing sandbox)**

  * Runs code securely with harness/limits, returns pass/fail, timing, and CO’s failure categories; used for coding problems and (via math adapters) for math checks as needed.

* **Tutor Orchestrator / LLM tools (existing)**

  * CO initiates tutor turns and streams hints/explanations over SSE using the platform’s normalized events (`message.start|delta|end`, etc.).

# Request flows your agent will implement

1. **Browse a track**

   * `GET /v1/tracks?subject=coding|math` → show available tracks/modules (CO).

2. **Start a session**

   * `POST /v1/sessions { subject, mode, track_id? | problem_id? }` → CO returns session and the first problem to work on (frontend then loads the problem content).

3. **Submit an attempt (subject‑agnostic)**

   * `POST /v1/submissions` with tagged payload:

     * Coding: `{ session_id, problem_id, subject:"coding", payload:{ language, code } }`
     * Math: `{ session_id, problem_id, subject:"math", payload:{ steps? , expression? } }`
   * CO internally pulls **hidden tests** from Problem Bank and calls Eval. Response returns visible details and hidden aggregates/categories; **hidden tests never leave trusted services**.

4. **Ask the tutor for help**

   * `POST /v1/tutor/messages { session_id, problem_id, hint_level (1–3), last_eval }` → you’ll receive an SSE URL/token or stream events directly with the normalized event model (`message.start/delta/end`, optional `tool.suggested_tests`).

# Who persists what

* **CO DB**: sessions, submissions metadata, mastery, spaced‑review queue, rubric links (so it can recommend and resume work quickly).
* **Problem Bank**: problem text, visible tests, internal hidden bundles.
* **Eval Service**: stateless code runs; returns results to CO.
* **Tutor/LLM**: stateless chat turns; CO supplies context (problem, user attempt summary, failure categories).

# Frontend contract (what your agent should assume)

* **Base**: `https://api.scimigo.com/v1` with Bearer JWT, JSON everywhere, ISO‑8601 timestamps, cursor pagination.
* **Core endpoints**: `/tracks`, `/sessions`, `/submissions`, `/tutor/messages`, `/tutor/stream` (SSE).
* **Rate limits**: \~60 req/min/user; **max 2 concurrent tutor SSE streams**—your client should back off and reuse a single stream per tab.
* **Security**: Never expect hidden tests client‑side; only show visible tests. Errors come in a unified `{ error: {code, message, details} }` shape.

# Mental model (ASCII)

```
[coding.scimigo.com UI]
      │  (JWT)
      ▼
[ CO API — tracks/sessions/submissions/tutor ]  ◀─── mastery, review, rubrics
   │         │                 │
   │         │                 └── calls → [ Tutor/LLM SSE ]  (hints/explanations):contentReference[oaicite:12]{index=12}
   │         └── calls → [ Eval Service ]      (run code / math checks):contentReference[oaicite:13]{index=13}
   └── pulls → [ Problem Bank ]  (visible tests to UI; hidden bundles internal):contentReference[oaicite:14]{index=14}
```

# Do / Don’t for your agent

* **Do**: treat CO as the single public gateway for learning flows (tracks, sessions, submissions, tutor). It abstracts problem selection, evaluation routing, and tutoring so the UI stays thin.
* **Do**: stream tutor messages via the normalized SSE protocol and render `message.delta` progressively (markdown/KaTeX friendly), exactly as the spec describes.
* **Don’t**: request or cache hidden tests; CO will never expose them by design.
* **Don’t**: call the Eval Service directly from the browser; always submit via CO so it can attach harnesses, apply limits, and classify failures.

If you want, I can give your agent example requests/responses for each endpoint (copy‑pasteable fetch/axios snippets) following the v1.1 shapes.

