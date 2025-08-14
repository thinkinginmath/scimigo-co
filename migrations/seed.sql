-- Seed SQL for Curriculum Orchestrator Database
-- Based on design.md specifications

-- Enable UUID extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tracks (published by CourseKit or generic tracks)
CREATE TABLE IF NOT EXISTS tracks (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         TEXT UNIQUE NOT NULL,
  subject      TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  title        TEXT NOT NULL,
  labels       JSONB NOT NULL DEFAULT '[]',  -- e.g., ["course:UIUC-MATH-241"]
  modules      JSONB NOT NULL DEFAULT '[]',  -- denormalized module index
  version      TEXT NOT NULL DEFAULT 'v1',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL,
  subject         TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  mode            TEXT NOT NULL CHECK (mode IN ('practice','mock','track')),
  track_id        UUID REFERENCES tracks(id),
  problem_id      TEXT,
  status          TEXT NOT NULL DEFAULT 'active', -- active|completed|abandoned
  last_hint_level INT  NOT NULL DEFAULT 0,
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_track ON sessions(track_id);

-- Submissions
CREATE TABLE IF NOT EXISTS submissions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id        UUID NOT NULL,
  problem_id     TEXT NOT NULL,
  subject        TEXT NOT NULL CHECK (subject IN ('coding','math','systems')),
  language       TEXT,                 -- for coding
  status         TEXT NOT NULL CHECK (status IN ('passed','failed','timeout','error')),
  visible_passed INT  NOT NULL DEFAULT 0,
  visible_total  INT  NOT NULL DEFAULT 0,
  hidden_passed  INT  NOT NULL DEFAULT 0,
  hidden_total   INT  NOT NULL DEFAULT 0,
  categories     JSONB NOT NULL DEFAULT '[]',  -- failure categories
  exec_ms        INT  NOT NULL DEFAULT 0,
  payload_sha256 TEXT,                 -- hash of user code or math content
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_submissions_session ON submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);

-- Mastery (topic- and outcome-based)
CREATE TABLE IF NOT EXISTS mastery (
  user_id     UUID NOT NULL,
  key_type    TEXT NOT NULL CHECK (key_type IN ('topic','outcome')),
  key_id      TEXT NOT NULL,        -- e.g., topic 'sliding-window' or outcome 'LO1'
  score       INT  NOT NULL CHECK (score BETWEEN 0 AND 100),
  ema         REAL NOT NULL DEFAULT 0.0,       -- optional EMA for stability
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, key_type, key_id)
);
CREATE INDEX IF NOT EXISTS idx_mastery_user ON mastery(user_id);

-- Review queue (spaced repetition)
CREATE TABLE IF NOT EXISTS review_queue (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  problem_id  TEXT NOT NULL,
  reason      TEXT NOT NULL,          -- fail|slow|heavy-hint|mock-gap
  next_due_at TIMESTAMPTZ NOT NULL,
  bucket      INT NOT NULL DEFAULT 0, -- 0,1,2,3 for 1d/3d/7d/21d
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, problem_id)
);
CREATE INDEX IF NOT EXISTS idx_review_due ON review_queue(next_due_at);

-- Rubrics (LLM-graded, for systems/math proof-sketch)
CREATE TABLE IF NOT EXISTS rubrics (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain      TEXT NOT NULL,          -- 'systems'|'math'
  title       TEXT NOT NULL,
  dimensions  JSONB NOT NULL,         -- [{id, name, scale:0..3, desc}]
  metadata    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rubric scores per submission (optional)
CREATE TABLE IF NOT EXISTS rubric_scores (
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  rubric_id     UUID NOT NULL REFERENCES rubrics(id),
  scores        JSONB NOT NULL,       -- {dim_id: score}
  feedback      JSONB NOT NULL,       -- structured gap statements
  PRIMARY KEY (submission_id, rubric_id)
);

-- Basic triggers
CREATE OR REPLACE FUNCTION touch_sessions_updated()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sessions_touch ON sessions;
CREATE TRIGGER trg_sessions_touch
BEFORE UPDATE ON sessions
FOR EACH ROW EXECUTE PROCEDURE touch_sessions_updated();

-- Insert sample data

-- Sample tracks
INSERT INTO tracks (slug, subject, title, labels, modules) VALUES
  ('intro-python', 'coding', 'Introduction to Python', 
   '["beginner", "python"]',
   '[{"id": "m1", "title": "Python Basics", "outcomes": ["LO1", "LO2"]}, 
     {"id": "m2", "title": "Data Structures", "outcomes": ["LO3", "LO4"]}]'),
  
  ('data-structures', 'coding', 'Data Structures and Algorithms',
   '["intermediate", "algorithms"]',
   '[{"id": "m1", "title": "Arrays and Strings", "outcomes": ["DS1", "DS2"]},
     {"id": "m2", "title": "Trees and Graphs", "outcomes": ["DS3", "DS4"]}]'),
  
  ('calc-1', 'math', 'Calculus I',
   '["course:MATH-241", "calculus"]',
   '[{"id": "m1", "title": "Limits", "outcomes": ["C1.1", "C1.2"]},
     {"id": "m2", "title": "Derivatives", "outcomes": ["C1.3", "C1.4"]}]'),
  
  ('systems-design', 'systems', 'System Design Fundamentals',
   '["advanced", "architecture"]',
   '[{"id": "m1", "title": "Scalability", "outcomes": ["SD1", "SD2"]},
     {"id": "m2", "title": "Reliability", "outcomes": ["SD3", "SD4"]}]')
ON CONFLICT (slug) DO NOTHING;

-- Sample rubrics
INSERT INTO rubrics (domain, title, dimensions) VALUES
  ('systems', 'System Design Rubric',
   '[{"id": "scalability", "name": "Scalability", "scale": 3, "desc": "Ability to handle growth"},
     {"id": "reliability", "name": "Reliability", "scale": 3, "desc": "System fault tolerance"},
     {"id": "performance", "name": "Performance", "scale": 3, "desc": "Response time and throughput"}]'),
  
  ('math', 'Mathematical Proof Rubric',
   '[{"id": "logic", "name": "Logical Flow", "scale": 3, "desc": "Coherence of proof steps"},
     {"id": "rigor", "name": "Mathematical Rigor", "scale": 3, "desc": "Precision and correctness"},
     {"id": "completeness", "name": "Completeness", "scale": 3, "desc": "All cases covered"}]')
ON CONFLICT DO NOTHING;