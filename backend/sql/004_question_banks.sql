-- Schema only: question rows are loaded separately by scripts.import_questions.
BEGIN;
SET LOCAL search_path TO prompt_war;
CREATE TABLE IF NOT EXISTS question_bank (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key text NOT NULL UNIQUE,
    kind text NOT NULL CHECK(kind IN ('fix','word_ban','recreate')),
    original_round integer NOT NULL CHECK(original_round BETWEEN 1 AND 3),
    source_number integer NOT NULL CHECK(source_number>0),
    source_file text NOT NULL,
    title text NOT NULL,
    task text NOT NULL CHECK(length(task)>0),
    flawed_output text NOT NULL DEFAULT '',
    expected_output text NOT NULL DEFAULT '',
    banned_words jsonb NOT NULL DEFAULT '[]',
    banned_word_variants jsonb NOT NULL DEFAULT '{}',
    participant_rules text NOT NULL,
    judge_notes text NOT NULL DEFAULT '',
    content_hash char(64) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(kind,source_number)
);
CREATE INDEX IF NOT EXISTS question_bank_pool ON question_bank(kind,active);
CREATE TABLE IF NOT EXISTS question_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id uuid NOT NULL,
    team_id uuid NOT NULL,
    question_id uuid NOT NULL REFERENCES question_bank(id),
    snapshot jsonb NOT NULL,
    assigned_by uuid NOT NULL REFERENCES members(user_id),
    assigned_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(round_id,team_id),
    UNIQUE(id,round_id,team_id),
    FOREIGN KEY(round_id,team_id) REFERENCES entries(round_id,team_id)
);
CREATE INDEX IF NOT EXISTS question_assignment_question ON question_assignments(question_id);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS assignment_id uuid;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='submission_assignment_matches_team' AND conrelid='prompt_war.submissions'::regclass) THEN
        ALTER TABLE submissions ADD CONSTRAINT submission_assignment_matches_team
            FOREIGN KEY(assignment_id,round_id,team_id) REFERENCES question_assignments(id,round_id,team_id);
    END IF;
END $$;
ALTER TABLE question_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_assignments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON question_bank,question_assignments FROM PUBLIC,anon,authenticated;
COMMIT;
