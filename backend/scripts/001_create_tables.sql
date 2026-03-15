-- ============================================================================
-- PolyMolt — Supabase (PostgreSQL) schema
-- Run this in the Supabase SQL Editor to create all required tables.
-- ============================================================================

-- questions
CREATE TABLE IF NOT EXISTS questions (
    id         BIGSERIAL    PRIMARY KEY,
    question_text TEXT      NOT NULL,
    location   TEXT         NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- stakeholder_responses
CREATE TABLE IF NOT EXISTS stakeholder_responses (
    id               BIGSERIAL    PRIMARY KEY,
    question_id      BIGINT       NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    phase            TEXT         NOT NULL DEFAULT 'legacy',
    stakeholder_id   TEXT         NOT NULL,
    stakeholder_role TEXT         NOT NULL,
    ai_agent_id      TEXT         NOT NULL,
    answer           TEXT         NOT NULL,
    confidence       NUMERIC(5,2),
    reasoning        TEXT,
    raw_payload      JSONB,
    created_at       TIMESTAMPTZ  DEFAULT NOW()
);

-- orchestrate_runs
CREATE TABLE IF NOT EXISTS orchestrate_runs (
    id                  BIGSERIAL    PRIMARY KEY,
    question_id         BIGINT       NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    topic_reasoning     TEXT,
    deep_analysis       TEXT,
    assigned_agent_id   TEXT,
    expertise_rationale TEXT,
    rag_context         TEXT,
    context_for_agents  TEXT,
    year                INTEGER,
    model               TEXT,
    full_response       JSONB,
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_stakeholder_responses_question_id
    ON stakeholder_responses(question_id);

CREATE INDEX IF NOT EXISTS idx_orchestrate_runs_question_id
    ON orchestrate_runs(question_id);

CREATE INDEX IF NOT EXISTS idx_questions_created_at
    ON questions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_questions_location
    ON questions(location);

-- View used by list_recent_questions (LEFT JOIN + GROUP BY in one query)
CREATE OR REPLACE VIEW questions_with_counts AS
SELECT
    q.id,
    q.question_text,
    q.location,
    q.created_at,
    COALESCE(SUM(CASE WHEN r.answer = 'YES' THEN 1 ELSE 0 END), 0)::INT AS yes_count,
    COALESCE(SUM(CASE WHEN r.answer = 'NO'  THEN 1 ELSE 0 END), 0)::INT AS no_count
FROM questions q
LEFT JOIN stakeholder_responses r ON r.question_id = q.id
GROUP BY q.id, q.question_text, q.location, q.created_at;
