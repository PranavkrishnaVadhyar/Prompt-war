-- Explicit migration for the four-model judging panel. No provider calls are made by SQL.
BEGIN;
SET LOCAL search_path TO prompt_war;
CREATE TABLE IF NOT EXISTS ai_panels (
    round_id uuid PRIMARY KEY REFERENCES rounds(id),
    roster jsonb NOT NULL CHECK(jsonb_typeof(roster)='array' AND jsonb_array_length(roster)=4),
    rubric_version text NOT NULL DEFAULT 'four-model-v1',
    created_by uuid NOT NULL REFERENCES members(user_id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ai_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id uuid NOT NULL REFERENCES submissions(id),
    round_id uuid NOT NULL REFERENCES rounds(id),
    status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','complete','incomplete','failed','superseded')),
    snapshot jsonb NOT NULL,
    model_results jsonb NOT NULL DEFAULT '{}',
    aggregate jsonb,
    error text,
    requested_by uuid NOT NULL REFERENCES members(user_id),
    retry_of uuid REFERENCES ai_runs(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    lease_until timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS ai_runs_one_active ON ai_runs(submission_id) WHERE status IN ('queued','running');
CREATE INDEX IF NOT EXISTS ai_runs_queue ON ai_runs(status,created_at);
CREATE INDEX IF NOT EXISTS ai_runs_submission ON ai_runs(submission_id,created_at DESC);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS ai_run_id uuid REFERENCES ai_runs(id);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS manual_override boolean NOT NULL DEFAULT false;
ALTER TABLE ai_panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ai_panels,ai_runs FROM PUBLIC,anon,authenticated;
COMMIT;

